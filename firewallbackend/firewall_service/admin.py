from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.utils.html import format_html
from django.db.models import Count, Min

from .models import FirewallType, Firewall


@admin.register(FirewallType)
class FirewallTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'data_center', 'owner', 'created_at')
    search_fields = ('name', 'description', 'data_center__name', 'owner__username')
    list_filter = ('data_center', 'owner')


@admin.register(Firewall)
class FirewallAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'data_center', 'firewall_type', 'owner', 'created_at')
    search_fields = ('name', 'ip_address', 'data_center__name', 'firewall_type__name', 'owner__username')
    list_filter = ('data_center', 'firewall_type', 'owner')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('deduplicated-by-ip/', self.admin_site.admin_view(self.deduplicated_by_ip_view), name='firewall_dedup_by_ip'),
        ]
        return custom_urls + urls

    def deduplicated_by_ip_view(self, request):
        # Construire un tableau HTML simple listant les IP uniques + compte + exemples
        aggregation = (
            Firewall.objects
            .values('ip_address')
            .annotate(count=Count('id'), any_name=Min('name'), any_owner=Min('owner__username'))
            .order_by('ip_address')
        )

        rows = []
        rows.append('<h2>Firewalls dédupliqués par IP</h2>')
        rows.append('<p>Liste de toutes les adresses IP uniques, toutes appartenances utilisateurs confondues.</p>')
        rows.append('<table style="width:100%;border-collapse:collapse" border="1" cellpadding="6">')
        rows.append('<thead><tr><th>IP Address</th><th>Occurrences</th><th>Exemple Nom</th><th>Exemple Propriétaire</th></tr></thead>')
        rows.append('<tbody>')
        for row in aggregation:
            rows.append(
                f"<tr><td>{row['ip_address']}</td><td>{row['count']}</td><td>{row['any_name'] or ''}</td><td>{row['any_owner'] or ''}</td></tr>"
            )
        rows.append('</tbody></table>')
        rows.append('<p style="margin-top:12px">Astuce: utilisez la recherche de l\'admin sur IP pour voir les doublons et les gérer.</p>')
        html = '\n'.join(rows)
        return HttpResponse(html) 