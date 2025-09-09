from django.core.management.base import BaseCommand
from auth_service.models import User, SSHUser

class Command(BaseCommand):
    help = 'Crée des SSHUser pour tous les utilisateurs existants'

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            if not hasattr(user, 'ssh_credentials'):
                SSHUser.objects.create(
                    user=user,
                    ssh_username=user.username,
                    ssh_password='default_password'  # L'utilisateur devra changer ce mot de passe
                )
                self.stdout.write(self.style.SUCCESS(f'Créé SSHUser pour {user.username}')) 