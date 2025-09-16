"""
Worker en arrière-plan pour les tâches de daily check
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Callable
from .ssh_executor import SSHExecutor
from .excel_generator import ExcelGenerator
from ..models import DailyCheck, CheckCommand
from ..screenshot_integration import capture_firewall_screenshot_with_fallback

logger = logging.getLogger(__name__)

class BackgroundWorker:
    """
    Worker pour exécuter les daily checks en arrière-plan
    """
    
    def __init__(self):
        self.ssh_executor = SSHExecutor()
        self.excel_generator = ExcelGenerator()
    
    def execute_daily_checks(self, firewalls: List, commands: List[str], user, 
                           task_id: str, status_callback: Callable) -> List[Dict[str, Any]]:
        """
        Exécute les daily checks pour une liste de firewalls avec génération d'un seul rapport
        
        Args:
            firewalls: Liste des firewalls à traiter
            commands: Liste des commandes à exécuter
            user: Utilisateur qui a lancé la tâche
            task_id: ID de la tâche
            status_callback: Fonction de callback pour mettre à jour le statut
            
        Returns:
            List[Dict]: Résultats des daily checks
        """
        total_firewalls = len(firewalls)
        processed_firewalls = 0
        results = []
        
        # Démarrer le rapport multi-firewall avec architecture de dossiers
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = self.excel_generator.start_multi_firewall_report(firewalls, timestamp)
        logger.info(f"Started multi-firewall report: {report_path}")
        
        # Grouper les firewalls par data center et type
        firewall_groups = self._group_firewalls(firewalls)
        summary_row = 6  # Commencer à la ligne 6 (après les en-têtes et info dossier)
        
        try:
            for dc_name, fw_types in firewall_groups.items():
                for fw_type, group_firewalls in fw_types.items():
                    for firewall in group_firewalls:
                        try:
                            # Mettre à jour le statut et vérifier le timeout
                            status_update = {
                                'message': f'Processing {firewall.name}...',
                                'progress': int((processed_firewalls / total_firewalls) * 100)
                            }
                            
                            # Vérifier si le callback retourne False (timeout)
                            if not status_callback(task_id, status_update):
                                logger.warning(f"Task {task_id} cancelled due to timeout")
                                break
                            
                            # Traiter ce firewall
                            result = self._process_single_firewall_for_multi_report(
                                firewall, commands, user, summary_row
                            )
                            results.append(result)
                            
                            processed_firewalls += 1
                            summary_row += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing firewall {firewall.id}: {str(e)}")
                            results.append({
                                'firewall_id': firewall.id,
                                'status': 'ERROR',
                                'success': False,
                                'error': str(e)
                            })
                            processed_firewalls += 1
                            summary_row += 1
            
            # Finaliser le rapport
            final_report_path = self.excel_generator.finalize_report()
            logger.info(f"Multi-firewall report finalized: {final_report_path}")
            
            # Ajouter le chemin du rapport à tous les résultats
            for result in results:
                result['report_path'] = final_report_path
            
        except Exception as e:
            logger.error(f"Error in multi-firewall report generation: {e}")
            # Essayer de finaliser le rapport même en cas d'erreur
            try:
                self.excel_generator.finalize_report()
            except:
                pass
        
        return results
    
    def _group_firewalls(self, firewalls: List) -> Dict[str, Dict[str, List]]:
        """
        Groupe les firewalls par data center et type
        
        Args:
            firewalls: Liste des firewalls
            
        Returns:
            Dict: Firewalls groupés
        """
        firewall_groups = {}
        
        for firewall in firewalls:
            dc_name = firewall.data_center.name if firewall.data_center else 'Unknown_DC'
            fw_type = firewall.firewall_type.name if firewall.firewall_type else 'Unknown_FW_Type'
            
            if dc_name not in firewall_groups:
                firewall_groups[dc_name] = {}
            if fw_type not in firewall_groups[dc_name]:
                firewall_groups[dc_name][fw_type] = []
            
            firewall_groups[dc_name][fw_type].append(firewall)
        
        return firewall_groups
    
    def _process_single_firewall_for_multi_report(self, firewall, commands: List[str], user, summary_row: int) -> Dict[str, Any]:
        """
        Traite un seul firewall pour le rapport multi-feuilles
        
        Args:
            firewall: Instance du modèle Firewall
            commands: Liste des commandes à exécuter
            user: Utilisateur qui exécute les commandes
            summary_row: Numéro de ligne pour le résumé
            
        Returns:
            Dict: Résultat du traitement
        """
        daily_check = None
        
        try:
            # Créer le daily check
            daily_check = DailyCheck.objects.create(
                firewall=firewall,
                status='PENDING'
            )
            
            # Capturer le screenshot (non bloquant)
            logger.info(f"Capturing screenshot for firewall {firewall.name}")
            screenshot_result = capture_firewall_screenshot_with_fallback(firewall, user)
            
            if screenshot_result['success']:
                daily_check.screenshot_base64 = screenshot_result['screenshot_base64']
                daily_check.screenshot_captured = True
                logger.info(f"Screenshot captured for firewall {firewall.name}")
            else:
                logger.warning(f"Screenshot capture failed for firewall {firewall.name}: {screenshot_result.get('error', 'Unknown error')}")
            
            daily_check.save()
            
            # Exécuter les commandes SSH avec timeout
            logger.info(f"Executing SSH commands for firewall {firewall.name}")
            ssh_results = self.ssh_executor.execute_commands_in_session(firewall, commands, user)
            
            # Vérifier si toutes les commandes ont échoué (connexion impossible)
            all_failed = all(cmd_result['status'] == 'failed' for cmd_result in ssh_results)
            if all_failed:
                logger.error(f"All SSH commands failed for firewall {firewall.name} - likely connection issue")
                daily_check.status = 'CONNECTION_FAILED'
                daily_check.save()
                
                # Ajouter au rapport multi-feuilles
                self.excel_generator.add_firewall_sheet(daily_check, ssh_results, firewall)
                self.excel_generator.update_summary_with_firewall(daily_check, firewall, summary_row)
                
                return {
                    'firewall_id': firewall.id,
                    'status': 'CONNECTION_FAILED',
                    'success': False,
                    'error': 'SSH connection failed - firewall may be unreachable'
                }
            
            # Créer les enregistrements CheckCommand
            check_results = []
            for cmd_result in ssh_results:
                command_result = CheckCommand.objects.create(
                    daily_check=daily_check,
                    command=cmd_result['command'],
                    actual_output=cmd_result['output'] if cmd_result['status'] == 'completed' else cmd_result['error'],
                    status='SUCCESS' if cmd_result['status'] == 'completed' else 'FAILED'
                )
                check_results.append(command_result)
            
            # Mettre à jour le statut
            daily_check.status = 'SUCCESS'
            for res in check_results:
                if res.status == 'FAILED':
                    daily_check.status = 'PARTIAL_SUCCESS'
                    break
            daily_check.save()
            
            # Ajouter au rapport multi-feuilles
            self.excel_generator.add_firewall_sheet(daily_check, ssh_results, firewall)
            self.excel_generator.update_summary_with_firewall(daily_check, firewall, summary_row)
            
            return {
                'firewall_id': firewall.id,
                'status': daily_check.status,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error processing firewall {firewall.id}: {str(e)}")
            
            # Mettre à jour le statut en cas d'erreur
            if daily_check:
                daily_check.status = 'ERROR'
                daily_check.save()
                
                # Ajouter au rapport même en cas d'erreur
                try:
                    error_results = [{
                        'command': 'Error',
                        'status': 'failed',
                        'output': None,
                        'error': str(e)
                    }]
                    self.excel_generator.add_firewall_sheet(daily_check, error_results, firewall)
                    self.excel_generator.update_summary_with_firewall(daily_check, firewall, summary_row)
                except:
                    pass
            
            return {
                'firewall_id': firewall.id,
                'status': 'ERROR',
                'success': False,
                'error': str(e)
            }
    
    def _process_single_firewall(self, firewall, commands: List[str], user) -> Dict[str, Any]:
        """
        Traite un seul firewall avec gestion d'erreur améliorée
        
        Args:
            firewall: Instance du modèle Firewall
            commands: Liste des commandes à exécuter
            user: Utilisateur qui exécute les commandes
            
        Returns:
            Dict: Résultat du traitement
        """
        daily_check = None
        
        try:
            # Créer le daily check
            daily_check = DailyCheck.objects.create(
                firewall=firewall,
                status='PENDING'
            )
            
            # Capturer le screenshot (non bloquant)
            logger.info(f"Capturing screenshot for firewall {firewall.name}")
            screenshot_result = capture_firewall_screenshot_with_fallback(firewall, user)
            
            if screenshot_result['success']:
                daily_check.screenshot_base64 = screenshot_result['screenshot_base64']
                daily_check.screenshot_captured = True
                logger.info(f"Screenshot captured for firewall {firewall.name}")
            else:
                logger.warning(f"Screenshot capture failed for firewall {firewall.name}: {screenshot_result.get('error', 'Unknown error')}")
            
            daily_check.save()
            
            # Exécuter les commandes SSH avec timeout
            logger.info(f"Executing SSH commands for firewall {firewall.name}")
            ssh_results = self.ssh_executor.execute_commands_in_session(firewall, commands, user)
            
            # Vérifier si toutes les commandes ont échoué (connexion impossible)
            all_failed = all(cmd_result['status'] == 'failed' for cmd_result in ssh_results)
            if all_failed:
                logger.error(f"All SSH commands failed for firewall {firewall.name} - likely connection issue")
                daily_check.status = 'CONNECTION_FAILED'
                daily_check.save()
                
                # Générer un rapport d'erreur
                filepath = self._generate_error_report(daily_check, firewall, "Connection failed")
                
                return {
                    'firewall_id': firewall.id,
                    'status': 'CONNECTION_FAILED',
                    'success': False,
                    'error': 'SSH connection failed - firewall may be unreachable',
                    'report_path': filepath
                }
            
            # Créer les enregistrements CheckCommand
            check_results = []
            for cmd_result in ssh_results:
                command_result = CheckCommand.objects.create(
                    daily_check=daily_check,
                    command=cmd_result['command'],
                    actual_output=cmd_result['output'] if cmd_result['status'] == 'completed' else cmd_result['error'],
                    status='SUCCESS' if cmd_result['status'] == 'completed' else 'FAILED'
                )
                check_results.append(command_result)
            
            # Générer le fichier Excel
            filepath = self.excel_generator.generate_report(daily_check, ssh_results, firewall)
            
            # Mettre à jour le statut
            daily_check.excel_report = filepath
            daily_check.status = 'SUCCESS'
            for res in check_results:
                if res.status == 'FAILED':
                    daily_check.status = 'PARTIAL_SUCCESS'
                    break
            daily_check.save()
            
            return {
                'firewall_id': firewall.id,
                'status': daily_check.status,
                'success': True,
                'report_path': filepath
            }
            
        except Exception as e:
            logger.error(f"Error processing firewall {firewall.id}: {str(e)}")
            
            # Mettre à jour le statut en cas d'erreur
            if daily_check:
                daily_check.status = 'ERROR'
                daily_check.save()
                
                # Générer un rapport d'erreur
                try:
                    filepath = self._generate_error_report(daily_check, firewall, str(e))
                except:
                    filepath = None
            
            return {
                'firewall_id': firewall.id,
                'status': 'ERROR',
                'success': False,
                'error': str(e),
                'report_path': filepath if daily_check else None
            }
    
    def _generate_error_report(self, daily_check, firewall, error_message: str) -> str:
        """
        Génère un rapport d'erreur Excel
        
        Args:
            daily_check: Instance du modèle DailyCheck
            firewall: Instance du modèle Firewall
            error_message: Message d'erreur
            
        Returns:
            str: Chemin vers le fichier Excel généré
        """
        try:
            # Créer des résultats d'erreur factices
            error_results = [{
                'command': 'Connection Test',
                'status': 'failed',
                'output': None,
                'error': error_message
            }]
            
            return self.excel_generator.generate_report(daily_check, error_results, firewall)
        except Exception as e:
            logger.error(f"Failed to generate error report: {e}")
            return None
