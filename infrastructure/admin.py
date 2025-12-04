from django.contrib import admin
from .models import Server, Extension


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['ip', 'alias', 'domain']
    search_fields = ['ip', 'alias', 'domain']
    list_filter = ['alias']
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ['extension_number']
    search_fields = ['extension_number']
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)
    
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin or request.user.is_onboarding
    
    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin