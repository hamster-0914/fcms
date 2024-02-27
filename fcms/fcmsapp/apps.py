from django.apps import AppConfig
from .blockchain import *

class FcmsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fcmsapp'