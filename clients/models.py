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
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'clients'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        indexes = [
            models.Index(fields=['name'], name='idx_clients_name'),
            models.Index(fields=['is_archived'], name='idx_clients_is_archived'),
        ]
    
    def __str__(self):
        return self.name