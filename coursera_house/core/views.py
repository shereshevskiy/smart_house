from django.conf import settings

import requests
from django.urls import reverse_lazy
from django.views.generic import FormView

from .models import Setting

from .form import ControllerForm


class ControllerView(FormView):
    form_class = ControllerForm
    template_name = 'core/control.html'
    success_url = reverse_lazy('form')
    HEADERS = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}

    def get_context_data(self, **kwargs):
        context = super(ControllerView, self).get_context_data()

        headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
        get_response = requests.get(settings.SMART_HOME_API_URL, headers=headers)
        data = get_response.json()['data']
        context['data'] = {item["name"]: item["value"] for item in data}
        return context

    def get_initial(self):
        return {}

    def form_valid(self, form):
        item, created = Setting.objects.update_or_create(controller_name="bedroom_target_temperature",
                                                         defaults={"value": int(
                                                             form.cleaned_data["bedroom_target_temperature"])})
        item, created = Setting.objects.update_or_create(controller_name="hot_water_target_temperature",
                                                         defaults={"value": int(
                                                             form.cleaned_data["hot_water_target_temperature"])})
        set_data = {"controllers": [
            {"name": "bedroom_light", "value": form.cleaned_data["bedroom_light"]},
            {"name": "bathroom_light", "value": form.cleaned_data["bathroom_light"]}
        ]
        }
        headers = {"Authorization": f"Bearer {settings.SMART_HOME_ACCESS_TOKEN}"}
        set_response = requests.post(settings.SMART_HOME_API_URL, headers=headers, json=set_data)
        return super(ControllerView, self).form_valid(form)
