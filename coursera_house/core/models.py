from django.db import models


# Create your models here.
class Setting(models.Model):
    controller_name = models.CharField(max_length=40, unique=False)
    label = models.CharField(max_length=100)
    value = models.IntegerField(default=20)
