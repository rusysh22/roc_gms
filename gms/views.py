import json
import math
import logging
from datetime import datetime, timedelta, date
from django.core.exceptions import ValidationError

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from .models import Event, Competition, Club, Participant, Match, MatchResult, Standings, Medal, SiteConfiguration, Venue, Announcement
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.contrib.auth.decorators import login_required
from collections import defaultdict
import calendar
from .forms import MatchResultFilterForm

logger = logging.getLogger(__name__)


def homepage(request):
    """Homepage view displaying active/upcoming events and latest announcements."""
    # Get events ordered by start date (closest first)
    events = Event.objects.select_related().all().order_by('start_date')
    
    # Get upcoming events (events starting from today onwards)
    today = timezone.now().date()
    upcoming_events = Event.objects.filter(start_date__gte=today).select_related().prefetch_related('competitions__format').order_by('start_date')
    
    # Get competitions for each upcoming event - handled by prefetch_related above
    for event in upcoming_events:
        event.competitions_list = event.competitions.all()
    
    # Get upcoming matches for the next 90 days and organize by date
    
    end_date = today + timedelta(days=90)  # Look for matches up to 3 months ahead
    all_upcoming_matches = Match.objects.filter(
        scheduled_time__date__gte=today,
        scheduled_time__date__lte=end_date
    ).select_related('competition', 'home_team', 'away_team', 'venue').order_by('scheduled_time')
    
    # Organize matches by date
    matches_by_date = defaultdict(list)
    for match in all_upcoming_matches:
        match_date = match.scheduled_time.date()
        matches_by_date[match_date].append(match)
    
    # Generate calendar data using helper
    months_data = _get_calendar_data(today, matches_by_date)
    
    # Get counts for statistics
    total_competitions = Competition.objects.count()
    total_clubs = Club.objects.count()
    total_participants = Participant.objects.count()
    
    # Get recent announcements (last 3) with related event information
    recent_announcements = Announcement.objects.select_related('event').order_by('-created_at')[:6]
    
    # Get site configuration, create if it doesn't exist
    site_config = SiteConfiguration.get_solo()
    
    context = {
        'events': events,
        'upcoming_events': upcoming_events,
        'matches_by_date': dict(matches_by_date),
        'months_data': months_data,
        'current_month_index': 0,  # Show current month first
        'total_competitions': total_competitions,
        'total_clubs': total_clubs,
        'total_participants': total_participants,
        'recent_announcements': recent_announcements,
        'site_config': site_config,
    }
    return render(request, 'gms/homepage.html', context)


def event_detail(request, event_id):
    """Event detail page showing event details, competitions, medal tally, and announcements."""
    event = get_object_or_404(Event, id=event_id)
    competitions = event.competitions.select_related('format').all()
    medals, medals_by_business_unit_list = _get_event_medals_data(event)
    
    announcements = event.announcements.all().order_by('-created_at')
    
    context = {
        'event': event,
        'competitions': competitions,
        'medals': medals,
        'medals_by_business_unit': medals_by_business_unit_list,
        'announcements': announcements,
    }
    return render(request, 'gms/event_detail.html', context)


def competition_detail(request, competition_id):
    """Competition detail page showing schedule, match results, and standings/bracket."""
    competition = get_object_or_404(Competition, id=competition_id)
    matches = competition.matches.select_related('home_team', 'away_team', 'venue').prefetch_related('referees').order_by('scheduled_time')
    standings = competition.standings.select_related('club').order_by('-points', '-wins')
    
    # Format-specific data
    format_structure_info = competition.get_format_structure_info()
    
    # Get medals for this competition
    competition_medals = Medal.objects.filter(competition=competition).select_related('club', 'event')

    context = {
        'competition': competition,
        'matches': matches,
        'standings': standings,
        'format_structure_info': format_structure_info,
        'competition_medals': competition_medals,
    }

    # If the format is single elimination, prepare the data for the bracket for the initial load
    if competition.format.format_type == 'SINGLE_ELIMINATION':
        # Generate bracket structure based on existing matches in the database or enrolled participants
        bracket_data = competition.get_bracket_data_for_visualization()
        context['teams_data_json'] = json.dumps(bracket_data)

    return render(request, 'gms/competition_detail.html', context)


def award_competition_medals(request, competition_id):
    """View to award medals for a competition."""
    if request.method == 'POST':
        competition = get_object_or_404(Competition, id=competition_id)
        
        # Only allow coordinators or superusers to award medals
        if (request.user.is_superuser or 
            request.user in competition.event.coordinators.all() or
            competition.created_by == request.user):
            
            try:
                competition.award_medals_for_competition()
                # Redirect back to the competition detail page
                return redirect('gms:competition_detail', competition_id=competition.id)
            except Exception as e:
                # Handle error appropriately
                # For now, we'll just redirect back with a generic message
                return redirect('gms:competition_detail', competition_id=competition.id)
        else:
            # Unauthorized access
            return redirect('gms:event_detail', event_id=competition.event.id)
    
    # If not POST, redirect back to competition
    return redirect('gms:competition_detail', competition_id=competition.id)


def club_detail(request, club_id):
    """Club detail page showing players in the club and matches the club is involved in."""
    club = get_object_or_404(Club, id=club_id)
    players = club.players.select_related('business_unit').all()
    matches = Match.objects.filter(
        Q(results__club=club) | 
        Q(home_team=club) |
        Q(away_team=club)
    ).select_related('competition', 'home_team', 'away_team', 'venue').prefetch_related('referees').distinct().order_by('scheduled_time')
    
    context = {
        'club': club,
        'players': players,
        'matches': matches,
    }
    return render(request, 'gms/club_detail.html', context)


# HTMX partial views for dynamic updates
def event_schedule_partial(request, event_id):
    """HTMX partial for event schedule."""
    event = get_object_or_404(Event, id=event_id)
    matches = Match.objects.filter(competition__event=event).select_related(
        'home_team', 'away_team', 'venue', 'competition'
    ).prefetch_related('referees').order_by('scheduled_time')
    
    return render(request, 'gms/partials/event_schedule.html', {'matches': matches})


def event_medals_partial(request, event_id):
    """HTMX partial for event medals."""
    event = get_object_or_404(Event, id=event_id)
    medals, medals_by_business_unit_list = _get_event_medals_data(event)
    
    return render(request, 'gms/partials/event_medals.html', {
        'medals': medals,
        'medals_by_business_unit': medals_by_business_unit_list
    })


def event_announcements_partial(request, event_id):
    """HTMX partial for event announcements."""
    event = get_object_or_404(Event, id=event_id)
    announcements = event.announcements.all().order_by('-created_at')
    
    return render(request, 'gms/partials/event_announcements.html', {'announcements': announcements})


def event_overview_partial(request, event_id):
    """HTMX partial for event overview (competitions, medals, announcements)."""
    event = get_object_or_404(Event, id=event_id)
    competitions = event.competitions.select_related('format').all()
    medals, medals_by_business_unit_list = _get_event_medals_data(event)
    announcements = event.announcements.all().order_by('-created_at')
    
    return render(request, 'gms/partials/event_overview.html', {
        'event': event,
        'competitions': competitions,
        'medals': medals,
        'medals_by_business_unit': medals_by_business_unit_list,
        'announcements': announcements,
    })


def competition_schedule_partial(request, competition_id):
    """HTMX partial for competition schedule."""
    competition = get_object_or_404(Competition, id=competition_id)
    matches = competition.matches.select_related(
        'home_team', 'away_team', 'venue'
    ).prefetch_related('results').order_by('scheduled_time')

    # Process matches to include scores
    matches_with_scores = []
    for match in matches:
        home_score = None
        away_score = None
        # This assumes a match has at most two results, one for each team
        for result in match.results.all():
            if result.club_id == match.home_team_id:
                home_score = result.score
            elif result.club_id == match.away_team_id:
                away_score = result.score
        
        matches_with_scores.append({
            'match': match,
            'home_score': home_score,
            'away_score': away_score
        })

    context = {
        'competition': competition,
        'matches_with_scores': matches_with_scores,
    }
    return render(request, 'gms/partials/competition_schedule.html', context)


