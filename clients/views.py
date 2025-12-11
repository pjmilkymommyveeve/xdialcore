from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from core.decorators import role_required
from django.contrib.auth.hashers import make_password   
from accounts.models import Role
from .models import Client
from campaigns.models import ClientCampaignModel, ResponseCategory
from calls.models import Call
from datetime import datetime
from django.db import transaction
from accounts.models import User
import csv
import json
from campaigns.models import (
    Campaign, 
    Model, 
    CampaignModel, 
    ClientCampaignModel,
    PrimaryDialer, 
    CloserDialer, 
    DialerSettings,
    Status, 
    StatusHistory
)


@login_required
@role_required([Role.CLIENT])
def client_landing(request):
    """Client landing page showing their campaigns"""
    try:
        client = Client.objects.get(client=request.user)
    except Client.DoesNotExist:
        return render(request, 'clients/client_landing.html', {
            'error': 'Client profile not found. Please contact administrator.'
        })
    
    campaigns = ClientCampaignModel.objects.filter(
        client=client,
        is_enabled=True
    ).select_related(
        'campaign_model__campaign',
        'campaign_model__model',
    ).prefetch_related('calls').order_by('-start_date')
    
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(is_active=True).count()
    inactive_campaigns = total_campaigns - active_campaigns
    
    campaign_data = []
    for campaign in campaigns:
        total_calls = Call.objects.filter(client_campaign_model=campaign).count()
        calls_transferred = Call.objects.filter(
            client_campaign_model=campaign,
            transferred=True
        ).count()
        
        transfer_percentage = 0
        if total_calls > 0:
            transfer_percentage = round((calls_transferred / total_calls) * 100)
        
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


