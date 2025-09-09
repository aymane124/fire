from django_filters import rest_framework as filters
from .models import Firewall

class FirewallFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    ip_address = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = Firewall
        fields = ['name', 'ip_address'] 