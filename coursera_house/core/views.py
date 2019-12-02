from django.conf import settings

import requests
from django.http import HttpResponseBadRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import FormView

from coursera_house.core.tasks import smart_home_manager
from .models import Setting

from .form import ControllerForm


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')

    def get(self, request, *args, **kwargs):
        # smart_home_manager()  # TODO убрать (для отладки)
        try:
            context = self.get_context_data()
        except (requests.exceptions.RequestException, ConnectionError):
            return HttpResponseBadRequest(status=502)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        try:
            form = ControllerForm(request.POST)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        except (requests.exceptions.RequestException, ConnectionError):
            return HttpResponseBadRequest(status=502)

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()

        headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
        get_response = requests.get(settings.SMART_HOME_API_URL, headers=headers)
        if get_response.status_code != 200:
            raise ConnectionError

        data = get_response.json()['data']
        context['data'] = {item["name"]: item["value"] for item in data}
        return context

    def get_initial(self):
        return {}

    def form_valid(self, form):
        headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
        try:
            item1, created = Setting.objects.update_or_create(controller_name="bedroom_target_temperature",
                                                     defaults={"value": int(
                                                         form.cleaned_data["bedroom_target_temperature"])})
            item2, created = Setting.objects.update_or_create(controller_name="hot_water_target_temperature",
                                                     defaults={"value": int(
                                                          form.cleaned_data["hot_water_target_temperature"])})

            get_response = requests.get(settings.SMART_HOME_API_URL, headers=headers)
            if get_response.status_code != 200:
                raise ConnectionError

            data = get_response.json()['data']
            controllers = {item["name"]: item["value"] for item in data}
            set_data = {"controllers": []}
            for light in ["bedroom_light", "bathroom_light"]:
                if controllers[light] != form.cleaned_data[light]:
                    set_data["controllers"].append({"name": light, "value": form.cleaned_data[light]})
            if set_data["controllers"]:
                set_response = requests.post(settings.SMART_HOME_API_URL, headers=headers, json=set_data)
                if set_response.status_code != 200:
                    return HttpResponse(status=502)
        except (requests.exceptions.RequestException, ConnectionError):
            return HttpResponse(status=502)
        return super(ControllerView, self).form_valid(form)

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return HttpResponseBadRequest(status=502)  # TODO under question
