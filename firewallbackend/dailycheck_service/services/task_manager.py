"""
Gestionnaire de tâches pour le service dailycheck
"""

import logging
import threading
import time
from queue import Queue
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TaskManager:
    """
    Gestionnaire centralisé des tâches de daily check
    """
    
    def __init__(self):
        self.task_queue = Queue()
        self.task_status = {}
        self.worker_thread = None
        self._start_worker()
    
    def _start_worker(self):
        """Démarre le thread worker en arrière-plan"""
        if not self.worker_thread or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Background worker thread started")
    
    def _worker_loop(self):
        """Boucle principale du worker"""
        while True:
            try:
                task = self.task_queue.get()
                if task is None:
                    break
                
                self._process_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in worker thread: {e}")
                continue
    
    def _process_task(self, task: Dict[str, Any]):
        """Traite une tâche de daily check avec timeout global"""
        task_id = task['task_id']
        start_time = time.time()
        max_task_timeout = 300  # 5 minutes maximum par tâche pour détection ultra-rapide
        
        try:
            # Initialiser le statut
            self.task_status[task_id] = {
                'status': 'running',
                'progress': 0,
                'message': 'Starting daily checks...',
                'start_time': start_time,
                'timeout': max_task_timeout
            }
            
            # Importer et exécuter le worker
            from .background_worker import BackgroundWorker
            worker = BackgroundWorker()
            
            # Vérifier le timeout périodiquement
            def timeout_check_callback(task_id, status):
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                if elapsed_time > max_task_timeout:
                    logger.warning(f"Task {task_id} exceeded maximum timeout of {max_task_timeout}s")
                    self.task_status[task_id].update({
                        'status': 'timeout',
                        'message': f'Task exceeded maximum timeout of {max_task_timeout}s',
                        'elapsed_time': elapsed_time
                    })
                    return False  # Arrêter le traitement
                
                # Mettre à jour le statut normal
                self._update_task_status(task_id, status)
                return True  # Continuer le traitement
            
            result = worker.execute_daily_checks(
                firewalls=task['firewalls'],
                commands=task['commands'],
                user=task['user'],
                task_id=task_id,
                status_callback=timeout_check_callback
            )
            
            # Mettre à jour le statut final
            elapsed_time = time.time() - start_time
            self.task_status[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': 'All daily checks completed',
                'results': result,
                'elapsed_time': elapsed_time
            })
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            elapsed_time = time.time() - start_time
            self.task_status[task_id].update({
                'status': 'failed',
                'message': str(e),
                'elapsed_time': elapsed_time
            })
    
    def _update_task_status(self, task_id: str, status: Dict[str, Any]):
        """Met à jour le statut d'une tâche"""
        if task_id in self.task_status:
            self.task_status[task_id].update(status)
    
    def add_task(self, firewalls: List, commands: List[str], user) -> str:
        """
        Ajoute une nouvelle tâche à la queue
        
        Args:
            firewalls: Liste des firewalls à traiter
            commands: Liste des commandes à exécuter
            user: Utilisateur qui a lancé la tâche
            
        Returns:
            str: ID de la tâche
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = {
            'task_id': task_id,
            'firewalls': firewalls,
            'commands': commands,
            'user': user
        }
        
        # Ajouter à la queue
        self.task_queue.put(task)
        
        # Initialiser le statut
        self.task_status[task_id] = {
            'status': 'pending',
            'progress': 0,
            'message': 'Task queued'
        }
        
        logger.info(f"Task {task_id} added to queue")
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'une tâche
        
        Args:
            task_id: ID de la tâche
            
        Returns:
            Dict avec le statut de la tâche
        """
        return self.task_status.get(task_id, {'status': 'not_found'})
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère tous les statuts de tâches
        
        Returns:
            Dict avec tous les statuts
        """
        return self.task_status.copy()

# Instance globale du gestionnaire de tâches
task_manager = TaskManager()
