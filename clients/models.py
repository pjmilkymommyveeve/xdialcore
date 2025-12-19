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
    
    class Meta:
        db_table = 'clients'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        indexes = [
            models.Index(fields=['name'], name='idx_clients_name'),
        ]
    
    def __str__(self):
        return self.name