from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.cache import cache
import json
import datetime
from datetime import datetime, time, timedelta


class TimestampedModel(models.Model):
    """Abstract model to add created_at and updated_at fields to other models."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditableModel(TimestampedModel):
    """Abstract model that extends TimestampedModel with created_by and updated_by fields."""
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_%(class)s_set'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_%(class)s_set'
    )

    class Meta:
        abstract = True


class SiteConfiguration(models.Model):
    """Singleton model to hold site-wide settings."""
    site_name = models.CharField(max_length=100, default='Rusydani on Cloud Corporate Games Hub')
    logo = models.ImageField(upload_to='site/', null=True, blank=True)
    favicon = models.ImageField(upload_to='site/', null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    footer_text = models.CharField(max_length=255, blank=True, default='© 2025 RoC GMS')
    hero_images = models.JSONField(default=list, blank=True, help_text="List of hero image paths for the slider")
    timezone = models.CharField(max_length=50, default='Asia/Jakarta', help_text="Site timezone (e.g. Asia/Jakarta)")

    def __str__(self):
        return self.site_name

    def add_hero_image(self, image_path, caption='', alt_text='', order=None):
        """Add a new hero image to the configuration."""
        if not self.hero_images:
            self.hero_images = []

        if order is None:
            order = len(self.hero_images)

        self.hero_images.append({
            'path': image_path,
            'caption': caption,
            'alt_text': alt_text,
            'order': order
        })
        self.save()

    def remove_hero_image(self, index):
        """Remove a hero image by index."""
        if self.hero_images and 0 <= index < len(self.hero_images):
            del self.hero_images[index]
            self.save()

    def get_active_hero_images(self):
        """Get only active hero images, ordered by their order field."""
        if not self.hero_images:
            return []
        
        from django.core.files.storage import default_storage
        images = sorted([img for img in self.hero_images], key=lambda x: x.get('order', 0))
        
        # Add full URL to each image for template usage
        for img in images:
            if 'path' in img:
                try:
                    img['url'] = default_storage.url(img['path'])
                except Exception:
                    # Fallback if storage fails or path is invalid
                    img['url'] = f"/media/{img['path']}"
                    
        return images

    def get_favicon_html(self):
        """Return HTML tag for favicon if available."""
        if self.favicon:
            from django.utils.html import format_html
            return format_html('<link rel="shortcut icon" type="image/png" href="{}">', self.favicon.url)
        return format_html('')

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteConfiguration.objects.exists():
            raise ValueError("Only one SiteConfiguration instance is allowed")
        super().save(*args, **kwargs)
        # Clear cache to ensure changes are reflected immediately
        cache.delete('site_config_context')

    @classmethod
    def get_solo(cls):
        """Returns the single instance of SiteConfiguration, creating it if needed."""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'site_name': 'Rusydani on Cloud Corporate Games Hub',
                'footer_text': '© 2025 Rusydani on Cloud GMS',
                'timezone': 'Asia/Jakarta'
            }
        )
        return obj


class BusinessUnit(AuditableModel):
    """Master data for company business units."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Business Unit"
        verbose_name_plural = "Business Units"


class Participant(AuditableModel):
    """Represents employees who are players (no login access)."""
    full_name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=50, unique=True)  # Unique identifier for the employee
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name='participants')
    profile_picture = models.ImageField(upload_to='participant_pics/', null=True, blank=True)
    employee_id_photo = models.ImageField(upload_to='employee_id_photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    class Meta:
        verbose_name = "Participant"
        verbose_name_plural = "Participants"


class Referee(AuditableModel):
    """Master data for match referees."""
    full_name = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=200, blank=True)
    license_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Referee"
        verbose_name_plural = "Referees"


class Venue(AuditableModel):
    """Venue for matches."""
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Venue"
        verbose_name_plural = "Venues"


class Event(AuditableModel):
    """Top-level container for major events."""
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='event_logos/', null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    coordinators = models.ManyToManyField(User, related_name='coordinated_events', blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Event"
        verbose_name_plural = "Events"


class Club(AuditableModel):
    """Teams representing departments or groups."""
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='club_logos/', null=True, blank=True)
    players = models.ManyToManyField(Participant, related_name='clubs', blank=True)
    managed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_club')
    contact_person_name = models.CharField(max_length=200, blank=True)
    contact_person_phone = models.CharField(max_length=20, blank=True)
    contact_person_email = models.EmailField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubs"