@login_required
@role_required([Role.CLIENT])
def campaign_dashboard(request, campaign_id):
    """Campaign dashboard showing call records"""
    try:
        client = Client.objects.get(client=request.user)
    except Client.DoesNotExist:
        return render(request, 'clients/campaign_dashboard.html', {
            'error': 'Client profile not found. Please contact administrator.'
        })
    
    campaign = get_object_or_404(
        ClientCampaignModel.objects.select_related(
            'campaign_model__campaign',
            'campaign_model__model',
        ),
        id=campaign_id,
        client=client,
        is_enabled=True
    )
    
    # Get filter parameters first (moved up)
    search_query = request.GET.get('search', '').strip()
    list_id_query = request.GET.get('list_id', '').strip()
    start_date = request.GET.get('start_date', '')
    start_time = request.GET.get('start_time', '')
    end_date = request.GET.get('end_date', '')
    end_time = request.GET.get('end_time', '')
    selected_categories = request.GET.getlist('categories')
    
    # Default to today if no date filters are provided
    has_any_filter = any([search_query, list_id_query, start_date, end_date, selected_categories])
    
    if not has_any_filter:
        # Set default to today
        today = datetime.now().date()
        start_date = today.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    # Build base query for category counts with filters applied
    category_count_query = Call.objects.filter(client_campaign_model=campaign)
    
    # Apply same filters to category counts
    if search_query:
        category_count_query = category_count_query.filter(
            Q(number__icontains=search_query) |
            Q(response_category__name__icontains=search_query)
        )
    
    if list_id_query:
        category_count_query = category_count_query.filter(list_id__icontains=list_id_query)
    
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        if start_time:
            time_obj = datetime.strptime(start_time, '%H:%M').time()
            start_datetime = datetime.combine(start_datetime.date(), time_obj)
        category_count_query = category_count_query.filter(timestamp__gte=start_datetime)
    
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        if end_time:
            time_obj = datetime.strptime(end_time, '%H:%M').time()
            end_datetime = datetime.combine(end_datetime.date(), time_obj)
        else:
            end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
        category_count_query = category_count_query.filter(timestamp__lte=end_datetime)
    
    # Get category counts based on filtered calls
    category_counts_raw = category_count_query.values(
        'response_category__id',
        'response_category__name'
    ).annotate(count=Count('id'))
    
    category_count_dict = {
        item['response_category__name'] or 'UNKNOWN': item['count'] 
        for item in category_counts_raw
    }
    
    all_categories = []
    for category in ResponseCategory.objects.all().order_by('name'):
        all_categories.append({
            'id': category.id,
            'name': category.name.capitalize(),
            'color': category.color,
            'count': category_count_dict.get(category.name, 0)
        })
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    list_id_query = request.GET.get('list_id', '').strip()
    start_date = request.GET.get('start_date', '')
    start_time = request.GET.get('start_time', '')
    end_date = request.GET.get('end_date', '')
    end_time = request.GET.get('end_time', '')
    selected_categories = request.GET.getlist('categories')
    
    # Default to today if no date filters are provided
    has_any_filter = any([search_query, list_id_query, start_date, end_date, selected_categories])
    
    if not has_any_filter:
        # Set default to today
        today = datetime.now().date()
        start_date = today.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    # Base query
    calls = Call.objects.filter(
        client_campaign_model=campaign
    ).select_related('response_category', 'voice').order_by('-timestamp')
    
    # Apply filters
    if search_query:
        calls = calls.filter(
            Q(number__icontains=search_query) |
            Q(response_category__name__icontains=search_query)
        )
    
    if list_id_query:
        calls = calls.filter(list_id__icontains=list_id_query)
    
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        if start_time:
            time_obj = datetime.strptime(start_time, '%H:%M').time()
            start_datetime = datetime.combine(start_datetime.date(), time_obj)
        calls = calls.filter(timestamp__gte=start_datetime)
    
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        if end_time:
            time_obj = datetime.strptime(end_time, '%H:%M').time()
            end_datetime = datetime.combine(end_datetime.date(), time_obj)
        else:
            end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
        calls = calls.filter(timestamp__lte=end_datetime)
    
    if selected_categories:
        calls = calls.filter(response_category__id__in=selected_categories)
    
    total_calls = calls.count()
    
    # Process calls - store transcript as plain text
    calls_data = []
    for call in calls[:50]:
        calls_data.append({
            'id': call.id,
            'number': call.number,
            'list_id': call.list_id or 'N/A',
            'category_color': call.response_category.color if call.response_category else '#6B7280',
            'category': call.response_category.name.capitalize() if call.response_category else 'Unknown',
            'timestamp': call.timestamp.strftime('%m/%d/%Y, %H:%M:%S'),
            'has_transcription': bool(call.transcription),
            'transcription': call.transcription or 'No transcript available',
        })
    
    context = {
        'client_name': client.name,
        'campaign': {
            'id': campaign.id,
            'name': campaign.campaign_model.campaign.name,
            'model': campaign.campaign_model.model.name,
            'is_active': campaign.is_active,
        },
        'calls': calls_data,
        'total_calls': total_calls,
        'all_categories': all_categories,
        'filters': {
            'search': search_query,
            'list_id': list_id_query,
            'start_date': start_date,
            'start_time': start_time,
            'end_date': end_date,
            'end_time': end_time,
            'selected_categories': [int(x) for x in selected_categories] if selected_categories else [],
        }
    }
    
    return render(request, 'clients/campaign_dashboard.html', context)


@login_required
@role_required([Role.CLIENT])
def campaign_recordings(request, campaign_id):
    """
    Recordings page - provides server configs for client-side fetching.
    Frontend will call backend API endpoint which fetches from recording servers.
    """
    try:
        client = Client.objects.get(client=request.user)
    except Client.DoesNotExist:
        return render(request, 'clients/campaign_recordings.html', {
            'error': 'Client profile not found. Please contact administrator.'
        })
    
    campaign = get_object_or_404(
        ClientCampaignModel.objects.select_related(
            'campaign_model__campaign',
            'campaign_model__model',
        ).prefetch_related('server_bots__server', 'server_bots__extension'),
        id=campaign_id,
        client=client,
        is_enabled=True
    )
    
    # Get all servers and extensions connected to this campaign
    server_configs = []
    for bot in campaign.server_bots.all():
        if bot.server:
            server_configs.append({
                'server_id': bot.server.id,
                'extension': str(bot.extension.extension_number),
                'alias': bot.server.alias or bot.server.ip,
            })
    
    context = {
        'client_name': client.name,
        'campaign': {
            'id': campaign.id,
            'name': campaign.campaign_model.campaign.name,
            'model': campaign.campaign_model.model.name,
        },
        'server_configs': json.dumps(server_configs),
        'has_servers': len(server_configs) > 0,
    }
    
    return render(request, 'clients/campaign_recordings.html', context)


