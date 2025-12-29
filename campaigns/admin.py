from django.contrib import admin
from django import forms
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
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
    filter_horizontal = ['transfer_settings']


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
            kwargs["queryset"] = Model.objects.prefetch_related('transfer_settings').order_by('name')
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            
            def label_with_settings(obj):
                settings = obj.transfer_settings.all()
                if settings.exists():
                    settings_str = ", ".join([ts.name for ts in settings[:3]])
                    if settings.count() > 3:
                        settings_str += f" (+{settings.count() - 3} more)"
                    return f"{obj.name} - {settings_str}"
                return f"{obj.name} - No Transfer Settings"
            
            formfield.label_from_instance = label_with_settings
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
        return request.user.is_superuser or request.user.is_admin 

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
    filter_horizontal = ['transfer_settings']

    def get_list_display(self, request):
        """Customize list_display based on user role"""
        base_display = [
            'id', 
            'get_client_name', 
            'get_campaign', 
            'get_model',
            'get_transfer_setting',
            'get_current_status',
            'is_active', 
            'bot_count', 
            'start_date',
        ]
        
        # QA users only see admin dashboard
        if request.user.is_qa:
            return base_display + ['get_admin_dashboard_link']
        
        # Admin and Onboarding see both dashboards
        if request.user.is_superuser or request.user.is_admin or request.user.is_onboarding:
            return base_display + ['get_client_dashboard_link', 'get_admin_dashboard_link']
        
        # Others see default
        return base_display

    def get_transfer_settings(self, obj):
        """Display all transfer settings for this model"""
        settings = obj.transfer_settings.all()
        if settings.exists():
            return ", ".join([ts.name for ts in settings])
        return "None"
    get_transfer_settings.short_description = 'Transfer Settings'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "transfer_settings":
            kwargs["queryset"] = TransferSettings.objects.order_by('display_order', 'name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
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
        return request.user.is_superuser or request.user.is_admin   

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
        return request.user.is_superuser or request.user.is_admin 

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
    readonly_fields = ['updated_at']

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 

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


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['status', 'get_client_campaign', 'start_date', 'end_date', 'duration']
    list_filter = ['status', 'start_date', 'end_date']
    search_fields = ['status__status_name', 'client_campaigns__client__name']
    readonly_fields = ['status', 'start_date', 'end_date', 'get_client_campaign', 'duration']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Status Information', {
            'fields': ('status', 'get_client_campaign')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'duration')
        }),
    )
    
    def get_client_campaign(self, obj):
        """Show which client campaign this history belongs to"""
        if obj.client_campaign:
            campaign = obj.client_campaign
            url = reverse('admin:campaigns_clientcampaignmodel_change', args=[campaign.pk])
            return format_html(
                '<a href="{}">{} - {}</a>',
                url,
                campaign.client.name,
                campaign.campaign_model
            )
        return "No associated campaign"
    get_client_campaign.short_description = 'Client Campaign'
    
    def duration(self, obj):
        """Calculate how long this status was active"""
        if obj.end_date:
            delta = obj.end_date - obj.start_date
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0 or not parts:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            
            return ", ".join(parts)
        return "Currently active"
    duration.short_description = 'Duration'
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return False
    
    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding or request.user.is_qa
    
    def has_add_permission(self, request):
        return False  # Status history should only be created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Status history should not be manually edited
    
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin

# ============================================================================
# SECTION 6: CLIENT CAMPAIGNS (Main Interface)
# ============================================================================

