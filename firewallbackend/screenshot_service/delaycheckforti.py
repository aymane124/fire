"""
Script delaycheckforti pour vérifier et capturer les informations du FortiGate
avec délai et vérifications intelligentes.
"""

import logging
import time
import base64
import requests
from typing import Dict, Any, Optional, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class DelayCheckForti:
    """
    Classe pour gérer la vérification et capture des informations FortiGate
    avec délais et vérifications intelligentes.
    """
    
    def __init__(self, page: Page, timeout: int = 30000):
        """
        Initialise le script DelayCheckForti.
        
        Args:
            page: Instance de la page Playwright
            timeout: Timeout en millisecondes (défaut: 30 secondes)
        """
        self.page = page
        self.timeout = timeout
        self.page.set_default_timeout(timeout)
        
    def wait_and_check_page_load(self, wait_time: int = 3000) -> bool:
        """
        Attend que la page se charge complètement et vérifie l'état.
        
        Args:
            wait_time: Temps d'attente en millisecondes
            
        Returns:
            bool: True si la page est chargée correctement
        """
        try:
            logger.info(f"Waiting {wait_time}ms for page to load...")
            self.page.wait_for_timeout(wait_time)
            
            # Vérifier que la page est chargée
            self.page.wait_for_load_state('domcontentloaded')
            
            # Vérifier qu'on n'est pas sur une page d'erreur
            current_url = self.page.url.lower()
            if 'error' in current_url or '404' in current_url:
                logger.warning(f"Page appears to be an error page: {current_url}")
                return False
                
            logger.info("Page loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error waiting for page load: {e}")
            return False
    
    def check_forticare_popup(self) -> bool:
        """
        Vérifie et ferme les popups FortiCare s'ils existent.
        
        Returns:
            bool: True si un popup a été fermé, False sinon
        """
        popup_selectors = [
            'button:has-text("Later")',
            'button:has-text("read-only")',
            'button:has-text("Read-Only")',
            'button:has-text("READ-ONLY")',
            'button:has-text("Remind me later")',
            'button:has-text("Skip")',
            'button:has-text("Plus tard")',
            'button:has-text("Ignorer")',
            'button:has-text("Passer")',
            '.btn:has-text("Later")',
            '.btn:has-text("read-only")',
            '.button:has-text("Later")',
            '.button:has-text("read-only")',
            '[data-testid*="later"]',
            '[data-testid*="skip"]',
            '[data-testid*="dismiss"]',
            'input[type="button"][value*="Later"]',
            'input[type="button"][value*="read-only"]'
        ]
        
        popup_closed = False
        for selector in popup_selectors:
            try:
                element = self.page.query_selector(selector)
                if element and element.is_visible():
                    logger.info(f"Closing popup with selector: {selector}")
                    element.click()
                    self.page.wait_for_timeout(500)
                    popup_closed = True
                    break
            except Exception:
                continue
                
        return popup_closed
    
    def wait_for_dashboard_ready(self, max_wait: int = 10000) -> bool:
        """
        Attend que le dashboard soit prêt avec vérifications intelligentes.
        
        Args:
            max_wait: Temps maximum d'attente en millisecondes
            
        Returns:
            bool: True si le dashboard est prêt
        """
        logger.info(f"Waiting up to {max_wait}ms for dashboard to be ready...")
        
        start_time = time.time()
        dashboard_ready = False
        
        while (time.time() - start_time) * 1000 < max_wait:
            try:
                # Vérifier si les widgets principaux sont présents
                system_widget = self.page.query_selector('f-system-information-widget, li:has(.widget-title:has-text("System Information"))')
                license_widget = self.page.query_selector('f-license-information-widget, li:has(.widget-title:has-text("Licenses"))')
                
                if system_widget and license_widget:
                    logger.info("Dashboard widgets detected - ready for capture")
                    dashboard_ready = True
                    break
                    
                # Vérifier les popups et les fermer
                if self.check_forticare_popup():
                    logger.info("Popup closed, continuing to wait...")
                    
                self.page.wait_for_timeout(1000)  # Attendre 1 seconde avant de revérifier
                
            except Exception as e:
                logger.warning(f"Error checking dashboard readiness: {e}")
                self.page.wait_for_timeout(1000)
                
        if not dashboard_ready:
            logger.warning("Dashboard readiness timeout reached")
            
        return dashboard_ready
    
    def find_system_info_widget(self) -> Optional[Any]:
        """
        Trouve le widget System Information.
        
        Returns:
            Element du widget ou None si non trouvé
        """
        selectors = [
            'f-system-information-widget',
            'f-system-information-widget .widget-content-container',
            'f-system-information-widget f-dashboard-widget',
            'li:has(.widget-title:has-text("System Information"))',
            'li:has(f-system-information-widget)',
            'li:has(.widget-title:has-text("System Information")):has(.table.key-value)',
            'li:has-text("System Information"):has-text("Hostname"):has-text("Serial Number")',
            'li[data-widget-id]:has(.widget-title:has-text("System Information"))',
            'div:has-text("System Information"):has-text("Hostname"):has-text("Serial Number")'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element and element.is_visible():
                    logger.info(f"Found System Information widget: {selector}")
                    return element
            except Exception:
                continue
                
        logger.warning("System Information widget not found")
        return None
    
    def find_license_widget(self) -> Optional[Any]:
        """
        Trouve le widget Licenses.
        
        Returns:
            Element du widget ou None si non trouvé
        """
        selectors = [
            'f-license-information-widget',
            'f-license-information-widget .widget-content-container',
            'f-license-information-widget f-dashboard-widget',
            'li:has(.widget-title:has-text("Licenses"))',
            'li:has(f-license-information-widget)',
            'li:has(.widget-title:has-text("Licenses")):has(.license-container)',
            'li:has-text("Licenses"):has-text("FortiCare Support"):has-text("IPS")',
            'li[data-widget-id]:has(.widget-title:has-text("Licenses"))',
            'div:has-text("Licenses"):has-text("FortiCare Support"):has-text("IPS")'
        ]
        
        for selector in selectors:
            try:
                element = self.page.query_selector(selector)
                if element and element.is_visible():
                    logger.info(f"Found Licenses widget: {selector}")
                    return element
            except Exception:
                continue
                
        logger.warning("Licenses widget not found")
        return None
    
    def capture_targeted_sections(self) -> Optional[bytes]:
        """
        Capture uniquement les sections System Information et Licenses.
        
        Returns:
            Bytes de l'image ou None en cas d'erreur
        """
        try:
            logger.info("Starting targeted capture of System Information and Licenses sections")
            
            # Trouver les widgets
            system_widget = self.find_system_info_widget()
            license_widget = self.find_license_widget()
            
            if not system_widget or not license_widget:
                logger.error("Could not find both required widgets")
                return None
            
            # Obtenir les coordonnées
            system_box = system_widget.bounding_box()
            license_box = license_widget.bounding_box()
            
            if not system_box or not license_box:
                logger.error("Could not get bounding boxes for widgets")
                return None
            
            logger.info(f"System widget: x={system_box['x']}, y={system_box['y']}, w={system_box['width']}, h={system_box['height']}")
            logger.info(f"License widget: x={license_box['x']}, y={license_box['y']}, w={license_box['width']}, h={license_box['height']}")
            
            # Calculer la zone combinée
            min_x = min(system_box['x'], license_box['x'])
            min_y = min(system_box['y'], license_box['y'])
            max_x = max(system_box['x'] + system_box['width'], license_box['x'] + license_box['width'])
            max_y = max(system_box['y'] + system_box['height'], license_box['y'] + license_box['height'])
            
            # Ajouter un padding avec 10px supplémentaires en haut
            padding = 20
            top_padding = 30  # 20px normal + 10px supplémentaires en haut
            clip_area = {
                'x': max(0, min_x - padding),
                'y': max(0, min_y - top_padding),  # Plus d'espace en haut
                'width': max_x - min_x + (padding * 2),
                'height': max_y - min_y + (padding * 2) + (top_padding - padding)  # Ajuster la hauteur
            }
            
            # Prendre la capture
            screenshot_bytes = self.page.screenshot(clip=clip_area)
            logger.info(f"Targeted screenshot captured successfully (area: {clip_area})")
            
            return screenshot_bytes
            
        except Exception as e:
            logger.error(f"Error capturing targeted sections: {e}")
            return None
    
    def execute_delay_check(self, url: str, wait_after_popup: int = 1000) -> Dict[str, Any]:
        """
        Exécute le processus complet de vérification avec délais.
        
        Args:
            url: URL du FortiGate
            wait_after_popup: Temps d'attente après fermeture de popup (ms)
            
        Returns:
            Dict avec les résultats de l'opération
        """
        result = {
            'success': False,
            'screenshot_bytes': None,
            'error': None,
            'steps_completed': []
        }
        
        try:
            logger.info(f"Starting DelayCheckForti execution for URL: {url}")
            
            # Étape 1: Aller à la page
            logger.info("Step 1: Navigating to page")
            self.page.goto(url)
            result['steps_completed'].append('navigation')
            
            # Étape 2: Attendre le chargement de la page
            logger.info("Step 2: Waiting for page load")
            if not self.wait_and_check_page_load():
                result['error'] = "Page failed to load properly"
                return result
            result['steps_completed'].append('page_load')
            
            # Étape 3: Vérifier et fermer les popups
            logger.info("Step 3: Checking and closing popups")
            popup_closed = self.check_forticare_popup()
            if popup_closed:
                logger.info(f"Popup closed, waiting {wait_after_popup}ms...")
                self.page.wait_for_timeout(wait_after_popup)
            result['steps_completed'].append('popup_check')
            
            # Étape 4: Attendre que le dashboard soit prêt
            logger.info("Step 4: Waiting for dashboard readiness")
            if not self.wait_for_dashboard_ready():
                logger.warning("Dashboard not fully ready, but proceeding...")
            result['steps_completed'].append('dashboard_ready')
            
            # Étape 5: Capturer les sections ciblées
            logger.info("Step 5: Capturing targeted sections")
            screenshot_bytes = self.capture_targeted_sections()
            if screenshot_bytes:
                result['screenshot_bytes'] = screenshot_bytes
                result['success'] = True
                result['steps_completed'].append('screenshot_capture')
            else:
                result['error'] = "Failed to capture targeted sections"
            
            logger.info(f"DelayCheckForti execution completed. Steps: {result['steps_completed']}")
            return result
            
        except Exception as e:
            logger.error(f"DelayCheckForti execution failed: {e}")
            result['error'] = str(e)
            return result


def execute_delaycheckforti(page: Page, url: str, timeout: int = 30000, wait_after_popup: int = 1000) -> Dict[str, Any]:
    """
    Fonction utilitaire pour exécuter DelayCheckForti.
    
    Args:
        page: Instance de la page Playwright
        url: URL du FortiGate
        timeout: Timeout en millisecondes
        wait_after_popup: Temps d'attente après fermeture de popup (ms)
        
    Returns:
        Dict avec les résultats de l'opération
    """
    delay_check = DelayCheckForti(page, timeout)
    return delay_check.execute_delay_check(url, wait_after_popup)


def execute_autonomous_delaycheckforti(
    ip_address: str,
    protocol: str = 'https',
    path: str = '/login',
    username: str = '',
    password: str = '',
    timeout: int = 30000,
    wait_after_popup: int = 1000,
    viewport_width: int = 1366,
    viewport_height: int = 768,
    ignore_https_errors: bool = True
) -> Dict[str, Any]:
    """
    Fonction autonome pour exécuter DelayCheckForti avec IP et protocole.
    Gère tout le processus : navigation, authentification, capture.
    
    Args:
        ip_address: Adresse IP du FortiGate
        protocol: Protocole (http ou https)
        path: Chemin d'accès (défaut: /login)
        username: Nom d'utilisateur
        password: Mot de passe
        timeout: Timeout en millisecondes
        wait_after_popup: Temps d'attente après fermeture de popup (ms)
        viewport_width: Largeur du viewport
        viewport_height: Hauteur du viewport
        ignore_https_errors: Ignorer les erreurs HTTPS
        
    Returns:
        Dict avec les résultats de l'opération
    """
    result = {
        'success': False,
        'screenshot_bytes': None,
        'image_base64': None,
        'error': None,
        'steps_completed': []
    }
    
    try:
        logger.info(f"Starting autonomous DelayCheckForti for {protocol}://{ip_address}{path}")
        
        # Construire l'URL
        base_url = f"{protocol}://{ip_address}"
        url = urljoin(base_url if base_url.endswith('/') else base_url + '/', path.lstrip('/'))
        
        with sync_playwright() as pw:
            # Lancer le navigateur
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height},
                ignore_https_errors=ignore_https_errors
            )
            page = context.new_page()
            page.set_default_timeout(timeout)
            
            # Tentative de pré-authentification via API HTTP
            if username and password:
                logger.info("Attempting pre-authentication via HTTP API")
                try:
                    parsed = urlparse(url)
                    base_origin = f"{parsed.scheme}://{parsed.hostname}"
                    if parsed.port:
                        base_origin += f":{parsed.port}"
                    
                    with requests.Session() as s:
                        s.verify = False if ignore_https_errors else True
                        s.headers.update({'User-Agent': 'Mozilla/5.0'})
                        login_endpoints = ['logincheck', 'remote/logincheck', 'logincgi']
                        payload_variants = [
                            {'username': username, 'secretkey': password},
                            {'ajax': '1', 'username': username, 'secretkey': password},
                        ]
                        
                        for ep in login_endpoints:
                            login_url = urljoin(base_origin if base_origin.endswith('/') else base_origin + '/', ep)
                            for pdata in payload_variants:
                                try:
                                    resp = s.post(login_url, data=pdata, timeout=min(15, max(5, timeout // 1000)), allow_redirects=True)
                                    if resp.status_code in (200, 302, 303) and s.cookies:
                                        # Transférer les cookies au contexte du navigateur
                                        cookies_to_add = []
                                        for c in s.cookies:
                                            cookies_to_add.append({
                                                'name': c.name,
                                                'value': c.value,
                                                'domain': parsed.hostname,
                                                'path': c.path or '/',
                                                'httpOnly': True,
                                                'secure': parsed.scheme == 'https',
                                            })
                                        if cookies_to_add:
                                            context.add_cookies(cookies_to_add)
                                            logger.info("Pre-authentication successful, cookies transferred")
                                            break
                                except Exception:
                                    continue
                            else:
                                continue
                            break
                except Exception as e:
                    logger.warning(f"Pre-authentication failed: {e}")
            
            # Naviguer vers la page
            logger.info(f"Navigating to: {url}")
            page.goto(url)
            result['steps_completed'].append('navigation')
            
            # Authentification UI si nécessaire
            if username and password:
                logger.info("Attempting UI authentication")
                current_url = page.url.lower()
                has_login_fields = page.query_selector('#username, input[name="username"], input[name="usr"]')
                
                if 'login' in current_url or 'auth' in current_url or has_login_fields:
                    username_selector = '#username, input[name="username"], input[name="usr"]'
                    password_selector = '#secretkey, input[type="password"][name="password"], input[type="password"]'
                    submit_selector = '#login_button, button[type="submit"], input[type="submit"], button:has-text("Log In"), button:has-text("Login")'
                    
                    def try_login(target):
                        try:
                            target.fill(username_selector, username)
                            target.fill(password_selector, password)
                            try:
                                target.click(submit_selector)
                                page.wait_for_timeout(3000)
                                return True
                            except Exception:
                                try:
                                    target.press(password_selector, 'Enter')
                                    page.wait_for_timeout(3000)
                                    return True
                                except Exception:
                                    return False
                        except Exception:
                            return False
                    
                    # Essayer sur la page principale
                    if try_login(page):
                        logger.info("Login successful on main page")
                        result['steps_completed'].append('ui_authentication')
                    else:
                        # Essayer dans un iframe
                        try:
                            iframe = page.query_selector('iframe')
                            if iframe:
                                frame = iframe.content_frame()
                                if frame and try_login(frame):
                                    logger.info("Login successful in iframe")
                                    result['steps_completed'].append('ui_authentication')
                        except Exception:
                            pass
            
            # Exécuter le processus DelayCheckForti
            delay_check = DelayCheckForti(page, timeout)
            delay_result = delay_check.execute_delay_check(page.url, wait_after_popup)
            
            if delay_result['success'] and delay_result['screenshot_bytes']:
                result['screenshot_bytes'] = delay_result['screenshot_bytes']
                result['image_base64'] = base64.b64encode(delay_result['screenshot_bytes']).decode('utf-8')
                result['success'] = True
                result['steps_completed'].extend(delay_result['steps_completed'])
                logger.info("Autonomous DelayCheckForti completed successfully")
            else:
                result['error'] = delay_result.get('error', 'Failed to capture screenshot')
            
            browser.close()
            
    except Exception as e:
        logger.error(f"Autonomous DelayCheckForti execution failed: {e}")
        result['error'] = str(e)
    
    return result