@login_required
@role_required([Role.CLIENT])
def data_export(request, campaign_id):
    """Data export page"""
    try:
        client = Client.objects.get(client=request.user)
    except Client.DoesNotExist:
        return render(request, 'clients/data_export.html', {
            'error': 'Client profile not found. Please contact administrator.'
        })
    
    campaign = get_object_or_404(
        ClientCampaignModel.objects.select_related(
            'campaign_model__campaign',
            'campaign_model__model',
        ),
        id=campaign_id,
        client=client,
        is_enabled=True
    )
    
    if request.method == 'POST':
        export_data_json = request.POST.get('export_data', '{}')
        export_data = json.loads(export_data_json)
        
        calls = Call.objects.filter(
            client_campaign_model=campaign
        ).select_related('response_category', 'voice')
        
        # Apply filters
        list_ids = export_data.get('list_ids', [])
        if list_ids:
            calls = calls.filter(list_id__in=list_ids)
        
        categories = export_data.get('categories', [])
        if categories:
            calls = calls.filter(response_category__id__in=categories)
        
        start_date = export_data.get('start_date')
        start_time = export_data.get('start_time')
        end_date = export_data.get('end_date')
        end_time = export_data.get('end_time')
        
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            if start_time:
                time_obj = datetime.strptime(start_time, '%H:%M').time()
                start_datetime = datetime.combine(start_datetime.date(), time_obj)
            calls = calls.filter(timestamp__gte=start_datetime)
        
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            if end_time:
                time_obj = datetime.strptime(end_time, '%H:%M').time()
                end_datetime = datetime.combine(end_datetime.date(), time_obj)
            else:
                end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            calls = calls.filter(timestamp__lte=end_datetime)
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        filename = f"call_data_{campaign.campaign_model.campaign.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Call ID', 'Phone Number', 'List ID', 'Category', 'Timestamp',
            'Transferred', 'Stage', 'Voice', 'Transcription'
        ])
        
        for call in calls:
            writer.writerow([
                call.id,
                call.number,
                call.list_id or '',
                call.response_category.name.capitalize() if call.response_category else 'Unknown',
                call.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if call.transferred else 'No',
                call.stage or 0,
                call.voice.name if call.voice else 'Unknown',
                call.transcription or ''
            ])
        
        return response
    
    # GET request - display form
    list_ids = Call.objects.filter(
        client_campaign_model=campaign,
        list_id__isnull=False
    ).exclude(list_id='').values_list('list_id', flat=True).distinct().order_by('list_id')
    
    category_counts_raw = Call.objects.filter(
        client_campaign_model=campaign
    ).values(
        'response_category__id',
        'response_category__name'
    ).annotate(count=Count('id'))
    
    all_categories = []
    category_count_dict = {
        item['response_category__name'] or 'UNKNOWN': item['count'] 
        for item in category_counts_raw
    }
    
    for category in ResponseCategory.objects.all().order_by('name'):
        all_categories.append({
            'id': category.id,
            'name': category.name.capitalize(),
            'count': category_count_dict.get(category.name, 0)
        })
    
    context = {
        'client_name': client.name,
        'campaign': {
            'id': campaign.id,
            'name': campaign.campaign_model.campaign.name,
            'model': campaign.campaign_model.model.name,
        },
        'list_ids': list(list_ids),
        'all_categories': all_categories,
    }
    
    return render(request, 'clients/data_export.html', context)


