import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gms_project.settings')

import django
django.setup()

# Now import Django related modules
from django.conf import settings
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from gms.views import homepage

def debug_homepage():
    factory = RequestFactory()
    request = factory.get('/')
    
    # Add session middleware to request
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    request.session.save()
    
    # Add user to request
    request.user = AnonymousUser()
    
    try:
        response = homepage(request)
        print("Response status code:", response.status_code)
        if response.status_code != 200:
            # If it's a 500/404/etc, the content might check errors
            print("Response content:", response.content.decode()[:2000])
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_homepage()
