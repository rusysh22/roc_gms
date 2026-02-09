import calendar
from datetime import date
from collections import defaultdict

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

# Test execution
today = date.today()
matches_by_date = defaultdict(list)
# Add some dummy matches
matches_by_date[today] = ['Match 1']
matches_by_date[today.replace(day=1)] = ['Match 2']

try:
    data = _get_calendar_data(today, matches_by_date)
    print("Successfully generated calendar data.")
    print(f"Number of months: {len(data)}")
    for month in data:
        print(f"Month: {month['month_name']} {month['year']}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
