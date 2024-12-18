from __future__ import absolute_import, unicode_literals
from celery import task
from django.core.mail import send_mail

from django.conf import settings

import requests

from .models import Setting


@task()
def smart_home_manager():
    # код для проверки условий

    # подготовка запроса на данные, запрос и продобработка данных
    headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
    # print("task test-------------------------------")
    try:
        get_response = requests.get(settings.SMART_HOME_API_URL, headers=headers)
        if get_response.status_code != 200:
            return None
        response_json = get_response.json()
        if response_json["status"] != 'ok':
            return None
    # except ConnectionError:
    except (requests.exceptions.RequestException, ConnectionError):
        return None

    controllers = {item['name']: item["value"] for item in response_json['data']}
    # print("controllers\n", controllers)

    # initialization
    set_data = dict()
    events_for_email = []

    def set_controller(set_name, set_value):
        if set_name == "boiler":
            if controllers["cold_water"] is False:
                set_value = False
        if set_name == "washing_machine":
            if controllers["cold_water"] is False:
                set_value = "off"
        if set_name == "curtains":
            if set_value == "slightly_open":
                return None
        if set_name in ["air_conditioner", "bedroom_light", "bathroom_light", "boiler"]:
            if controllers["smoke_detector"] is True:
                set_value = False
        if set_name == "washing_machine":
            if controllers["smoke_detector"] is True:
                set_value = "off"

        if controllers.get(set_name, "not 'name'") != set_value:
            set_data[set_name] = set_value

    # 1
    if controllers["leak_detector"]:
        events_for_email.append({"leak_detector": True})
        set_controller("cold_water", False)
        set_controller("hot_water", False)

    # 2
    if not controllers["cold_water"]:
        set_controller("boiler", False)
        set_controller("washing_machine", "off")

    # 3
    hot_water_target_temperature, created = \
        Setting.objects.get_or_create(controller_name="hot_water_target_temperature")
    # print("---------------------------hot_water_target_temperature.value", hot_water_target_temperature.value)

    if controllers["boiler_temperature"] < hot_water_target_temperature.value * 0.9:
        if not controllers["smoke_detector"]:
            set_controller("boiler", True)

    # 3.1
    # print('controllers["boiler_temperature"]', controllers["boiler_temperature"])
    # print("hot_water_target_temperature.value", hot_water_target_temperature.value)
    # print("hot_water_target_temperature.value * 1.1", hot_water_target_temperature.value * 1.1)
    if controllers["boiler_temperature"] >= hot_water_target_temperature.value * 1.1:
        set_controller("boiler", False)

    # 4
    # реализовано в set_controller()

    # 5
    if controllers["outdoor_light"] < 50:
        if not controllers["bedroom_light"]:
            set_controller("curtains", "open")

    if (controllers["outdoor_light"] > 50) or controllers["bedroom_light"]:
        set_controller("curtains", "close")

    # 6
    if controllers["smoke_detector"]:
        list_for_off = [("air_conditioner", False), ("bedroom_light", False), ("bathroom_light", False),
                        ("boiler", False), ("washing_machine", "off")]
        for name, value in list_for_off:
            set_controller(name, value)

    # 7
    bedroom_target_temperature, created = Setting.objects.get_or_create(controller_name="bedroom_target_temperature")
    if controllers["bedroom_temperature"] > bedroom_target_temperature.value * 1.1:
        if not controllers["smoke_detector"]:
            set_controller("air_conditioner", True)
    # 7.1
    if controllers["bedroom_temperature"] < bedroom_target_temperature.value * 0.9:
        set_controller("air_conditioner", False)

    post_data = {"controllers": [{"name": pair[0], "value": pair[1]} for pair in set_data.items()]}
    print("post_data", post_data)

    if post_data["controllers"]:
        try:
            post_response = requests.post(settings.SMART_HOME_API_URL, headers=headers, json=post_data)
            print('post_response.json()["status"]', post_response.json()["status"])
            print("post_response.status_code", post_response.status_code)
            if post_response.status_code != 200:
                return None
            post_response_json = post_response.json()
            if post_response_json["status"] != 'ok':
                return None

        except (requests.exceptions.RequestException, ConnectionError):
            return None
    else:
        return None

    if events_for_email:
        subject = f"NOTE: Smart house message"
        message = f"Events: {events_for_email}. \nDone: {set_data}"
        print("message", message)
        email_from = settings.EMAIL_HOST_USER
        emails_to = [settings.EMAIL_RECEPIENT]
        send_mail(
            subject,
            message,
            email_from,
            emails_to,
            fail_silently=False,
        )
