from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/terminal/(?P<firewall_id>[^/]+)/$', consumers.TerminalConsumer.as_asgi()),
]
