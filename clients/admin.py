from django.contrib import admin
from django import forms
from django.db import transaction
from django.contrib.auth.hashers import make_password
from .models import Client
from accounts.models import User, Role


class ClientCreationForm(forms.ModelForm):
    """Form for creating client with automatic user creation"""
    
    # Fields for creating the user
    username = forms.CharField(
        max_length=100,
        help_text="Username for the client to login"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Password for the client account"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
        help_text="Re-enter the password"
    )
    
    class Meta:
        model = Client
        fields = ['name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing, hide user creation fields and show current user
        if self.instance.pk:
            self.fields.pop('username')
            self.fields.pop('password')
            self.fields.pop('password_confirm')
    
    def clean_username(self):
        """Check if username already exists"""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(f"Username '{username}' is already taken")
        return username
    
    def clean(self):
        """Validate passwords match"""
        cleaned_data = super().clean()
        
        # Only validate passwords for new clients
        if not self.instance.pk:
            password = cleaned_data.get('password')
            password_confirm = cleaned_data.get('password_confirm')
            
            if password and password_confirm:
                if password != password_confirm:
                    raise forms.ValidationError({
                        'password_confirm': "Passwords do not match"
                    })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Create user and client together"""
        client = super().save(commit=False)
        
        # If this is a new client, create the user first
        if not self.instance.pk:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            
            # Get or create CLIENT role
            client_role, _ = Role.objects.get_or_create(
                name=Role.CLIENT,
                defaults={'name': Role.CLIENT}
            )
            
            # Create user with hashed password
            user = User.objects.create(
                username=username,
                password=make_password(password),
                role=client_role,
                is_active=True,
                is_staff=False
            )
            
            # Link the user to client
            client.client = user
        
        if commit:
            client.save()
        
        return client


class ClientEditForm(forms.ModelForm):
    """Form for editing existing client"""
    
    current_username = forms.CharField(
        disabled=True,
        required=False,
        help_text="Current username (cannot be changed)"
    )
    
    class Meta:
        model = Client
        fields = ['name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance.pk:
            self.fields['current_username'].initial = self.instance.client.username


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_username']
    search_fields = ['name', 'client__username']
    
    def get_form(self, request, obj=None, **kwargs):
        """Use different forms for add vs change"""
        if obj is None:
            # Creating new client
            kwargs['form'] = ClientCreationForm
        else:
            # Editing existing client
            kwargs['form'] = ClientEditForm
        return super().get_form(request, obj, **kwargs)
    
    def get_fieldsets(self, request, obj=None):
        """Different fieldsets for add vs change"""
        if obj is None:
            # Creating new client
            return (
                ('User Account', {
                    'fields': ('username', 'password', 'password_confirm'),
                    'description': 'Create login credentials for the client'
                }),
                ('Client Information', {
                    'fields': ('name',)
                }),
            )
        else:
            # Editing existing client
            return (
                ('User Account', {
                    'fields': ('current_username',),
                    'description': 'User account information'
                }),
                ('Client Information', {
                    'fields': ('name',)
                }),
            )
    
    def get_username(self, obj):
        """Display the username"""
        return obj.client.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'client__username'
    
    @transaction.atomic
    def save_model(self, request, obj, form, change):
        """Save with transaction to ensure user and client are created together"""
        super().save_model(request, obj, form, change)
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin)
    
    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_admin :
            return True
        
    
    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 
    
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 
    
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_authenticated:
            return qs.none()
        if request.user.is_superuser or request.user.is_admin:
            return qs
        if request.user.is_client:
            return qs.filter(client=request.user)
        return qs.none()