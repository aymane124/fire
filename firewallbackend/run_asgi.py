import os
import sys
import django
import logging
import uvicorn
from django.core.management import execute_from_command_line

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firewallbackend.settings')
        django.setup()
        
        # Disable autoreload when running as PyInstaller executable
        if getattr(sys, 'frozen', False):
            os.environ['DJANGO_AUTORELOAD_ENV'] = 'false'
            # Add the application directory to the path
            application_path = os.path.dirname(os.path.abspath(sys.executable))
            if application_path not in sys.path:
                sys.path.insert(0, application_path)
            
            # Ensure staticfiles directory exists
            staticfiles_dir = os.path.join(application_path, 'staticfiles')
            if not os.path.exists(staticfiles_dir):
                os.makedirs(staticfiles_dir)
        
        logger.info("Starting ASGI server on http://0.0.0.0:8000")
        
        # Use uvicorn with ASGI application
        uvicorn.run(
            "firewallbackend.asgi:application",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"Failed to start ASGI server: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
