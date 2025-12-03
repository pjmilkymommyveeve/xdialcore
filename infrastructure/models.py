from django.db import models


class Server(models.Model):
    """Server information"""
    ip = models.CharField(max_length=45)  # Supports IPv4 and IPv6
    alias = models.CharField(max_length=100, blank=True, null=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'servers'
        indexes = [
            models.Index(fields=['ip'], name='idx_servers_ip'),
            models.Index(fields=['alias'], name='idx_servers_alias'),
        ]
    
    def __str__(self):
        return self.alias or self.ip


class Extension(models.Model):
    """Extension numbers"""
    extension_number = models.IntegerField(unique=True)
    
    class Meta:
        db_table = 'extensions'
        indexes = [
            models.Index(fields=['extension_number'], name='idx_extensions_extension_number'),
        ]
    
    def __str__(self):
        return str(self.extension_number)


class PrimaryDialer(models.Model):
    """Primary dialer configuration"""
    ip_validation_link = models.CharField(max_length=500, blank=True, null=True)
    admin_link = models.CharField(max_length=500, blank=True, null=True)
    admin_username = models.CharField(max_length=100, blank=True, null=True)
    admin_password = models.CharField(max_length=255, blank=True, null=True)
    fronting_campaign = models.CharField(max_length=255, blank=True, null=True)
    verifier_campaign = models.CharField(max_length=255, blank=True, null=True)
    port = models.IntegerField(default=5060)
    
    class Meta:
        db_table = 'primary_dialer'
        indexes = [
            models.Index(fields=['port'], name='idx_primary_dialer_port'),
        ]
    
    def __str__(self):
        return f"Primary Dialer - {self.admin_link or 'No Link'}"


class CloserDialer(models.Model):
    """Closer dialer configuration"""
    ip_validation_link = models.CharField(max_length=500, blank=True, null=True)
    admin_link = models.CharField(max_length=500, blank=True, null=True)
    admin_username = models.CharField(max_length=100, blank=True, null=True)
    admin_password = models.CharField(max_length=255, blank=True, null=True)
    closer_campaign = models.CharField(max_length=255)
    ingroup = models.CharField(max_length=255)
    port = models.IntegerField(default=5060)
    
    class Meta:
        db_table = 'closer_dialer'
        indexes = [
            models.Index(fields=['port'], name='idx_closer_dialer_port'),
        ]
    
    def __str__(self):
        return f"Closer Dialer - {self.closer_campaign}"


class DialerSettings(models.Model):
    """Dialer settings configuration"""
    has_separate_closer = models.BooleanField(default=False)
    primary_dialer = models.ForeignKey(
        PrimaryDialer,
        on_delete=models.RESTRICT,
        related_name='dialer_settings'
    )
    closer_dialer = models.ForeignKey(
        CloserDialer,
        on_delete=models.RESTRICT,
        related_name='dialer_settings',
        blank=True,
        null=True
    )
    
    class Meta:
        db_table = 'dialer_settings'
        verbose_name_plural = 'Dialer settings'
        indexes = [
            models.Index(fields=['primary_dialer'], name='idx_dialer_settings_primary_dialer_id'),
            models.Index(fields=['closer_dialer'], name='idx_dialer_settings_closer_dialer_id'),
        ]
    
    def __str__(self):
        return f"Dialer Settings - {self.id}"

