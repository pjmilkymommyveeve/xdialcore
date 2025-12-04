from django.db import models


class Server(models.Model):
    ip = models.CharField(max_length=45)
    alias = models.CharField(max_length=100, blank=True, null=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'servers'
        verbose_name = 'Server'
        verbose_name_plural = 'Servers'
        indexes = [
            models.Index(fields=['ip'], name='idx_servers_ip'),
            models.Index(fields=['alias'], name='idx_servers_alias'),
        ]
    
    def __str__(self):
        return self.alias or self.ip


class Extension(models.Model):
    extension_number = models.IntegerField(unique=True)
    
    class Meta:
        db_table = 'extensions'
        verbose_name = 'Extension'
        verbose_name_plural = 'Extensions'
        indexes = [
            models.Index(fields=['extension_number'], name='idx_ext_number'),
        ]
    
    def __str__(self):
        return str(self.extension_number)