from django.apps import AppConfig
from django.apps import apps
import os
from django.db.models.signals import pre_save, post_save,pre_delete


class BUDjangoProxyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'BUDjangoProxyApp'

    def ready(self):
        from BUDjangoProxyApp.models import update_activity_logger, post_activity_logger,delete_activity_logger

        for model in apps.get_models():
            if model.__name__!= 'ActivityLog' and model.__name__ !='Scheduler' and model.__name__ !='API' and model.__name__ !='APIVersion':
                pre_save.connect(update_activity_logger, sender=model, weak=False)
                post_save.connect(post_activity_logger, sender=model, weak=False)
                pre_delete.connect(delete_activity_logger, sender=model, weak=False)