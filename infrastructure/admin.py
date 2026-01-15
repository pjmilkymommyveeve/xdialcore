from django.contrib import admin
from django.db.models import Sum
from .models import Server, Extension

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['ip', 'alias', 'domain', 'total_bot_count']
    search_fields = ['ip', 'alias', 'domain']
    list_filter = ['alias']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _total_bot_count=Sum('campaign_bots__bot_count')
        )

    def total_bot_count(self, obj):
        """Display total bot count across all campaigns on this server"""
        return obj._total_bot_count or 0
    total_bot_count.short_description = 'Total Bots'
    total_bot_count.admin_order_field = '_total_bot_count'

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)

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


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ['extension_number']
    search_fields = ['extension_number']

    def get_queryset(self, request):
        """Order extensions by prefix (first two digits) to group them together"""
        qs = super().get_queryset(request)
        return qs.order_by('extension_number')

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return (request.user.is_superuser or 
                request.user.is_admin or 
                request.user.is_onboarding)

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