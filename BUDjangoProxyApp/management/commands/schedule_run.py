# scheduler/management/commands/schedule_run.py
from django.core.management.base import BaseCommand, CommandError

from django.utils import timezone
from django.db import transaction
from BUDjangoProxyApp.lib.execute_task import execute_task
from BUDjangoProxyApp.models import Scheduler
from BUDjangoProxyApp.services import DynamicLoader
from croniter import croniter

class Command(BaseCommand):
    help = "Runs all due scheduler jobs (combined run + exec)"

    def handle(self, *args, **options):
        dynamic_loader = DynamicLoader.DynamicAppManager
        dynamic_loader.initialize()
        now = timezone.now().replace(second=0, microsecond=0)

        with transaction.atomic():
            schedulers = (
                Scheduler.objects
                .select_for_update(skip_locked=True)
                .filter(enabled=True)
            )

            for task in schedulers:
                if self.is_due(task, now):
                    execute_task(task, dynamic_loader)

    # ----------------------------------------------------
    # Determine whether this task should run this minute
    # ----------------------------------------------------
    def is_due(self, task, now):
        """
        Laravel-style cron matching:
        run if cron expression matches *this* minute
        """
        base = task.last_exec_cron or (now - timezone.timedelta(minutes=1))
        itr = croniter(task.cron, base)

        next_run = itr.get_next(timezone.datetime)
        next_run = timezone.make_aware(next_run) if timezone.is_naive(next_run) else next_run

        return next_run <= now
