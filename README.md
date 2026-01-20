# Corporate Games Management System (GMS)

A comprehensive web application built with Django to manage internal multi-sport events for a company.

## Features

- **Event Management**: Create and manage major corporate events
- **Competition Management**: Organize competitions for different sports
- **Club & Player Management**: Create teams and assign employees to them
- **Match Scheduling**: Automatically generate match schedules based on competition format
- **Results & Standings**: Track match results and calculate standings/medal tallies
- **Role-based Access**: Super Admin, Event Coordinator, and Employee access levels
- **Dynamic Updates**: Real-time updates using HTMX
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Backend**: Python with Django Framework
- **Database**: PostgreSQL
- **Frontend**: Django Templates, Tailwind CSS, HTMX, Alpine.js
- **Dependency Management**: Poetry

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd django_gms
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Create a `.env` file in the root directory with the following content:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key-here-change-in-production
   DB_NAME=pgdb
   DB_USER=openpg
   DB_PASSWORD=openpgpwd
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. Run migrations:
   ```
   poetry run python manage.py migrate
   ```

5. Create a superuser:
   ```
   poetry run python manage.py createsuperuser
   ```

6. Start the development server:
   ```
   poetry run python manage.py runserver
   ```

## Project Structure

```
django_gms/
├── gms/                    # Main Django app
│   ├── migrations/         # Database migrations
│   ├── models.py          # Django models
│   ├── views.py           # Django views
│   ├── urls.py            # URL patterns
│   ├── admin.py           # Admin interface customization
│   └── context_processors.py # Context processors
├── gms_project/           # Django project settings
│   ├── settings.py        # Project settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI application
├── static/                # Static files (CSS, JS, images)
│   └── css/
│       └── style.css      # Custom styles
├── templates/             # Django templates
│   ├── base.html          # Base template
│   └── gms/               # App templates
│       ├── homepage.html
│       ├── event_detail.html
│       ├── competition_detail.html
│       ├── club_detail.html
│       └── partials/      # HTMX partial templates
├── .env                   # Environment variables
├── .gitignore             # Git ignore file
├── manage.py              # Django management script
├── pyproject.toml         # Poetry dependency management
└── poetry.lock            # Lock file for dependencies
```

## Models Overview

- `SiteConfiguration`: Singleton model for site-wide settings
- `BusinessUnit`: Company business units
- `Participant`: Employee players
- `Referee`: Match referees
- `Venue`: Competition venues
- `Event`: Top-level events
- `Club`: Teams
- `CompetitionFormat`: Formats like league or elimination
- `Competition`: Individual competitions within events
- `Match`: Individual matches
- `MatchResult`: Results of matches
- `Disqualification`: Records of disqualifications
- `Standings`: Competition standings
- `Medal`: Medal awards
- `Announcement`: Event announcements

## Admin Interface

The admin interface is heavily customized for the business workflow:

1. **Super Admin**: Creates events and assigns coordinators
2. **Event Coordinator**: Manages competitions, clubs, and scheduling for assigned events
3. **View-only Access**: Employees can view schedules and results

## Frontend Pages

- **Homepage**: Lists active/upcoming events and announcements
- **Event Detail**: Shows event details, competitions, medals, and announcements
- **Competition Detail**: Displays schedule, results, and standings
- **Club Detail**: Shows club members and match schedule

## Key Functionality

- Dynamic content updates using HTMX
- Powerful filtering and search capabilities
- Automatic match schedule generation
- Real-time standings calculation
- Role-based access control
- Responsive design for all devices

## Development Notes

- Use `poetry run python manage.py` for all Django commands
- Templates use Tailwind CSS utility classes
- HTMX is used for dynamic updates without page refreshes
- Alpine.js handles client-side UI interactions
- All sensitive data is managed through environment variables