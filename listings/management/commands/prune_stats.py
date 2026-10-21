from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import PageView


class Command(BaseCommand):
    help = 'Delete visit records older than a number of days (default 400) to keep the database small.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=400)

    def handle(self, *args, **opts):
        cutoff = timezone.localdate() - timedelta(days=opts['days'])
        n, _ = PageView.objects.filter(day__lt=cutoff).delete()
        self.stdout.write(f'Deleted {n} old visit record(s).')
