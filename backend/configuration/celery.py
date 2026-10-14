import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configuration.settings.base')

app = Celery('configuration')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'remove-old-deleted-mailbox-entries-daily-12-am': {
        'task': 'mail.tasks.remove_old_deleted_mailbox_entries',
        'schedule': crontab(hour=0, minute=0),
    },
}
