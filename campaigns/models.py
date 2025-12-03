from django.db import models


class Model(models.Model):
    """AI Model configuration"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    transfer_settings = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'models'
        indexes = [
            models.Index(fields=['name'], name='idx_models_name'),
        ]
    
    def __str__(self):
        return self.name


class Campaign(models.Model):
    """Campaign information"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'campaigns'
        indexes = [
            models.Index(fields=['name'], name='idx_campaigns_name'),
        ]
    
    def __str__(self):
        return self.name


class CampaignModel(models.Model):
    """Campaign-Model relationship"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_models'
    )
    model = models.ForeignKey(
        Model,
        on_delete=models.RESTRICT,
        related_name='campaign_models'
    )
    
    class Meta:
        db_table = 'campaign_model'
        unique_together = [['campaign', 'model']]
        indexes = [
            models.Index(fields=['campaign'], name='idx_campaign_model_campaign_id'),
            models.Index(fields=['model'], name='idx_campaign_model_model_id'),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.model.name}"


class CampaignRequirements(models.Model):
    """Campaign requirements configuration"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    long_call_scripts_active = models.BooleanField(default=False)
    disposition_set = models.TextField(blank=True, null=True)
    bot_count = models.IntegerField(blank=True, null=True)
    
    class Meta:
        db_table = 'campaign_requirements'
        verbose_name_plural = 'Campaign requirements'
        indexes = [
            models.Index(fields=['name'], name='idx_campaign_requirements_name'),
        ]
    
    def __str__(self):
        return self.name


class Status(models.Model):
    """Status tracking"""
    status_name = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'status'
        verbose_name_plural = 'Statuses'
        indexes = [
            models.Index(fields=['status_name'], name='idx_status_status_name'),
            models.Index(fields=['updated_at'], name='idx_status_updated_at'),
        ]
    
    def __str__(self):
        return self.status_name


class StatusHistory(models.Model):
    """Status history tracking"""
    status = models.ForeignKey(
        Status,
        on_delete=models.RESTRICT,
        related_name='history'
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'status_history'
        verbose_name_plural = 'Status histories'
        indexes = [
            models.Index(fields=['status'], name='idx_status_history_status_id'),
            models.Index(fields=['start_date'], name='idx_status_history_start_date'),
            models.Index(fields=['end_date'], name='idx_status_history_end_date'),
        ]
    
    def __str__(self):
        return f"{self.status.status_name} - {self.start_date}"


class Voice(models.Model):
    """Voice configuration"""
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        db_table = 'voices'
        indexes = [
            models.Index(fields=['name'], name='idx_voices_name'),
        ]
    
    def __str__(self):
        return self.name


class CampaignVoiceStats(models.Model):
    """Campaign voice statistics"""
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='voice_stats'
    )
    voice = models.ForeignKey(
        Voice,
        on_delete=models.CASCADE,
        related_name='campaign_stats'
    )
    interested_count = models.BigIntegerField(default=0)
    
    class Meta:
        db_table = 'campaign_voice_stats'
        unique_together = [['campaign', 'voice']]
        verbose_name_plural = 'Campaign voice statistics'
        indexes = [
            models.Index(fields=['campaign'], name='idx_campaign_voice_stats_campaign_id'),
            models.Index(fields=['voice'], name='idx_campaign_voice_stats_voice_id'),
            models.Index(fields=['interested_count'], name='idx_campaign_voice_stats_interested_count'),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.voice.name}"


class ClientCampaignModel(models.Model):
    """Client campaign model association"""
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='campaign_models'
    )
    campaign_model = models.ForeignKey(
        CampaignModel,
        on_delete=models.RESTRICT,
        related_name='client_associations'
    )
    status_history = models.ForeignKey(
        StatusHistory,
        on_delete=models.SET_NULL,
        related_name='client_campaigns',
        blank=True,
        null=True
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    is_custom = models.BooleanField(default=False)
    custom_comments = models.TextField(blank=True, null=True)
    current_remote_agents = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    dialer_settings = models.ForeignKey(
        'infrastructure.DialerSettings',
        on_delete=models.SET_NULL,
        related_name='client_campaigns',
        blank=True,
        null=True
    )
    campaign_requirements = models.ForeignKey(
        CampaignRequirements,
        on_delete=models.SET_NULL,
        related_name='client_campaigns',
        blank=True,
        null=True
    )
    
    class Meta:
        db_table = 'client_campaign_model'
        indexes = [
            models.Index(fields=['client'], name='idx_client_campaign_model_client_id'),
            models.Index(fields=['campaign_model'], name='idx_client_campaign_model_campaign_model_id'),
            models.Index(fields=['is_active'], name='idx_client_campaign_model_is_active'),
            models.Index(fields=['is_enabled'], name='idx_client_campaign_model_is_enabled'),
            models.Index(fields=['start_date'], name='idx_client_campaign_model_start_date'),
            models.Index(fields=['end_date'], name='idx_client_campaign_model_end_date'),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.campaign_model}"


class ServerCampaignBots(models.Model):
    """Server campaign bot configuration"""
    client_campaign_model = models.ForeignKey(
        ClientCampaignModel,
        on_delete=models.CASCADE,
        related_name='server_bots'
    )
    server = models.ForeignKey(
        'infrastructure.Server',
        on_delete=models.CASCADE,
        related_name='campaign_bots'
    )
    extension = models.ForeignKey(
        'infrastructure.Extension',
        on_delete=models.CASCADE,
        related_name='campaign_bots'
    )
    bot_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'server_campaign_bots'
        verbose_name_plural = 'Server campaign bots'
        indexes = [
            models.Index(fields=['client_campaign_model'], name='idx_server_campaign_bots_client_campaign_model_id'),
            models.Index(fields=['server'], name='idx_server_campaign_bots_server_id'),
            models.Index(fields=['extension'], name='idx_server_campaign_bots_extension_id'),
        ]
    
    def __str__(self):
        return f"{self.server} - {self.client_campaign_model}"

