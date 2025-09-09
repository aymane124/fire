from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from asgiref.sync import async_to_sync

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        'recipient', 'subject', 'sent_at', 'status', 'from_email', 'smtp_host', 'smtp_port'
    )
    list_filter = ('status', 'smtp_host', 'sent_at')
    search_fields = ('recipient', 'subject', 'from_email')
    readonly_fields = ('sent_at',)


 
