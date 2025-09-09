from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SSHUser
from .utils.crypto import encrypt_user_data, encrypt_ssh_data
import logging
from template_service.models import Variable
from datacenter_service.models import DataCenter
from firewall_service.models import FirewallType, Firewall
from firewall_service.default_data import DEFAULT_FIREWALL_ROWS

logger = logging.getLogger(__name__)

User = get_user_model()

# Liste des variables par défaut avec leurs noms et descriptions
DEFAULT_VARIABLES = [
    {'name': 'Hostname', 'description': 'Hostname of the device'},
    {'name': 'IP Address', 'description': 'IP Address of the device'},
    {'name': 'VDOM', 'description': 'Virtual Domain'},
    {'name': 'set name', 'description': 'Name of the configuration'},
    {'name': 'set srcaddr ', 'description': 'Source IP Address'},
    {'name': 'set srcaddr', 'description': 'Description of the source'},
    {'name': 'set srcintf', 'description': 'Source network interface'},
    {'name': 'set dstaddr', 'description': 'Destination IP Address'},
    {'name': 'set dstaddr', 'description': 'Description of the destination'},
    {'name': 'set dstintf', 'description': 'Destination network interface'},
    {'name': 'set service', 'description': 'Network service'}
]

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal pour créer un profil utilisateur, SSH user et les variables par défaut lors de la création d'un nouvel utilisateur
    """
    if created:
        try:
            # Créer automatiquement un SSH user avec les mêmes identifiants
            if not hasattr(instance, 'ssh_credentials'):
                try:
                    ssh_user = SSHUser.objects.create(
                        user=instance,
                        ssh_username=instance.username,
                        ssh_password=''  # Empty password for now, user will set it later
                    )
                    logger.info(f"SSH user créé pour l'utilisateur {instance.username}")
                except Exception as e:
                    logger.warning(f"Impossible de créer SSH user pour {instance.username}: {str(e)}")
            
            # Vérifier si l'utilisateur a déjà des variables
            existing_variables = Variable.objects.filter(user=instance)
            if existing_variables.exists():
                logger.info(f"L'utilisateur {instance.username} a déjà des variables, aucune création nécessaire")
                return

            # Créer les variables par défaut pour le nouvel utilisateur
            for var_data in DEFAULT_VARIABLES:
                # Vérifier si la variable existe déjà pour cet utilisateur
                if not Variable.objects.filter(user=instance, name=var_data['name']).exists():
                    Variable.objects.create(
                        name=var_data['name'],
                        description=var_data['description'],
                        user=instance
                    )
                    logger.info(f"Variable {var_data['name']} créée pour l'utilisateur {instance.username}")
            
            logger.info(f"Toutes les variables par défaut ont été créées pour l'utilisateur {instance.username}")

            # Seeder: créer datacenters, types et firewalls par défaut pour ce user
            # Indexer les types par (datacenter, type)
            created_dc = {}
            created_types = {}
            for row in DEFAULT_FIREWALL_ROWS:
                dc_name = row['datacenter']
                type_name = row['type']
                fw_name = row['firewall']
                ip = row['ip']

                # Datacenter par user (unique par nom et owner via modèle)
                dc_key = dc_name
                if dc_key not in created_dc:
                    dc_obj, _ = DataCenter.objects.get_or_create(
                        name=dc_name,
                        owner=instance,
                        defaults={'description': f"Auto seed for {instance.username}"}
                    )
                    created_dc[dc_key] = dc_obj
                dc_obj = created_dc[dc_key]

                # FirewallType unique (name + data_center)
                type_key = (dc_name, type_name)
                if type_key not in created_types:
                    ft_obj, _ = FirewallType.objects.get_or_create(
                        name=type_name,
                        data_center=dc_obj,
                        defaults={
                            'description': f"Seed type {type_name}",
                            'attributes_schema': {},
                            'owner': instance
                        }
                    )
                    created_types[type_key] = ft_obj
                ft_obj = created_types[type_key]

                # Firewall unique par (name + owner) via contrainte d'usage
                Firewall.objects.get_or_create(
                    name=fw_name,
                    owner=instance,
                    defaults={
                        'ip_address': ip,
                        'data_center': dc_obj,
                        'firewall_type': ft_obj
                    }
                )
            logger.info(f"Données firewall par défaut créées pour {instance.username}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du profil pour l'utilisateur {instance.username}: {str(e)}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal pour sauvegarder le profil utilisateur lors de la mise à jour d'un utilisateur
    """
    # Vous pouvez ajouter ici la logique pour sauvegarder le profil utilisateur
    pass

# Suppression du signal create_ssh_user car nous ne stockons plus les mots de passe en clair
# Les SSHUser devront être créés manuellement avec les bons identifiants
# ou via l'interface utilisateur avec des mots de passe séparés

# Suppression du signal qui crée automatiquement un SSHUser
# Les SSHUser devront être créés manuellement avec les bons identifiants 