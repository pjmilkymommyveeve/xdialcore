from django.contrib import admin
from .models import Call


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'stage', 'timestamp', 'client_campaign_model']
    list_filter = ['stage', 'timestamp']
    search_fields = ['number', 'list_id', 'transcription']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Call Information', {
            'fields': ('client_campaign_model', 'number', 'timestamp')
        }),
        ('Details', {
            'fields': ('stage', 'response_category', 'list_id')
        }),
        ('Transcription', {
            'fields': ('transcription',),
            'classes': ('collapse',)
        }),
    )
    
    def has_module_permission(self, request):
        # All roles can access calls
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa or 
                request.user.is_client)
    
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.is_admin or request.user.is_qa:
            return True
        if request.user.is_client and obj:
            return obj.client_campaign_model.client.client == request.user
        return False
    
    def has_change_permission(self, request, obj=None):
        # Only admin and QA can edit calls
        return request.user.is_superuser or request.user.is_admin or request.user.is_qa
    
    def has_delete_permission(self, request, obj=None):
        # Only admin can delete calls
        return request.user.is_superuser or request.user.is_admin
    
    def has_add_permission(self, request):
        # Only admin and onboarding can add calls manually
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin or request.user.is_qa:
            return qs
        if request.user.is_client:
            return qs.filter(client_campaign_model__client__client=request.user)
        return qs.none()