class CompetitionFormat(AuditableModel):
    """Master table for competition formats."""
    FORMAT_TYPE_CHOICES = [
        ('SINGLE_ELIMINATION', 'Single Elimination'),
        ('DOUBLE_ELIMINATION', 'Double Elimination'),
        ('LEAGUE', 'League'),
        ('ROUND_ROBIN', 'Round Robin'),
        ('SWISS_SYSTEM', 'Swiss System'),
        ('KNOCKOUT', 'Knockout'),
        ('OTHER', 'Other'),
    ]

    FORMAT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMING_SOON', 'Coming Soon'),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    format_type = models.CharField(max_length=20, choices=FORMAT_TYPE_CHOICES, default='OTHER')
    status = models.CharField(
        max_length=15,
        choices=FORMAT_STATUS_CHOICES,
        default='ACTIVE',
        help_text="Status of this competition format"
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Set status based on format_type if not explicitly set
        if not self.status or self.status == 'ACTIVE':  # Only set if not explicitly set to COMING_SOON
            if self.format_type in ['SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION', 'LEAGUE', 'ROUND_ROBIN']:
                self.status = 'ACTIVE'
            else:
                self.status = 'COMING_SOON'
        super().save(*args, **kwargs)

    def get_format_display_name(self):
        """Get the display name for the format type."""
        return dict(self.FORMAT_TYPE_CHOICES).get(self.format_type, self.format_type)

    class Meta:
        verbose_name = "Competition Format"
        verbose_name_plural = "Competition Formats"

    def get_format_structure_info(self):
        """Get information about the structure of this format."""
        format_info = {
            'SINGLE_ELIMINATION': {
                'description': 'Teams are eliminated after one loss. The tournament continues until one team remains.',
                'structure': 'Bracket style with single elimination',
                'rounds_calculation': 'log2(number_of_teams)',
                'matches_calculation': 'number_of_teams - 1'
            },
            'DOUBLE_ELIMINATION': {
                'description': 'Teams are eliminated after two losses. Features winner and loser brackets.',
                'structure': 'Two-bracket system (winner and loser)',
                'rounds_calculation': '2 * log2(number_of_teams) - 1',
                'matches_calculation': '2 * number_of_teams - 2'
            },
            'LEAGUE': {
                'description': 'All teams play each other in a round-robin fashion within their division.',
                'structure': 'Round-robin within divisions',
                'rounds_calculation': 'number_of_teams - 1',
                'matches_calculation': 'number_of_teams * (number_of_teams - 1) / 2'
            },
            'ROUND_ROBIN': {
                'description': 'All participants/teams play each other once.',
                'structure': 'All play all',
                'rounds_calculation': 'number_of_teams - 1',
                'matches_calculation': 'number_of_teams * (number_of_teams - 1) / 2'
            },
            'SWISS_SYSTEM': {
                'description': 'Participants are paired based on performance to ensure even matches.',
                'structure': 'Performance-based pairing',
                'rounds_calculation': 'determined_by_organizer',
                'matches_calculation': 'determined_by_organizer'
            },
            'KNOCKOUT': {
                'description': 'Similar to single elimination, teams are knocked out after losses.',
                'structure': 'Bracket style elimination',
                'rounds_calculation': 'log2(number_of_teams)',
                'matches_calculation': 'number_of_teams - 1'
            },
            'OTHER': {
                'description': 'Custom or other format type.',
                'structure': 'Custom structure',
                'rounds_calculation': 'custom',
                'matches_calculation': 'custom'
            }
        }
        return format_info.get(self.format_type, format_info['OTHER'])

    class Meta:
        verbose_name = "Competition Format"
        verbose_name_plural = "Competition Formats"


class Competition(AuditableModel):
    """Competition within an event."""
    FREQUENCY_CHOICES = [
        ('WEEKEND', 'Weekend Only'),
        ('WEEKDAY', 'Weekday Only'),
        ('ALL_DAYS', 'All Days'),
        ('CUSTOM', 'Custom Days'),
    ]

    MATCH_TYPE_CHOICES = [
        ('1VS1_MATCH', '1vs1 Match'),
        ('RACE_TIME', 'Race Time'),
        ('COMPETITION_POINT', 'Competition Point'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='competitions')
    name = models.CharField(max_length=100)
    format = models.ForeignKey(CompetitionFormat, on_delete=models.PROTECT, related_name='competitions')
    PARTICIPANT_TYPE_CHOICES = [
        ('CLUBS', 'Clubs'),
        ('PARTICIPANTS', 'Participants'),
    ]

    match_type = models.CharField(
        max_length=30,
        choices=MATCH_TYPE_CHOICES,
        default='1VS1_MATCH',
        help_text="Type of match for this competition"
    )
    participant_type = models.CharField(
        max_length=20,
        choices=PARTICIPANT_TYPE_CHOICES,
        default='CLUBS',
        help_text="Type of participants for this competition (Clubs or Participants)"
    )
    number_of_clubs = models.PositiveIntegerField(
        help_text="Expected number of clubs participating in this competition",
        null=True,
        blank=True
    )
    enrolled_clubs = models.ManyToManyField(Club, related_name='enrolled_competitions', blank=True)

    # Fields for participants (for individual competitions)
    number_of_participants = models.PositiveIntegerField(
        help_text="Expected number of participants in this competition (for individual competitions)",
        null=True,
        blank=True
    )
    enrolled_participants = models.ManyToManyField(Participant, blank=True, related_name='competitions_enrolled')

    # Fields for league system with groups
    is_league_with_groups = models.BooleanField(
        default=False,
        help_text="Check if this competition uses league system with groups"
    )
    number_of_groups = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of groups in the league system (only applicable if using league with groups)"
    )
    clubs_per_group = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of clubs per group (only applicable if using league with groups)"
    )

    # New fields for automatic scheduling
    frequency_day = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='ALL_DAYS',
        help_text="Frequency of competition days (weekend, weekday, all days, or custom)"
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Start date for the competition matches"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="End date for the competition matches"
    )
    
    # Field to specify sport type for appropriate statistics labels
    SPORT_TYPE_CHOICES = [
        ('FOOTBALL', 'Football/Soccer'),
        ('VOLLEYBALL', 'Volleyball'),
        ('BASKETBALL', 'Basketball'),
        ('TENNIS', 'Tennis'),
        ('BADMINTON', 'Badminton'),
        ('PETANQUE', 'Petanque'),
        ('OTHER', 'Other'),
    ]
    sport_type = models.CharField(
        max_length=20,
        choices=SPORT_TYPE_CHOICES,
        default='FOOTBALL',
        help_text="Type of sport for appropriate statistics labeling (GF/GA/GD for football, SF/SA/SD for volleyball, etc.)"
    )
    has_third_place_match = models.BooleanField(
        default=False,
        help_text="Check if this competition should have a third-place match."
    )

    def __str__(self):
        return f"{self.name} - {self.event.name}"

    def get_format_structure_info(self):
        """Get the structure information for this competition's format."""
        return self.format.get_format_structure_info()

    def generate_schedule_for_format(self, ordered_participants=None):
        """Generate a schedule based on the competition format."""
        # Validasi sebelum penjadwalan
        self.validate_for_scheduling()

        # Use the date-aware versions to ensure proper scheduling within competition dates
        from datetime import timedelta
        from django.utils import timezone

        # Get enrolled clubs/participants
        if ordered_participants is not None:
            clubs = ordered_participants
        else:
            clubs = self.get_enrolled_clubs_list()
            
        if len(clubs) < 2:
            return []

        # Determine start and end dates
        start_date = self.start_date or timezone.now().date()
        end_date = self.end_date or (start_date + timedelta(days=30))  # Default 30 days if no end date
        
        # Safety validation: ensure start_date is not after end_date
        if start_date > end_date:
            # If start date is after end date, use start date + 30 days as end date
            end_date = start_date + timedelta(days=30)

        frequency_day = self.frequency_day or 'ALL_DAYS'

        if self.format.format_type == 'SINGLE_ELIMINATION':
            return self._generate_single_elimination_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        elif self.format.format_type == 'LEAGUE' or self.format_type == 'ROUND_ROBIN':
            return self._generate_league_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        elif self.format.format_type == 'DOUBLE_ELIMINATION':
            return self._generate_double_elimination_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        else:
            # For other formats, return a basic schedule
            return self._generate_basic_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )

    def _generate_single_elimination_schedule(self):
        """Generate a single elimination bracket with full structure for visualization."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # For single elimination, need to handle byes if number of clubs is not a power of 2
        # First round might have some teams getting byes to the next round
        num_teams = len(clubs)

        # Calculate the next power of 2 for proper bracket size
        next_power_of_2 = self.get_next_power_of_2(num_teams)

        # Calculate number of byes needed
        byes_needed = next_power_of_2 - num_teams

        # Create matches in a single elimination format
        matches = []

        # Prepare teams (add placeholder teams for byes)
        bracket_teams = clubs[:]
        for i in range(byes_needed):
            bracket_teams.append(None)  # Placeholder for bye

        # Calculate total rounds needed
        import math
        total_rounds = int(math.log2(next_power_of_2))

        # Create all rounds in advance to ensure complete bracket structure
        round_num = 1
        current_round_teams = bracket_teams[:]

        # Create matches for each round until we reach the final
        while len(current_round_teams) > 1:
            next_round_teams = []

            # Process teams in pairs for this round
            for i in range(0, len(current_round_teams), 2):
                team1 = current_round_teams[i]
                team2 = current_round_teams[i + 1] if i + 1 < len(current_round_teams) else None

                # Create a match for this pair - determine correct fields based on participant type
                match_fields = {
                    'competition': self,
                    'round_number': round_num,
                    'scheduled_time': timezone.now(),
                    'created_by': self.created_by,
                    'updated_by': self.updated_by
                }
                
                if self.participant_type == 'PARTICIPANTS':
                    match_fields['home_participant'] = team1
                    match_fields['away_participant'] = team2
                else:
                    match_fields['home_team'] = team1
                    match_fields['away_team'] = team2
                    
                match = Match.objects.create(**match_fields)
                matches.append(match)

                # Add placeholder for the winner to advance to the next round
                next_round_teams.append(None)  # Will be filled when results are set

            current_round_teams = next_round_teams
            round_num += 1

        return matches

    def generate_draft_schedule_for_format(self):
        """Generate a schedule with draft status based on the competition format."""
        # Validasi sebelum penjadwalan
        self.validate_for_scheduling()

        # Get enrolled clubs/participants
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # For draft matches, we don't assign specific times yet
        # Use a different approach that creates matches with status=DRAFT and no scheduled_time
        if self.format.format_type == 'SINGLE_ELIMINATION':
            return self._generate_draft_single_elimination_schedule()
        elif self.format.format_type == 'LEAGUE' or self.format.format_type == 'ROUND_ROBIN':
            return self._generate_draft_league_schedule()
        elif self.format.format_type == 'DOUBLE_ELIMINATION':
            return self._generate_draft_double_elimination_schedule()
        else:
            # For other formats, return a basic schedule
            return self._generate_draft_basic_schedule()

    def _generate_draft_single_elimination_schedule(self):
        """Generate a single elimination bracket with draft status for date assignment."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # For single elimination, need to handle byes if number of clubs is not a power of 2
        # First round might have some teams getting byes to the next round
        num_teams = len(clubs)

        # Calculate the next power of 2 for proper bracket size
        next_power_of_2 = self.get_next_power_of_2(num_teams)

        # Calculate number of byes needed
        byes_needed = next_power_of_2 - num_teams

        # Create matches in a single elimination format
        matches = []

        # Prepare teams (add placeholder teams for byes)
        bracket_teams = clubs[:]
        for i in range(byes_needed):
            bracket_teams.append(None)  # Placeholder for bye

        # Calculate total rounds needed
        import math
        total_rounds = int(math.log2(next_power_of_2))

        # Create all rounds in advance to ensure complete bracket structure
        round_num = 1
        current_round_teams = bracket_teams[:]

        # Create matches for each round until we reach the final
        while len(current_round_teams) > 1:
            next_round_teams = []

            # Process teams in pairs for this round
            for i in range(0, len(current_round_teams), 2):
                team1 = current_round_teams[i]
                team2 = current_round_teams[i + 1] if i + 1 < len(current_round_teams) else None

                # Create a match for this pair with DRAFT status
                # Use a placeholder time within the competition period to avoid validation errors
                from datetime import datetime
                start_time = self.start_date or timezone.now().date()
                placeholder_time = timezone.make_aware(
                    datetime.combine(start_time, datetime.min.time().replace(hour=9, minute=0))  # 9:00 AM
                )
                
                # Create a match for this pair with DRAFT status - determine correct fields based on participant type
                match_fields = {
                    'competition': self,
                    'round_number': round_num,
                    'status': 'DRAFT',  # Draft status to indicate it needs date assignment
                    'scheduled_time': placeholder_time,  # Placeholder time within competition period
                    'created_by': self.created_by,
                    'updated_by': self.updated_by
                }
                
                if self.participant_type == 'PARTICIPANTS':
                    match_fields['home_participant'] = team1
                    match_fields['away_participant'] = team2
                else:
                    match_fields['home_team'] = team1
                    match_fields['away_team'] = team2
                    
                match = Match.objects.create(**match_fields)
                matches.append(match)

                # Add placeholder for the winner to advance to the next round
                next_round_teams.append(None)  # Will be filled when results are set

            current_round_teams = next_round_teams
            round_num += 1

        return matches

    def _generate_league_schedule(self):
        """Generate a league/round-robin schedule."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        matches = []
        round_num = 1

        # If using league with groups, create matches within each group
        if self.is_league_with_groups:
            # Organize clubs into groups
            groups = self._organize_clubs_into_groups(clubs)

            # Create matches within each group
            for group_idx, group_clubs in enumerate(groups):
                # Round-robin within the group: each team plays every other team in the group
                import itertools
                for home_team, away_team in itertools.combinations(group_clubs, 2):
                    # Determine correct fields based on participant type
                    match_fields = {
                        'competition': self,
                        'round_number': round_num,
                        'group_number': group_idx + 1,  # Store which group this match belongs to
                        'scheduled_time': timezone.now()  # Should be set appropriately in a real system
                    }
                    
                    if self.participant_type == 'PARTICIPANTS':
                        match_fields['home_participant'] = home_team
                        match_fields['away_participant'] = away_team
                    else:
                        match_fields['home_team'] = home_team
                        match_fields['away_team'] = away_team
                        
                    match = Match.objects.create(**match_fields)
                    matches.append(match)
        else:
            # Standard round-robin: each team plays every other team
            import itertools
            # Generate all combinations of 2 clubs
            for home_team, away_team in itertools.combinations(clubs, 2):
                # Create match between two clubs - determine correct fields based on participant type
                match_fields = {
                    'competition': self,
                    'round_number': round_num,
                    'scheduled_time': timezone.now(),  # Should be set appropriately in a real system
                }
                
                if self.participant_type == 'PARTICIPANTS':
                    match_fields['home_participant'] = home_team
                    match_fields['away_participant'] = away_team
                else:
                    match_fields['home_team'] = home_team
                    match_fields['away_team'] = away_team
                    
                match = Match.objects.create(**match_fields)
                matches.append(match)

        return matches

    def _generate_draft_league_schedule(self):
        """Generate a league/round-robin schedule with draft status."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        matches = []
        round_num = 1

        # If using league with groups, create matches within each group
        if self.is_league_with_groups:
            # Organize clubs into groups
            groups = self._organize_clubs_into_groups(clubs)

            # Create matches within each group
            for group_idx, group_clubs in enumerate(groups):
                # Round-robin within the group: each team plays every other team in the group
                import itertools
                for home_team, away_team in itertools.combinations(group_clubs, 2):
                    # Determine correct fields based on participant type
                    match_fields = {
                        'competition': self,
                        'round_number': round_num,
                        'status': 'DRAFT',  # Draft status to indicate it needs date assignment
                        'group_number': group_idx + 1,  # Store which group this match belongs to
                        'scheduled_time': timezone.now(),  # Placeholder time that will be updated later
                    }
                    
                    if self.participant_type == 'PARTICIPANTS':
                        match_fields['home_participant'] = home_team
                        match_fields['away_participant'] = away_team
                    else:
                        match_fields['home_team'] = home_team
                        match_fields['away_team'] = away_team
                        
                    match = Match.objects.create(**match_fields)
                    matches.append(match)
        else:
            # Standard round-robin: each team plays every other team
            import itertools
            # Generate all combinations of 2 clubs
            for home_team, away_team in itertools.combinations(clubs, 2):
                # Create match between two clubs with DRAFT status - determine correct fields based on participant type
                match_fields = {
                    'competition': self,
                    'round_number': round_num,
                    'status': 'DRAFT',  # Draft status to indicate it needs date assignment
                    'scheduled_time': timezone.now(),  # Placeholder time that will be updated later
                }
                
                if self.participant_type == 'PARTICIPANTS':
                    match_fields['home_participant'] = home_team
                    match_fields['away_participant'] = away_team
                else:
                    match_fields['home_team'] = home_team
                    match_fields['away_team'] = away_team
                    
                match = Match.objects.create(**match_fields)
                matches.append(match)

        return matches

    def _generate_double_elimination_schedule(self):
        """Generate a double elimination bracket."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # For double elimination, we need both winner and loser brackets
        import math

        # Pad clubs to next power of 2 for proper bracket
        padded_clubs = clubs[:]
        while len(padded_clubs) & (len(padded_clubs) - 1) != 0:  # Not a power of 2
            padded_clubs.append(None)  # Use None as placeholder for bye

        matches = []
        round_num = 1
        current_winner_bracket = padded_clubs[:]

        # Initial round in winner bracket
        for i in range(0, len(current_winner_bracket), 2):
            if i + 1 < len(current_winner_bracket):
                home_team = current_winner_bracket[i]
                away_team = current_winner_bracket[i + 1]

                if home_team is not None and away_team is not None:
                    # Determine correct fields based on participant type
                    match_fields = {
                        'competition': self,
                        'round_number': round_num,
                        'bracket_type': 'WINNER',
                        'scheduled_time': timezone.now(),
                    }
                    
                    if self.participant_type == 'PARTICIPANTS':
                        match_fields['home_participant'] = home_team
                        match_fields['away_participant'] = away_team
                    else:
                        match_fields['home_team'] = home_team
                        match_fields['away_team'] = away_team
                        
                    match = Match.objects.create(**match_fields)
                    matches.append(match)

        return matches

    def _generate_draft_double_elimination_schedule(self):
        """Generate a double elimination bracket with draft status for date assignment."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # For double elimination, we need both winner and loser brackets
        import math

        # Pad clubs to next power of 2 for proper bracket
        padded_clubs = clubs[:]
        while len(padded_clubs) & (len(padded_clubs) - 1) != 0:  # Not a power of 2
            padded_clubs.append(None)  # Use None as placeholder for bye

        matches = []
        round_num = 1
        current_winner_bracket = padded_clubs[:]

        # Initial round in winner bracket
        for i in range(0, len(current_winner_bracket), 2):
            if i + 1 < len(current_winner_bracket):
                home_team = current_winner_bracket[i]
                away_team = current_winner_bracket[i + 1]

                if home_team is not None and away_team is not None:
                    # Determine correct fields based on participant type
                    match_fields = {
                        'competition': self,
                        'round_number': round_num,
                        'status': 'DRAFT',  # Draft status to indicate it needs date assignment
                        'bracket_type': 'WINNER',
                        'scheduled_time': timezone.now(),  # Placeholder time that will be updated later
                    }
                    
                    if self.participant_type == 'PARTICIPANTS':
                        match_fields['home_participant'] = home_team
                        match_fields['away_participant'] = away_team
                    else:
                        match_fields['home_team'] = home_team
                        match_fields['away_team'] = away_team
                        
                    match = Match.objects.create(**match_fields)
                    matches.append(match)

        return matches

    def _generate_basic_schedule(self):
        """Generate a basic schedule for other formats."""
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        matches = []

        # If using league with groups, create matches within each group
        if self.is_league_with_groups:
            # Organize clubs into groups
            groups = self._organize_clubs_into_groups(clubs)

            # Create matches within each group
            for group_idx, group_clubs in enumerate(groups):
                # Round-robin within the group: each team plays every other team in the group
                import itertools
                for home_team, away_team in itertools.combinations(group_clubs, 2):
                    match = Match.objects.create(
                        competition=self,
                        home_team=home_team,
                        away_team=away_team,
                        scheduled_time=timezone.now(),
                        round_number=1,
                        group_number=group_idx + 1  # Store which group this match belongs to
                    )
                    matches.append(match)
        else:
            # For basic format without groups, create matches between all clubs (round-robin style)
            import itertools
            for home_team, away_team in itertools.combinations(clubs, 2):
                match = Match.objects.create(
                    competition=self,
                    home_team=home_team,
                    away_team=away_team,
                    scheduled_time=timezone.now(),
                    round_number=1
                )
                matches.append(match)

        return matches

    def clean(self):
        from django.core.exceptions import ValidationError
        # Validate to ensure at least 2 clubs are planned if the field is set
        if self.number_of_clubs is not None and self.number_of_clubs < 2:
            raise ValidationError(
                f"Minimum number of clubs planned must be 2. You planned for {self.number_of_clubs} clubs."
            )

        # Validation depends on competition format and number of clubs planned
        # Check if format exists before accessing its attributes
        if hasattr(self, 'format') and self.format and self.number_of_clubs is not None:
            if self.format.format_type in ['SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION', 'KNOCKOUT']:
                # For elimination formats, number of clubs ideally should be a power of 2 (2, 4, 8, 16, 32, etc.)
                import math
                log2_count = math.log2(self.number_of_clubs)
                if not log2_count.is_integer():
                    # But we still allow it for flexibility
                    pass
            elif self.format.format_type in ['LEAGUE', 'ROUND_ROBIN']:
                # League/round-robin format requires at least 2 clubs
                if self.number_of_clubs < 2:
                    raise ValidationError(
                        f"For format {self.format.get_format_display_name()}, "
                        f"at least 2 clubs are required. You planned for {self.number_of_clubs} clubs."
                    )

        # Validate that the selected format is active (not coming soon)
        if hasattr(self, 'format') and self.format and self.format.status == 'COMING_SOON':
            raise ValidationError(
                f"The selected format '{self.format.name}' is coming soon and currently not available for use. "
                f"Please select an active format: Single Elimination, Double Elimination, League, or Round Robin."
            )

        # Validation for league with groups
        if self.is_league_with_groups:
            # Validate that number of groups is set
            if not self.number_of_groups or self.number_of_groups < 1:
                raise ValidationError("Number of groups must be at least 1 when using league with groups.")

            # Validate that clubs per group is set
            if not self.clubs_per_group or self.clubs_per_group < 2:
                raise ValidationError("Number of clubs per group must be at least 2 when using league with groups.")

            # Calculate expected number of clubs based on groups and clubs per group
            expected_clubs = self.number_of_groups * self.clubs_per_group
            if self.number_of_clubs != expected_clubs:
                raise ValidationError(
                    f"For league with {self.number_of_groups} groups and {self.clubs_per_group} clubs per group, "
                    f"expected {expected_clubs} total clubs, but {self.number_of_clubs} clubs were planned."
                )

        # Validation for participants vs clubs based on participant_type
        if self.participant_type == 'PARTICIPANTS':
            # For participant competitions, validate participants instead of clubs
            if self.number_of_participants is not None and self.number_of_participants < 2:
                raise ValidationError(
                    f"For participant competitions, minimum number of participants planned must be 2. "
                    f"You planned for {self.number_of_participants} participants."
                )

            # Skip enrollment count validation in the clean method since M2M is processed after saving
            # The enrollment count validation will be handled after the instance is saved
        else:
            # For club competitions (default behavior), validate clubs
            if self.number_of_clubs is not None and self.number_of_clubs < 2:
                raise ValidationError(
                    f"Minimum number of clubs planned must be 2. You planned for {self.number_of_clubs} clubs."
                )

        # Validate that start_date is not after end_date
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(
                f"Start date ({self.start_date}) cannot be after end date ({self.end_date})."
            )

    def get_next_power_of_2(self, n):
        """Helper method to calculate the next power of 2 for bracket sizing."""
        if n <= 1:
            return 1
        power = 1
        while power < n:
            power *= 2
        return power



    def save(self, *args, **kwargs):
        # Validasi sebelum menyimpan
        self.clean()
        super().save(*args, **kwargs)



    def validate_for_scheduling(self):
        """Validation method for scheduling based on competition format"""
        from django.core.exceptions import ValidationError
        # Use _prefetched_objects_cache or fetch fresh data to avoid stale cache issues
        if self.participant_type == 'PARTICIPANTS':
            enrolled_count = self.enrolled_participants.count()
        else:
            enrolled_count = self.enrolled_clubs.count()

        if self.format:
            if self.format.format_type in ['SINGLE_ELIMINATION', 'DOUBLE_ELIMINATION', 'KNOCKOUT']:
                # For elimination formats, number of clubs should ideally be a power of 2 (2, 4, 8, 16, 32, etc.)
                if enrolled_count > 0:
                    # Check if the number of clubs is a power of 2
                    import math
                    log2_count = math.log2(enrolled_count)
                    if not log2_count.is_integer():
                        # To accommodate competition formats with non-power-of-2 club counts,
                        # we can adjust the system to add "bye" rounds
                        pass  # We can add logic here to handle non-power-of-2 club counts
            elif self.format.format_type in ['LEAGUE', 'ROUND_ROBIN']:
                # League/round-robin format requires at least 2 participants
                if enrolled_count < 2:
                    entity_type = "participants" if self.participant_type == 'PARTICIPANTS' else "clubs"
                    raise ValidationError(
                        f"For format {self.format.get_format_display_name()}, "
                        f"at least 2 {entity_type} are required. You currently have {enrolled_count} {entity_type}."
                    )

        # Additional validation for league with groups
        if self.is_league_with_groups:
            expected_count = self.number_of_groups * self.clubs_per_group
            if enrolled_count != expected_count:
                entity_type = "participants" if self.participant_type == 'PARTICIPANTS' else "clubs"
                raise ValidationError(
                    f"For league with {self.number_of_groups} groups and {self.clubs_per_group} {entity_type} per group, "
                    f"expected {expected_count} total {entity_type} to be enrolled, but {enrolled_count} {entity_type} are enrolled."
                )

        # Additional validation based on participant_type
        if self.participant_type == 'PARTICIPANTS':
            # Skip enrollment count validation in validate_for_scheduling since M2M is processed after saving
            # The enrollment count validation will be handled after the instance is saved
            pass
        else:
            # Check if enrolled count matches the planned number of clubs
            if self.number_of_clubs is not None and self.number_of_clubs > 0 and enrolled_count != self.number_of_clubs:
                 raise ValidationError(
                    f"Expected {self.number_of_clubs} clubs to be enrolled, but {enrolled_count} are enrolled."
                )
            # Skip enrollment count validation for clubs in validate_for_scheduling since M2M is processed after saving
            # The enrollment count validation will be handled after the instance is saved
            pass

    def validate_enrollment_count(self):
        """Validate that enrollment count matches planned number after M2M is updated."""
        from django.core.exceptions import ValidationError
        if self.participant_type == 'PARTICIPANTS':
            if self.number_of_participants:
                enrolled_count = self.enrolled_participants.count()
                if enrolled_count != self.number_of_participants:
                    raise ValidationError(
                        f"Number of enrolled participants ({enrolled_count}) must match "
                        f"the planned number ({self.number_of_participants})."
                    )
        elif self.participant_type == 'CLUBS':
            if self.number_of_clubs:
                enrolled_count = self.enrolled_clubs.count()
                if enrolled_count != self.number_of_clubs:
                    raise ValidationError(
                        f"Number of enrolled clubs ({enrolled_count}) must match the planned number ({self.number_of_clubs})."
                    )

    def get_enrolled_clubs_list(self):
        """Get enrolled entities as a list, optimized for scheduling algorithms."""
        from django.core.cache import cache
        cache_key = f"seeding_order_{self.id}"
        cached_seeding = cache.get(cache_key)

        if cached_seeding and isinstance(cached_seeding, list):
            # Use cached seeding order
            ordered_entities = []
            if self.participant_type == 'PARTICIPANTS':
                # Create a mapping from IDs to participants
                participants_map = {p.id: p for p in self.enrolled_participants.all()}
                # Add participants in the cached seeding order
                for participant_id in cached_seeding:
                    if participant_id in participants_map:
                        ordered_entities.append(participants_map[participant_id])
                        
                # Also add any remaining participants not in cache (shouldn't happen if cache has all)
                existing_ids = set(cached_seeding)
                for participant in self.enrolled_participants.all():
                    if participant.id not in existing_ids and participant not in ordered_entities:
                        ordered_entities.append(participant)
            else:  # CLUBS
                # Create a mapping from IDs to clubs
                clubs_map = {c.id: c for c in self.enrolled_clubs.all()}
                # Add clubs in the cached seeding order
                for club_id in cached_seeding:
                    if club_id in clubs_map:
                        ordered_entities.append(clubs_map[club_id])
                        
                # Also add any remaining clubs not in cache (shouldn't happen if cache has all)
                existing_ids = set(cached_seeding)
                for club in self.enrolled_clubs.all():
                    if club.id not in existing_ids and club not in ordered_entities:
                        ordered_entities.append(club)
            
            return ordered_entities
        else:
            # Use default order
            if self.participant_type == 'PARTICIPANTS':
                return list(self.enrolled_participants.all())
            else:
                return list(self.enrolled_clubs.all())

    def _organize_clubs_into_groups(self, clubs):
        """Organize clubs into groups based on number_of_groups and clubs_per_group."""
        if not self.is_league_with_groups or not self.number_of_groups or not self.clubs_per_group:
            # If not using groups, return all clubs in a single group
            return [clubs]

        # Shuffle clubs to randomize grouping (optional)
        import random
        shuffled_clubs = clubs[:]  # Create a copy
        random.shuffle(shuffled_clubs)

        # Split clubs into groups
        groups = []
        for i in range(0, len(shuffled_clubs), self.clubs_per_group):
            group = shuffled_clubs[i:i + self.clubs_per_group]
            if group:  # Only add non-empty groups
                groups.append(group)

        return groups

    def get_next_available_date(self, current_date, frequency_day, start_date=None, end_date=None):
        """Get the next available date based on frequency settings."""
        from datetime import timedelta

        if frequency_day == 'ALL_DAYS':
            # Return next day
            next_date = current_date + timedelta(days=1)
        elif frequency_day == 'WEEKDAY':
            # Skip weekends
            next_date = current_date + timedelta(days=1)
            while next_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                next_date += timedelta(days=1)
        elif frequency_day == 'WEEKEND':
            # Only weekends
            next_date = current_date + timedelta(days=1)
            while next_date.weekday() < 5:  # Only Saturday (5) and Sunday (6)
                next_date += timedelta(days=1)
        else:  # CUSTOM
            # Find the next custom day after current_date
            next_date = current_date + timedelta(days=1)

            # Get all custom days in range
            custom_days = [custom_day.date for custom_day in self.custom_days.filter(
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')]

            if custom_days:
                for custom_date in custom_days:
                    if custom_date > current_date:
                        return custom_date
                # If no more custom days after current_date, return end_date + 1 or current_date
                return end_date + timedelta(days=1) if end_date else current_date + timedelta(days=1)
            else:
                # No custom days set, return end date + 1 so scheduling stops
                return end_date + timedelta(days=1) if end_date else current_date + timedelta(days=1)

        # If using one of the standard frequency types, make sure it's within range
        if start_date and end_date and next_date > end_date:
            return end_date + timedelta(days=1)  # Return out-of-range date to stop scheduling

        return next_date

    def generate_schedule_with_dates(self):
        """Generate a schedule based on the competition format with date constraints."""
        from datetime import timedelta
        from django.utils import timezone

        # Validate before scheduling
        self.validate_for_scheduling()

        # Get enrolled clubs
        clubs = self.get_enrolled_clubs_list()
        if len(clubs) < 2:
            return []

        # Determine start and end dates
        start_date = self.start_date or timezone.now().date()
        end_date = self.end_date or (start_date + timedelta(days=30))  # Default 30 days if no end date
        
        # Safety validation: ensure start_date is not after end_date
        if start_date > end_date:
            # If start date is after end date, use start date + 30 days as end date
            end_date = start_date + timedelta(days=30)
        frequency_day = self.frequency_day or 'ALL_DAYS'

        # Generate schedule based on format
        if self.format.format_type == 'SINGLE_ELIMINATION':
            return self._generate_single_elimination_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        elif self.format.format_type == 'LEAGUE' or self.format.format_type == 'ROUND_ROBIN':
            return self._generate_league_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        elif self.format.format_type == 'DOUBLE_ELIMINATION':
            return self._generate_double_elimination_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )
        else:
            return self._generate_basic_schedule_with_dates(
                clubs, start_date, end_date, frequency_day
            )

    def _generate_single_elimination_schedule_with_dates(self, clubs, start_date, end_date, frequency_day):
        """Generate a single elimination bracket with dates."""
        from datetime import timedelta
        from django.utils import timezone

        if len(clubs) < 2:
            return []

        # For single elimination, need to handle byes if number of clubs is not a power of 2
        num_teams = len(clubs)

        # Calculate the next power of 2 for proper bracket size
        next_power_of_2 = self.get_next_power_of_2(num_teams)

        # Calculate number of byes needed
        byes_needed = next_power_of_2 - num_teams

        # Create matches in a single elimination format
        matches = []

        # First, we need to create the structure for the bracket
        import math

        # Calculate total rounds needed
        total_rounds = int(math.log2(next_power_of_2))

        # Prepare teams (add placeholder teams for byes)
        bracket_teams = clubs[:]
        for i in range(byes_needed):
            bracket_teams.append(None)  # Placeholder for bye

        # Create matches in each round with scheduling
        current_round_teams = bracket_teams[:]
        round_num = 1
        current_date = start_date

        while len(current_round_teams) > 1 and current_date <= end_date:
            next_round_teams = []

            # Create matches for this round
            for i in range(0, len(current_round_teams), 2):
                team1 = current_round_teams[i]
                team2 = current_round_teams[i + 1] if i + 1 < len(current_round_teams) else None

                # If both teams exist, create a match
                if team1 is not None and team2 is not None:
                    # Only create match if within date range
                    if current_date <= end_date:
                        # Determine the correct fields based on participant type
                        match_fields = {'competition': self, 'round_number': round_num}
                        
                        if self.participant_type == 'PARTICIPANTS':
                            match_fields['home_participant'] = team1
                            match_fields['away_participant'] = team2
                        else:
                            match_fields['home_team'] = team1
                            match_fields['away_team'] = team2
                            
                        match_fields['scheduled_time'] = timezone.make_aware(
                            datetime.combine(current_date, time(10, 0))  # Default time 10:00 AM
                        )
                        match_fields['created_by'] = self.created_by if self.created_by else None
                        match_fields['updated_by'] = self.updated_by if self.updated_by else None
                        
                        match = Match.objects.create(**match_fields)
                        matches.append(match)
                        next_round_teams.append(None)  # Winner of this match will be placed here
                    else:
                        break
                elif team1 is not None and team2 is None:
                    # Team1 gets a bye to next round
                    next_round_teams.append(team1)
                elif team1 is None and team2 is not None:
                    # Team2 gets a bye to next round
                    next_round_teams.append(team2)
                else:
                    # Both are None (shouldn't happen in single elimination)
                    next_round_teams.append(None)

            # Move to next available date for the next round
            if current_round_teams:
                current_date = self.get_next_available_date(current_date, frequency_day, start_date, end_date)
            current_round_teams = next_round_teams
            round_num += 1

            if current_date > end_date:
                break

        return matches

    def _generate_league_schedule_with_dates(self, clubs, start_date, end_date, frequency_day):
        """Generate a league/round-robin schedule with dates."""
        from datetime import timedelta
        import itertools
        from django.utils import timezone

        if len(clubs) < 2:
            return []

        matches = []
        current_date = start_date
        
        groups = [clubs]
        if self.is_league_with_groups:
            groups = self._organize_clubs_into_groups(clubs)

        for group_idx, group_clubs in enumerate(groups):
            if len(group_clubs) < 2:
                continue

            for home_team, away_team in itertools.combinations(group_clubs, 2):
                if current_date > end_date:
                    break

                match_fields = {
                    'competition': self,
                    'round_number': 1,
                    'group_number': group_idx + 1 if self.is_league_with_groups else None,
                    'scheduled_time': timezone.make_aware(datetime.combine(current_date, time(10, 0))),
                }

                if self.participant_type == 'PARTICIPANTS':
                    match_fields['home_participant'] = home_team
                    match_fields['away_participant'] = away_team
                else:
                    match_fields['home_team'] = home_team
                    match_fields['away_team'] = away_team
                
                matches.append(Match.objects.create(**match_fields))
                current_date = self.get_next_available_date(current_date, frequency_day, start_date, end_date)
            
            if current_date > end_date:
                break

        return matches

    def _generate_double_elimination_schedule_with_dates(self, clubs, start_date, end_date, frequency_day):
        """Generate a double elimination bracket with dates."""
        from datetime import timedelta
        import math
        from django.utils import timezone

        if len(clubs) < 2:
            return []

        # For double elimination, we need both winner and loser brackets
        # Pad clubs to next power of 2 for proper bracket
        padded_clubs = clubs[:]
        while len(padded_clubs) & (len(padded_clubs) - 1) != 0:  # Not a power of 2
            padded_clubs.append(None)  # Use None as placeholder for bye

        matches = []
        current_date = start_date
        round_num = 1
        current_winner_bracket = padded_clubs[:]

        # Initial round in winner bracket
        for i in range(0, len(current_winner_bracket), 2):
            if i + 1 < len(current_winner_bracket):
                home_team = current_winner_bracket[i]
                away_team = current_winner_bracket[i + 1]

                # Only create match if both teams exist and within date range
                if home_team is not None and away_team is not None:
                    if current_date <= end_date:
                        match = Match.objects.create(
                            competition=self,
                            home_team=home_team,
                            away_team=away_team,
                            scheduled_time=timezone.make_aware(
                                datetime.combine(current_date, time(10, 0))  # Default time 10:00 AM
                            ),
                            round_number=round_num,
                            bracket_type='WINNER'
                        )
                        matches.append(match)

                        # Move to next available date for the next match
                        current_date = self.get_next_available_date(current_date, frequency_day, start_date, end_date)

                        if current_date > end_date:
                            break
                    else:
                        break

        return matches

    def _generate_basic_schedule_with_dates(self, clubs, start_date, end_date, frequency_day):
        """Generate a basic schedule with dates."""
        from datetime import timedelta
        import itertools
        from django.utils import timezone

        if len(clubs) < 2:
            return []

        matches = []
        current_date = start_date
        round_num = 1

        # If using league with groups, create matches within each group
        if self.is_league_with_groups:
            # Organize clubs into groups
            groups = self._organize_clubs_into_groups(clubs)

            # Create matches within each group
            for group_idx, group_clubs in enumerate(groups):
                # Round-robin within the group: each team plays every other team in the group
                for home_team, away_team in itertools.combinations(group_clubs, 2):
                    # Only create match if within date range
                    if current_date <= end_date:
                        match = Match.objects.create(
                            competition=self,
                            home_team=home_team,
                            away_team=away_team,
                            scheduled_time=timezone.make_aware(
                                datetime.combine(current_date, time(10, 0))  # Default time 10:00 AM
                            ),
                            round_number=round_num,
                            group_number=group_idx + 1  # Store which group this match belongs to
                        )
                        matches.append(match)

                        # Move to next available date for the next match
                        current_date = self.get_next_available_date(current_date, frequency_day, start_date, end_date)

                        if current_date > end_date:
                            break
                    else:
                        break
        else:
            # Standard round-robin: each team plays every other team
            # Generate all combinations of 2 clubs
            for home_team, away_team in itertools.combinations(clubs, 2):
                # Only create match if within date range
                if current_date <= end_date:
                    match = Match.objects.create(
                        competition=self,
                        home_team=home_team,
                        away_team=away_team,
                        scheduled_time=timezone.make_aware(
                            datetime.combine(current_date, time(10, 0))  # Default time 10:00 AM
                        ),
                        round_number=round_num
                    )
                    matches.append(match)

                    # Move to next available date for the next match
                    current_date = self.get_next_available_date(current_date, frequency_day, start_date, end_date)

                    if current_date > end_date:
                        break
                else:
                    break

        return matches

    def get_bracket_matches_by_round(self):
        """Get matches organized by round for bracket display."""
        matches = self.matches.all()
        bracket_data = {}
        
        # Group matches by round
        for match in matches:
            round_num = match.round_number or 1
            if round_num not in bracket_data:
                bracket_data[round_num] = []
            bracket_data[round_num].append(match)

        # Return dictionary with sorted keys
        return {round_num: bracket_data[round_num] for round_num in sorted(bracket_data.keys())}

    def get_bracket_data_for_visualization(self):
        """Generate bracket data in the format expected by the Gracket library for visualization."""
        matches = self.matches.select_related(
            'home_team', 'away_team', 'home_participant', 'away_participant'
        ).all().order_by('round_number')

        if not matches.exists():
            # If no matches exist, return data based on enrolled participants
            if self.participant_type == 'CLUBS':
                participants = self.enrolled_clubs.all().order_by('name')
            else:
                participants = self.enrolled_participants.all().order_by('full_name')

            teams_data = []
            for i, participant in enumerate(participants):
                teams_data.append({
                    "name": getattr(participant, 'name', getattr(participant, 'full_name', 'Unknown')),
                    "id": f"team-{participant.pk}",
                    "seed": i + 1
                })
            return teams_data

        # Group matches by round to create the bracket structure
        matches_by_round = {}
        for match in matches:
            round_num = match.round_number or 1
            if round_num not in matches_by_round:
                matches_by_round[round_num] = []
            matches_by_round[round_num].append(match)

        # Create bracket structure in the format expected by Gracket
        # The Gracket library expects tournament data organized by rounds
        max_round = max(matches_by_round.keys()) if matches_by_round else 1

        # Calculate total rounds for descriptive TBD names
        import math
        enroll_count = self.enrolled_clubs.count() if self.participant_type == 'CLUBS' else self.enrolled_participants.count()
        total_rounds = int(math.log2(self.get_next_power_of_2(len(self.get_enrolled_clubs_list())))) if enroll_count > 0 else 1

        tournament_structure = []
        for round_num in range(1, max_round + 1):
            if round_num in matches_by_round:
                round_matches = []
                for match in matches_by_round[round_num]:
                    # Create team objects for this match using helper method
                    home_team_data, away_team_data = self._create_team_data_for_bracket(match, round_num, total_rounds)
                    round_matches.append([home_team_data, away_team_data])
                tournament_structure.append(round_matches)
            else:
                tournament_structure.append([])  # Empty round if no matches

        return tournament_structure

    def _create_team_data_for_bracket(self, match, round_num, total_rounds):
        """Helper method to create standardized team data for bracket visualization."""
        # Determine team names and IDs based on participant type
        if self.participant_type == 'PARTICIPANTS':
            # For participant-based competitions
            if match.home_participant:
                home_team_name = match.home_participant.full_name
                home_team_id = f"team-{match.home_participant.pk}"
            else:
                home_team_name = self._get_tbd_name(round_num, total_rounds, "participant")
                home_team_id = "tbd-home"

            if match.away_participant:
                away_team_name = match.away_participant.full_name
                away_team_id = f"team-{match.away_participant.pk}"
            else:
                away_team_name = self._get_tbd_name(round_num, total_rounds, "participant")
                away_team_id = "tbd-away"
        else:
            # For club-based competitions
            if match.home_team:
                home_team_name = match.home_team.name
                home_team_id = f"team-{match.home_team.pk}"
            else:
                home_team_name = self._get_tbd_name(round_num, total_rounds, "team")
                home_team_id = "tbd-home"

            if match.away_team:
                away_team_name = match.away_team.name
                away_team_id = f"team-{match.away_team.pk}"
            else:
                away_team_name = self._get_tbd_name(round_num, total_rounds, "team")
                away_team_id = "tbd-away"

        # Format date for display in bracket if available
        date_str = ""
        if match.scheduled_time:
            date_str = f"\n{match.scheduled_time.strftime('%m/%d %H:%M')}"

        # Create team data objects
        home_team_data = {
            "name": home_team_name + date_str,
            "id": home_team_id,
            "date": match.scheduled_time.strftime('%m/%d %H:%M') if match.scheduled_time else None
        }

        away_team_data = {
            "name": away_team_name + date_str,
            "id": away_team_id,
            "date": match.scheduled_time.strftime('%m/%d %H:%M') if match.scheduled_time else None
        }

        return home_team_data, away_team_data

    def _get_tbd_name(self, round_num, total_rounds, entity_type="team"):
        """Helper method to get descriptive TBD names based on round position."""
        if round_num == total_rounds:  # Final
            return f"TBD Final"
        elif round_num == total_rounds - 1:  # Semifinal
            return f"TBD Semifinal"
        elif round_num == total_rounds - 2:  # Quarterfinal
            return f"TBD Quarterfinal"
        else:
            return f"TBD"


    class Meta:
        verbose_name = "Competition"
        verbose_name_plural = "Competitions"

    @classmethod
    def get_active_formats(cls):
        """Get only active competition formats (not coming soon)."""
        from django.db import models
        active_formats = CompetitionFormat.objects.filter(status='ACTIVE')
        return active_formats


class CustomDay(TimestampedModel):
    """Model to store custom days for scheduling."""
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='custom_days')
    date = models.DateField()
    description = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.competition.name} - {self.date.strftime('%Y-%m-%d')}"

    class Meta:
        unique_together = ('competition', 'date')
        verbose_name = "Custom Day"
        verbose_name_plural = "Custom Days"


