from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'is_archived']
    list_filter = ['is_archived']
    search_fields = ['name', 'client__username']
    readonly_fields = ['client']
    
    def has_module_permission(self, request):
        # Admin, Onboarding, and QA can access
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
            return obj.client == request.user
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
            return qs.filter(client=request.user)
        return qs.none()