from django.contrib import admin
from django import forms
from .models import Call
from campaigns.models import ClientCampaignModel


class CallForm(forms.ModelForm):
    """Custom form with filtered client campaigns"""
    
    class Meta:
        model = Call
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter client_campaign_model: only non-archived clients
        self.fields['client_campaign_model'].queryset = ClientCampaignModel.objects.filter(
            client__is_archived=False
        ).select_related(
            'client', 'campaign_model__campaign', 'campaign_model__model'
        ).order_by('client__name', 'campaign_model__campaign__name')
        
        # Better label for dropdown
        self.fields['client_campaign_model'].label_from_instance = lambda obj: (
            f"{obj.client.name} - {obj.campaign_model.campaign.name} - {obj.campaign_model.model.name}"
        )


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    form = CallForm
    list_display = ['id', 'number', 'stage', 'timestamp', 'get_client', 'get_campaign']
    list_filter = ['stage', 'timestamp', 'client_campaign_model__campaign_model__campaign']
    search_fields = ['number', 'list_id', 'transcription', 'client_campaign_model__client__name']
    readonly_fields = ['client_campaign_model', 'number', 'timestamp', 'stage', 'response_category', 'list_id', 'transcription']
    date_hierarchy = 'timestamp'
    
    # Optimize queries
    list_select_related = [
        'client_campaign_model__client',
        'client_campaign_model__campaign_model__campaign',
        'client_campaign_model__campaign_model__model'
    ]
    
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
    
    def get_client(self, obj):
        """Display client name"""
        return obj.client_campaign_model.client.name
    get_client.short_description = 'Client'
    get_client.admin_order_field = 'client_campaign_model__client__name'
    
    def get_campaign(self, obj):
        """Display campaign name"""
        return obj.client_campaign_model.campaign_model.campaign.name
    get_campaign.short_description = 'Campaign'
    get_campaign.admin_order_field = 'client_campaign_model__campaign_model__campaign__name'
    
    def has_module_permission(self, request):
        """Allow viewing module if authenticated with proper role"""
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding or 
                request.user.is_qa or 
                request.user.is_client)
    
    def has_view_permission(self, request, obj=None):
        """Allow viewing calls"""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_admin or request.user.is_qa or request.user.is_onboarding:
            return True
        if request.user.is_client and obj:
            return obj.client_campaign_model.client.client == request.user
        if request.user.is_client and not obj:
            # Allow viewing list for clients
            return True
        return False
    
    def has_add_permission(self, request):
        """Disable adding calls through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing calls through admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting calls through admin"""
        return False
    
    def get_queryset(self, request):
        """Filter queryset based on user role"""
        qs = super().get_queryset(request)
        if not request.user.is_authenticated:
            return qs.none()
        if request.user.is_superuser or request.user.is_admin or request.user.is_qa or request.user.is_onboarding:
            return qs
        if request.user.is_client:
            return qs.filter(client_campaign_model__client__client=request.user)
        return qs.none()
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """Override to make all fields readonly in change form"""
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_save_and_add_another'] = False
        return super().changeform_view(request, object_id, form_url, extra_context)