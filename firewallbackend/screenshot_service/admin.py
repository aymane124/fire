from django.contrib import admin
from .models import ScreenshotReport

@admin.register(ScreenshotReport)
class ScreenshotReportAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'protocol', 'created_at', 'user', 'has_excel_file']
    list_filter = ['protocol', 'created_at', 'user']
    search_fields = ['ip_address', 'user']
    readonly_fields = ['id', 'created_at', 'screenshot_base64']
    ordering = ['-created_at']
    
    def has_excel_file(self, obj):
        return bool(obj.excel_file_path)
    has_excel_file.boolean = True
    has_excel_file.short_description = 'Fichier Excel'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('id', 'ip_address', 'protocol', 'url', 'user', 'created_at')
        }),
        ('Screenshot', {
            'fields': ('screenshot_base64', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('Fichier Excel', {
            'fields': ('excel_file_path',),
            'classes': ('collapse',)
        }),
    )

