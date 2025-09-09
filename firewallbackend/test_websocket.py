#!/usr/bin/env python
import os
import sys
import django
import asyncio
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firewallbackend.settings')
django.setup()

from websocket_service.models import TerminalSession, TerminalCommand
from auth_service.models import User
from firewall_service.models import Firewall

def test_websocket_connection():
    print("🔍 Test de connexion WebSocket")
    print("=" * 50)
    
    # Vérifier les utilisateurs
    users = User.objects.filter(is_active=True)
    print(f"👥 Utilisateurs actifs: {users.count()}")
    for user in users:
        print(f"   - {user.username} (ID: {user.id})")
    
    # Vérifier les firewalls
    firewalls = Firewall.objects.all()
    print(f"\n🖥️ Firewalls disponibles: {firewalls.count()}")
    for fw in firewalls:
        print(f"   - {fw.name} (ID: {fw.id}) - {fw.ip_address}")
    
    # Vérifier les sessions actives
    active_sessions = TerminalSession.objects.filter(is_active=True)
    print(f"\n🔌 Sessions WebSocket actives: {active_sessions.count()}")
    for session in active_sessions:
        print(f"   - Session {session.session_id} - User: {session.user.username} - Firewall: {session.firewall.name}")
    
    # Test du channel layer
    print(f"\n📡 Test du channel layer...")
    try:
        channel_layer = get_channel_layer()
        print(f"   ✅ Channel layer initialisé")
        
        # Test d'envoi de message
        test_group = "test_group"
        test_message = {
            'type': 'test_message',
            'content': 'Test message'
        }
        
        async_to_sync(channel_layer.group_send)(test_group, test_message)
        print(f"   ✅ Message envoyé au groupe {test_group}")
        
        # Vérifier les channels dans le groupe
        channels = async_to_sync(channel_layer.group_channels)(test_group)
        print(f"   📊 Channels dans le groupe: {len(channels)}")
        
    except Exception as e:
        print(f"   ❌ Erreur channel layer: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ Test terminé")

if __name__ == "__main__":
    test_websocket_connection()
