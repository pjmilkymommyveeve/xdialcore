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
    StatusHistory,
    TransferSettings
)


# Edit this only |
CATEGORY_MAPPING = {
    "ANSWER_MACHINE_greeting": "Answering Machine",
    "ANSWER_MACHINE": "Answering Machine",
    "ANSWER_MACHINE_hello": "Answering Machine",

    "DO_NOT_CALL": "Do Not Call",
    "DO_NOT_CALL_greeting": "Do Not Call",
    "DO_NOT_CALL_hello": "Do Not Call",

    "DNQ": "Do Not Qualify",

    "NOT_INTERESTED": "Not Interested",
    "NOT_INTERESTED_transfer": "Not Interested",

    "Not_Responding": "Not Responding",
    "Not_Responding_greeting": "Not Responding",
    "Not_Responding_hello": "Not Responding",

    "neutral_keywords": "Neutral",
    "already_keywords": "Neutral",
    "busy_keywords": "Neutral",
    "rebuttal_keywords": "Neutral",

    "INTERESTED": "Interested",
    "INTERESTED_transfer": "Interested",

    "UNKNOWN_hello": "Unknown",
    "UNKNOWN_greeting": "Unknown",
    "UNKNOWN": "Unknown",
    "UNKNOWN_transfer": "Unknown",

    "User_Silent_hello": "User Silent",
    "User_Silent_greeting": "User Silent",
    "User Slient": "User Silent",  

    "Honeypot_K_hello": "Honeypot",
    "Honeypot_K_greeting": "Honeypot",
    "Honeypot_K": "Honeypot",
    "Honeypot_S": "Honeypot",
}