def competition_standings_partial(request, competition_id):
    """HTMX partial for competition standings."""
    competition = get_object_or_404(Competition, id=competition_id)
    standings = competition.standings.select_related('club').order_by('-points', '-wins')
    
    return render(request, 'gms/partials/competition_standings.html', {
        'competition': competition,
        'standings': standings
    })


def competition_results_partial(request, competition_id):
    """HTMX partial for competition results."""
    competition = get_object_or_404(Competition, id=competition_id)
    matches = competition.matches.filter(status='COMPLETED').select_related(
        'home_team', 'away_team', 'venue'
    ).prefetch_related('results').order_by('-scheduled_time')[:5]  # Limit to last 5 completed matches (most recent first)
    
    return render(request, 'gms/partials/competition_results.html', {
        'competition': competition,
        'matches': matches
    })

def competition_bracket_display_partial(request, competition_id):
    """HTMX partial for displaying a single-elimination bracket."""
    competition = get_object_or_404(Competition, id=competition_id)
    
    # Get participants based on competition type
    if competition.participant_type == 'CLUBS':
        participants = competition.enrolled_clubs.all().order_by('name')
    else:
        participants = competition.enrolled_participants.all().order_by('full_name')

    # Format participants into the list of teams required by Gracket.js
    teams_data = []
    for i, participant in enumerate(participants):
        teams_data.append({
            "name": participant.name if hasattr(participant, 'name') else participant.full_name,
            "id": f"team-{participant.pk}",
            "seed": i + 1
        })

    # Convert to JSON for the template
    teams_json = json.dumps(teams_data)

    context = {
        'competition': competition,
        'teams_data_json': teams_json,
    }
    
    return render(request, 'gms/partials/competition_bracket_display.html', context)


def club_matches_partial(request, club_id):
    """HTMX partial for club matches."""
    club = get_object_or_404(Club, id=club_id)
    matches = Match.objects.filter(
        Q(home_team=club) | 
        Q(away_team=club)
    ).select_related('competition', 'home_team', 'away_team', 'venue').prefetch_related('referees').distinct().order_by('scheduled_time')
    
    return render(request, 'gms/partials/club_matches.html', {'matches': matches})


# Search and filtering views
def search_players(request):
    """Search for players by name."""
    query = request.GET.get('q', '')
    if query:
        players = Participant.objects.filter(
            Q(full_name__icontains=query) | Q(employee_id__icontains=query)
        )[:10]  # Limit to 10 results
    else:
        players = Participant.objects.none()
    
    results = []
    for player in players:
        results.append({
            'id': player.id,
            'full_name': player.full_name,
            'employee_id': player.employee_id,
            'business_unit': player.business_unit.name if player.business_unit else '',
        })
    
    return JsonResponse({'results': results})


def search_clubs(request):
    """Search for clubs by name."""
    query = request.GET.get('q', '')
    if query:
        clubs = Club.objects.filter(name__icontains=query)[:10]  # Limit to 10 results
    else:
        clubs = Club.objects.none()
    
    results = []
    for club in clubs:
        results.append({
            'id': club.id,
            'name': club.name,
        })
    
    return JsonResponse({'results': results})


def events_list(request):
    """List all events."""
    events = Event.objects.all().order_by('-start_date')
    context = {
        'events': events,
    }
    return render(request, 'gms/events_list.html', context)


def competitions_list(request):
    """List all competitions."""
    competitions = Competition.objects.select_related('event', 'format').all().order_by('-event__start_date')
    context = {
        'competitions': competitions,
    }
    return render(request, 'gms/competitions_list.html', context)


def announcements_list(request):
    """List all announcements."""
    # Get all announcements from all events
    announcements = Announcement.objects.select_related('event').all().order_by('-created_at')
    context = {
        'announcements': announcements,
    }
    return render(request, 'gms/announcements_list.html', context)


def clubs_list(request):
    """List all clubs."""
    clubs = Club.objects.all().order_by('name')
    context = {
        'clubs': clubs,
    }
    return render(request, 'gms/clubs_list.html', context)


def contact_page(request):
    """Contact page."""
    # Get site configuration to access contact information
    site_config, created = SiteConfiguration.objects.get_or_create(pk=1)
    context = {
        'site_config': site_config,
    }
    return render(request, 'gms/contact.html', context)


def match_results_input(request):
    """View for inputting match results by schedule date with filtering."""
    # timezone is already imported at module level
    
    # Initialize filter form
    filter_form = MatchResultFilterForm(request.GET or None)
    
    # Get filtered matches based on form filters
    # Get filtered matches based on form filters
    matches = Match.objects.filter(status='SCHEDULED').select_related(
        'home_team', 'away_team', 'venue', 'competition'
    ).prefetch_related('results').order_by('scheduled_time')
    
    # Filter by today's date if no date is provided
    if not request.GET.get('scheduled_date'):
        today = date.today()
        matches = matches.filter(scheduled_time__date=today)
    elif request.GET.get('scheduled_date'):
        try:
            scheduled_date = datetime.strptime(request.GET.get('scheduled_date'), '%Y-%m-%d').date()
            matches = matches.filter(scheduled_time__date=scheduled_date)
        except ValueError:
            pass  # Invalid date format, don't filter
    
    if request.GET.get('competition'):
        matches = matches.filter(competition_id=request.GET.get('competition'))
    
    if request.GET.get('status') and request.GET.get('status') != '':
        matches = matches.filter(status=request.GET.get('status'))
    
    # If form is submitted, process the results
    if request.method == 'POST':
        success_count = 0
        error_count = 0
        
        # Process POST data to create match results
        for match in matches:
            # Get form data for each match
            result_outcome = request.POST.get(f'result_outcome_{match.id}')
            result_score = request.POST.get(f'result_score_{match.id}')
            result_club = request.POST.get(f'result_club_{match.id}')
            result_data = request.POST.get(f'result_data_{match.id}')
            
            # Check if we have valid data to create a result
            if result_outcome and result_club:
                try:
                    # Create or update match result
                    result, created = MatchResult.objects.get_or_create(
                        match=match,
                        club_id=result_club,
                        defaults={
                            'outcome': result_outcome,
                            'score': result_score if result_score else None,
                            'result_data': result_data if result_data else {},
                            'created_by': request.user if request.user.is_authenticated else None,
                            'updated_by': request.user if request.user.is_authenticated else None
                        }
                    )
                    
                    if not created:
                        result.outcome = result_outcome
                        result.score = result_score if result_score else None
                        result.result_data = result_data if result_data else {}
                        result.updated_by = request.user if request.user.is_authenticated else None
                        result.save()
                    
                    success_count += 1
                    
                    # Update match status to 'COMPLETED' if both teams have results
                    match_results = MatchResult.objects.filter(match=match)
                    if match_results.count() >= 2:  # Both clubs have results
                        match.status = 'COMPLETED'
                        match.save()
                
                except Exception as e:
                    error_count += 1
                    error_count += 1
                    # Log the error for debugging
                    logger.error(f"Error saving result for match {match.id}: {str(e)}")
        
        # Add messages for user feedback
        if success_count > 0:
            messages.success(request, f'Successfully saved {success_count} match result(s).')
        if error_count > 0:
            messages.error(request, f'Error saving {error_count} match result(s).')
        
        # Redirect to same page to avoid resubmission
        return redirect(reverse('gms:match_results_input') + '?' + request.GET.urlencode())
    
    # For each match, get existing results
    matches_with_results = []
    for match in matches:
        # Get existing results for this match
        existing_results = match.results.all()
        result_map = {result.club.id: result for result in existing_results}
        
        matches_with_results.append({
            'match': match,
            'home_result': result_map.get(match.home_team.id),
            'away_result': result_map.get(match.away_team.id),
        })
    
    context = {
        'filter_form': filter_form,
        'matches_with_results': matches_with_results,
    }
    return render(request, 'gms/match_results_input.html', context)





def _get_event_medals_data(event):
    """Helper to get medals and aggregated business unit data for an event."""
    medals = Medal.objects.filter(event=event).select_related('competition', 'club').prefetch_related('club__players').order_by('medal_type', 'competition__name')
    
    # Aggregate medals by Business Unit
    medals_by_business_unit = {}
    for medal in medals:
        # Get all participants in the club that won the medal
        participants = medal.club.players.all()
        for participant in participants:
            business_unit = participant.business_unit
            if business_unit not in medals_by_business_unit:
                medals_by_business_unit[business_unit] = {'gold': 0, 'silver': 0, 'bronze': 0, 'total': 0}
            
            # Increment the appropriate medal count
            if medal.medal_type == 'GOLD':
                medals_by_business_unit[business_unit]['gold'] += 1
            elif medal.medal_type == 'SILVER':
                medals_by_business_unit[business_unit]['silver'] += 1
            elif medal.medal_type == 'BRONZE':
                medals_by_business_unit[business_unit]['bronze'] += 1
            
            medals_by_business_unit[business_unit]['total'] += 1
    
    # Convert to list and sort by total medals (descending)
    medals_by_business_unit_list = []
    for business_unit, counts in medals_by_business_unit.items():
        medals_by_business_unit_list.append({
            'business_unit': business_unit,
            'gold': counts['gold'],
            'silver': counts['silver'],
            'bronze': counts['bronze'],
            'total': counts['total']
        })
    
    # Sort by total medals, then gold, then silver, then bronze
    medals_by_business_unit_list.sort(key=lambda x: (-x['total'], -x['gold'], -x['silver'], -x['bronze']))
    
    return medals, medals_by_business_unit_list


def _get_calendar_data(today, matches_by_date):
    """Helper to generate calendar data for the homepage."""
    # Get the first day of current month for calendar view
    current_month = today.replace(day=1)
    
    # Collect all months that have matches
    months_with_matches = set()
    for match_date in matches_by_date.keys():
        months_with_matches.add((match_date.year, match_date.month))
    
    # Also include the current month if it doesn't have matches
    months_with_matches.add((current_month.year, current_month.month))
    
    # Sort months chronologically
    sorted_months = sorted(list(months_with_matches))
    
    # Generate calendar for each month and collect data
    months_data = []
    for year, month in sorted_months[:3]:  # Show max 3 months
        cal = calendar.monthcalendar(year, month)
        
        # Create a list of weeks with days and associated matches for this month
        calendar_weeks = []
        for week in cal:
            week_data = []
            for day in week:
                if day != 0:  # 0 represents days outside the current month
                    current_date = date(year, month, day)
                    day_matches = matches_by_date.get(current_date, [])
                    week_data.append({
                        'day': day,
                        'date': current_date,
                        'matches': day_matches,
                        'is_today': current_date == today
                    })
                else:
                    week_data.append({
                        'day': 0,
                        'date': None,
                        'matches': [],
                        'is_today': False
                    })
            calendar_weeks.append(week_data)
        
        months_data.append({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'weeks': calendar_weeks
        })
    
    return months_data


def _advance_winner_to_next_round(match, winner, competition):
    """Helper function to advance winner to the next round match."""
    if not match.round_number:
        return
    
    next_round_num = match.round_number + 1
    if competition.format.format_type != 'SINGLE_ELIMINATION':
        return
    
    # Find the next match in the next round where a team position is not yet filled
    next_round_matches = Match.objects.filter(
        competition=competition, 
        round_number=next_round_num
    ).order_by('id')  # Order by id to ensure consistent progression
    
    # Find the first match in the next round that has an empty team slot
    for next_match in next_round_matches:
        if competition.participant_type == 'CLUBS':
            # For club competitions, set club fields
            if not next_match.home_team_id:
                next_match.home_team = winner
                next_match.save()
                break
            elif not next_match.away_team_id:
                next_match.away_team = winner
                next_match.save()
                break
        else:  # PARTICIPANTS
            # For participant competitions, set participant fields
            if not next_match.home_participant_id:
                next_match.home_participant = winner
                next_match.save()
                break
            elif not next_match.away_participant_id:
                next_match.away_participant = winner
                next_match.save()
                break


def _generate_draft_bracket_structure(participants):
    """Helper function to generate draft bracket structure for single elimination."""

    participant_list = list(participants)
    num_participants = len(participant_list)

    # Calculate the real number of rounds based on actual participants (with byes)
    total_rounds = int(math.ceil(math.log2(num_participants))) if num_participants > 0 else 0
    total_rounds = max(1, min(16, total_rounds))  # Ensure reasonable bounds
    
    draft_matches_by_round = {}
    
    if num_participants <= 1:
        # Special case: 1 participant 
        if num_participants == 1:
            draft_matches_by_round[1] = [{
                'id': 1,
                'round_number': 1,
                'home_team': participant_list[0],
                'home_team_seed': 1,
                'away_team': None,
                'away_team_seed': None
            }]
    else:
        # For single elimination with potential byes
        next_power_of_2 = 2 ** total_rounds  # This is the bracket size
        byes_count = next_power_of_2 - num_participants  # Number of first-round byes
        teams_playing_first_round = num_participants - byes_count  # Teams that play in first round
        first_round_match_count = teams_playing_first_round // 2
        
        match_counter = 1
        
        # Create first round matches
        first_round_matches = []
        for i in range(0, teams_playing_first_round, 2):
            if i < len(participant_list) and (i + 1) < len(participant_list):
                match_data = {
                    'id': match_counter,
                    'round_number': 1,
                    'home_team': participant_list[i],
                    'home_team_seed': i + 1,
                    'away_team': participant_list[i + 1],
                    'away_team_seed': i + 2,
                }
                first_round_matches.append(match_data)
                match_counter += 1
        
        if first_round_matches:
            draft_matches_by_round[1] = first_round_matches
        
        # Generate subsequent rounds - each round has half the matches of the previous
        prev_round_matches = first_round_matches
        for round_num in range(2, total_rounds + 1):
            # Each subsequent round has half the matches of the previous round
            prev_count = len(prev_round_matches) if prev_round_matches else 0
            current_round_match_count = max(1, prev_count // 2)
            
            current_round_matches = []
            for i in range(current_round_match_count):
                match_data = {
                    'id': match_counter,
                    'round_number': round_num,
                    'home_team': None,
                    'away_team': None,
                    'home_team_source': f"winner_match_{(i*2)+1}_round_{round_num-1}",
                    'away_team_source': f"winner_match_{(i*2)+2}_round_{round_num-1}",
                }
                current_round_matches.append(match_data)
                match_counter += 1
            
            if current_round_matches:
                draft_matches_by_round[round_num] = current_round_matches
            
            prev_round_matches = current_round_matches
    
    return draft_matches_by_round





def manage_playoffs(request, competition_id):
    """Interactive playoff bracket management page."""
    competition = get_object_or_404(Competition, id=competition_id)
    
    # Handle POST requests (saving seeding, shuffling, and setting winners)
    if request.method == 'POST':
        # Handle shuffling
        if 'shuffle' in request.POST:
            # Generate bracket with shuffled teams
            try:
                # Clear existing matches if any
                Match.objects.filter(competition=competition).delete()
                # Generate new bracket with shuffled teams
                matches = competition.generate_schedule_for_format()
                messages.success(request, "Bracket shuffled successfully!")
            except Exception as e:
                # Log the error for debugging
                logger.error(f"Error shuffling bracket: {str(e)}")
                messages.error(request, "Error shuffling bracket. Please try again.")
        
        # Handle setting a winner for a match
        elif 'match_id' in request.POST and 'winner_id' in request.POST:
            match_id = request.POST.get('match_id')
            winner_id = request.POST.get('winner_id')
            
            try:
                match = Match.objects.select_related('home_team', 'away_team').get(
                    id=match_id, competition=competition
                )
                
                # Update match status to completed
                match.status = 'COMPLETED'
                match.save()
                
                # Update the result for this match
                if winner_id:
                    if competition.participant_type == 'CLUBS':
                        winner_club = Club.objects.get(id=winner_id)
                        
                        # Create or update match result for the winner
                        match_result, created = MatchResult.objects.update_or_create(
                            match=match,
                            club=winner_club,
                            defaults={
                                'outcome': 'WIN',
                                'result_data': {},
                                'created_by': request.user if request.user.is_authenticated else None,
                                'updated_by': request.user if request.user.is_authenticated else None
                            }
                        )
                        
                        # Create or update loss result for the other team
                        if match.home_team and match.away_team:
                            losing_club = match.away_team if match.home_team == winner_club else match.home_team
                            
                            if losing_club:
                                MatchResult.objects.update_or_create(
                                    match=match,
                                    club=losing_club,
                                    defaults={
                                        'outcome': 'LOSS',
                                        'result_data': {},
                                        'created_by': request.user if request.user.is_authenticated else None,
                                        'updated_by': request.user if request.user.is_authenticated else None
                                    }
                                )
                    
                    # For participants, we'd need to handle differently - for now, let's skip
                    else:
                        winner_participant = Participant.objects.get(id=winner_id)
                
                # After setting a winner, update the next round match with this winner
                _advance_winner_to_next_round(match, winner_club if competition.participant_type == 'CLUBS' else winner_participant, competition)
                
            except (Match.DoesNotExist, Club.DoesNotExist, Participant.DoesNotExist) as e:
                # Log the error for debugging
                logger.error(f"Error setting match winner: {str(e)}")
                messages.error(request, "Error setting match winner: Invalid match or participant.")
            except Exception as e:
                # Log the error for debugging
                logger.error(f"Unexpected error setting match winner: {str(e)}")
                messages.error(request, "Error setting match winner. Please try again.")
        
        # Handle generating bracket structure (draft mode)

        # Handle generating actual matches to database
        elif 'generate_matches' in request.POST:
            # Process seeding form to generate schedule and save to database
            try:
                # Clear existing matches if any
                Match.objects.filter(competition=competition).delete()
                # Generate new bracket based on selected seeding
                matches = competition.generate_schedule_for_format()
                messages.success(request, "Bracket generated successfully!")
            except Exception as e:
                # Log the error for debugging
                print(f"Error generating matches: {str(e)}")
                messages.error(request, "Error generating matches. Please try again.")
        # Handle saving seeding (which generates the bracket schedule)
        elif 'save_seeding' in request.POST:
            # Process seeding form to generate schedule
            try:
                # Clear existing matches if any
                Match.objects.filter(competition=competition).delete()
                # Generate new bracket based on selected seeding
                matches = competition.generate_schedule_for_format()
                messages.success(request, "Seeding saved successfully!")
            except Exception as e:
                # Log the error for debugging
                print(f"Error saving seeding: {str(e)}")
                messages.error(request, "Error saving seeding. Please try again.")
    
    # Get matches ordered by round - ALL matches for the competition
    matches = Match.objects.filter(competition=competition).select_related(
        'home_team', 'away_team'
    ).order_by('round_number', 'id')
    
    # Organize matches by round (enhanced logic for the bracket tree)
    matches_by_round = {}
    for match in matches:
        round_num = match.round_number or 1
        # Use setdefault for more efficient dict creation
        matches_by_round.setdefault(round_num, []).append(match)
    
    # Get participants based on competition type
    if competition.participant_type == 'CLUBS':
        participants = competition.enrolled_clubs.all()
    else:
        participants = competition.enrolled_participants.all()

    # Handle manually ordered participants after participants variable is defined
    # This applies for draft bracket generation
    if request.method == 'POST':
        ordered_participants_str = request.POST.get('ordered_participants', '')
        if ordered_participants_str:
            # Parse the ordered participant IDs
            try:
                ordered_participant_ids = [int(pid) for pid in ordered_participants_str.split(',') if pid.strip()]
                # Convert participants to dict for O(1) lookup
                participants_dict = {p.id: p for p in participants}
                # Sort participants according to the provided order
                ordered_participants = []
                
                # Add participants in the specified order
                for pid in ordered_participant_ids:
                    if pid in participants_dict:
                        ordered_participants.append(participants_dict[pid])
                
                # Add any remaining participants that weren't in the drag list
                for pid, participant in participants_dict.items():
                    if pid not in ordered_participant_ids:
                        ordered_participants.append(participant)
                
                # Override participants with ordered ones
                participants = ordered_participants
            except ValueError:
                # If parsing fails, continue with original participants
                pass
    
    # Sort rounds for proper display
    sorted_matches_by_round = {k: v for k, v in sorted(matches_by_round.items())}
    
    # For draft mode: generate bracket structure based on enrolled participants
    # Calculate bracket structure without saving to database
    draft_matches_by_round = {}
    if participants and len(participants) > 0 and competition.format.format_type == 'SINGLE_ELIMINATION':
        draft_matches_by_round = _generate_draft_bracket_structure(participants)
    
    # Prepare data for jQuery Gracket plugin (Single Elimination)
    gracket_data = []
    gracket_round_labels = []
    
    if competition.format.format_type == 'SINGLE_ELIMINATION':
        # Convert draft matches to Gracket format
        round_numbers = sorted(draft_matches_by_round.keys())
        for i, round_num in enumerate(round_numbers):
            round_matches = draft_matches_by_round[round_num]
            round_games = []
            
            # Create proper round labels based on standard tournament naming
            total_rounds = len(round_numbers)
            round_label = _get_round_label(round_num, total_rounds, round_matches)
            gracket_round_labels.append(round_label)
            
            # Process matches in this round
            for match in round_matches:
                game = []
                
                # Add first team (home team)
                if match['home_team']:
                    if competition.participant_type == 'CLUBS':
                        team_name = match['home_team'].name
                    else:
                        team_name = match['home_team'].full_name or match['home_team'].employee_id or "No Name"
                else:
                    team_name = "TBD"
                
                team1 = {
                    'name': team_name,
                    'id': match['home_team'].id if match['home_team'] else None,
                    'seed': match.get('home_team_seed', None) or 0,  # Safe access to seed
                    'score': 0,  # Default score for draft mode
                    'source': match.get('home_team_source', None),  # Source of this team for bracket connections
                }
                
                # Add second team (away team) if exists
                if match['away_team']:
                    if competition.participant_type == 'CLUBS':
                        team_name = match['away_team'].name
                    else:
                        team_name = match['away_team'].full_name or match['away_team'].employee_id or "No Name"
                else:
                    team_name = "TBD"
                
                team2 = {
                    'name': team_name,
                    'id': match['away_team'].id if match['away_team'] else None,
                    'seed': match.get('away_team_seed', None) or 0,  # Safe access to seed
                    'score': 0,  # Default score for draft mode
                    'source': match.get('away_team_source', None),  # Source of this team for bracket connections
                }
                
                round_games.append([team1, team2])
            
            gracket_data.append(round_games)
    
    # Convert to JSON-safe format for template
    gracket_data_json = json.dumps(gracket_data, ensure_ascii=False)
    gracket_round_labels_json = json.dumps(gracket_round_labels, ensure_ascii=False)

    context = {
        'competition': competition,
        'matches_by_round': sorted_matches_by_round,
        'draft_matches_by_round': draft_matches_by_round,
        'participants': participants,
        'participant_type': competition.participant_type,
        'gracket_data': gracket_data_json,
        'gracket_round_labels': gracket_round_labels_json,
    }
    
    if request.headers.get('HX-Request'):
        # Return only the bracket section for HTMX requests
        html = render_to_string('gms/partials/playoff_bracket_gracket.html', context, request=request)
        return JsonResponse({'html': html})
    
    return render(request, 'gms/manage_playoffs.html', context)


def create_bracket_format_from_ordered_ids(ordered_ids, all_participants_dict):
    """
    Create bracket data in the format required by jquery.bracket
    """
    if not ordered_ids:
        return {"teams": [], "results": []}

    # Get the team names in the order they were seeded
    ordered_teams = [all_participants_dict[str(pid)] for pid in ordered_ids if str(pid) in all_participants_dict]

    # Calculate the next power of 2 for the total number of slots needed
    import math
    n_teams = len(ordered_teams)
    if n_teams == 0:
        return {"teams": [], "results": []}
        
    # We need a power of 2 slots. 
    # If n_teams is 3, we need 4 slots (2 matches).
    # If n_teams is 5, we need 8 slots (4 matches).
    power = 1
    while power < n_teams:
        power *= 2
    
    # Pad with "BYE" to reach the power of 2
    while len(ordered_teams) < power:
        ordered_teams.append("BYE")

    # Pair up teams for matches (create pairs: [team1, team2], [team3, team4], etc.)
    teams = []
    for i in range(0, len(ordered_teams), 2):
        # Since we padded to even number (power of 2), i+1 is always safe
        teams.append([ordered_teams[i], ordered_teams[i + 1]])

    # Calculate number of rounds in the tournament (single elimination)
    # Since we padded to power of 2, len(teams) is also a power of 2 (or 1/2 of a power of 2)
    # Example: 8 teams -> 4 matches. log2(4) = 2. 
    # Rounds needed: Quarters (4 matches), Semis (2), Final (1). Total 3 rounds.
    # log2(4) + 1 = 3. Correct.
    
    num_rounds = int(math.log2(len(teams))) + 1 if len(teams) > 0 else 0
        
    # Create the results structure
    results = []
    
    # We need to generate the structure for the bracket.
    # The 'results' array is an array of arrays.
    # results[0] is the first round (e.g. Quarter Finals)
    # results[1] is the second round (e.g. Semi Finals)
    # ...
    
    current_matches_count = len(teams)
    
    # We iterate until we have 1 match (the final)
    while current_matches_count >= 1:
        round_results = []
        for _ in range(current_matches_count):
            # Each match result is [team1_score, team2_score]
            # Initialize with nulls (empty scores)
            round_results.append([None, None]) 
        results.append(round_results)
        
        if current_matches_count == 1:
            break
            
        # Next round has half the matches
        current_matches_count = current_matches_count // 2

    return {
        "teams": teams,
        "results": results
    }


def bracket_detail(request, competition_id):
    """Standalone single elimination bracket view using jquery-bracket."""
    competition = get_object_or_404(Competition, id=competition_id)

    # Get the ordered team IDs from cache (from seeding)
    from django.core.cache import cache
    cache_key = f"seeding_order_{competition.id}"
    ordered_team_ids = cache.get(cache_key, [])  # Get this from your data

    # Get all participants to map IDs to names
    all_participants = {}
    if competition.participant_type == 'CLUBS':
        for participant in competition.enrolled_clubs.all():
            all_participants[str(participant.id)] = str(participant.name)  # Adjust name field as needed
    else:
        for participant in competition.enrolled_participants.all():
            all_participants[str(participant.id)] = str(participant.full_name)  # Adjust name field as needed

    # Generate bracket data
    bracket_data = create_bracket_format_from_ordered_ids(ordered_team_ids, all_participants)

    context = {
        'competition': competition,
        'participants': list(competition.enrolled_clubs.all()) if competition.participant_type == 'CLUBS' else list(competition.enrolled_participants.all()),
        'jquery_bracket_data': json.dumps(bracket_data),
    }

    return render(request, 'gms/bracket_detail.html', context)


def bracket_detail_gracket(request, competition_id):
    """Alternative bracket view using Gracket."""
    competition = get_object_or_404(Competition, id=competition_id)

    # Get participants
    participants = []
    if competition.participant_type == 'CLUBS':
        for p in competition.enrolled_clubs.all():
            participants.append({'id': p.id, 'name': p.name})
    else:
        for p in competition.enrolled_participants.all():
            participants.append({'id': p.id, 'name': p.full_name})

    # Get the ordered team IDs from cache (from seeding)
    from django.core.cache import cache
    cache_key = f"seeding_order_{competition.id}"
    ordered_team_ids = cache.get(cache_key, [])

    if ordered_team_ids:
        # Reorder participants based on ordered_team_ids
        participants_map = {str(p['id']): p for p in participants}
        ordered_participants = []
        # ordered_team_ids might be strings or ints, ensure consistency
        ordered_ids_str = [str(pid) for pid in ordered_team_ids]
        
        for pid in ordered_ids_str:
            if pid in participants_map:
                ordered_participants.append(participants_map[pid])

        # Add any remaining participants that weren't in the ordered list
        existing_ids = set(ordered_ids_str)
        for p in participants:
            if str(p['id']) not in existing_ids:
                ordered_participants.append(p)

        participants = ordered_participants

    # Prefix IDs with 'team_' to avoid invalid CSS selector errors in Gracket
    # (Gracket seems to use IDs as class selectors, and numeric classes are invalid if not escaped)
    for p in participants:
        p['id'] = f"team_{p['id']}"

    # Get all matches for this competition to populate the modal
    matches = Match.objects.filter(competition=competition).select_related('venue').prefetch_related('referees')
    matches_lookup = {}
    
    for match in matches:
        # Create a key based on round and match index (assuming standard ordering)
        # Note: This is a simplification. In a real scenario, you might need a more robust way 
        # to map Gracket's internal representation to database matches.
        # For now, we'll pass the list of matches and let the frontend try to map them 
        # or we can use the match ID if we can embed it in the Gracket rendering.
        
        # Better approach: Pass all matches keyed by their round/index if available, 
        # or just a list that the frontend can use if it knows the order.
        # Since Gracket generates the structure, we might need to rely on the order.
        pass

    # Fetch master data for the modal
    from .models import Venue, Referee
    venues = Venue.objects.all()
    referees = Referee.objects.all()
    
    # Serialize matches for frontend use
    matches_data = []
    
    # Group matches by round to determine match_num
    matches_by_round = {}
    for m in matches:
        r = m.round_number
        if r not in matches_by_round:
            matches_by_round[r] = []
        matches_by_round[r].append(m)
        
    # Sort matches within each round by ID (assuming creation order matches bracket order)
    for r in matches_by_round:
        matches_by_round[r].sort(key=lambda x: x.id)
        
    # Flatten back to list with calculated match_num
    for r, round_matches in matches_by_round.items():
        for i, m in enumerate(round_matches):
            # Handle M2M referees - just take the first one for the single-select UI
            current_referee = m.referees.first()
            
            matches_data.append({
                'id': m.id,
                'round': m.round_number,
                'match_num': i + 1, # 1-based index within the round
                'scheduled_time': m.scheduled_time.isoformat() if m.scheduled_time else None,
                'venue_id': m.venue.id if m.venue else None,
                'referee_id': current_referee.id if current_referee else None,
                'home_team_id': f"team_{m.home_team.id}" if m.home_team else None, # Adjust for Club/Participant
                'away_team_id': f"team_{m.away_team.id}" if m.away_team else None,
            })

    context = {
        'competition': competition,
        'teams_data_json': json.dumps(participants),
        'matches_data_json': json.dumps(matches_data),
        'venues': venues,
        'referees': referees,
    }
    return render(request, 'gms/bracket_detail_gracket.html', context)


def generate_bracket_matches(request, competition_id):
    """API endpoint to generate single elimination matches for a competition."""
    from django.http import JsonResponse
    
    if request.method == 'POST':
        try:
            competition = get_object_or_404(Competition, id=competition_id)
            
            # Check if user has permission to generate matches (similar to admin)
            if not (request.user.is_superuser or 
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            # Check if matches already exist
            existing_matches = Match.objects.filter(competition=competition).exists()
            if existing_matches:
                # Optionally clear existing matches first
                Match.objects.filter(competition=competition).delete()

            # Generate new matches using the competition's generate_schedule_for_format method
            matches = competition.generate_schedule_for_format()
            
            # Return success response
            return JsonResponse({
                'success': True, 
                'message': f'Successfully generated {len(matches)} matches',
                'match_count': len(matches)
            })
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error generating matches: {error_msg}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def generate_round_robin_schedule(request, competition_id):
    """Generate and display a round-robin schedule for a competition."""
    competition = get_object_or_404(Competition, id=competition_id)

    # Permission check
    if not (request.user.is_superuser or
            request.user in competition.event.coordinators.all() or
            competition.created_by == request.user):
        messages.error(request, "You do not have permission to generate a schedule for this competition.")
        return redirect('gms:competition_detail', competition_id=competition.id)

    if request.method == 'POST':
        try:
            # Clear existing matches
            Match.objects.filter(competition=competition).delete()
            # Generate new matches
            matches = competition.generate_schedule_for_format()
            messages.success(request, f"Successfully generated {len(matches)} matches for the round-robin schedule.")
        except Exception as e:
            messages.error(request, f"Error generating schedule: {e}")
        
        return redirect('gms:generate_round_robin_schedule', competition_id=competition.id)

    matches = competition.matches.select_related('home_team', 'away_team', 'venue').order_by('scheduled_time')
    
    # Get club/participant list to know which teams are in the competition
    if competition.participant_type == 'CLUBS':
        all_participants = list(competition.enrolled_clubs.all().order_by('name'))
    else:  # PARTICIPANTS
        all_participants = list(competition.enrolled_participants.all().order_by('full_name'))
    
    # Prepare teams data for the jquery-group plugin
    # Use all participants for seeding, not just those in existing matches
    teams_data = []
    for participant in all_participants:
        if competition.participant_type == 'CLUBS':
            teams_data.append({'id': participant.id, 'name': participant.name})
        else:  # PARTICIPANTS
            teams_data.append({'id': participant.id, 'name': participant.full_name})

    # For league competitions with groups, group matches by group number
    groups_data = []
    if competition.is_league_with_groups and competition.number_of_groups:
        # Get the properly organized clubs into groups using the same function used in _generate_league_schedule_with_dates
        if all_participants:
            groups = competition._organize_clubs_into_groups(all_participants)
            
            # Group matches by their group_number
            matches_by_group_number = {}
            for match in matches:
                group_num = match.group_number or 1  # Default to group 1 if no group_number
                if group_num not in matches_by_group_number:
                    matches_by_group_number[group_num] = []
                matches_by_group_number[group_num].append(match)
            
            # Create groups data with proper teams distribution
            for group_idx, group_clubs in enumerate(groups, 1):
                group_matches = matches_by_group_number.get(group_idx, [])
                
                # Get teams in this specific group
                if competition.participant_type == 'CLUBS':
                    group_teams_data = [{'id': club.id, 'name': club.name} for club in group_clubs]
                else:  # PARTICIPANTS
                    group_teams_data = [{'id': participant.id, 'name': participant.full_name} for participant in group_clubs]
                
                # Group matches by their round number within this group
                matches_by_round = {}
                for match in group_matches:
                    round_num = match.round_number or 1
                    if round_num not in matches_by_round:
                        matches_by_round[round_num] = []
                    matches_by_round[round_num].append(match)
                
                # Convert to sorted list of rounds
                sorted_rounds = []
                for round_num in sorted(matches_by_round.keys()):
                    sorted_rounds.append({
                        'round_number': round_num,
                        'matches': matches_by_round[round_num]
                    })
                
                groups_data.append({
                    'id': f'group_{group_idx}',
                    'name': f'Group {group_idx}',
                    'teams': group_teams_data,
                    'matches': group_matches,
                    'rounds': sorted_rounds  # Add rounds data for visualization
                })
            
            # If there are more groups than we have data for, create empty groups
            for group_idx in range(len(groups) + 1, competition.number_of_groups + 1):
                groups_data.append({
                    'id': f'group_{group_idx}',
                    'name': f'Group {group_idx}',
                    'teams': [],
                    'matches': []
                })
    else:
        # Single group with all teams - organize matches by rounds
        # Group matches by their round number
        matches_by_round = {}
        for match in matches:
            round_num = match.round_number or 1
            if round_num not in matches_by_round:
                matches_by_round[round_num] = []
            matches_by_round[round_num].append(match)
        
        # Convert to sorted list of rounds
        sorted_rounds = []
        for round_num in sorted(matches_by_round.keys()):
            sorted_rounds.append({
                'round_number': round_num,
                'matches': matches_by_round[round_num]
            })
        
        groups_data.append({
            'id': 'all',
            'name': 'All Teams',
            'teams': teams_data,
            'matches': list(matches),
            'rounds': sorted_rounds  # Add rounds data for visualization
        })
    
    context = {
        'competition': competition,
        'matches': matches,
        'teams_data': teams_data,  # Pass the actual teams_data list for seeding step
        'teams_data_json': json.dumps(teams_data),
        'groups_data': groups_data
    }
    return render(request, 'gms/round_robin_schedule.html', context)



def update_bracket_seeding(request, competition_id):
    """API endpoint to update the seeding order for a competition."""
    from django.views.decorators.csrf import csrf_protect
    from django.utils.decorators import method_decorator
    
    if request.method == 'POST':
        try:
            competition = get_object_or_404(Competition, id=competition_id)
            
            # Check if user has permission to update seeding
            if not (request.user.is_superuser or 
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            # Get the ordered team IDs from the request
            ordered_teams = request.POST.get('ordered_teams', '')
            if not ordered_teams:
                return JsonResponse({'success': False, 'error': 'No team order provided'}, status=400)
            
            # Parse the ordered team IDs
            try:
                team_ids = [int(id) for id in ordered_teams.split(',') if id.strip()]
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid team IDs format'}, status=400)
                
            # Get the enrolled teams to validate the IDs provided
            if competition.participant_type == 'CLUBS':
                enrolled_teams = competition.enrolled_clubs.all()
            else:
                enrolled_teams = competition.enrolled_participants.all()
                
            enrolled_ids = {obj.id for obj in enrolled_teams}
            
            # Validate that all provided IDs are valid
            if not set(team_ids).issubset(enrolled_ids):
                return JsonResponse({'success': False, 'error': 'Invalid team IDs provided'}, status=400)
                
            # Clear any existing matches before generating with new seeding
            Match.objects.filter(competition=competition).delete()
            
            # Save the seeding order to cache
            from django.core.cache import cache
            cache_key = f"seeding_order_{competition.id}"
            cache.set(cache_key, team_ids, 300)  # Cache for 5 minutes
            
            # Generate matches with the new seeding
            matches = competition.generate_schedule_for_format()
            
            return JsonResponse({
                'success': True, 
                'message': f'Seeding updated and {len(matches)} matches generated',
                'match_count': len(matches)
            })
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error updating seeding: {error_msg}")
            print(traceback.format_exc())
            # Return a proper JSON error response instead of potentially HTML
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def update_bracket_team(request):
    """API endpoint to update a team in the bracket."""
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            competition_id = data.get('competition_id')
            old_team_name = data.get('old_team_name')
            new_team_name = data.get('new_team_name')
            change_type = data.get('change_type')
            
            # Get the competition
            competition = get_object_or_404(Competition, id=competition_id)
            
            # Check permission
            if not (request.user.is_superuser or 
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
            
            # Handle special values like BYE and TBD
            if new_team_name in ['BYE', 'TBD']:
                # These are placeholder values that don't map to actual teams
                pass
            else:
                # Validate that the new team name corresponds to an enrolled team
                if competition.participant_type == 'CLUBS':
                    enrolled_teams = competition.enrolled_clubs.all()
                    team_names = [club.name for club in enrolled_teams]
                    if new_team_name not in team_names:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Team "{new_team_name}" is not enrolled in this competition'
                        }, status=400)
                else:  # PARTICIPANTS
                    enrolled_teams = competition.enrolled_participants.all()
                    team_names = [participant.full_name for participant in enrolled_teams]
                    if new_team_name not in team_names:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Participant "{new_team_name}" is not enrolled in this competition'
                        }, status=400)
            
            # For now, just log the change and return success
            # In a full implementation, you'd want to map the visual change to actual Match objects
            # This requires maintaining a mapping between SVG elements and Match model instances
            
            return JsonResponse({
                'success': True,
                'message': f'Team name updated from "{old_team_name}" to "{new_team_name}"',
                'change_type': change_type,
                'new_team_name': new_team_name
            })
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error updating bracket team: {error_msg}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def generate_draft_matches(request, competition_id):
    """API endpoint to generate draft matches for a competition."""
    from django.http import JsonResponse

    if request.method == 'POST':
        try:
            competition = get_object_or_404(Competition, id=competition_id)

            # Check if user has permission to generate matches (similar to admin)
            if not (request.user.is_superuser or
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            # Check if matches already exist
            existing_matches = Match.objects.filter(competition=competition).exists()
            if existing_matches:
                # Optionally clear existing matches first
                Match.objects.filter(competition=competition).delete()

            # Generate new matches using the competition's generate_schedule_for_format method with draft status
            matches = competition.generate_draft_schedule_for_format()

            # Return success response
            return JsonResponse({
                'success': True,
                'message': f'Successfully generated {len(matches)} draft matches',
                'match_count': len(matches),
                'redirect_url': reverse('gms:assign_match_dates', args=[competition_id])
            })

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error generating draft matches: {error_msg}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def assign_match_dates(request, competition_id):
    """View to assign dates to draft matches before finalizing schedule."""
    competition = get_object_or_404(Competition, id=competition_id)
    
    # Check if user has permission
    if not (request.user.is_superuser or
           request.user in competition.event.coordinators.all() or
           competition.created_by == request.user):
        messages.error(request, "You don't have permission to assign match dates.")
        return redirect('competition_detail', competition_id=competition.id)

    # Get all draft matches for this competition
    draft_matches = Match.objects.filter(competition=competition, status='DRAFT').order_by('round_number', 'scheduled_time')
    
    if request.method == 'POST':
        # Process date assignments
        try:
            for match in draft_matches:
                date_key = f'match_date_{match.id}'
                time_key = f'match_time_{match.id}'
                
                if date_key in request.POST and time_key in request.POST:
                    date_str = request.POST.get(date_key)
                    time_str = request.POST.get(time_key)
                    
                    if date_str and time_str:
                        # Combine date and time strings
                        datetime_str = f"{date_str} {time_str}"
                        scheduled_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                        
                        # Update the match with the new scheduled time
                        match.scheduled_time = scheduled_datetime
                        match.status = 'SCHEDULED'
                        match.save()
            
            messages.success(request, f'Successfully assigned dates to {len(draft_matches)} matches. Schedule finalized!')
            return redirect('competition_detail', competition_id=competition.id)
        except Exception as e:
            messages.error(request, f'Error assigning match dates: {str(e)}')
    
    # For GET request, show the date assignment form
    return render(request, 'gms/assign_match_dates.html', {
        'competition': competition,
        'draft_matches': draft_matches,
    })


def finalize_schedule(request, competition_id):
    """API endpoint to finalize the schedule after dates have been assigned."""
    from django.http import JsonResponse

    if request.method == 'POST':
        try:
            competition = get_object_or_404(Competition, id=competition_id)

            # Check if user has permission to finalize schedule
            if not (request.user.is_superuser or
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            # Update all draft matches to scheduled status
            draft_matches = Match.objects.filter(competition=competition, status='DRAFT')
            updated_count = 0
            
            for match in draft_matches:
                # Only update if a date has been assigned
                if match.scheduled_time != timezone.now():  # If it's still the default placeholder
                    # You could set a default date here, or ensure all matches have proper dates
                    match.status = 'SCHEDULED'
                    match.save()
                    updated_count += 1
                else:
                    # This means the date hasn't been properly assigned yet
                    return JsonResponse({
                        'success': False, 
                        'error': 'Some matches still have default dates. Please assign dates to all matches first.'
                    }, status=400)

            return JsonResponse({
                'success': True,
                'message': f'Successfully finalized schedule for {updated_count} matches'
            })

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error finalizing schedule: {error_msg}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def fetch_draft_matches(request, competition_id):
    """API endpoint to fetch draft matches for a competition."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.db.models import Max

    try:
        competition = get_object_or_404(Competition, id=competition_id)

        # Check if user has permission
        if not (request.user.is_superuser or
               request.user in competition.event.coordinators.all() or
               competition.created_by == request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        # Get all draft matches for this competition
        draft_matches = Match.objects.filter(competition=competition, status='DRAFT').order_by('round_number', 'id')

        # Prepare matches data for the frontend
        matches_data = []
        for match in draft_matches:
            # Hitung total rounds untuk kompetisi ini - ambil dari semua draft matches
            competition_draft_matches = match.competition.matches.filter(status='DRAFT')
            total_rounds = competition_draft_matches.aggregate(max_round=Max('round_number'))['max_round'] or 1
            
            match_data = {
                'id': match.id,
                'round_number': match.round_number,
                'total_rounds': total_rounds,
                'home_team_name': match.home_team.name if match.home_team else 'TBD',
                'away_team_name': match.away_team.name if match.away_team else 'TBD',
                'scheduled_time': match.scheduled_time.isoformat() if match.scheduled_time else None,
                'venue_id': match.venue.id if match.venue else None,
            }
            matches_data.append(match_data)

        return JsonResponse({
            'success': True,
            'matches': matches_data
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error fetching draft matches: {error_msg}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def get_all_venues(request):
    """API endpoint to fetch all venues for dropdown selection."""
    from django.http import JsonResponse
    
    try:
        # Check if user has permission to view venues (any authenticated user can view)
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=403)

        venues = Venue.objects.all().order_by('name')
        venues_data = []
        
        for venue in venues:
            venues_data.append({
                'id': venue.id,
                'name': venue.name,
                'address': venue.address
            })

        return JsonResponse({
            'success': True,
            'venues': venues_data
        })

    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error fetching venues: {error_msg}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg}, status=500)


def assign_match_dates_inline(request, competition_id):
    """API endpoint to assign dates to matches within the bracket page."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.utils.dateparse import parse_datetime
    import json

    if request.method == 'POST':
        try:
            competition = get_object_or_404(Competition, id=competition_id)

            # Check if user has permission
            if not (request.user.is_superuser or
                   request.user in competition.event.coordinators.all() or
                   competition.created_by == request.user):
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

            # Parse JSON data from request body
            data = json.loads(request.body)
            matches_data = data.get('matches', [])

            # Process date assignments
            updated_count = 0
            for match_data in matches_data:
                match_id = match_data.get('id')
                date_str = match_data.get('date')
                time_str = match_data.get('time')

                if match_id and date_str and time_str:
                    # Combine date and time strings
                    datetime_str = f"{date_str} {time_str}"
                    scheduled_datetime = parse_datetime(datetime_str)
                    
                    if scheduled_datetime:
                        # Update the match with the new scheduled time
                        try:
                            match = Match.objects.get(id=match_id, competition=competition)
                            match.scheduled_time = scheduled_datetime
                            match.status = 'SCHEDULED'
                            match.save()
                            updated_count += 1
                        except Match.DoesNotExist:
                            # Skip if match doesn't exist or doesn't belong to this competition
                            continue

            return JsonResponse({
                'success': True,
                'message': f'Successfully assigned dates to {updated_count} matches'
            })

        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Error assigning match dates inline: {error_msg}")
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


def favicon(request):
    """Serve the favicon from SiteConfiguration if available."""
    from django.http import HttpResponse, Http404
    from django.conf import settings
    from .models import SiteConfiguration
    
    # Get the site configuration
    site_config = SiteConfiguration.get_solo()
    
    if site_config and site_config.favicon:
        try:
            # Open and return the favicon file
            with open(site_config.favicon.path, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/x-icon')
        except FileNotFoundError:
            # If the file doesn't exist, return a 404
            raise Http404("Favicon not found")
    
    # If no favicon in site config, try to serve from static files
    import os
    favicon_path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'favicon.ico')
    if os.path.exists(favicon_path):
        with open(favicon_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='image/x-icon')
    
    # If no favicon available anywhere, return 404
    raise Http404("Favicon not found")


@require_POST
@csrf_protect
def update_match_details(request):
    """API endpoint to update match details from the bracket modal."""
    try:
        data = json.loads(request.body)
        match_id = data.get('match_id')
        scheduled_time_str = data.get('scheduled_time')
        venue_id = data.get('venue_id')
        referee_id = data.get('referee_id')

        if not match_id:
            return JsonResponse({'success': False, 'error': 'Match ID is required.'}, status=400)

        match = get_object_or_404(Match, id=match_id)

        # Check permissions
        if not (request.user.is_superuser or
                request.user in match.competition.event.coordinators.all() or
                match.competition.created_by == request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

        if scheduled_time_str:
            # Input format from datetime-local is 'YYYY-MM-DDTHH:MM'
            # This is a naive datetime, so we need to make it aware
            naive_dt = datetime.fromisoformat(scheduled_time_str)
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            match.scheduled_time = aware_dt
        else:
            match.scheduled_time = None

        if venue_id:
            # Make sure to import Venue model
            from .models import Venue
            venue = get_object_or_404(Venue, id=venue_id)
            match.venue = venue
        else:
            match.venue = None # Allow unsetting the venue

        if referee_id:
            from .models import Referee
            referee = get_object_or_404(Referee, id=referee_id)
            # Since the UI only supports one referee, we replace any existing ones
            match.referees.set([referee])
        else:
            match.referees.clear()

        match.save()

        return JsonResponse({
            'success': True,
            'message': 'Match details updated successfully.',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
    except Match.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Match not found.'}, status=404)
    except Venue.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Venue not found.'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def save_seeding_and_generate_matches(request, competition_id):
    """
    API endpoint to save a user-defined seeding order and generate the
    corresponding bracket matches for a single-elimination competition.
    """
    try:
        print(f"save_seeding_and_generate_matches called for competition {competition_id}")
        
        data = json.loads(request.body)
        print(f"JSON parsed successfully: {data}")
        ordered_ids_str = data.get('ordered_ids', [])
        print(f"ordered_ids: {ordered_ids_str}")
        
        if not ordered_ids_str:
            return JsonResponse({'success': False, 'error': 'No seeding order provided.'}, status=400)

        # Convert string IDs to integers
        try:
            ordered_ids = [int(id) for id in ordered_ids_str]
            print(f"converted ordered_ids: {ordered_ids}")
        except (ValueError, TypeError) as e:
            print(f"Error converting IDs: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid ID format in seeding order.'}, status=400)

        competition = get_object_or_404(Competition, id=competition_id)
        print(f"Got competition: {competition.name}, participant_type: {competition.participant_type}")

        # --- Permission Check ---
        if not (request.user.is_superuser or
                request.user in competition.event.coordinators.all() or
                competition.created_by == request.user):
            return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

        # --- Get all enrolled participants/clubs ---
        if competition.participant_type == 'CLUBS':
            enrolled_entities = competition.enrolled_clubs.all()
            enrolled_map = {p.id: p for p in enrolled_entities}
        else:
            enrolled_entities = competition.enrolled_participants.all()
            enrolled_map = {p.id: p for p in enrolled_entities}
        print(f"Retrieved enrolled entities, count: {len(enrolled_map)}")

        # --- Validate the ordered list ---
        for pid in ordered_ids:
            participant = enrolled_map.get(pid)
            if not participant:
                return JsonResponse({'success': False, 'error': f'Invalid participant ID {pid} in seeding order.'}, status=400)
        print("All participant IDs validated")

        # --- Save the ordered seeding to cache ---
        from django.core.cache import cache
        cache_key = f"seeding_order_{competition.id}"
        cache.set(cache_key, ordered_ids, 3600)  # Cache for 1 hour
        print("Seeding order saved to cache")

        # --- Validate before generating Bracket ---
        # Check if there are enough enrolled participants for bracket generation
        enrolled_count = competition.enrolled_clubs.count() if competition.participant_type == 'CLUBS' else competition.enrolled_participants.count()
        print(f"Enrolled count: {enrolled_count}")
        
        if enrolled_count < 2:
            return JsonResponse({
                'success': False, 
                'error': f'Not enough enrolled participants. Need at least 2, but only have {enrolled_count}.'
            }, status=400)

        # --- Generate Bracket ---
        # Clear any existing matches
        deleted_count = Match.objects.filter(competition=competition).delete()[0]
        print(f"Deleted {deleted_count} existing matches")

        # Generate new matches using the competition's method - THIS IS WHERE ERROR LIKELY OCCURS
        print("About to call generate_schedule_for_format...")
        try:
            matches = competition.generate_schedule_for_format()
            print(f"Successfully generated {len(matches)} matches")
        except Exception as e:
            print(f"Error in generate_schedule_for_format: {str(e)}")
            import traceback
            traceback.print_exc()
            # Check if this is a validation error related to enrollment count
            if "enrolled" in str(e).lower() and "planned" in str(e).lower():
                # If it's the enrollment count validation issue, provide specific message
                enrolled_count = competition.enrolled_clubs.count() if competition.participant_type == 'CLUBS' else competition.enrolled_participants.count()
                planned_count = competition.number_of_clubs if competition.participant_type == 'CLUBS' else competition.number_of_participants
                return JsonResponse({
                    'success': False, 
                    'error': f'Enrollment mismatch: {enrolled_count} enrolled but {planned_count} planned. Update the planned number in the competition settings.'
                }, status=400)
            else:
                # Re-raise the exception to be caught by the outer exception handler
                raise

        # --- Generate bracket data for jquery-bracket ---
        # Get all participants to map IDs to names
        all_participants = {}
        if competition.participant_type == 'CLUBS':
            for participant in competition.enrolled_clubs.all():
                all_participants[str(participant.id)] = str(participant.name)
        else:
            for participant in competition.enrolled_participants.all():
                all_participants[str(participant.id)] = str(participant.full_name)

        # Generate the bracket data in the correct format
        bracket_data = create_bracket_format_from_ordered_ids(ordered_ids, all_participants)

        return JsonResponse({
            'success': True,
            'message': f'Seeding saved and {len(matches)} matches generated successfully!',
            'bracket_data': bracket_data  # Send the properly formatted data
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
    except ValidationError as e:
        # Handle Django validation errors specifically with 400 status
        error_message = str(e)
        if hasattr(e, 'message_dict'):
            error_message = str(e.message_dict)
        elif hasattr(e, 'messages'):
            error_message = str(e.messages)
        return JsonResponse({'success': False, 'error': f'Validation error: {error_message}'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid ID format in seeding order.'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
@login_required
def reset_bracket(request, competition_id):
    """
    Deletes all matches for a given competition to allow reseeding.
    """
    competition = get_object_or_404(Competition, id=competition_id)

    # --- Permission Check ---
    if not (request.user.is_superuser or
            request.user in competition.event.coordinators.all() or
            competition.created_by == request.user):
        messages.error(request, "You do not have permission to reset this bracket.")
        return redirect('gms:bracket_detail', competition_id=competition.id)

    # Delete all matches for this competition
    competition.matches.all().delete()

    messages.success(request, "Bracket has been reset. You can now re-seed the participants.")
    return redirect('gms:bracket_detail', competition_id=competition.id)
