from django.contrib import admin
from .models import Server, Extension, PrimaryDialer, CloserDialer, DialerSettings


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['ip', 'alias', 'domain']
    search_fields = ['ip', 'alias', 'domain']
    list_filter = ['alias']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ['extension_number']
    search_fields = ['extension_number']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(PrimaryDialer)
class PrimaryDialerAdmin(admin.ModelAdmin):
    list_display = ['id', 'admin_link', 'port', 'fronting_campaign', 'verifier_campaign']
    search_fields = ['admin_link', 'fronting_campaign', 'verifier_campaign']
    list_filter = ['port']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(CloserDialer)
class CloserDialerAdmin(admin.ModelAdmin):
    list_display = ['id', 'admin_link', 'closer_campaign', 'ingroup', 'port']
    search_fields = ['admin_link', 'closer_campaign', 'ingroup']
    list_filter = ['port']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin


@admin.register(DialerSettings)
class DialerSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'has_separate_closer', 'primary_dialer', 'closer_dialer']
    list_filter = ['has_separate_closer']
    
    def has_module_permission(self, request):
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_admin

