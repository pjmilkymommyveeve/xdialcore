from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from core.decorators import role_required
from accounts.models import Role
from .models import Client
from campaigns.models import ClientCampaignModel
from calls.models import Call


@login_required
@role_required([Role.CLIENT])
def client_landing(request):
    """
    Client landing page showing their campaigns
    Only shows campaigns belonging to the logged-in client
    Each client can ONLY see their own data
    """
    
    # Get the client profile for the logged-in user
    try:
        client = Client.objects.get(client=request.user)
    except Client.DoesNotExist:
        return render(request, 'clients/client_landing.html', {
            'error': 'Client profile not found. Please contact administrator.'
        })
    
    # Get all campaigns for THIS SPECIFIC CLIENT ONLY
    campaigns = ClientCampaignModel.objects.filter(
        client=client,  # This ensures isolation - client can only see their own campaigns
        is_enabled=True
    ).select_related(
        'campaign_model__campaign',
        'campaign_model__model',
    ).prefetch_related(
        'calls'
    ).order_by('-start_date')
    
    # Calculate statistics
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(is_active=True).count()
    inactive_campaigns = total_campaigns - active_campaigns
    
    # Process each campaign to add calculated fields
    campaign_data = []
    
    for campaign in campaigns:
        # Get call statistics for this campaign
        total_calls = Call.objects.filter(
            client_campaign_model=campaign
        ).count()
        
        calls_transferred = Call.objects.filter(
            client_campaign_model=campaign,
            transferred=True
        ).count()
        
        # Calculate transfer percentage
        transfer_percentage = 0
        if total_calls > 0:
            transfer_percentage = round((calls_transferred / total_calls) * 100)
        
        # Format dates
        start_date_formatted = campaign.start_date.strftime('%m/%d/%y') if campaign.start_date else 'N/A'
        end_date_formatted = campaign.end_date.strftime('%m/%d/%y') if campaign.end_date else 'N/A'
        
        campaign_data.append({
            'id': campaign.id,
            'campaign_name': campaign.campaign_model.campaign.name,
            'model_name': campaign.campaign_model.model.name,
            'is_active': campaign.is_active,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'total_calls': total_calls,
            'calls_transferred': calls_transferred,
            'transfer_percentage': transfer_percentage,
        })
    
    context = {
        'client_name': client.name,
        'campaigns': campaign_data,
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'inactive_campaigns': inactive_campaigns,
    }
    
    return render(request, 'clients/client_landing.html', context)