class Match(AuditableModel):
    """Model representing a match in a competition."""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('POSTPONED', 'Postponed'),
        ('IN_PROGRESS', 'In Progress'),
    ]

    BRACKET_TYPE_CHOICES = [
        ('WINNER', 'Winner Bracket'),
        ('LOSER', 'Loser Bracket'),
    ]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='matches')
    # Fields for club-based competitions
    home_team = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True, related_name='home_matches')
    away_team = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True, related_name='away_matches')
    # Fields for participant-based competitions
    home_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True, related_name='home_matches')
    away_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True, related_name='away_matches')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    streaming_link = models.URLField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    round_number = models.PositiveIntegerField(null=True, blank=True)
    bracket_type = models.CharField(max_length=10, choices=BRACKET_TYPE_CHOICES, null=True, blank=True)
    group_number = models.PositiveIntegerField(null=True, blank=True, help_text="Group number for matches in league with groups")
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    # Winner field should also accommodate both clubs and participants
    winner_club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches_as_club')
    winner_participant = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches_as_participant')
    referees = models.ManyToManyField(Referee, blank=True)

    # Fields for league matches vs bracket matches
    is_league_match = models.BooleanField(default=False, help_text="Whether this is a league match instead of bracket")
    league_points_home = models.IntegerField(default=0, help_text="Points awarded to home team in league system")
    league_points_away = models.IntegerField(default=0, help_text="Points awarded to away team in league system")

    def __str__(self):
        if self.competition.participant_type == 'PARTICIPANTS':
            home_name = self.home_participant.full_name if self.home_participant else "TBD"
            away_name = self.away_participant.full_name if self.away_participant else "TBD"
        else:
            home_name = self.home_team.name if self.home_team else "TBD"
            away_name = self.away_team.name if self.away_team else "TBD"
        time_str = self.scheduled_time.strftime('%Y-%m-%d %H:%M') if self.scheduled_time else "TBD"
        return f"{self.competition.name}: {home_name} vs {away_name} ({time_str})"

    def get_scores(self):
        """Get home and away scores from related MatchResult objects."""
        home_score = None
        away_score = None
        for result in self.results.all():
            if self.competition.participant_type == 'CLUBS':
                if result.club_id == self.home_team_id:
                    home_score = result.score
                elif result.club_id == self.away_team_id:
                    away_score = result.score
            else: # PARTICIPANTS
                if result.participant_id == self.home_participant_id:
                    home_score = result.score
                elif result.participant_id == self.away_participant_id:
                    away_score = result.score
        return home_score, away_score

    def get_home_team_name(self):
        """Get the home team/participant name, handling TBD cases."""
        if self.competition.participant_type == 'PARTICIPANTS':
            return self.home_participant.full_name if self.home_participant else "TBD"
        else:
            return self.home_team.name if self.home_team else "TBD"

    def get_away_team_name(self):
        """Get the away team/participant name, handling TBD cases."""
        if self.competition.participant_type == 'PARTICIPANTS':
            return self.away_participant.full_name if self.away_participant else "TBD"
        else:
            return self.away_team.name if self.away_team else "TBD"

    def get_formatted_time(self):
        """Get the scheduled time in a formatted string."""
        if self.scheduled_time:
            return self.scheduled_time.strftime('%Y-%m-%d %H:%M')
        return "TBD"

    def get_match_data_for_visualization(self):
        """Get match data formatted for bracket visualization."""
        # Determine the correct home/away names based on participant type
        if self.competition.participant_type == 'PARTICIPANTS':
            home_name = self.home_participant.full_name if self.home_participant else "TBD"
            away_name = self.away_participant.full_name if self.away_participant else "TBD"
        else:
            home_name = self.home_team.name if self.home_team else "TBD"
            away_name = self.away_team.name if self.away_team else "TBD"
            
        return {
            'id': self.id,
            'home_team_name': home_name,
            'away_team_name': away_name,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'round_number': self.round_number or 1,
            'status': self.status,
            'venue': self.venue.name if self.venue else "TBD",
            'home_team_id': self.home_participant.id if self.competition.participant_type == 'PARTICIPANTS' and self.home_participant else self.home_team.id if self.home_team else None,
            'away_team_id': self.away_participant.id if self.competition.participant_type == 'PARTICIPANTS' and self.away_participant else self.away_team.id if self.away_team else None,
        }

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Determine participant type from the competition
        participant_type = self.competition.participant_type if hasattr(self.competition, 'participant_type') else 'CLUBS'
        
        if participant_type == 'CLUBS':
            # For club competitions, validate club fields
            if self.home_team and self.away_team and self.home_team == self.away_team:
                raise ValidationError("Home team and away team cannot be the same.")
            
            # Ensure participant fields are empty for club competitions
            if self.home_participant or self.away_participant:
                raise ValidationError("Participant fields should not be used for club-based competitions.")
        
        elif participant_type == 'PARTICIPANTS':
            # For participant competitions, validate participant fields
            if self.home_participant and self.away_participant and self.home_participant == self.away_participant:
                raise ValidationError("Home participant and away participant cannot be the same.")
            
            # Ensure club fields are empty for participant competitions  
            if self.home_team or self.away_team:
                raise ValidationError("Club fields should not be used for participant-based competitions.")

        # Validate scheduled time - but allow more flexible scheduling for draft matches
        if self.scheduled_time and self.competition.start_date and self.competition.end_date:
            if self.scheduled_time.date() < self.competition.start_date or self.scheduled_time.date() > self.competition.end_date:
                # For draft matches, allow scheduling outside the competition period (will be updated later)
                if self.status != 'DRAFT':
                    raise ValidationError(
                        f"Scheduled time must be between {self.competition.start_date} and {self.competition.end_date}."
                    )

        # Validate bracket_type for double elimination formats
        if self.competition.format.format_type == 'DOUBLE_ELIMINATION':
            if self.bracket_type not in ['WINNER', 'LOSER']:
                raise ValidationError("Bracket type must be specified for double elimination format.")

    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Match"
        verbose_name_plural = "Matches"