@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
@role_required([Role.CLIENT])
def campaign_dashboard(request, campaign_id):
    """Campaign dashboard showing call records - latest stage only with combined categories"""
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
        today = datetime.now().date()
        start_date = today.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    # Base query - get latest stage calls using subquery
    from django.db.models import OuterRef, Subquery, Max
    
    # Subquery to get the maximum stage for each number
    latest_stage_subquery = Call.objects.filter(
        client_campaign_model=campaign,
        number=OuterRef('number')
    ).order_by().values('number').annotate(
        max_stage=Max('stage')
    ).values('max_stage')[:1]
    
    # Build base query for category counts with latest stage filter
    category_count_query = Call.objects.filter(
        client_campaign_model=campaign,
        stage=Subquery(latest_stage_subquery)
    )
    
    # Apply filters to category counts
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
    
    # Get category counts based on filtered calls (latest stage only)
    category_counts_raw = category_count_query.values(
        'response_category__id',
        'response_category__name',
        'response_category__color'
    ).annotate(count=Count('id'))
    
    # Get ALL categories from database to ensure we show all, even with zero counts
    all_db_categories = ResponseCategory.objects.all().values('id', 'name', 'color')
    
    # Combine categories according to mapping
    combined_counts = {}
    category_id_to_combined = {}  # Maps original category IDs to combined category names
    category_colors = {}  # Store colors for combined categories
    
    # First, initialize all possible combined categories with zero counts
    for db_cat in all_db_categories:
        original_name = db_cat['name'] or 'UNKNOWN'
        combined_name = CATEGORY_MAPPING.get(original_name, original_name)
        
        if combined_name not in combined_counts:
            combined_counts[combined_name] = 0
            category_colors[combined_name] = db_cat['color'] or '#6B7280'
    
    # Now add the actual counts
    for item in category_counts_raw:
        original_name = item['response_category__name'] or 'UNKNOWN'
        original_id = item['response_category__id']
        count = item['count']
        color = item['response_category__color'] or '#6B7280'
        
        # Get the mapped category name
        combined_name = CATEGORY_MAPPING.get(original_name, original_name)
        
        # Store mapping of original ID to combined name
        category_id_to_combined[original_id] = combined_name
        
        # Accumulate counts for combined categories
        combined_counts[combined_name] += count
        # Update color if we didn't have one yet
        if not category_colors.get(combined_name):
            category_colors[combined_name] = color
    
    # Build the all_categories list with combined categories
    all_categories = []
    for combined_name, count in sorted(combined_counts.items()):
        all_categories.append({
            'name': combined_name.capitalize(),
            'color': category_colors.get(combined_name, '#6B7280'),
            'count': count,
            'original_name': combined_name  # Keep for filtering
        })
    
    # Base query for calls - only latest stage per number
    calls = Call.objects.filter(
        client_campaign_model=campaign,
        stage=Subquery(latest_stage_subquery)
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
    
    # Filter by combined categories if selected
    if selected_categories:
        # Find all original category names that map to selected combined categories
        original_names = [
            name for name, combined in CATEGORY_MAPPING.items() 
            if combined in selected_categories
        ]
        # Also include the combined names themselves if they weren't mapped
        original_names.extend([cat for cat in selected_categories if cat not in CATEGORY_MAPPING.values()])
        
        calls = calls.filter(response_category__name__in=original_names)
    
    total_calls = calls.count()
    
    # Process calls - store transcript as plain text with combined category names
    calls_data = []
    for call in calls[:50]:
        original_category_name = call.response_category.name if call.response_category else 'Unknown'
        combined_category_name = CATEGORY_MAPPING.get(original_category_name, original_category_name)
        
        calls_data.append({
            'id': call.id,
            'number': call.number,
            'list_id': call.list_id or 'N/A',
            'category_color': call.response_category.color if call.response_category else '#6B7280',
            'category': combined_category_name.capitalize(),
            'timestamp': call.timestamp.strftime('%m/%d/%Y, %H:%M:%S'),
            'stage': call.stage or 0,
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
            'selected_categories': selected_categories,
        }
    }
    
    return render(request, 'clients/campaign_dashboard.html', context)


@login_required(login_url='/accounts/login/')
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


@login_required(login_url='/accounts/login/')
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
    GET: Display form with dynamic transfer settings
    POST: Process form and create all database entries
    """
    if request.method == 'GET':
        # Get all campaigns
        campaigns = Campaign.objects.all().order_by('name')
        
        # Build campaign configuration for JavaScript
        # This maps campaign names to their available models with transfer settings
        campaign_config = {}
        for campaign in campaigns:
            # Get all unique models available for this campaign with their transfer settings
            campaign_models = CampaignModel.objects.filter(
                campaign=campaign
            ).select_related('model', 'model__transfer_settings').values(
                'model__name',
                'model__transfer_settings__id',
                'model__transfer_settings__name'
            ).distinct()
            
            # Group by model name and collect transfer settings
            models_dict = {}
            for cm in campaign_models:
                model_name = cm['model__name']
                if model_name not in models_dict:
                    models_dict[model_name] = []
                if cm['model__transfer_settings__id']:
                    models_dict[model_name].append({
                        'id': cm['model__transfer_settings__id'],
                        'name': cm['model__transfer_settings__name']
                    })
            
            campaign_config[campaign.name] = models_dict
        
        # Get all transfer settings with their properties
        transfer_settings = TransferSettings.objects.all().order_by('display_order')
        transfer_settings_data = []
        for ts in transfer_settings:
            transfer_settings_data.append({
                'id': ts.id,
                'name': ts.name,
                'description': ts.description or '',
                'is_recommended': ts.is_recommended,
                'quality_score': ts.quality_score,
                'volume_score': ts.volume_score,
                'display_order': ts.display_order
            })
        
        context = {
            'campaigns': campaigns,
            'campaign_config': json.dumps(campaign_config),
            'transfer_settings': json.dumps(transfer_settings_data)
        }
        
        return render(request, 'clients/integration_request.html', context)
    
    elif request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            
            # Start database transaction
            with transaction.atomic():
                # 1. Create or get unique company name
                base_company_name = data.get('companyName', '').strip()
                if not base_company_name:
                    return JsonResponse({
                        'success': False,
                        'message': 'Company name is required'
                    }, status=400)
                
                company_name = base_company_name
                counter = 1
                
                # Check if company name exists and increment if needed
                while Client.objects.filter(name=company_name).exists():
                    company_name = f"{counter}{base_company_name}"
                    counter += 1
                
                # 2. Create User with Client role
                client_role = Role.objects.get(name=Role.CLIENT)
                
                # Create username from company name (lowercase, no spaces)
                username = company_name.lower().replace(' ', '_')
                
                # Ensure username is unique
                original_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{original_username}{counter}"
                    counter += 1
                
                user = User.objects.create(
                    username=username,
                    password=make_password('clientdefault123'),
                    role=client_role,
                    is_active=True
                )
                
                # 3. Create Client profile
                client = Client.objects.create(
                    client=user,
                    name=company_name,
                    is_archived=False
                )
                
                # 4. Get Campaign
                campaign_name = data.get('campaign')
                campaign = Campaign.objects.get(name=campaign_name)
                
                # 5. Get Transfer Settings and Model based on transfer_settings_id
                transfer_settings_id = data.get('transferSettingsId')
                
                if not transfer_settings_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Transfer settings selection is required'
                    }, status=400)
                
                transfer_setting = TransferSettings.objects.get(id=transfer_settings_id)
                
                # Get the model associated with this transfer setting
                # The model_name is also sent from frontend for verification
                model_name = data.get('modelName')
                model = Model.objects.get(
                    name=model_name,
                    transfer_settings=transfer_setting
                )
                
                # 6. Get or create CampaignModel
                campaign_model = CampaignModel.objects.get(
                    campaign=campaign,
                    model=model
                )
                
                # 7. Create CloserDialer (if separate dialer)
                closer_dialer = None
                setup_type = data.get('setupType', 'same')
                
                if setup_type == 'separate':
                    closer_dialer = CloserDialer.objects.create(
                        ip_validation_link=data.get('closerIpValidation', ''),
                        admin_link=data.get('closerAdminLink', ''),
                        admin_username=data.get('closerUser', ''),
                        admin_password=data.get('closerPassword', ''),
                        closer_campaign=data.get('closerCampaign', ''),
                        ingroup=data.get('closerIngroup', ''),
                        port=int(data.get('closerPort', 5060))
                    )
                
                # 8. Create DialerSettings
                dialer_settings = DialerSettings.objects.create(
                    closer_dialer=closer_dialer
                )
                
                # 9. Create PrimaryDialer and link to DialerSettings
                primary_dialer = PrimaryDialer.objects.create(
                    ip_validation_link=data.get('primaryIpValidation', ''),
                    admin_link=data.get('primaryAdminLink', ''),
                    admin_username=data.get('primaryUser', ''),
                    admin_password=data.get('primaryPassword', ''),
                    fronting_campaign=data.get('primaryBotsCampaign', ''),
                    verifier_campaign=data.get('primaryUserSeries', ''),
                    port=int(data.get('primaryPort', 5060)),
                    dialer_settings=dialer_settings
                )
                
                # 10. Get Status
                status, created = Status.objects.get_or_create(status_name='Pending Approval')
                
                # 11. Create StatusHistory
                status_history = StatusHistory.objects.create(
                    status=status,
                    start_date=datetime.now(),
                    end_date=None
                )
                
                # 12. Create ClientCampaignModel (main entry)
                bot_count = int(data.get('numberOfBots', 0))
                
                client_campaign_model = ClientCampaignModel.objects.create(
                    client=client,
                    campaign_model=campaign_model,
                    status_history=status_history,
                    start_date=datetime.now(),
                    end_date=None,
                    is_custom=False,
                    custom_comments='',
                    current_remote_agents=data.get('customRequirements', ''),
                    is_active=False,  # Not active until approved
                    is_enabled=True,
                    is_approved=False,  # Requires admin approval
                    dialer_settings=dialer_settings,
                    bot_count=bot_count,
                    long_call_scripts_active=False,
                    disposition_set=False
                )
                
                # Return success response
                return JsonResponse({
                    'success': True,
                    'message': 'Integration request submitted successfully!',
                    'data': {
                        'username': username,
                        'client_id': client.client_id,
                        'client_name': company_name,
                        'campaign': campaign_name,
                        'model': model_name,
                        'transfer_setting': transfer_setting.name,
                        'bot_count': bot_count,
                        'campaign_model_id': client_campaign_model.id
                    }
                }, status=201)
        
        except Campaign.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected campaign does not exist'
            }, status=400)
        
        except Model.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Model configuration not found for selected settings'
            }, status=400)
        
        except TransferSettings.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Transfer settings not found'
            }, status=400)
        
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