"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

# Add your project directory to the sys.path
path = '/home/edvoyagenotes/project'
if path not in sys.path:
    sys.path.insert(0, path)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# Get the WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
