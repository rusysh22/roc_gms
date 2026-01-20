from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from .models import SiteConfiguration
import pytz


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the timezone from site configuration with caching to improve performance
        cache_key = 'site_config_timezone'
        site_config = cache.get(cache_key)
        
        if site_config is None:
            try:
                site_config = SiteConfiguration.get_solo()  # Gunakan metode yang telah ditambahkan sebelumnya
                cache.set(cache_key, site_config, 300)  # Cache for 5 minutes
            except:
                # If there's any error (like database not ready), deactivate timezone
                timezone.deactivate()
                return self.get_response(request)
        
        # Set timezone based on site configuration
        if hasattr(site_config, 'timezone') and site_config.timezone:
            try:
                tz = pytz.timezone(site_config.timezone)
                timezone.activate(tz)
            except pytz.exceptions.UnknownTimeZoneError:
                # If timezone is invalid, deactivate timezone
                timezone.deactivate()
        else:
            # Default to UTC if no timezone is set
            timezone.deactivate()
        
        # Set admin theme and color scheme in session
        try:
            # Use the existing site_config that was already fetched
            if hasattr(site_config, 'admin_theme') and hasattr(request, 'session'):
                request.session['admin_theme'] = getattr(site_config, 'admin_theme', 'auto')
                request.session['admin_color_scheme'] = getattr(site_config, 'admin_color_scheme', 'default')
        except:
            pass  # Fail silently if there's an issue accessing SiteConfiguration
        
        response = self.get_response(request)
        return response