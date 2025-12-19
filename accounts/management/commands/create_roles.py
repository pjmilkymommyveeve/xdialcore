from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'Create initial roles'
    
    def handle(self, *args, **kwargs):
        roles = [
            Role.ADMIN,
            Role.CLIENT,
            Role.CLIENT_MEMBER,
            Role.ONBOARDING,
            Role.QA,
        ]
        
        for role_name in roles:
            role, created = Role.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created role: {role.get_name_display()}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Role already exists: {role.get_name_display()}')
                )