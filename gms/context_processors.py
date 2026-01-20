from django.core.cache import cache
from .models import SiteConfiguration

def site_config(request):
    """
    Context processor to make site configuration available in all templates.
    """
    # Check cache first to improve performance
    cache_key = 'site_config_context'
    site_config = cache.get(cache_key)
    
    if site_config is None:
        try:
            site_config = SiteConfiguration.get_solo()  # Gunakan metode yang telah ditambahkan sebelumnya
            # Cache the site_config for 5 minutes to reduce DB queries
            cache.set(cache_key, site_config, 300)
        except:
            # In case of any error (like table doesn't exist yet), return None
            site_config = None
    
    return {'site_config': site_config}