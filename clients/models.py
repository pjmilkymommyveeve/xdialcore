from django.db import models
from accounts.models import User


class Client(models.Model):
    client = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='client_profile'
    )
    name = models.CharField(max_length=255)
    assembly_api_key = models.CharField(max_length=32)
    plain_password = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'clients'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        indexes = [
            models.Index(fields=['name'], name='idx_clients_name'),
        ]
    
    def __str__(self):
        return self.name
    
class ClientEmployee(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='employer',
        limit_choices_to={'role__name': 'client_member'}
    )
    
    class Meta:
        db_table = 'client_employees'
        verbose_name = 'Client Employee'
        verbose_name_plural = 'Client Employees'
        unique_together = [['client', 'user']]
        indexes = [
            models.Index(fields=['client'], name='idx_client_emp_client'),
            models.Index(fields=['user'], name='idx_client_emp_user'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.client.name}"