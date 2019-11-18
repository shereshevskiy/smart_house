from __future__ import absolute_import, unicode_literals
from celery import task
from django.core.mail import send_mail

from django.conf import settings

import requests

from .models import Setting

@task()
def smart_home_manager():
    # Здесь ваш код для проверки условий

    # подготовка запроса на данные, запрос и продобработка данных
    headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
    get_response = requests.get(settings.SMART_HOME_API_URL, headers=headers)
    controllers = {item['name']: item for item in get_response.json()['data']}

    # initialization
    data = {"controllers": []}
    events_for_email = []

    def set_controllers(name_value_pairs):
        controllers_in_data = list(map(lambda x: x["name"], data['controllers']))

        for name, value in name_value_pairs:
            if name in controllers_in_data:
                ind = controllers_in_data.index(name)
                data["controllers"].pop(ind)
            data["controllers"].append({"name": name, "value": value})

    # 1
    if controllers["leak_detector"]["value"]:
        events_for_email.append({"leak_detector": True})
        set_controllers(
            [("cold_water", False), ("hot_water", False)]
        )

    # 3
    if controllers["boiler_temperature"]["value"] < controllers["hot_water_target_temperature"]["value"] * 0.9:
        if controllers["cold_water"]["value"]:
            set_controllers(
                [("boiler", True)]
            )
    # 3.1
    if controllers["boiler_temperature"]["value"] >= controllers["hot_water_target_temperature"]["value"] * 1.1:
        set_controllers(
            [("boiler", False)]
        )

    # 4
    if controllers["curtains"]["value"] == "slightly_open":
        set_controllers(
            [("curtains", "slightly_open")]
        )

    # 5
    if controllers["outdoor_light"]["value"] < 50:
        if controllers["curtains"]["value"] != "slightly_open":
            if not controllers["bedroom_light"]["value"]:
                set_controllers(
                    [("curtains", "open")]
                )
    else:
        if controllers["curtains"]["value"] != "slightly_open":
            if controllers["bedroom_light"]["value"]:
                set_controllers(
                    [("curtains", "close")]
                )

    # 2
    if not controllers["cold_water"]["value"]:
        set_controllers(
            [("boiler", False), ("washing_machine", "off")]
        )

    # 6
    if controllers["smoke_detector"]["value"]:
        list_for_off = ["air_conditioner", "bedroom_light", "bathroom_light", "boiler", "washing_machine"]
        set_controllers(
            zip(list_for_off, [False] * (len(list_for_off) - 1) + ["off"])
        )

    # 7
    if controllers["bedroom_temperature"]["value"] > controllers["bedroom_target_temperature "]["value"] * 1.1:
        set_controllers(
            [("air_conditioner", True)]
        )
    # 7.1
    if controllers["bedroom_temperature"]["value"] < controllers["bedroom_target_temperature "]["value"] * 0.9:
        set_controllers(
            [("air_conditioner", False)]
        )

    post_response = requests.post(settings.SMART_HOME_API_URL, headers=headers, json=data)

    if events_for_email:
        subject = f"NOTE: Smart house message"
        message = f"Events: {events_for_email}. \nDone: {data}"
        email_from = "vrn.realty@gmail.com"
        emails_to = [settings.EMAIL_RECEPIENT]
        send_mail(
            subject,
            message,
            email_from,
            emails_to,
            fail_silently=False,
        )
