from django.contrib import admin
from django import forms
from django.utils import timezone
from django.db import transaction
from .models import (
    TransferSettings,
    Model,
    Campaign,
    CampaignModel,
    Voice,
    ResponseCategory,
    Status,
    StatusHistory,
    PrimaryDialer,
    CloserDialer,
    DialerSettings,
    ClientCampaignModel,
    ServerCampaignBots
)
from clients.models import Client
from infrastructure.models import Server, Extension


# ============================================================================
# SECTION 1: INLINE ADMINS FOR NESTED MODELS
# ============================================================================

class ServerCampaignBotsInline(admin.TabularInline):
    model = ServerCampaignBots
    extra = 1
    fields = ['server', 'extension', 'bot_count']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "server":
            kwargs["queryset"] = Server.objects.order_by('alias', 'ip')
        if db_field.name == "extension":
            kwargs["queryset"] = Extension.objects.order_by('extension_number')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PrimaryDialerInline(admin.TabularInline):
    """Inline for managing Primary Dialers within DialerSettings"""
    model = PrimaryDialer
    extra = 1
    fields = ['admin_link', 'admin_username', 'admin_password', 'fronting_campaign', 'verifier_campaign', 'port']
    verbose_name = 'Primary Dialer'
    verbose_name_plural = 'Primary Dialers'


# ============================================================================
# SECTION 2: CAMPAIGN MODEL WITH INLINE CAMPAIGN AND MODEL MANAGEMENT
# ============================================================================

class CampaignInline(admin.StackedInline):
    model = Campaign
    extra = 0
    fields = ['name', 'description']
    show_change_link = True


class ModelInline(admin.StackedInline):
    model = Model
    extra = 0
    fields = ['name', 'description', 'transfer_settings']
    show_change_link = True


@admin.register(CampaignModel)
class CampaignModelAdmin(admin.ModelAdmin):
    list_display = ['get_campaign_name', 'get_model_name']
    list_filter = ['campaign']
    search_fields = ['campaign__name', 'model__name']
    
    fieldsets = (
        ('Campaign-Model Pairing', {
            'fields': ('campaign', 'model')
        }),
    )

    def get_campaign_name(self, obj):
        return obj.campaign.name
    get_campaign_name.short_description = 'Campaign'
    get_campaign_name.admin_order_field = 'campaign__name'

    def get_model_name(self, obj):
        return obj.model.name
    get_model_name.short_description = 'Model'
    get_model_name.admin_order_field = 'model__name'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "campaign":
            kwargs["queryset"] = Campaign.objects.order_by('name')
        if db_field.name == "model":
            kwargs["queryset"] = Model.objects.select_related('transfer_settings').order_by('name')
            # Customize the display to show model name with transfer settings
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            formfield.label_from_instance = lambda obj: (
                f"{obj.name} - {obj.transfer_settings.name}" 
                if obj.transfer_settings 
                else f"{obj.name} - No Transfer Settings"
            )
            return formfield
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin

# ============================================================================
# SECTION 3: STANDALONE MODELS (TransferSettings, Campaign, Model, Voice, ResponseCategory)
# ============================================================================

@admin.register(TransferSettings)
class TransferSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_model_count']
    search_fields = ['name']

    def get_model_count(self, obj):
        """Display number of models using this transfer setting"""
        return obj.models.count()
    get_model_count.short_description = 'Models Using'

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'get_transfer_settings']
    search_fields = ['name', 'description']
    list_filter = ['transfer_settings']

    def get_transfer_settings(self, obj):
        return obj.transfer_settings.name if obj.transfer_settings else "Not Set"
    get_transfer_settings.short_description = 'Transfer Settings'
    get_transfer_settings.admin_order_field = 'transfer_settings__name'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "transfer_settings":
            kwargs["queryset"] = TransferSettings.objects.order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(Voice)
class VoiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_call_count']
    search_fields = ['name']

    def get_call_count(self, obj):
        """Display number of calls using this voice"""
        return obj.calls.count()
    get_call_count.short_description = 'Total Calls'

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(ResponseCategory)
class ResponseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'get_call_count']
    search_fields = ['name']
    list_filter = ['color']

    def get_call_count(self, obj):
        """Display number of calls with this response category"""
        return obj.calls.count()
    get_call_count.short_description = 'Total Calls'

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


# ============================================================================
# SECTION 4: DIALER MANAGEMENT
# ============================================================================

@admin.register(PrimaryDialer)
class PrimaryDialerAdmin(admin.ModelAdmin):
    list_display = ['id', 'admin_link', 'port', 'fronting_campaign', 'verifier_campaign', 'get_dialer_settings']
    search_fields = ['admin_link', 'fronting_campaign', 'verifier_campaign']
    list_filter = ['port', 'dialer_settings']
    
    fieldsets = (
        ('Dialer Connection', {
            'fields': ('dialer_settings', 'admin_link', 'admin_username', 'admin_password', 'ip_validation_link', 'port')
        }),
        ('Campaign Settings', {
            'fields': ('fronting_campaign', 'verifier_campaign')
        }),
    )

    def get_dialer_settings(self, obj):
        if obj.dialer_settings:
            return f"Settings #{obj.dialer_settings.id}"
        return "Not assigned"
    get_dialer_settings.short_description = 'Dialer Settings'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "dialer_settings":
            kwargs["queryset"] = DialerSettings.objects.order_by('-id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(CloserDialer)
class CloserDialerAdmin(admin.ModelAdmin):
    list_display = ['id', 'admin_link', 'closer_campaign', 'ingroup', 'port']
    search_fields = ['admin_link', 'closer_campaign', 'ingroup']
    list_filter = ['port']

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(DialerSettings)
class DialerSettingsAdmin(admin.ModelAdmin):
    inlines = [PrimaryDialerInline]
    list_display = ['id', 'get_primary_dialers_count', 'closer_dialer', 'get_client_campaigns_count']
    list_filter = ['closer_dialer']
    search_fields = ['closer_dialer__admin_link', 'id']
    
    fieldsets = (
        ('Dialer Configuration', {
            'fields': ('closer_dialer',),
            'description': 'Configure the closer dialer for this settings group. Primary dialers are managed below.'
        }),
    )

    def get_primary_dialers_count(self, obj):
        """Display count of primary dialers"""
        count = obj.primary_dialers.count()
        return f"{count} dialer(s)"
    get_primary_dialers_count.short_description = 'Primary Dialers'

    def get_client_campaigns_count(self, obj):
        count = obj.client_campaigns.count()
        return f"{count} campaign(s)"
    get_client_campaigns_count.short_description = 'Used By'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "closer_dialer":
            kwargs["queryset"] = CloserDialer.objects.order_by('-id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


# ============================================================================
# SECTION 5: SUPPORTING MODELS
# ============================================================================

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ['status_name', 'updated_at']
    search_fields = ['status_name']
    readonly_fields = ['status_name', 'updated_at']

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['status', 'start_date', 'end_date']
    list_filter = ['status', 'start_date']
    search_fields = ['status__status_name']
    readonly_fields = ['status', 'start_date', 'end_date']
    date_hierarchy = 'start_date'
    
    def has_module_permission(self, request):
        return False
    
    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa
    
    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


# ============================================================================
# SECTION 6: CLIENT CAMPAIGNS (Main Interface)
# ============================================================================

class ClientCampaignModelForm(forms.ModelForm):
    class Meta:
        model = ClientCampaignModel
        exclude = ['status_history']
        widgets = {
            'custom_comments': forms.Textarea(attrs={'rows': 3}),
            'current_remote_agents': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_archived=False).select_related('client').order_by('name')
        self.fields['campaign_model'].queryset = CampaignModel.objects.select_related('campaign', 'model').order_by('campaign__name', 'model__name')
        self.fields['campaign_model'].label_from_instance = lambda obj: f"{obj.campaign.name} - {obj.model.name}"
        self.fields['dialer_settings'].queryset = DialerSettings.objects.select_related('closer_dialer').prefetch_related('primary_dialers').order_by('-id')
        
        if not self.instance.pk:
            self.initial['start_date'] = timezone.now()
            self.initial['is_enabled'] = True
        
        self.fields['client'].help_text = "Select the client (only non-archived clients shown)"
        self.fields['campaign_model'].help_text = "Select campaign and model combination"
        self.fields['dialer_settings'].help_text = "Select or create dialer settings (use Dialer Settings menu to manage)"
        self.fields['is_active'].help_text = "Is this campaign currently running?"
        self.fields['is_enabled'].help_text = "Is this configuration enabled for use?"
        self.fields['is_approved'].help_text = "Has this campaign been approved?"
        self.fields['is_custom'].help_text = "Check if this is a custom configuration"
        self.fields['bot_count'].help_text = "Number of bots for this campaign"
        self.fields['long_call_scripts_active'].help_text = "Are long call scripts active?"
        self.fields['disposition_set'].help_text = "Is disposition set configured?"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')
        client = cleaned_data.get('client')

        if client and client.is_archived:
            raise forms.ValidationError({'client': "Cannot assign campaign to archived client"})

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError({'end_date': "End date cannot be before start date"})

        if is_active and end_date:
            raise forms.ValidationError({'is_active': "Cannot be active if campaign has ended (end date is set)"})

        return cleaned_data


@admin.register(ClientCampaignModel)
class ClientCampaignModelAdmin(admin.ModelAdmin):
    form = ClientCampaignModelForm
    inlines = [ServerCampaignBotsInline]
    readonly_fields = ['status_history']
    
    list_display = ['id', 'get_client_name', 'get_campaign', 'get_model', 'is_active', 'is_enabled', 'is_approved', 'bot_count', 'start_date']
    list_filter = ['is_active', 'is_enabled', 'is_approved', 'is_custom', 'long_call_scripts_active', 'disposition_set', 'start_date']
    search_fields = ['id', 'client__name', 'campaign_model__campaign__name', 'campaign_model__model__name']
    date_hierarchy = 'start_date'
    list_select_related = ['client__client', 'campaign_model__campaign', 'campaign_model__model']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'campaign_model', 'start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_active', 'is_enabled', 'is_approved', 'status_history')
        }),
        ('Campaign Configuration', {
            'fields': ('bot_count', 'long_call_scripts_active', 'disposition_set'),
        }),
        ('Customization', {
            'fields': ('is_custom', 'custom_comments', 'current_remote_agents'),
            'classes': ('collapse',)
        }),
        ('Dialer Configuration', {
            'fields': ('dialer_settings',),
            'description': 'Select existing configuration or create new via the Dialer Settings admin section'
        }),
    )

    def get_client_name(self, obj):
        return obj.client.name
    get_client_name.short_description = 'Client'
    get_client_name.admin_order_field = 'client__name'

    def get_campaign(self, obj):
        return obj.campaign_model.campaign.name
    get_campaign.short_description = 'Campaign'
    get_campaign.admin_order_field = 'campaign_model__campaign__name'

    def get_model(self, obj):
        return obj.campaign_model.model.name
    get_model.short_description = 'Model'
    get_model.admin_order_field = 'campaign_model__model__name'

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa:
            return True
        if request.user.is_client and obj:
            return obj.client.client == request.user
        return False

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_authenticated:
            return qs.none()
        if request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa:
            return qs
        if request.user.is_client:
            return qs.filter(client__client=request.user)
        return qs.none()


@admin.register(ServerCampaignBots)
class ServerCampaignBotsAdmin(admin.ModelAdmin):
    list_display = ['client_campaign_model', 'server', 'extension', 'bot_count']
    list_filter = ['server']
    search_fields = ['client_campaign_model__client__name', 'server__alias', 'extension__extension_number']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client_campaign_model":
            kwargs["queryset"] = ClientCampaignModel.objects.filter(
                client__is_archived=False
            ).select_related('client', 'campaign_model__campaign', 'campaign_model__model')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_module_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin