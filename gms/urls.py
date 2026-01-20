from django.urls import path
from . import views

app_name = 'gms'

urlpatterns = [
    # Main pages
    path('', views.homepage, name='homepage'),
    path('events/', views.events_list, name='events'),
    path('competitions/', views.competitions_list, name='competitions'),
    path('announcements/', views.announcements_list, name='announcements'),
    path('clubs/', views.clubs_list, name='clubs'),
    path('contact/', views.contact_page, name='contact'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('competition/<int:competition_id>/', views.competition_detail, name='competition_detail'),
    path('competition/<int:competition_id>/award-medals/', views.award_competition_medals, name='award_competition_medals'),
    path('club/<int:club_id>/', views.club_detail, name='club_detail'),
    path('match-results-input/', views.match_results_input, name='match_results_input'),
    path('competition/<int:competition_id>/manage-playoffs/', views.manage_playoffs, name='manage_playoffs'),
    path('bracket/gracket/<int:competition_id>/', views.bracket_detail_gracket, name='bracket_detail_gracket'),
    path('bracket/<int:competition_id>/', views.bracket_detail, name='bracket_detail'),
    path('bracket/generate-matches/<int:competition_id>/', views.generate_bracket_matches, name='generate_bracket_matches'),
    path('competition/<int:competition_id>/generate-round-robin/', views.generate_round_robin_schedule, name='generate_round_robin_schedule'),
    path('bracket/generate-draft-matches/<int:competition_id>/', views.generate_draft_matches, name='generate_draft_matches'),
    path('bracket/update-seeding/<int:competition_id>/', views.update_bracket_seeding, name='update_bracket_seeding'),
    path('bracket/update-team/', views.update_bracket_team, name='update_bracket_team'),
    path('bracket/assign-dates/<int:competition_id>/', views.assign_match_dates, name='assign_match_dates'),
    path('bracket/finalize-schedule/<int:competition_id>/', views.finalize_schedule, name='finalize_schedule'),
    path('bracket/fetch-draft-matches/<int:competition_id>/', views.fetch_draft_matches, name='fetch_draft_matches'),
    path('bracket/assign-match-dates-inline/<int:competition_id>/', views.assign_match_dates_inline, name='assign_match_dates_inline'),
    path('bracket/venues/', views.get_all_venues, name='get_all_venues'),
    path('bracket/update-match-details/', views.update_match_details, name='update_match_details'),
    path('bracket/save-seeding/<int:competition_id>/', views.save_seeding_and_generate_matches, name='save_seeding_and_generate_matches'),
    path('bracket/reset/<int:competition_id>/', views.reset_bracket, name='reset_bracket'),
    
    # HTMX partials for dynamic updates
    path('htmx/event/<int:event_id>/overview/', views.event_overview_partial, name='event_overview_partial'),
    path('htmx/event/<int:event_id>/schedule/', views.event_schedule_partial, name='event_schedule_partial'),
    path('htmx/event/<int:event_id>/medals/', views.event_medals_partial, name='event_medals_partial'),
    path('htmx/event/<int:event_id>/announcements/', views.event_announcements_partial, name='event_announcements_partial'),
    path('htmx/competition/<int:competition_id>/schedule/', views.competition_schedule_partial, name='competition_schedule_partial'),
    path('htmx/competition/<int:competition_id>/standings/', views.competition_standings_partial, name='competition_standings_partial'),
    path('htmx/competition/<int:competition_id>/results/', views.competition_results_partial, name='competition_results_partial'),
    path('htmx/competition/<int:competition_id>/bracket_display/', views.competition_bracket_display_partial, name='competition_bracket_display_partial'),
    path('htmx/club/<int:club_id>/matches/', views.club_matches_partial, name='club_matches_partial'),
    
    # Search and filtering endpoints
    path('search/players/', views.search_players, name='search_players'),
    path('search/clubs/', views.search_clubs, name='search_clubs'),
    path('favicon.ico', views.favicon, name='favicon'),
    
    # Silence Chrome DevTools 404
    path('.well-known/appspecific/com.chrome.devtools.json', lambda request: __import__('django.http').http.JsonResponse({}), name='chrome_devtools_dummy'),
]

# Menambahkan dokumentasi untuk URL patterns
"""
URL patterns untuk aplikasi GMS:

Main pages:
- '' - Homepage
- 'event/<int:event_id>/' - Detail event
- 'competition/<int:competition_id>/' - Detail kompetisi
- 'club/<int:club_id>/' - Detail klub

HTMX partials:
- 'htmx/event/<int:event_id>/schedule/' - Jadwal event (partial)
- 'htmx/event/<int:event_id>/medals/' - Penghargaan event (partial)
- 'htmx/competition/<int:competition_id>/schedule/' - Jadwal kompetisi (partial)
- 'htmx/competition/<int:competition_id>/standings/' - Klasemen kompetisi (partial)
- 'htmx/competition/<int:competition_id>/results/' - Hasil kompetisi (partial)
- 'htmx/club/<int:club_id>/matches/' - Pertandingan klub (partial)

Search endpoints:
- 'search/players/' - Pencarian pemain
- 'search/clubs/' - Pencarian klub
"""