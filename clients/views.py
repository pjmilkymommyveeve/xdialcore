from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
import logging
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Max
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


logger = logging.getLogger(__name__)

# Edit this only |
CATEGORY_MAPPING = {
    "greetingresponse": "Greeting Response",
    "notfeelinggood": "Not Feeling Good",
    "dnc": "Do Not Call",
    "honeypot_hardcoded": "Honeypot",
    "honeypot": "Honeypot",
    "spanishanswermachine": "Spanish Answering Machine",
    "answermachine": "Answering Machine",
    "already": "Already Customer",
    "rebuttal": "Rebuttal",
    "notinterested": "Not Interested",
    "busy": "Busy",
    "dnq": "Do Not Qualify",
    "qualified": "Qualified",
    "neutral": "Neutral",
    "repeatpitch": "Repeat Pitch"
}



@login_required(login_url='/accounts/login/')
@role_required([Role.CLIENT, Role.ONBOARDING, Role.ADMIN])
def client_landing(request):
    """Client landing page showing their campaigns"""
    # For admin/onboarding users, they can view all clients (but this view shows logged-in user's campaigns)
    if request.user.role.name in [Role.ADMIN, Role.ONBOARDING]:
        # Admin/onboarding users viewing as themselves - show their campaigns if they have a client profile
        try:
            client = Client.objects.get(client=request.user)
        except Client.DoesNotExist:
            return render(request, 'clients/client_landing.html', {
                'error': 'Client profile not found. Please contact administrator.'
            })
    else:
        # Regular client user
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
@role_required([Role.CLIENT, Role.ONBOARDING, Role.ADMIN])
def campaign_dashboard(request, campaign_id):
    """Campaign dashboard showing call records - latest stage only with combined categories"""
    try:
        logger.info(f"User {request.user.username} accessing campaign dashboard {campaign_id}")
        
        # For admin/onboarding users, skip client validation
        if request.user.role.name in [Role.ADMIN, Role.ONBOARDING]:
            logger.debug(f"Admin/Onboarding user access for campaign {campaign_id}")
            campaign = get_object_or_404(
                ClientCampaignModel.objects.select_related(
                    'campaign_model__campaign',
                    'campaign_model__model',
                    'client',
                ),
                id=campaign_id,
                is_enabled=True
            )
            client = campaign.client
        else:
            # For client users, validate they own this campaign
            logger.debug(f"Client user access for campaign {campaign_id}")
            try:
                client = Client.objects.get(client=request.user)
                logger.debug(f"Found client: {client.name}")
            except Client.DoesNotExist:
                logger.error(f"Client profile not found for user {request.user.username}")
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
        
        logger.info(f"Campaign found: {campaign.campaign_model.campaign.name}")
        
        # Get filter parameters
        search_query = request.GET.get('search', '').strip()
        list_id_query = request.GET.get('list_id', '').strip()
        start_date = request.GET.get('start_date', '')
        start_time = request.GET.get('start_time', '')
        end_date = request.GET.get('end_date', '')
        end_time = request.GET.get('end_time', '')
        selected_categories = request.GET.getlist('categories')
        
        logger.debug(f"Filters - search: {search_query}, list_id: {list_id_query}, dates: {start_date} to {end_date}")
        
        # Default to today if no date filters are provided
        has_any_filter = any([search_query, list_id_query, start_date, end_date, selected_categories])
        
        if not has_any_filter:
            today = datetime.now().date()
            start_date = today.strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            logger.debug(f"No filters provided, defaulting to today: {start_date}")
        
        # Get latest stage for each number (simplified approach)
        logger.info("Fetching latest stage for each number...")
        try:
            latest_calls_by_number = Call.objects.filter(
                client_campaign_model=campaign
            ).values('number').annotate(
                max_stage=Max('stage')
            )
            
            # Build a dict for quick lookup
            latest_stages = {item['number']: item['max_stage'] for item in latest_calls_by_number}
            logger.debug(f"Found {len(latest_stages)} unique numbers with latest stages")
            
        except Exception as e:
            logger.error(f"Error fetching latest stages: {str(e)}", exc_info=True)
            return render(request, 'clients/campaign_dashboard.html', {
                'error': f'Database error while fetching call data: {str(e)}'
            })
        
        # Build base query for category counts
        logger.info("Building category counts query...")
        try:
            category_count_query = Call.objects.filter(
                client_campaign_model=campaign
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
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    if start_time:
                        time_obj = datetime.strptime(start_time, '%H:%M').time()
                        start_datetime = datetime.combine(start_datetime.date(), time_obj)
                    category_count_query = category_count_query.filter(timestamp__gte=start_datetime)
                    logger.debug(f"Applied start date filter: {start_datetime}")
                except ValueError as e:
                    logger.error(f"Invalid start date format: {start_date} - {str(e)}")
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    if end_time:
                        time_obj = datetime.strptime(end_time, '%H:%M').time()
                        end_datetime = datetime.combine(end_datetime.date(), time_obj)
                    else:
                        end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
                    category_count_query = category_count_query.filter(timestamp__lte=end_datetime)
                    logger.debug(f"Applied end date filter: {end_datetime}")
                except ValueError as e:
                    logger.error(f"Invalid end date format: {end_date} - {str(e)}")
            
            # Filter to only latest stage calls
            latest_stage_calls = []
            for call in category_count_query.select_related('response_category'):
                if call.number in latest_stages and call.stage == latest_stages[call.number]:
                    latest_stage_calls.append(call)
            
            logger.debug(f"Filtered to {len(latest_stage_calls)} calls at latest stage")
            
        except Exception as e:
            logger.error(f"Error building category count query: {str(e)}", exc_info=True)
            return render(request, 'clients/campaign_dashboard.html', {
                'error': f'Error processing filters: {str(e)}'
            })
        
        # Get category counts
        logger.info("Processing category counts...")
        try:
            # Get ALL categories from database
            all_db_categories = ResponseCategory.objects.all().values('id', 'name', 'color')
            logger.debug(f"Found {len(all_db_categories)} categories in database")
            
            # Count categories from filtered calls
            category_counts_raw = {}
            for call in latest_stage_calls:
                if call.response_category:
                    cat_id = call.response_category.id
                    if cat_id not in category_counts_raw:
                        category_counts_raw[cat_id] = {
                            'id': cat_id,
                            'name': call.response_category.name,
                            'color': call.response_category.color,
                            'count': 0
                        }
                    category_counts_raw[cat_id]['count'] += 1
            
            # Combine categories according to mapping
            combined_counts = {}
            category_colors = {}
            
            # Initialize all possible combined categories with zero counts
            for db_cat in all_db_categories:
                original_name = db_cat['name'] or 'UNKNOWN'
                combined_name = CATEGORY_MAPPING.get(original_name, original_name)
                
                if combined_name not in combined_counts:
                    combined_counts[combined_name] = 0
                    category_colors[combined_name] = db_cat['color'] or '#6B7280'
            
            # Add actual counts
            for cat_data in category_counts_raw.values():
                original_name = cat_data['name'] or 'UNKNOWN'
                combined_name = CATEGORY_MAPPING.get(original_name, original_name)
                combined_counts[combined_name] += cat_data['count']
                if not category_colors.get(combined_name):
                    category_colors[combined_name] = cat_data['color'] or '#6B7280'
            
            # Build the all_categories list
            all_categories = []
            for combined_name, count in sorted(combined_counts.items()):
                all_categories.append({
                    'name': combined_name.capitalize(),
                    'color': category_colors.get(combined_name, '#6B7280'),
                    'count': count,
                    'original_name': combined_name
                })
            
            logger.debug(f"Processed {len(all_categories)} combined categories")
            
        except Exception as e:
            logger.error(f"Error processing category counts: {str(e)}", exc_info=True)
            return render(request, 'clients/campaign_dashboard.html', {
                'error': f'Error processing category data: {str(e)}'
            })
        
        # Build calls query
        logger.info("Building main calls query...")
        try:
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
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    if start_time:
                        time_obj = datetime.strptime(start_time, '%H:%M').time()
                        start_datetime = datetime.combine(start_datetime.date(), time_obj)
                    calls = calls.filter(timestamp__gte=start_datetime)
                except ValueError as e:
                    logger.error(f"Invalid start date in calls filter: {str(e)}")
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    if end_time:
                        time_obj = datetime.strptime(end_time, '%H:%M').time()
                        end_datetime = datetime.combine(end_datetime.date(), time_obj)
                    else:
                        end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
                    calls = calls.filter(timestamp__lte=end_datetime)
                except ValueError as e:
                    logger.error(f"Invalid end date in calls filter: {str(e)}")
            
            # Filter by combined categories if selected
            if selected_categories:
                original_names = [
                    name for name, combined in CATEGORY_MAPPING.items() 
                    if combined in selected_categories
                ]
                original_names.extend([cat for cat in selected_categories if cat not in CATEGORY_MAPPING.values()])
                calls = calls.filter(response_category__name__in=original_names)
            
            # Filter to latest stage only
            calls_list = []
            for call in calls:
                if call.number in latest_stages and call.stage == latest_stages[call.number]:
                    calls_list.append(call)
            
            total_calls = len(calls_list)
            logger.info(f"Total calls after filtering: {total_calls}")
            
        except Exception as e:
            logger.error(f"Error building calls query: {str(e)}", exc_info=True)
            return render(request, 'clients/campaign_dashboard.html', {
                'error': f'Error fetching call records: {str(e)}'
            })
        
        # Process calls data
        logger.info("Processing calls data for display...")
        try:
            calls_data = []
            for call in calls_list[:50]:
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
            
            logger.debug(f"Processed {len(calls_data)} calls for display")
            
        except Exception as e:
            logger.error(f"Error processing calls data: {str(e)}", exc_info=True)
            return render(request, 'clients/campaign_dashboard.html', {
                'error': f'Error formatting call data: {str(e)}'
            })
        
        # Build context
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
        
        logger.info(f"Successfully rendered dashboard for campaign {campaign_id}")
        return render(request, 'clients/campaign_dashboard.html', context)
        
    except ClientCampaignModel.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found or not enabled")
        return render(request, 'clients/campaign_dashboard.html', {
            'error': 'Campaign not found or access denied.'
        })
    
    except Exception as e:
        logger.error(f"Unexpected error in campaign_dashboard for campaign {campaign_id}: {str(e)}", exc_info=True)
        return render(request, 'clients/campaign_dashboard.html', {
            'error': f'An unexpected error occurred. Please contact support. Error: {str(e)}'
        })
        
@login_required(login_url='/accounts/login/')
@role_required([Role.CLIENT, Role.ONBOARDING, Role.ADMIN])
def campaign_recordings(request, campaign_id):
    """
    Recordings page - provides server configs for client-side fetching.
    Frontend will call backend API endpoint which fetches from recording servers.
    """
    # For admin/onboarding users, skip client validation
    if request.user.role.name in [Role.ADMIN, Role.ONBOARDING]:
        campaign = get_object_or_404(
            ClientCampaignModel.objects.select_related(
                'campaign_model__campaign',
                'campaign_model__model',
                'client',
            ).prefetch_related('server_bots__server', 'server_bots__extension'),
            id=campaign_id,
            is_enabled=True
        )
        client = campaign.client
    else:
        # For client users, validate they own this campaign
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
@role_required([Role.CLIENT, Role.ONBOARDING, Role.ADMIN])
def data_export(request, campaign_id):
    """Data export page with combined category mapping - COMPLETE FIX"""
    logger.info(f"=== DATA EXPORT START === User: {request.user.username}, Campaign: {campaign_id}, Method: {request.method}")
    
    try:
        # Get campaign and client (existing code)
        if request.user.role.name in [Role.ADMIN, Role.ONBOARDING]:
            logger.debug(f"Admin/Onboarding user access for campaign {campaign_id}")
            campaign = get_object_or_404(
                ClientCampaignModel.objects.select_related(
                    'campaign_model__campaign',
                    'campaign_model__model',
                    'client',
                ),
                id=campaign_id,
                is_enabled=True
            )
            client = campaign.client
        else:
            logger.debug(f"Client user access for campaign {campaign_id}")
            try:
                client = Client.objects.get(client=request.user)
                logger.debug(f"Found client: {client.name}")
            except Client.DoesNotExist:
                logger.error(f"Client profile not found for user {request.user.username}")
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
        
        logger.info(f"Campaign found: {campaign.campaign_model.campaign.name}")
    
    except Exception as e:
        logger.error(f"Error fetching campaign: {str(e)}", exc_info=True)
        return render(request, 'clients/data_export.html', {
            'error': f'Error loading campaign: {str(e)}'
        })
    
    if request.method == 'POST':
        logger.info("POST request - Starting export")
        try:
            export_data_json = request.POST.get('export_data', '{}')
            logger.debug(f"Export data JSON: {export_data_json}")
            export_data = json.loads(export_data_json)
            logger.debug(f"Parsed export data: {export_data}")
            
            # Get latest stage for each number
            logger.info("Fetching latest stages...")
            latest_calls_by_number = Call.objects.filter(
                client_campaign_model=campaign
            ).values('number').annotate(
                max_stage=Max('stage')
            )
            latest_stages = {item['number']: item['max_stage'] for item in latest_calls_by_number}
            logger.debug(f"Found {len(latest_stages)} unique numbers with latest stages")
            
            calls = Call.objects.filter(
                client_campaign_model=campaign
            ).select_related('response_category', 'voice')
            
            logger.info("Applying filters...")
            
            # Apply list ID filter
            list_ids = export_data.get('list_ids', [])
            if list_ids:
                logger.debug(f"Filtering by list_ids: {list_ids}")
                calls = calls.filter(list_id__in=list_ids)
            
            # ✅ FIXED: Handle combined categories properly using combined_name
            selected_combined_categories = export_data.get('categories', [])
            if selected_combined_categories:
                logger.debug(f"Selected combined categories: {selected_combined_categories}")
                
                # Build reverse mapping: combined_name -> [original_names]
                reverse_mapping = {}
                for original_name, combined_name in CATEGORY_MAPPING.items():
                    if combined_name not in reverse_mapping:
                        reverse_mapping[combined_name] = []
                    reverse_mapping[combined_name].append(original_name)
                
                # Find all original category names that map to selected combined categories
                original_category_names = []
                for selected_combined in selected_combined_categories:
                    # Handle both mapped and unmapped categories
                    if selected_combined in reverse_mapping:
                        original_category_names.extend(reverse_mapping[selected_combined])
                    else:
                        # Category not in mapping, use as-is
                        original_category_names.append(selected_combined)
                
                logger.info(f"Matched original category names: {original_category_names}")
                
                if original_category_names:
                    calls = calls.filter(response_category__name__in=original_category_names)
                    logger.info(f"Filtered calls count after category filter: {calls.count()}")
            
            # Apply date filters
            start_date = export_data.get('start_date')
            start_time = export_data.get('start_time')
            end_date = export_data.get('end_date')
            end_time = export_data.get('end_time')
            
            if start_date:
                logger.debug(f"Start date filter: {start_date} {start_time}")
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    if start_time:
                        time_obj = datetime.strptime(start_time, '%H:%M').time()
                        start_datetime = datetime.combine(start_datetime.date(), time_obj)
                    calls = calls.filter(timestamp__gte=start_datetime)
                    logger.debug(f"Applied start datetime: {start_datetime}")
                except Exception as e:
                    logger.error(f"Error parsing start date: {str(e)}")
            
            if end_date:
                logger.debug(f"End date filter: {end_date} {end_time}")
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    if end_time:
                        time_obj = datetime.strptime(end_time, '%H:%M').time()
                        end_datetime = datetime.combine(end_datetime.date(), time_obj)
                    else:
                        end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
                    calls = calls.filter(timestamp__lte=end_datetime)
                    logger.debug(f"Applied end datetime: {end_datetime}")
                except Exception as e:
                    logger.error(f"Error parsing end date: {str(e)}")
            
            logger.info(f"Total calls before latest stage filter: {calls.count()}")
            
            # Filter to latest stage only
            logger.info("Filtering to latest stage only...")
            filtered_calls = []
            for call in calls:
                if call.number in latest_stages and call.stage == latest_stages[call.number]:
                    filtered_calls.append(call)
            
            logger.info(f"✓ FINAL: Total calls after latest stage filter: {len(filtered_calls)}")
            
            if len(filtered_calls) == 0:
                logger.warning("No calls matched the filters!")
            
            # Create CSV
            logger.info("Creating CSV response...")
            response = HttpResponse(content_type='text/csv')
            filename = f"call_data_{campaign.campaign_model.campaign.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Call ID', 'Phone Number', 'List ID', 'Category', 'Timestamp',
                'Transferred', 'Stage', 'Voice', 'Transcription'
            ])
            
            for call in filtered_calls:
                # Map original category to combined category name
                original_category_name = call.response_category.name if call.response_category else 'Unknown'
                combined_category_name = CATEGORY_MAPPING.get(
                    original_category_name,
                    original_category_name
                )
                
                writer.writerow([
                    call.id,
                    call.number,
                    call.list_id or '',
                    combined_category_name.capitalize(),
                    call.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Yes' if call.transferred else 'No',
                    call.stage or 0,
                    call.voice.name if call.voice else 'Unknown',
                    call.transcription or ''
                ])
            
            logger.info(f"✓ CSV export successful: {len(filtered_calls)} records written")
            return response
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}", exc_info=True)
            return render(request, 'clients/data_export.html', {
                'error': f'Invalid export data format: {str(e)}',
                'client_name': client.name,
                'campaign': {
                    'id': campaign.id,
                    'name': campaign.campaign_model.campaign.name,
                    'model': campaign.campaign_model.model.name,
                },
                'list_ids': [],
                'all_categories': [],
            })
        
        except Exception as e:
            logger.error(f"Error during export: {str(e)}", exc_info=True)
            return render(request, 'clients/data_export.html', {
                'error': f'Error generating export: {str(e)}',
                'client_name': client.name,
                'campaign': {
                    'id': campaign.id,
                    'name': campaign.campaign_model.campaign.name,
                    'model': campaign.campaign_model.model.name,
                },
                'list_ids': [],
                'all_categories': [],
            })
    
    # GET request - display form with combined categories
    logger.info("GET request - Displaying export form")
    try:
        logger.info("Fetching list IDs...")
        list_ids = Call.objects.filter(
            client_campaign_model=campaign,
            list_id__isnull=False
        ).exclude(list_id='').values_list('list_id', flat=True).distinct().order_by('list_id')
        logger.debug(f"Found {len(list_ids)} unique list IDs")
        
        # Get latest stage for each number for accurate counts
        logger.info("Fetching latest stages for counts...")
        latest_calls_by_number = Call.objects.filter(
            client_campaign_model=campaign
        ).values('number').annotate(
            max_stage=Max('stage')
        )
        latest_stages = {item['number']: item['max_stage'] for item in latest_calls_by_number}
        logger.debug(f"Found {len(latest_stages)} unique numbers")
        
        # Get all categories from database
        logger.info("Fetching categories...")
        all_db_categories = ResponseCategory.objects.all()
        logger.debug(f"Total categories in database: {all_db_categories.count()}")
        
        # Get call counts per original category (ONLY LATEST STAGE)
        logger.info("Counting calls by category (latest stage only)...")
        all_calls = Call.objects.filter(
            client_campaign_model=campaign
        ).select_related('response_category')
        
        total_calls_before_filter = all_calls.count()
        logger.debug(f"Total calls before latest stage filter: {total_calls_before_filter}")
        
        # Filter to latest stage only
        latest_stage_calls = []
        for call in all_calls:
            if call.number in latest_stages and call.stage == latest_stages[call.number]:
                latest_stage_calls.append(call)
        
        logger.debug(f"Total calls after latest stage filter: {len(latest_stage_calls)}")
        
        # Count categories from latest stage calls
        category_count_dict = {}
        for call in latest_stage_calls:
            if call.response_category:
                cat_name = call.response_category.name or 'UNKNOWN'
                category_count_dict[cat_name] = category_count_dict.get(cat_name, 0) + 1
        
        logger.debug(f"Category counts (raw): {category_count_dict}")
        
        # Combine categories according to mapping
        logger.info("Combining categories according to mapping...")
        combined_counts = {}
        
        for db_cat in all_db_categories:
            original_name = db_cat.name or 'UNKNOWN'
            combined_name = CATEGORY_MAPPING.get(original_name, original_name)
            count = category_count_dict.get(original_name, 0)
            
            logger.debug(f"Category: {original_name} -> {combined_name} (count: {count})")
            
            # Accumulate counts for combined categories
            if combined_name in combined_counts:
                combined_counts[combined_name] += count
            else:
                combined_counts[combined_name] = count
        
        logger.debug(f"Combined counts: {combined_counts}")
        
        # ✅ FIXED: Build all_categories with proper combined_name for form submission
        all_categories = []
        for combined_name, count in sorted(combined_counts.items()):
            all_categories.append({
                'name': combined_name.capitalize(),
                'combined_name': combined_name,  # This is what gets sent to backend
                'count': count
            })
        
        logger.info(f"Built {len(all_categories)} categories for display")
        logger.info(f"Total records (latest stage only): {len(latest_stage_calls)}")
        
        context = {
            'client_name': client.name,
            'campaign': {
                'id': campaign.id,
                'name': campaign.campaign_model.campaign.name,
                'model': campaign.campaign_model.model.name,
            },
            'list_ids': list(list_ids),
            'all_categories': all_categories,
            'total_records': len(latest_stage_calls),
        }
        
        logger.info(f"Rendering data_export.html with {len(list_ids)} list_ids and {len(all_categories)} categories")
        return render(request, 'clients/data_export.html', context)
    
    except Exception as e:
        logger.error(f"Error in GET request: {str(e)}", exc_info=True)
        return render(request, 'clients/data_export.html', {
            'error': f'Error loading export form: {str(e)}',
            'client_name': client.name,
            'campaign': {
                'id': campaign.id,
                'name': campaign.campaign_model.campaign.name,
                'model': campaign.campaign_model.model.name,
            },
            'list_ids': [],
            'all_categories': [],
            'total_records': 0,
        })
    
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
            # Get all unique models available for this campaign
            campaign_models = CampaignModel.objects.filter(
                campaign=campaign
            ).select_related('model').prefetch_related('model__transfer_settings')
            
            # Group by model name and collect transfer settings
            models_dict = {}
            for cm in campaign_models:
                model_name = cm.model.name
                if model_name not in models_dict:
                    models_dict[model_name] = []
                
                # Get all transfer settings for this model
                for ts in cm.model.transfer_settings.all():
                    # Avoid duplicates
                    if not any(t['id'] == ts.id for t in models_dict[model_name]):
                        models_dict[model_name].append({
                            'id': ts.id,
                            'name': ts.name
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
                model = Model.objects.filter(
                    name=model_name,
                    transfer_settings=transfer_setting
                ).first()
                
                if not model:
                    return JsonResponse({
                        'success': False,
                        'message': 'Model configuration not found for selected settings'
                    }, status=400)
                
                # 6. Get or create CampaignModel
                campaign_model, created = CampaignModel.objects.get_or_create(
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
@login_required(login_url='/accounts/login/')
@role_required([Role.CLIENT, Role.ONBOARDING, Role.ADMIN])
def add_campaign(request):
    """
    Add new campaign for existing logged-in client.
    GET: Display form with dynamic transfer settings
    POST: Process form and create ClientCampaignModel entry
    """
    # Get client profile
    if request.user.role.name in [Role.ADMIN, Role.ONBOARDING]:
        try:
            client = Client.objects.get(client=request.user)
        except Client.DoesNotExist:
            return render(request, 'clients/add_campaign.html', {
                'error': 'Client profile not found. Please contact administrator.'
            })
    else:
        try:
            client = Client.objects.get(client=request.user)
        except Client.DoesNotExist:
            return render(request, 'clients/add_campaign.html', {
                'error': 'Client profile not found. Please contact administrator.'
            })
    
    if request.method == 'GET':
        # Get all campaigns
        campaigns = Campaign.objects.all().order_by('name')
        
        # Build campaign configuration for JavaScript
        campaign_config = {}
        for campaign in campaigns:
            # Get all unique models available for this campaign
            campaign_models = CampaignModel.objects.filter(
                campaign=campaign
            ).select_related('model').prefetch_related('model__transfer_settings')
            
            # Group by model name and collect transfer settings
            models_dict = {}
            for cm in campaign_models:
                model_name = cm.model.name
                if model_name not in models_dict:
                    models_dict[model_name] = []
                
                # Get all transfer settings for this model
                for ts in cm.model.transfer_settings.all():
                    # Avoid duplicates
                    if not any(t['id'] == ts.id for t in models_dict[model_name]):
                        models_dict[model_name].append({
                            'id': ts.id,
                            'name': ts.name
                        })
            
            campaign_config[campaign.name] = models_dict
        
        # Get all transfer settings
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
            'client_name': client.name,
            'campaigns': campaigns,
            'campaign_config': json.dumps(campaign_config),
            'transfer_settings': json.dumps(transfer_settings_data)
        }
        
        return render(request, 'clients/add_campaign.html', context)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            with transaction.atomic():
                # Get Campaign
                campaign_name = data.get('campaign')
                campaign = Campaign.objects.get(name=campaign_name)
                
                # Get Transfer Settings and Model
                transfer_settings_id = data.get('transferSettingsId')
                
                if not transfer_settings_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Transfer settings selection is required'
                    }, status=400)
                
                transfer_setting = TransferSettings.objects.get(id=transfer_settings_id)
                
                # Get the model
                model_name = data.get('modelName')
                model = Model.objects.filter(
                    name=model_name,
                    transfer_settings=transfer_setting
                ).first()
                
                if not model:
                    return JsonResponse({
                        'success': False,
                        'message': 'Model configuration not found for selected settings'
                    }, status=400)
                
                # Get or create CampaignModel
                campaign_model, created = CampaignModel.objects.get_or_create(
                    campaign=campaign,
                    model=model
                )
                
                # Create CloserDialer (if separate dialer)
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
                
                # Create DialerSettings
                dialer_settings = DialerSettings.objects.create(
                    closer_dialer=closer_dialer
                )
                
                # Create PrimaryDialer
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
                
                # Get Status
                status, created = Status.objects.get_or_create(status_name='Pending Approval')
                
                # Create StatusHistory
                status_history = StatusHistory.objects.create(
                    status=status,
                    start_date=datetime.now(),
                    end_date=None
                )
                
                # Create ClientCampaignModel
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
                    is_active=False,
                    is_enabled=True,
                    is_approved=False,
                    dialer_settings=dialer_settings,
                    bot_count=bot_count,
                    long_call_scripts_active=False,
                    disposition_set=False
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Campaign request submitted successfully! It will be reviewed by our team.',
                    'data': {
                        'client_name': client.name,
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
        
        except TransferSettings.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Transfer settings not found'
            }, status=400)
        
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