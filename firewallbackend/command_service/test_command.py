import paramiko
import time

def test_ssh_command():
    # Paramètres de connexion
    hostname = "172.16.24.130"
    username = "aymane"
    password = "bFbIiDewoIWKaXw1@"
    command = "show"

    try:
        # Création du client SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Tentative de connexion à {hostname}...")
        ssh.connect(hostname, username=username, password=password, timeout=10)
        print("Connexion établie avec succès!")
        
        print(f"Exécution de la commande: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Attendre que la commande se termine
        exit_status = stdout.channel.recv_exit_status()
        
        # Lire la sortie
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print("\nSortie de la commande:")
        print(output)
        
        if error:
            print("\nErreurs:")
            print(error)
            
        print(f"\nCode de sortie: {exit_status}")
        
    except Exception as e:
        print(f"Erreur lors de l'exécution: {str(e)}")
    finally:
        ssh.close()
        print("\nConnexion fermée")

if __name__ == "__main__":
    test_ssh_command() 