class ClientCampaignModelForm(forms.ModelForm):

    status = forms.ModelChoiceField(
        queryset=Status.objects.all(),
        required=True,
        help_text="Select the status for this campaign"
    )

    class Meta:
        model = ClientCampaignModel
        fields = '__all__'
        exclude = []
        widgets = {
            'custom_comments': forms.Textarea(attrs={'rows': 3}),
            'current_remote_agents': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.select_related('client').order_by('name')
        self.fields['campaign_model'].queryset = CampaignModel.objects.select_related('campaign', 'model').order_by('campaign__name', 'model__name')
        self.fields['campaign_model'].label_from_instance = lambda obj: f"{obj.campaign.name} - {obj.model.name}"
        self.fields['dialer_settings'].queryset = DialerSettings.objects.select_related('closer_dialer').prefetch_related('primary_dialers').order_by('-id')
        
        if 'campaign_model' in self.data:
            try:
                campaign_model_id = int(self.data.get('campaign_model'))
                campaign_model = CampaignModel.objects.get(id=campaign_model_id)
                self.fields['selected_transfer_setting'].queryset = campaign_model.model.transfer_settings.all()
            except (ValueError, TypeError, CampaignModel.DoesNotExist):
                self.fields['selected_transfer_setting'].queryset = TransferSettings.objects.none()
        elif self.instance.pk and self.instance.campaign_model:
            self.fields['selected_transfer_setting'].queryset = self.instance.campaign_model.model.transfer_settings.all()
        else:
            self.fields['selected_transfer_setting'].queryset = TransferSettings.objects.none()

        # If editing an existing instance
        if self.instance.pk:
            # Make client field readonly for existing instances
            self.fields['client'].disabled = True
            self.fields['client'].help_text = "Client cannot be changed after creation"
            
            # Set current status from status_history
            current_history = self.instance.status_history.filter(end_date__isnull=True).first()
            if current_history:
                self.initial['status'] = current_history.status
                self.fields['status'].initial = current_history.status
        else:
            # For new instances, set default values
            self.initial['start_date'] = timezone.now()
            # Set default status to "Not Approved"
            try:
                not_approved_status = Status.objects.get(status_name='Not Approved')
                self.initial['status'] = not_approved_status
                self.fields['status'].initial = not_approved_status
            except Status.DoesNotExist:
                pass
    
        
        self.fields['client'].help_text = "Select the client" if not self.instance.pk else "Client cannot be changed after creation"
        self.fields['campaign_model'].help_text = "Select campaign and model combination"
        self.fields['dialer_settings'].help_text = "Select or create dialer settings (use Dialer Settings menu to manage)"
        self.fields['selected_transfer_setting'].help_text = "Select transfer setting from available options for this model"
        self.fields['is_active'].help_text = "Is this campaign currently running?"
        self.fields['is_custom'].help_text = "Check if this is a custom configuration"
        self.fields['bot_count'].help_text = "Number of bots for this campaign"
        self.fields['long_call_scripts_active'].help_text = "Are long call scripts active?"
        self.fields['disposition_set'].help_text = "Is disposition set configured?"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_active = cleaned_data.get('is_active')
        campaign_model = cleaned_data.get('campaign_model')
        selected_transfer_setting = cleaned_data.get('selected_transfer_setting')

        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError({'end_date': "End date cannot be before start date"})

        if is_active and end_date:
            raise forms.ValidationError({'is_active': "Cannot be active if campaign has ended (end date is set)"})

        # Validate transfer setting belongs to the model
        if campaign_model and selected_transfer_setting:
            if not campaign_model.model.transfer_settings.filter(id=selected_transfer_setting.id).exists():
                raise forms.ValidationError({
                    'selected_transfer_setting': "Selected transfer setting must be available for this campaign's model"
                })

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_status = self.cleaned_data.get('status')
        
        # Store the new status on the instance so we can save it later
        instance._new_status = new_status
        
        if commit:
            with transaction.atomic():
                instance.save()
                
                # Get current status
                current_history = instance.status_history.filter(end_date__isnull=True).first()
                old_status = current_history.status if current_history else None
                
                # Update status if changed or new
                if old_status != new_status:
                    # Close old status history if it exists
                    if current_history:
                        current_history.end_date = timezone.now()
                        current_history.save()
                    
                    # Create new status history
                    StatusHistory.objects.create(
                        client_campaign=instance,
                        status=new_status,
                        start_date=timezone.now()
                    )
                
                self.save_m2m()
        
        return instance
    
class CurrentStatusFilter(admin.SimpleListFilter):
    title = 'current status'
    parameter_name = 'current_status'

    def lookups(self, request, model_admin):
        """Return list of statuses to filter by"""
        statuses = Status.objects.all().order_by('status_name')
        return [(status.id, status.status_name) for status in statuses]

    def queryset(self, request, queryset):
        """Filter queryset based on selected status"""
        if self.value():
            # Get all ClientCampaignModel IDs that have this status as current
            status_id = self.value()
            campaign_ids = StatusHistory.objects.filter(
                status_id=status_id,
                end_date__isnull=True  # Only current/active statuses
            ).values_list('client_campaign_id', flat=True)
            
            return queryset.filter(id__in=campaign_ids)
        return queryset
    
@admin.register(ClientCampaignModel)
class ClientCampaignModelAdmin(admin.ModelAdmin):
    form = ClientCampaignModelForm
    inlines = [ServerCampaignBotsInline]
    readonly_fields = ['get_status_history_display']
    
    list_display = [
        'id', 
        'get_client_name', 
        'get_campaign', 
        'get_model',
        'get_transfer_setting',
        'get_current_status',
        'is_active', 
        'bot_count', 
        'start_date',
        'get_client_dashboard_link',
        'get_admin_dashboard_link',
    ]
    list_filter = [
        CurrentStatusFilter,
        'is_active', 
        'is_custom', 
        'long_call_scripts_active', 
        'disposition_set', 
        'start_date',
        'campaign_model__campaign',
        'campaign_model__model',
        'client',
    ]
    search_fields = [
        'id', 
        'client__name', 
        'campaign_model__campaign__name', 
        'campaign_model__model__name',
        'campaign_model__campaign__description',
        'custom_comments'
    ]
    date_hierarchy = 'start_date'
    list_select_related = ['client__client', 'campaign_model__campaign', 'campaign_model__model']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'campaign_model', 'selected_transfer_setting', 'start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'get_status_history_display')
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

    def save_model(self, request, obj, form, change):
        """Override to handle status updates when commit=False is used with inlines"""
        if hasattr(obj, '_new_status'):
            new_status = obj._new_status
            
            with transaction.atomic():
                # Save the object first
                super().save_model(request, obj, form, change)
                
                # Get current status
                current_history = obj.status_history.filter(end_date__isnull=True).first()
                old_status = current_history.status if current_history else None
                
                # Update status if changed or new
                if old_status != new_status:
                    # Close old status history if it exists
                    if current_history:
                        current_history.end_date = timezone.now()
                        current_history.save()
                    
                    # Create new status history
                    StatusHistory.objects.create(
                        client_campaign=obj,
                        status=new_status,
                        start_date=timezone.now()
                    )
        else:
            super().save_model(request, obj, form, change)

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

    def get_current_status(self, obj):
        """Display current status with color coding"""
        current_history = obj.status_history.filter(end_date__isnull=True).first()
        if current_history:
            status_name = current_history.status.status_name
            color_map = {
                'Not Approved': '#999999',
                'Enabled': '#28a745',
                'Disabled': '#dc3545',
                'Archived': '#6c757d'
            }
            color = color_map.get(status_name, '#007bff')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                status_name
            )
        return mark_safe('<span style="color: #999999;">No Status</span>')

    get_current_status.short_description = 'Status'
    get_current_status.admin_order_field = 'status_history__status__status_name'

    def get_client_dashboard_link(self, obj):
        """Display link to client dashboard"""
        if obj.pk:
            dashboard_url = f"https://dashboard.xlitexcore.xdialnetworks.com/dashboard?campaign_id={obj.pk}"
            return format_html(
                '<a class="button" href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; white-space: nowrap; display: inline-block;">Client Dashboard</a>',
                dashboard_url
            )
        return "-"

    get_client_dashboard_link.short_description = 'Client Dashboard'

    def get_admin_dashboard_link(self, obj):
        """Display link to admin dashboard (placeholder)"""
        if obj.pk:
            dashboard_url = f"https://dashboard.xlitexcore.xdialnetworks.com/admin-dashboard?campaign_id={obj.pk}"
            return format_html(
                '<a class="button" href="{}" target="_blank" style="background-color: #417690; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; white-space: nowrap; display: inline-block;">Client Dashboard</a>',
                dashboard_url
            )
        return "-"

    get_admin_dashboard_link.short_description = 'Admin Dashboard'
    def get_status_history_display(self, obj):
        """Display link to view full status history"""
        if obj.pk:
            url = reverse('admin:campaigns_statushistory_changelist')
            # Add filter parameter to show only this campaign's history
            filter_url = f"{url}?client_campaign__id__exact={obj.pk}"
            return format_html(
                '<a class="button" href="{}" target="_blank">View Status History</a>',
                filter_url
            )
        return "Save to view history"
    get_status_history_display.short_description = 'Status History'

    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding 

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

    def get_transfer_setting(self, obj):
        if obj.selected_transfer_setting:
            return obj.selected_transfer_setting.name
        return '-'
    get_transfer_setting.short_description = 'Transfer Setting'
    get_transfer_setting.admin_order_field = 'selected_transfer_setting__name'

@admin.register(ServerCampaignBots)
class ServerCampaignBotsAdmin(admin.ModelAdmin):
    list_display = ['client_campaign_model', 'server', 'extension', 'bot_count']
    list_filter = ['server']
    search_fields = ['client_campaign_model__client__name', 'server__alias', 'extension__extension_number']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "client_campaign_model":
            kwargs["queryset"] = ClientCampaignModel.objects.select_related(
                'client', 'campaign_model__campaign', 'campaign_model__model'
            ).order_by('client__name')
        if db_field.name == "server":
            kwargs["queryset"] = Server.objects.order_by('alias', 'ip')
        if db_field.name == "extension":
            kwargs["queryset"] = Extension.objects.order_by('extension_number')
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