from django.db import models


class TransferSettings(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        db_table = 'transfer_settings'
        verbose_name = 'Transfer Setting'
        verbose_name_plural = 'Transfer Settings'
        indexes = [
            models.Index(fields=['name'], name='idx_transfer_settings_name'),
        ]
    
    def __str__(self):
        return self.name


class Model(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    transfer_settings = models.ForeignKey(
        TransferSettings,
        on_delete=models.SET_NULL,
        related_name='models',
        blank=True,
        null=True
    )
    
    class Meta:
        db_table = 'models'
        verbose_name = 'Model'
        verbose_name_plural = 'Models'
        indexes = [
            models.Index(fields=['name'], name='idx_models_name'),
            models.Index(fields=['transfer_settings'], name='idx_models_transfer_settings'),
        ]
    
    def __str__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'campaigns'
        verbose_name = 'Campaign'
        verbose_name_plural = 'Campaigns'
        indexes = [
            models.Index(fields=['name'], name='idx_campaigns_name'),
        ]
    
    def __str__(self):
        return self.name


class CampaignModel(models.Model):
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
        verbose_name = 'Campaign-Model Pair'
        verbose_name_plural = 'Campaign-Model Pairs'
        unique_together = [['campaign', 'model']]
        indexes = [
            models.Index(fields=['campaign'], name='idx_campaign_model_campaign_id'),
            models.Index(fields=['model'], name='idx_campaign_model_model_id'),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} - {self.model.name}"


class Voice(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        db_table = 'voices'
        verbose_name = 'Voice'
        verbose_name_plural = 'Voices'
        indexes = [
            models.Index(fields=['name'], name='idx_voices_name'),
        ]
    
    def __str__(self):
        return self.name


class ResponseCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    color = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'response_categories'
        verbose_name = 'Response Category'
        verbose_name_plural = 'Response Categories'
        indexes = [
            models.Index(fields=['name'], name='idx_response_categories_name'),
        ]
    
    def __str__(self):
        return self.name


class Status(models.Model):
    status_name = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'status'
        verbose_name = 'Status'
        verbose_name_plural = 'Statuses'
        indexes = [
            models.Index(fields=['status_name'], name='idx_status_status_name'),
            models.Index(fields=['updated_at'], name='idx_status_updated_at'),
        ]
    
    def __str__(self):
        return self.status_name


class StatusHistory(models.Model):
    status = models.ForeignKey(
        Status,
        on_delete=models.RESTRICT,
        related_name='history'
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'status_history'
        verbose_name = 'Status History'
        verbose_name_plural = 'Status History'
        indexes = [
            models.Index(fields=['status'], name='idx_status_history_status_id'),
            models.Index(fields=['start_date'], name='idx_status_history_start_date'),
            models.Index(fields=['end_date'], name='idx_status_history_end_date'),
        ]
    
    def __str__(self):
        return f"{self.status.status_name} - {self.start_date}"


class PrimaryDialer(models.Model):
    ip_validation_link = models.CharField(max_length=500, blank=True, null=True)
    admin_link = models.CharField(max_length=500, blank=True, null=True)
    admin_username = models.CharField(max_length=100, blank=True, null=True)
    admin_password = models.CharField(max_length=255, blank=True, null=True)
    fronting_campaign = models.CharField(max_length=255, blank=True, null=True)
    verifier_campaign = models.CharField(max_length=255, blank=True, null=True)
    port = models.IntegerField(default=5060)
    dialer_settings = models.ForeignKey(
        'DialerSettings',
        on_delete=models.CASCADE,
        related_name='primary_dialers',
        blank=True,
        null=True
    )
    
    class Meta:
        db_table = 'primary_dialer'
        verbose_name = 'Primary Dialer'
        verbose_name_plural = 'Primary Dialers'
        indexes = [
            models.Index(fields=['port'], name='idx_primary_dialer_port'),
            models.Index(fields=['dialer_settings'], name='idx_primary_dialer_settings'),
        ]
    
    def __str__(self):
        return f"Primary Dialer - {self.admin_link or 'No Link'}"


class CloserDialer(models.Model):
    ip_validation_link = models.CharField(max_length=500, blank=True, null=True)
    admin_link = models.CharField(max_length=500, blank=True, null=True)
    admin_username = models.CharField(max_length=100, blank=True, null=True)
    admin_password = models.CharField(max_length=255, blank=True, null=True)
    closer_campaign = models.CharField(max_length=255)
    ingroup = models.CharField(max_length=255)
    port = models.IntegerField(default=5060)
    
    class Meta:
        db_table = 'closer_dialer'
        verbose_name = 'Closer Dialer'
        verbose_name_plural = 'Closer Dialers'
        indexes = [
            models.Index(fields=['port'], name='idx_closer_dialer_port'),
        ]
    
    def __str__(self):
        return f"Closer Dialer - {self.closer_campaign}"


class DialerSettings(models.Model):
    closer_dialer = models.ForeignKey(
        CloserDialer,
        on_delete=models.RESTRICT,
        related_name='dialer_settings',
        blank=True,
        null=True
    )
    
    class Meta:
        db_table = 'dialer_settings'
        verbose_name = 'Dialer Settings'
        verbose_name_plural = 'Dialer Settings'
        indexes = [
            models.Index(fields=['closer_dialer'], name='idx_ds_closer'),
        ]
    
    def __str__(self):
        return f"Dialer Settings #{self.id}"


class ClientCampaignModel(models.Model):
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
    is_approved = models.BooleanField(default=False)
    # Dialer configuration
    dialer_settings = models.ForeignKey(
        DialerSettings,
        on_delete=models.SET_NULL,
        related_name='client_campaigns',
        blank=True,
        null=True
    )
    bot_count = models.IntegerField(default=0, help_text="Number of bots for this campaign")
    long_call_scripts_active = models.BooleanField(default=False, help_text="Are long call scripts active?")
    disposition_set = models.BooleanField(default=False, help_text="Is disposition set configured?")
    
    class Meta:
        db_table = 'client_campaign_model'
        verbose_name = 'Client Campaign'
        verbose_name_plural = 'Client Campaigns'
        indexes = [
            models.Index(fields=['client'], name='idx_ccm_client'),
            models.Index(fields=['campaign_model'], name='idx_ccm_camp_model'),
            models.Index(fields=['is_active'], name='idx_ccm_active'),
            models.Index(fields=['is_enabled'], name='idx_ccm_enabled'),
            models.Index(fields=['is_approved'], name='idx_ccm_approved'),
            models.Index(fields=['start_date'], name='idx_ccm_start'),
            models.Index(fields=['end_date'], name='idx_ccm_end'),
            models.Index(fields=['bot_count'], name='idx_ccm_bot_count'),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.campaign_model}"


class ServerCampaignBots(models.Model):
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
        verbose_name = 'Server Campaign Bot'
        verbose_name_plural = 'Server Campaign Bots'
        indexes = [
            models.Index(fields=['client_campaign_model'], name='idx_scb_ccm'),
            models.Index(fields=['server'], name='idx_scb_server'),
            models.Index(fields=['extension'], name='idx_scb_extension'),
        ]
    
    def __str__(self):
        return f"{self.server} - {self.client_campaign_model}"