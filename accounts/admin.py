from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username']
    ordering = ['username']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Role', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'is_staff'),
        }),
    )
    
    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 
    
    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.is_admin 
    
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.is_admin:
            return True
      
    
    