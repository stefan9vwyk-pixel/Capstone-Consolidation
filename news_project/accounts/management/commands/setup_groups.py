from django.core.management.base import BaseCommand
from accounts.signals import _setup_groups


class Command(BaseCommand):
    help = 'Manually trigger user groups and permissions setup'

    def handle(self, *args, **options):
        try:
            _setup_groups
            self.stdout.write(
                self.style.SUCCESS(
                    'Groups and permissions configured successfully.'
                ))
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f'Could not set up groups: {e}'
                ))
