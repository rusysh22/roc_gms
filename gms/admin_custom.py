from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpRequest
from gms.models import (
    SiteConfiguration, BusinessUnit, Participant, Referee, Venue, 
    Event, Club, CompetitionFormat, Competition, Match, MatchResult, 
    Disqualification, Standings, Medal, Announcement
)
from gms.admin import (
    SiteConfigurationAdmin, BusinessUnitAdmin, ParticipantAdmin, RefereeAdmin, VenueAdmin, 
    EventAdmin, ClubAdmin, CompetitionFormatAdmin, CompetitionAdmin, MatchAdmin, MatchResultAdmin, 
    DisqualificationAdmin, StandingsAdmin, MedalAdmin, AnnouncementAdmin
)

class CustomAdminSite(AdminSite):
    """
    Custom admin site that dynamically sets the site title and logo
    based on SiteConfiguration
    """
    
    def each_context(self, request):
        """
        Return a dictionary of variables to add to the template context for
        *every* page in the admin site.
        """
        context = super().each_context(request)
        
        # Get the site configuration
        try:
            site_config = SiteConfiguration.objects.first()
            if site_config:
                # Update the site title dynamically
                self.site_header = site_config.site_name
                self.site_title = site_config.site_name
                
                context.update({
                    'site_name': site_config.site_name,
                    'site_header': site_config.site_name,
                    'site_title': site_config.site_name,
                    'site_logo': site_config.logo.url if site_config.logo else None,
                    'site_favicon': site_config.favicon.url if site_config.favicon else None,
                })
            else:
                context.update({
                    'site_name': 'GMS Admin',
                    'site_header': 'GMS Administration',
                    'site_title': 'GMS Admin',
                    'site_logo': None,
                    'site_favicon': None,
                })
        except:
            # Fallback in case of database issues
            context.update({
                'site_name': 'GMS Admin',
                'site_header': 'GMS Administration',
                'site_title': 'GMS Admin',
                'site_logo': None,
                'site_favicon': None,
            })
        
        return context

# Create a custom admin site instance
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register all models with their respective admin classes
custom_admin_site.register(SiteConfiguration, SiteConfigurationAdmin)
custom_admin_site.register(BusinessUnit, BusinessUnitAdmin)
custom_admin_site.register(Participant, ParticipantAdmin)
custom_admin_site.register(Referee, RefereeAdmin)
custom_admin_site.register(Venue, VenueAdmin)
custom_admin_site.register(Event, EventAdmin)
custom_admin_site.register(Club, ClubAdmin)
custom_admin_site.register(CompetitionFormat, CompetitionFormatAdmin)
custom_admin_site.register(Competition, CompetitionAdmin)
custom_admin_site.register(Match, MatchAdmin)
custom_admin_site.register(MatchResult, MatchResultAdmin)
custom_admin_site.register(Disqualification, DisqualificationAdmin)
custom_admin_site.register(Standings, StandingsAdmin)
custom_admin_site.register(Medal, MedalAdmin)
custom_admin_site.register(Announcement, AnnouncementAdmin)

# Also register User
from django.contrib.auth.models import User
from gms.admin_user import CustomUserAdmin

custom_admin_site.register(User, CustomUserAdmin)