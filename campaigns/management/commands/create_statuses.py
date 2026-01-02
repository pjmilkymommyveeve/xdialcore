from django.core.management.base import BaseCommand
from campaigns.models import Status


class Command(BaseCommand):
    help = 'Create initial statuses'
    
    def handle(self, *args, **kwargs):
        statuses = [
            'Not Approved',
            'Enabled',
            'Disabled',
            'Archived',
            'Testing'
        ]
        
        for status_name in statuses:
            status, created = Status.objects.get_or_create(status_name=status_name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created status: {status.status_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Status already exists: {status.status_name}')
                )