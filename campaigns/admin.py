from django.contrib import admin
from .models import (
    Model, Campaign, CampaignModel, CampaignRequirements,
    Status, StatusHistory, Voice, CampaignVoiceStats,
    ClientCampaignModel, ServerCampaignBots
)


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(CampaignModel)
class CampaignModelAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'model']
    list_filter = ['campaign']
    search_fields = ['campaign__name', 'model__name']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(CampaignRequirements)
class CampaignRequirementsAdmin(admin.ModelAdmin):
    list_display = ['name', 'long_call_scripts_active', 'bot_count']
    list_filter = ['long_call_scripts_active']
    search_fields = ['name', 'description']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ['status_name', 'updated_at']
    search_fields = ['status_name']
    readonly_fields = ['updated_at']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['status', 'start_date', 'end_date']
    list_filter = ['status', 'start_date']
    search_fields = ['status__status_name']
    date_hierarchy = 'start_date'
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(Voice)
class VoiceAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(CampaignVoiceStats)
class CampaignVoiceStatsAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'voice', 'interested_count']
    list_filter = ['campaign', 'voice']
    search_fields = ['campaign__name', 'voice__name']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_qa)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


class ServerCampaignBotsInline(admin.TabularInline):
    model = ServerCampaignBots
    extra = 1
    fields = ['server', 'extension', 'bot_count']


@admin.register(ClientCampaignModel)
class ClientCampaignModelAdmin(admin.ModelAdmin):
    list_display = [
        'client', 'campaign_model', 'is_active', 'is_enabled', 
        'start_date', 'end_date'
    ]
    list_filter = ['is_active', 'is_enabled', 'is_custom', 'start_date']
    search_fields = [
        'client__name', 
        'campaign_model__campaign__name',
        'campaign_model__model__name'
    ]
    readonly_fields = ['start_date']
    date_hierarchy = 'start_date'
    inlines = [ServerCampaignBotsInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'campaign_model', 'start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_active', 'is_enabled', 'status_history')
        }),
        ('Customization', {
            'fields': ('is_custom', 'custom_comments', 'current_remote_agents')
        }),
        ('Configuration', {
            'fields': ('dialer_settings', 'campaign_requirements')
        }),
    )
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa)
    
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_admin or request.user.is_onboarding or request.user.is_qa:
            return True
        if request.user.is_client and obj:
            return obj.client.client == request.user
        return False
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_admin:
            return True
        if request.user.is_onboarding:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa:
            return qs
        if request.user.is_client:
            return qs.filter(client__client=request.user)
        return qs.none()


@admin.register(ServerCampaignBots)
class ServerCampaignBotsAdmin(admin.ModelAdmin):
    list_display = ['client_campaign_model', 'server', 'extension', 'bot_count']
    list_filter = ['server']
    search_fields = [
        'client_campaign_model__client__name',
        'server__alias',
        'extension__extension_number'
    ]
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin

