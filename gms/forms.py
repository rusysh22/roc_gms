from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.core.exceptions import ValidationError

# Also create specific forms for other models that might have label issues
from gms.models import Event, Competition, Participant, Club, SiteConfiguration, Match, MatchResult

class EventForm(ModelForm):
    class Meta:
        model = Event
        fields = '__all__'


class CompetitionForm(ModelForm):
    class Meta:
        model = Competition
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initially set format as required
        self.fields['format'].required = True  # Make sure format is required
        
        # Order the fields to ensure dates come before frequency_day
        field_order = ['name', 'event', 'format', 'match_type', 'participant_type', 'has_third_place_match', 'number_of_clubs', 'enrolled_clubs', 'number_of_participants', 'enrolled_participants', 'is_league_with_groups', 'number_of_groups', 'clubs_per_group', 'start_date', 'end_date', 'frequency_day']
        self.fields = {k: self.fields[k] for k in field_order if k in self.fields}
        
        # Update help text for league with groups fields to make them more descriptive
        if 'is_league_with_groups' in self.fields:
            self.fields['is_league_with_groups'].label = "Use League System with Groups"
            self.fields['is_league_with_groups'].help_text = "Check this to divide the league into separate groups"
        
        if 'number_of_groups' in self.fields:
            self.fields['number_of_groups'].help_text = "Number of groups to divide the competition into"
        
        if 'clubs_per_group' in self.fields:
            self.fields['clubs_per_group'].help_text = "Number of clubs in each group"
        
        # Update help text for participant fields to make them more descriptive
        if 'number_of_participants' in self.fields:
            self.fields['number_of_participants'].help_text = "Expected number of participants (for individual competitions)"
        
        if 'enrolled_participants' in self.fields:
            self.fields['enrolled_participants'].help_text = "Participants enrolled in this competition (for individual competitions)"
        
        # Update help text for participant type field
        if 'participant_type' in self.fields:
            self.fields['participant_type'].help_text = "Select whether clubs or participants will compete in this competition"
        
        # Initially set required based on initial participant_type
        self.update_required_fields()

        # Initialize field visibility based on participant type via JavaScript
        # The actual visibility logic is handled by participant_type_handler.js
        # which will show/hide fields based on the participant_type selection
    
    def update_required_fields(self):
        """Update required status of number_of_clubs and number_of_participants based on participant_type"""
        participant_type = self.data.get('participant_type') or self.initial.get('participant_type', 'CLUBS')
        
        # Reset both to not required - making them optional
        self.fields['number_of_clubs'].required = False
        self.fields['number_of_participants'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        participant_type = cleaned_data.get('participant_type', 'CLUBS')
        number_of_clubs = cleaned_data.get('number_of_clubs')
        enrolled_clubs = cleaned_data.get('enrolled_clubs', [])
        number_of_participants = cleaned_data.get('number_of_participants')
        enrolled_participants = cleaned_data.get('enrolled_participants', [])

        # Only validate enrolled clubs when participant_type is 'CLUBS'
        if participant_type == 'CLUBS' and number_of_clubs and enrolled_clubs is not None:
            enrolled_count = len(enrolled_clubs) if hasattr(enrolled_clubs, '__len__') else 0
            # Check if the count matches the planned number
            # Note: This validation may not be completely accurate for M2M in admin
            # since M2M is handled after form cleaning
            if enrolled_count != number_of_clubs:
                raise ValidationError(f"Number of enrolled clubs ({enrolled_count}) must match planned number ({number_of_clubs}).")

        # Only validate enrolled participants when participant_type is 'PARTICIPANTS'
        elif participant_type == 'PARTICIPANTS' and number_of_participants and enrolled_participants is not None:
            enrolled_count = len(enrolled_participants) if hasattr(enrolled_participants, '__len__') else 0
            # Check if the count matches the planned number
            # Note: This validation may not be completely accurate for M2M in admin
            # since M2M is handled after form cleaning
            if enrolled_count != number_of_participants:
                raise ValidationError(f"Number of enrolled participants ({enrolled_count}) must match planned number ({number_of_participants}).")
        
        # Validate date range when CUSTOM frequency is selected
        frequency_day = cleaned_data.get('frequency_day')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if frequency_day == 'CUSTOM':
            if not start_date:
                raise ValidationError("Start date is required when frequency is set to 'Custom Days'.")
            if not end_date:
                raise ValidationError("End date is required when frequency is set to 'Custom Days'.")
            if start_date and end_date and start_date > end_date:
                raise ValidationError("Start date cannot be after end date.")
        
        # Additional validation for CustomDay if any are submitted via form
        # This is a more complex validation that would typically happen in the admin or view
        # since CustomDay is an inline model
        if frequency_day == 'CUSTOM' and start_date and end_date:
            # Check if any CustomDay instances have dates outside the range
            # This validation would be more applicable when saving related CustomDay instances
            custom_days = self.data.getlist('customday_set-0-date')
            for custom_day_str in custom_days:
                if custom_day_str:
                    try:
                        from datetime import datetime
                        custom_day = datetime.strptime(custom_day_str, '%Y-%m-%d').date()
                        if custom_day < start_date or custom_day > end_date:
                            raise ValidationError(f"Custom day {custom_day} must be within the range {start_date} to {end_date}.")
                    except ValueError:
                        # Date format error already handled by Django
                        pass
        
        # Validate league with groups fields
        is_league_with_groups = cleaned_data.get('is_league_with_groups')
        number_of_groups = cleaned_data.get('number_of_groups')
        clubs_per_group = cleaned_data.get('clubs_per_group')
        
        if is_league_with_groups:
            if not number_of_groups:
                raise ValidationError("Number of groups is required when using league with groups.")
            if not clubs_per_group:
                raise ValidationError("Clubs per group is required when using league with groups.")
            
            if number_of_groups < 1:
                raise ValidationError("Number of groups must be at least 1.")
            if clubs_per_group < 2:
                raise ValidationError("Clubs per group must be at least 2.")
            
            # Check if total clubs matches expected number
            expected_clubs = number_of_groups * clubs_per_group
            if number_of_clubs != expected_clubs:
                raise ValidationError(
                    f"For {number_of_groups} groups with {clubs_per_group} clubs per group, "
                    f"expected {expected_clubs} total clubs, but {number_of_clubs} clubs were planned."
                )
        
        # Validate minimum number requirements but make them optional
        if participant_type == 'CLUBS' and number_of_clubs is not None and number_of_clubs != '':
            if number_of_clubs < 2:
                raise ValidationError(f"For club competitions, minimum number of clubs must be 2, but you entered {number_of_clubs}.")
            
            # We skip the enrollment count validation in the form since M2M is processed after saving
            # The model-level validation will handle this
        elif participant_type == 'PARTICIPANTS' and number_of_participants is not None and number_of_participants != '':
            if number_of_participants < 2:
                raise ValidationError(f"For participant competitions, minimum number of participants must be 2, but you entered {number_of_participants}.")
            
            # We skip the enrollment count validation in the form since M2M is processed after saving
            # The model-level validation will handle this
        
        return cleaned_data


class ParticipantForm(ModelForm):
    class Meta:
        model = Participant
        fields = '__all__'


class ClubForm(ModelForm):
    class Meta:
        model = Club
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure proper initialization of form fields
        # This can help with accessibility issues in admin themes


TIMEZONE_CHOICES = [
    ('UTC', 'UTC'),
    ('Asia/Jakarta', 'Asia/Jakarta (GMT+7)'),
    ('Asia/Makassar', 'Asia/Makassar (GMT+8)'),
    ('Asia/Jayapura', 'Asia/Jayapura (GMT+9)'),
    ('Asia/Kuala_Lumpur', 'Asia/Kuala_Lumpur (GMT+8)'),
    ('Asia/Singapore', 'Asia/Singapore (GMT+8)'),
]

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')


class MultipleFileInput(forms.FileInput):
    """Custom widget for multiple file uploads with styling"""
    def __init__(self, attrs=None):
        super().__init__(attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs['multiple'] = True
        # Add more specific and overriding classes for Unfold with wow effect but more compact
        if 'class' not in attrs:
            attrs['class'] = ''
        attrs['class'] += ' w-full text-sm text-gray-900 border-2 border-dashed border-blue-400 rounded-lg cursor-pointer bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 py-3 transition-all duration-300 hover:shadow-md hover:border-blue-500 focus:outline-none dark:border-blue-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-gradient-to-r file:from-blue-600 file:to-purple-600 file:text-white hover:file:from-blue-700 hover:file:to-purple-700 file:shadow-sm file:transition-all file:duration-300 file:hover:scale-105 file:cursor-pointer'
        return super().render(name, value, attrs, renderer)

class SiteConfigurationForm(ModelForm):
    hero_images_upload = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'id': 'id_hero_images_upload',
        }),
        help_text="Upload multiple images for the hero slider (max 10 files, max 5MB each, images only). Hold Ctrl/Cmd to select multiple files."
    )
    hero_images_to_remove = forms.CharField(
        required=False,
        label='',  # Suppress label for hidden field
        widget=forms.HiddenInput(attrs={'id': 'id_hero_images_to_remove'}),
    )
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        help_text="Select the site's timezone"
    )
    
    class Meta:
        model = SiteConfiguration
        fields = '__all__'
    
    def clean_hero_images_upload(self):
        files = self.files.getlist('hero_images_upload')
        
        # Check number of files
        if files and len(files) > 10:
            raise ValidationError('You can upload a maximum of 10 files.')
        
        # Check total size
        total_size = sum(file.size for file in files or [])
        max_total_size = 4 * 1024 * 1024  # 4MB limit for Vercel
        
        if total_size > max_total_size:
            raise ValidationError(f'Total upload size ({total_size / (1024*1024):.2f} MB) exceeds the 4MB limit. Please upload fewer or smaller images.')

        # Check each file
        for file in files or []:
            # Check file type (image only)
            if file.content_type and not file.content_type.startswith('image/'):
                raise ValidationError('Only image files are allowed.')
            
            # Check individual file size (max 2MB = 2 * 1024 * 1024 bytes)
            max_size = 2 * 1024 * 1024  # 2MB in bytes
            if file.size > max_size:
                raise ValidationError(f'File {file.name} is too large. Maximum individual file size is 2MB.')
        
        return files


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Menghapus field password agar tidak ditampilkan di form
        if 'password' in self.fields:
            del self.fields['password']


class MatchResultForm(forms.ModelForm):
    """Form for entering match results, filtered by scheduled date"""
    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Filter matches by scheduled date"
    )
    
    class Meta:
        model = MatchResult
        fields = ['match', 'club', 'outcome', 'score', 'result_data', 'documentation_file']
        widgets = {
            'match': forms.Select(attrs={'class': 'form-select'}),
            'club': forms.Select(attrs={'class': 'form-select'}),
            'outcome': forms.Select(attrs={'class': 'form-select'}),
            'result_data': forms.Textarea(attrs={'rows': 3}),
            'documentation_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        scheduled_date = kwargs.pop('scheduled_date', None)
        super().__init__(*args, **kwargs)
        
        # Filter matches by date if provided
        if scheduled_date:
            self.fields['match'].queryset = Match.objects.filter(
                scheduled_time__date=scheduled_date
            ).select_related('home_team', 'away_team', 'competition')
        else:
            # Filter to show only scheduled matches without results yet
            self.fields['match'].queryset = Match.objects.filter(
                status='SCHEDULED'
            ).select_related('home_team', 'away_team', 'competition')
        
        # Only show clubs that are participating in the selected match
        if self.instance and self.instance.match:
            participating_clubs = [
                self.instance.match.home_team,
                self.instance.match.away_team
            ]
            self.fields['club'].queryset = Club.objects.filter(
                id__in=[c.id for c in participating_clubs if c]
            )
        else:
            self.fields['club'].queryset = Club.objects.all()


class MatchResultFilterForm(forms.Form):
    """Form for filtering matches by date"""
    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white'}),
        label="Schedule Date"
    )
    competition = forms.ModelChoiceField(
        queryset=Competition.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Match.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-600 dark:border-gray-500 dark:placeholder-gray-400 dark:text-white'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today if no initial data
        if not self.data and not self.initial.get('scheduled_date'):
            from datetime import date
            self.initial['scheduled_date'] = date.today()