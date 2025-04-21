from django.core.management.base import BaseCommand
from BUDjangoProxyApp.services.DynamicLoader import DynamicAppManager

class Command(BaseCommand):
    help = 'Reload all dynamic projects'

    def handle(self, *args, **kwargs):
        DynamicAppManager.reload_all_instances()
        self.stdout.write(self.style.SUCCESS('All projects reloaded successfully'))