class MatchResult(AuditableModel):
    """Model to store match result details."""
    OUTCOME_CHOICES = [
        ('WIN', 'Win'),
        ('LOSS', 'Loss'),
        ('DRAW', 'Draw'),
        ('TBD', 'To Be Determined'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='results')
    # Support both club-based and participant-based results
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True, related_name='match_results')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=True, blank=True, related_name='match_results')
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES, default='TBD')
    score = models.IntegerField(null=True, blank=True, help_text="Score of the match for this participant/team")
    result_data = models.JSONField()
    documentation_file = models.FileField(
        upload_to='match_docs/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )

    def __str__(self):
        # Determine the entity name based on participant type of the associated match's competition
        if self.match.competition.participant_type == 'PARTICIPANTS':
            entity_name = self.participant.full_name if self.participant else "Unknown Participant"
        else:
            entity_name = self.club.name if self.club else "Unknown Club"
        return f"{entity_name} - {self.match.competition.name}: {self.outcome}"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Validate that either club or participant is set, but not both
        if self.match.competition.participant_type == 'PARTICIPANTS':
            if not self.participant:
                raise ValidationError("For participant-based competitions, participant must be specified.")
            if self.club:
                raise ValidationError("Club field should not be used for participant-based results.")
        else:
            if not self.club:
                raise ValidationError("For club-based competitions, club must be specified.")
            if self.participant:
                raise ValidationError("Participant field should not be used for club-based results.")

    def save(self, *args, **kwargs):
        # Run validation before saving
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Match Result"
        verbose_name_plural = "Match Results"


class Disqualification(AuditableModel):
    """Model to store disqualification details."""
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='disqualifications')
    competition = models.ForeignKey(Competition, on_delete=models.SET_NULL, null=True, blank=True, related_name='disqualifications')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='disqualifications')
    reason = models.TextField()
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.participant.full_name} - {self.reason[:50]}..."

    class Meta:
        verbose_name = "Disqualification"
        verbose_name_plural = "Disqualifications"