def integration_request(request):
    """
    Public integration request form.
    GET: Display form with dynamic campaign/model data
    POST: Process form and create all database entries
    """
    if request.method == 'GET':
        # Fetch all campaigns and models from database
        campaigns = Campaign.objects.all().order_by('name')
        models = Model.objects.all().order_by('name')
        
        # Build campaign config mapping (campaign -> available models)
        campaign_config = {}
        for cm in CampaignModel.objects.select_related('campaign', 'model'):
            campaign_name = cm.campaign.name
            model_name = cm.model.name
            if campaign_name not in campaign_config:
                campaign_config[campaign_name] = []
            campaign_config[campaign_name].append(model_name)
        
        context = {
            'campaigns': campaigns,
            'models': models,
            'campaign_config': json.dumps(campaign_config),
        }
        return render(request, 'clients/integration_request.html', context)
    
    elif request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = [
                'companyName', 'campaign', 'model', 'numberOfBots',
                'primaryIpValidation', 'primaryAdminLink',
                'primaryUser', 'primaryPassword'
            ]
            
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'message': f'Missing required field: {field}'
                    }, status=400)
            
            # Start database transaction
            with transaction.atomic():
                # 1. Create User account with CLIENT role
                client_role = Role.objects.get(name=Role.CLIENT)
                
                # Generate unique username from company name
                base_username = data['companyName'].lower().replace(' ', '_')
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User.objects.create(
                    username=username,
                    password=make_password('clientdefault123'),
                    role=client_role,
                    is_active=True
                )
                
                # 2. Create Client profile
                client = Client.objects.create(
                    client=user,
                    name=data['companyName'],
                    is_archived=False
                )
                
                # 3. Get or create Campaign
                campaign, _ = Campaign.objects.get_or_create(
                    name=data['campaign'],
                    defaults={'description': f'{data["campaign"]} campaign'}
                )
                
                # 4. Get or create Model
                model, _ = Model.objects.get_or_create(
                    name=data['model'],
                    defaults={
                        'description': f'{data["model"]} model',
                        'transfer_settings': data.get('transferSettings', 'balanced')
                    }
                )
                
                # 5. Get or create CampaignModel association
                campaign_model, _ = CampaignModel.objects.get_or_create(
                    campaign=campaign,
                    model=model
                )
                
                # 6. Create CloserDialer (if separate dialer)
                closer_dialer = None
                if data.get('setupType') == 'separate':
                    closer_dialer = CloserDialer.objects.create(
                        ip_validation_link=data.get('closerIpValidation', ''),
                        admin_link=data.get('closerAdminLink', ''),
                        admin_username=data.get('closerUser', ''),
                        admin_password=data.get('closerPassword', ''),
                        closer_campaign=data.get('closerCampaign', ''),
                        ingroup=data.get('closerIngroup', ''),
                        port=int(data.get('closerPort', 5060))
                    )
                
                # 7. Create DialerSettings
                dialer_settings = DialerSettings.objects.create(
                    closer_dialer=closer_dialer
                )
                
                # 8. Create PrimaryDialer and link to DialerSettings
                primary_dialer = PrimaryDialer.objects.create(
                    ip_validation_link=data['primaryIpValidation'],
                    admin_link=data['primaryAdminLink'],
                    admin_username=data['primaryUser'],
                    admin_password=data['primaryPassword'],
                    fronting_campaign=data.get('primaryBotsCampaign', ''),
                    verifier_campaign=data.get('primaryUserSeries', ''),
                    port=int(data.get('primaryPort', 5060)),
                    dialer_settings=dialer_settings
                )
                
                # 9. Create Status
                status = Status.objects.create(
                    status_name='Pending Approval'
                )
                
                # 10. Create StatusHistory
                status_history = StatusHistory.objects.create(
                    status=status,
                    start_date=datetime.now(),
                    end_date=None
                )
                
                # 11. Create ClientCampaignModel (main entry) with campaign requirements
                client_campaign_model = ClientCampaignModel.objects.create(
                    client=client,
                    campaign_model=campaign_model,
                    status_history=status_history,
                    start_date=datetime.now(),
                    end_date=None,
                    is_custom=bool(data.get('customRequirements')),
                    custom_comments=data.get('customRequirements', ''),
                    current_remote_agents=data.get('customRequirements', ''),
                    is_active=False,  # Not active until approved
                    is_enabled=True,
                    is_approved=False,  # Requires admin approval
                    dialer_settings=dialer_settings,
                    # Campaign requirements fields (moved from separate table)
                    bot_count=int(data['numberOfBots']),
                    long_call_scripts_active=False,  # Default to False
                    disposition_set=False  # Default to False
                )
                
                # Return success response
                return JsonResponse({
                    'success': True,
                    'message': 'Integration request submitted successfully!',
                    'data': {
                        'username': username,
                        'client_id': client.client_id,
                        'campaign_id': client_campaign_model.id
                    }
                }, status=201)
        
        except Role.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Client role not found in system. Please contact administrator.'
            }, status=500)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)