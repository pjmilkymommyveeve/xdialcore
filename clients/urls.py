# clients/urls.py
from django.urls import path
from . import views, api_views

app_name = 'clients'

urlpatterns = [
    # Main pages (require login)
    path('', views.client_landing, name='client_landing'),
    path('campaign/<int:campaign_id>/dashboard/', views.campaign_dashboard, name='campaign_dashboard'),
    path('campaign/<int:campaign_id>/recordings/', views.campaign_recordings, name='campaign_recordings'),
    path('campaign/<int:campaign_id>/export/', views.data_export, name='data_export'),
    path('campaign/add/', views.add_campaign, name='add_campaign'),
    path('integration/request/', views.integration_request, name='integration_request'),
    path('api/recordings/', api_views.fetch_recordings, name='api_fetch_recordings'),
]