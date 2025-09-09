from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SSHUser

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone_number', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2'),
        }),
    )

    # Only superusers can edit or delete superuser accounts from the admin
    def has_change_permission(self, request, obj=None):
        base = super().has_change_permission(request, obj)
        if not base:
            return False
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        base = super().has_delete_permission(request, obj)
        if not base:
            return False
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return True

    # Prevent bulk delete of superusers by staff via actions
    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser and 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

@admin.register(SSHUser)
class SSHUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'ssh_username', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'ssh_username')
    ordering = ('-created_at',)
