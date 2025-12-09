# clients/api_views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.decorators import role_required
from accounts.models import Role
from infrastructure.models import Server
import requests
import re


def parse_duration_to_seconds(duration_str):
    """Convert duration string (MM:SS or HH:MM:SS) to seconds for sorting."""
    if not duration_str or duration_str == 'N/A':
        return 0
    
    parts = duration_str.split(':')
    try:
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        return 0
    return 0


def parse_size_to_bytes(size_str):
    """Convert size string (e.g., '1.5 MB') to bytes for sorting."""
    if not size_str or size_str == 'N/A':
        return 0
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024
    }
    
    match = re.match(r'^([\d.]+)\s*([A-Z]+)$', size_str, re.IGNORECASE)
    if match:
        try:
            value = float(match.group(1))
            unit = match.group(2).upper()
            return value * units.get(unit, 1)
        except (ValueError, KeyError):
            return 0
    return 0


@login_required
@role_required([Role.CLIENT, Role.ADMIN])
@require_http_methods(["GET"])
def fetch_recordings(request):
    """
    Fetch recordings from a recording server with server-side pagination and sorting.
    
    Query Parameters:
    - server_id (required): ID of the server
    - date (required): Date in YYYYMMDD format
    - extension (required): Extension to filter recordings
    - number (optional): Phone number to filter recordings
    - page (optional): Page number (default: 1)
    - page_size (optional): Records per page (default: 100, max: 500)
    - sort_by (optional): Column to sort by (time, phone, duration, size)
    - sort_dir (optional): Sort direction (asc, desc)
    
    Returns:
    JSON response with:
    - recordings: List of recordings for current page
    - total_count: Total number of recordings
    - page: Current page number
    - page_size: Records per page
    - total_pages: Total number of pages
    """
    server_id = request.GET.get('server_id')
    date = request.GET.get('date')
    extension = request.GET.get('extension')
    number = request.GET.get('number')
    
    # Pagination parameters
    try:
        page = int(request.GET.get('page', 1))
        page = max(1, page)  # Ensure page is at least 1
    except (ValueError, TypeError):
        page = 1
    
    try:
        page_size = int(request.GET.get('page_size', 100))
        page_size = min(max(1, page_size), 500)  # Clamp between 1 and 500
    except (ValueError, TypeError):
        page_size = 100
    
    # Sort parameters
    sort_by = request.GET.get('sort_by', 'time')
    sort_dir = request.GET.get('sort_dir', 'desc')
    
    # Validate sort parameters
    valid_sort_columns = ['time', 'phone', 'duration', 'size']
    if sort_by not in valid_sort_columns:
        sort_by = 'time'
    
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'desc'
    
    # Validate required parameters
    if not all([server_id, date, extension]):
        return JsonResponse({
            'error': 'Missing required parameters: server_id, date, extension'
        }, status=400)
    
    # Validate server_id is integer
    try:
        server_id = int(server_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid server_id'}, status=400)
    
    # Validate date format (YYYYMMDD)
    if not (len(date) == 8 and date.isdigit()):
        return JsonResponse({
            'error': 'Invalid date format. Expected YYYYMMDD'
        }, status=400)
    
    # Get domain from database
    try:
        server = Server.objects.get(id=server_id)
        domain = server.domain
    except Server.DoesNotExist:
        return JsonResponse({'error': 'Server not found'}, status=404)
    
    if not domain:
        return JsonResponse({'error': 'Server domain not configured'}, status=404)
    
    # Ensure domain ends with /
    if not domain.endswith('/'):
        domain += '/'
    
    # Construct full API URL
    api_url = f"{domain}server_api/fetch_recording.php"
    
    # Build request parameters for recording server
    params = {
        'date': date,
        'extension': extension
    }
    
    if number:
        params['number'] = number
    
    # Make request to recording server
    try:
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Convert to list if needed
        if isinstance(data, dict):
            recordings = list(data.values())
        elif isinstance(data, list):
            recordings = data
        else:
            recordings = []
        
        # Get total count before sorting/pagination
        total_count = len(recordings)
        
        # Sort recordings server-side
        if sort_by == 'time':
            recordings.sort(
                key=lambda x: x.get('time', ''),
                reverse=(sort_dir == 'desc')
            )
        elif sort_by == 'phone':
            recordings.sort(
                key=lambda x: x.get('phone_number') or x.get('number', ''),
                reverse=(sort_dir == 'desc')
            )
        elif sort_by == 'duration':
            recordings.sort(
                key=lambda x: parse_duration_to_seconds(x.get('duration', '')),
                reverse=(sort_dir == 'desc')
            )
        elif sort_by == 'size':
            recordings.sort(
                key=lambda x: parse_size_to_bytes(x.get('size', '')),
                reverse=(sort_dir == 'desc')
            )
        
        # Calculate pagination
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get page slice
        paginated_recordings = recordings[start_idx:end_idx]
        
        return JsonResponse({
            'recordings': paginated_recordings,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        })
        
    except requests.exceptions.Timeout:
        return JsonResponse({
            'error': 'Request to recording server timed out'
        }, status=504)
    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'error': 'Could not connect to recording server'
        }, status=503)
    except requests.exceptions.HTTPError as e:
        return JsonResponse({
            'error': f'Recording server returned error: {e.response.status_code}'
        }, status=e.response.status_code)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'error': f'Failed to fetch recordings: {str(e)}'
        }, status=500)
    except ValueError:
        return JsonResponse({
            'error': 'Invalid JSON response from recording server'
        }, status=502)