class Announcement(AuditableModel):
    """Model to store event announcements."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return f"{self.event.name} - {self.title}"

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"


class Standings(models.Model):
    """Model for tracking team standings in competitions."""
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='standings')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='standings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    points = models.IntegerField(default=0)
    played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    goals_for = models.IntegerField(default=0)
    goals_against = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.club.name} - {self.competition.name}: {self.points} pts"

    @property
    def games_played(self):
        return self.wins + self.draws + self.losses

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    def update_standings(self):
        """Update the standings based on match results."""
        # Reset stats
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.goals_for = 0
        self.goals_against = 0
        self.points = 0

        # Process all matches for this club in this competition
        matches = Match.objects.filter(
            competition=self.competition,
            status='COMPLETED'
        ).filter(
            models.Q(home_team=self.club) | models.Q(away_team=self.club)
        )

        for match in matches:
            if match.home_team == self.club:
                # This club is the home team
                if match.home_team_score > match.away_team_score:
                    self.wins += 1
                    self.points += 3
                elif match.home_team_score == match.away_team_score:
                    self.draws += 1
                    self.points += 1
                else:
                    self.losses += 1

                self.goals_for += match.home_team_score or 0
                self.goals_against += match.away_team_score or 0
            else:
                # This club is the away team
                if match.away_team_score > match.home_team_score:
                    self.wins += 1
                    self.points += 3
                elif match.away_team_score == match.home_team_score:
                    self.draws += 1
                    self.points += 1
                else:
                    self.losses += 1

                self.goals_for += match.away_team_score or 0
                self.goals_against += match.home_team_score or 0

        # Calculate points based on format
        format_points = self.competition.format.format_type
        if format_points in ['LEAGUE', 'ROUND_ROBIN']:
            # For league formats, points are calculated as wins*3 + draws*1
            self.points = self.wins * 3 + self.draws * 1
        else:
            # For other formats, might use different point systems
            self.points = self.wins * 3 + self.draws * 1

        self.played = self.wins + self.draws + self.losses
        self.save()

    class Meta:
        verbose_name = "Standing"
        verbose_name_plural = "Standings"
        unique_together = ('competition', 'club')


class Medal(AuditableModel):
    """Model for tracking medals awarded in competitions."""
    MEDAL_CHOICES = [
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
        ('BRONZE', 'Bronze'),
        ('PARTICIPATION', 'Participation'),
    ]

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name='medals_awarded')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='medals_awarded')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='medals_received', null=True, blank=True)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='medals_received', null=True, blank=True)
    medal_type = models.CharField(max_length=20, choices=MEDAL_CHOICES)
    awarded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    awarded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        recipient = self.club.name if self.club else (self.participant.full_name if self.participant else "Unknown")
        return f"{self.medal_type} Medal - {recipient} - {self.competition.name}"

    def save(self, *args, **kwargs):
        # Validate that either club or participant is set, but not both
        if not (bool(self.club) ^ bool(self.participant)):  # XOR: exactly one should be true
            raise ValidationError("Either club or participant must be set, but not both.")
        
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Medal"
        verbose_name_plural = "Medals"
        unique_together = ('competition', 'medal_type', 'club', 'participant')