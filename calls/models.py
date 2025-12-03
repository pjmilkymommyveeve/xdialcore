from django.db import models


class Call(models.Model):
    """Call records"""
    client_campaign_model = models.ForeignKey(
        'campaigns.ClientCampaignModel',
        on_delete=models.CASCADE,
        related_name='calls'
    )
    number = models.CharField(max_length=20)
    transcription = models.TextField(blank=True, null=True)
    stage = models.IntegerField(blank=True, null=True)
    response_category = models.TextField(blank=True, null=True)
    list_id = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'calls'
        indexes = [
            models.Index(fields=['client_campaign_model'], name='idx_calls_client_campaign_model_id'),
            models.Index(fields=['number'], name='idx_calls_number'),
            models.Index(fields=['timestamp'], name='idx_calls_timestamp'),
            models.Index(fields=['stage'], name='idx_calls_stage'),
            models.Index(fields=['list_id'], name='idx_calls_list_id'),
        ]
    
    def __str__(self):
        return f"Call {self.id} - {self.number}"