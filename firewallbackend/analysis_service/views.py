from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from firewall_service.models import Firewall
import os
import re

class FlowMatrixView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    LOCAL_SAVE_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'FirewallConfigs')

    def _clean_ip_address(self, ip_address):
        return ip_address.split('/')[0] if '/' in ip_address else ip_address

    def _search_ip_in_config(self, ip_address, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            clean_ip = self._clean_ip_address(ip_address)
            found_addresses = {}

            # Analyse des adresses
            current_block = None
            in_block = False
            current_comment = None

            for line in config_content.splitlines():
                line = line.strip()
                if line.startswith('edit '):
                    current_block = line.split('edit ')[1].strip('"')
                    in_block = True
                    current_comment = None
                elif line == 'next':
                    in_block = False
                elif in_block:
                    if 'set comment' in line:
                        current_comment = line.split('set comment')[1].strip().strip('"')
                    if any(x in line for x in ['set subnet', 'set ip', 'set start-ip', 'set end-ip']):
                        if clean_ip in line:
                            found_addresses[current_block] = current_comment

            # Interfaces
            current_interface = None
            in_interface_block = False
            for line in config_content.splitlines():
                line = line.strip()
                if line.startswith('edit '):
                    current_interface = line.split('edit ')[1].strip('"')
                    in_interface_block = True
                    current_comment = None
                elif line == 'next':
                    in_interface_block = False
                elif in_interface_block:
                    if 'set description' in line:
                        current_comment = line.split('set description')[1].strip().strip('"')
                    if 'set ip' in line and clean_ip in line:
                        found_addresses[current_interface] = current_comment

            # Adress groups
            current_group = None
            in_group_block = False
            for line in config_content.splitlines():
                line = line.strip()
                if line.startswith('edit '):
                    current_group = line.split('edit ')[1].strip('"')
                    in_group_block = True
                    current_comment = None
                elif line == 'next':
                    in_group_block = False
                elif in_group_block:
                    if 'set comment' in line:
                        current_comment = line.split('set comment')[1].strip().strip('"')
                    elif 'set member' in line and clean_ip in line:
                        found_addresses[current_group] = current_comment

            return sorted([{'name': k, 'comment': v or ''} for k, v in found_addresses.items()])

        except Exception as e:
            print(f"Erreur lecture config: {str(e)}")
            return []

    def _search_groups_in_config(self, address_name, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            group_blocks = re.finditer(
                r'config firewall addrgrp\n\s+edit "([^"]+)"\n(.*?)\n\s+next',
                config_content,
                re.DOTALL
            )

            groups = []
            for block in group_blocks:
                group_name = block.group(1)
                content = block.group(2)
                if f'set member "{address_name}"' in content:
                    groups.append(group_name)

            return groups

        except Exception as e:
            print(f"Erreur groupe: {str(e)}")
            return []

    def analyze_ip(self, request):
        try:
            source_ip = request.data.get('source_ip')
            firewall_id = request.data.get('firewall_id')
            data_center_name = request.data.get('data_center_name')
            firewall_type_name = request.data.get('firewall_type_name')

            if not all([source_ip, firewall_id, data_center_name, firewall_type_name]):
                return Response(
                    {'error': 'source_ip, firewall_id, data_center_name et firewall_type_name sont requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            firewall_dir = os.path.join(self.LOCAL_SAVE_DIR, data_center_name, firewall_type_name)

            if not os.path.exists(firewall_dir):
                return Response(
                    {'error': 'Aucun fichier de configuration trouvé pour ce pare-feu'},
                    status=status.HTTP_404_NOT_FOUND
                )

            config_files = [f for f in os.listdir(firewall_dir) if f.endswith('.txt')]
            if not config_files:
                return Response(
                    {'error': 'Aucun fichier de configuration trouvé pour ce pare-feu'},
                    status=status.HTTP_404_NOT_FOUND
                )

            latest_file = max(config_files, key=lambda x: os.path.getctime(os.path.join(firewall_dir, x)))
            config_path = os.path.join(firewall_dir, latest_file)

            ip_results = self._search_ip_in_config(source_ip, config_path)
            if not ip_results:
                return Response(
                    {'error': 'Adresse IP non trouvée dans la configuration'},
                    status=status.HTTP_404_NOT_FOUND
                )

            for result in ip_results:
                result['groups'] = self._search_groups_in_config(result['name'], config_path)

            return Response({
                'ip': source_ip,
                'matches': ip_results,
                'config_path': config_path,
                'file_list': config_files
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'analyse: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, *args, **kwargs):
        return self.analyze_ip(request)
