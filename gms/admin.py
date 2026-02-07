from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.forms import forms
from .models import (
    SiteConfiguration, BusinessUnit, Participant, Referee, Venue, 
    Event, Club, CompetitionFormat, Competition, CustomDay, Match, MatchResult, 
    Disqualification, Standings, Medal, Announcement
)
from .forms import EventForm, CompetitionForm, ParticipantForm, ClubForm
from django.core.exceptions import ValidationError
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
import json
import datetime
from datetime import datetime, time, timedelta

# Import the user admin configuration
from . import admin_user


from .forms import SiteConfigurationForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.files.storage import default_storage

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(ModelAdmin):
    """Admin interface for SiteConfiguration model."""
    form = SiteConfigurationForm
    readonly_fields = ('display_hero_images',)
    
    fieldsets = (
        ('Site Information', {
            'fields': ('site_name', 'logo', 'favicon')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'footer_text'),
            'classes': ('collapse',)
        }),
        ('Timezone', {
            'fields': ('timezone',),
            'classes': ('collapse',)
        }),

        ('Hero Slider Images', {
            'fields': ('hero_images_upload', 'display_hero_images', 'hero_images_to_remove'),
            'description': 'Upload multiple images for the hero slider section on the landing page'
        }),
    )

    class Media:
        js = ('js/admin_upload_limit.js',)

    def response_change(self, request, obj):
        # Trigger a cache clear or reload settings when SiteConfiguration is updated
        from django.core.cache import cache
        cache.delete('admin_logo_url')
        return super().response_change(request, obj)

    def display_hero_images(self, obj):
        """Display the currently uploaded hero images."""
        if not obj:
            return mark_safe('<p>No site configuration object.</p>')
        
        if not obj.hero_images:
            return mark_safe('<p style="color: #666; font-style: italic;">No hero images uploaded yet.</p>')
        
        images_html = []
        for idx, img_data in enumerate(obj.hero_images):
            img_path = img_data.get('path', '')
            caption = img_data.get('caption', '')
            alt_text = img_data.get('alt_text', '')
            
            if img_path:
                # Get the filename from the path and truncate if too long
                filename = img_path.split('/')[-1]
                display_name = caption or filename
                if len(display_name) > 20:
                    display_name = display_name[:17] + "..."
                
                # Create a div with the image and remove button
                image_html = f'''
                <div style="display: inline-block; margin: 5px; position: relative; border: 1px solid #ddd; border-radius: 4px; padding: 5px;">
                    <div style="position: relative;">
                        <img src="/media/{img_path}" alt="{alt_text}" style="max-width: 150px; max-height: 100px; object-fit: cover;">
                        <button type="button" 
                                onclick="removeHeroImage({idx})" 
                                style="position: absolute; top: -8px; right: -8px; width: 20px; height: 20px; border-radius: 50%; background: red; color: white; border: none; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;"
                                title="Remove image">
                            ×
                        </button>
                    </div>
                    <div style="font-size: 12px; margin-top: 2px; text-align: center; max-width: 150px; overflow: hidden; text-overflow: ellipsis;">
                        {display_name}
                    </div>
                </div>
                '''
                images_html.append(image_html)
        
        # Add JavaScript for removing images and handling form submission
        js_code = '''
        <script>
        // Store the indexes of images to remove
        let imagesToRemove = [];
        
        function removeHeroImage(index) {
            if (confirm('Are you sure you want to remove this image?')) {
                // Add index to the list of images to remove
                if (!imagesToRemove.includes(index)) {
                    imagesToRemove.push(index);
                    
                    // Try to find the hidden input field by ID (most reliable in Django admin)
                    var removeField = document.getElementById('id_hero_images_to_remove');
                    
                    if (removeField) {
                        removeField.value = imagesToRemove.join(',');
                        console.log("Updated remove field with:", removeField.value);
                    } else {
                        console.log("Hidden field for image removal not found!");
                    }
                    
                    // Remove the image element from the DOM completely
                    event.target.closest('div[style*="inline-block"]').remove();
                }
            }
        }
        </script>
        '''
        
        # Combine all HTML content
        all_content = ''.join(images_html) + js_code
        return mark_safe(f'<div style="display: flex; flex-wrap: wrap;">{all_content}</div>')
    
    display_hero_images.short_description = 'Current Hero Images'

    def save_model(self, request, obj, form, change):
        # Get the images to remove - try both cleaned_data and POST data
        images_to_remove_str = form.cleaned_data.get('hero_images_to_remove', '').strip()
        
        # If not found in cleaned_data, try directly from POST
        if not images_to_remove_str:
            images_to_remove_str = request.POST.get('hero_images_to_remove', '').strip()
        
        # Handle image removal first
        if images_to_remove_str:
            try:
                indices_to_remove = [int(i) for i in images_to_remove_str.split(',') if i.strip()]
                # Sort in reverse order to avoid index shifting issues when deleting
                indices_to_remove = sorted(set(indices_to_remove), reverse=True)  # Use set to remove duplicates
                
                if obj.hero_images:
                    existing_images = obj.hero_images
                    
                    for index in indices_to_remove:
                        if 0 <= index < len(existing_images):
                            # Remove the image file from storage
                            from django.core.files.storage import default_storage
                            image_path = existing_images[index]['path']
                            
                            if default_storage.exists(image_path):
                                default_storage.delete(image_path)
                            
                            # Remove from the list
                            del existing_images[index]
                    
                    obj.hero_images = existing_images
            except (ValueError, IndexError):
                # Handle any errors in index parsing
                pass
        
        # Handle multiple image uploads
        if 'hero_images_upload' in request.FILES:
            uploaded_files = request.FILES.getlist('hero_images_upload')
            existing_images = obj.hero_images or []
            
            for uploaded_file in uploaded_files:
                # Save the uploaded file
                from django.core.files.storage import default_storage
                
                # Generate unique filename
                filename = default_storage.save(f'hero_slider/{uploaded_file.name}', uploaded_file)
                
                # Add to existing images list
                existing_images.append({
                    'path': filename,
                    'caption': '',
                    'alt_text': '',
                    'order': len(existing_images)
                })
            
            obj.hero_images = existing_images
        
        super().save_model(request, obj, form, change)
        
        # If admin theme was changed, we might want to show a message
        if 'admin_theme' in form.changed_data:
            from django.contrib import messages
            messages.success(
                request, 
                f"Admin theme changed to {obj.get_admin_theme_display()}. Please refresh the page to see changes."
            )


# Base admin class with common configurations to reduce code duplication
class BaseAdmin(ModelAdmin):
    """Base admin class with common configurations."""
    exclude = ('created_by', 'updated_by')
    list_per_page = 25
    
    def get_readonly_fields(self, request, obj=None):
        """Customize readonly fields to include timestamp fields if not superuser."""
        # Always include the excluded audit fields as readonly
        readonly_fields = list(self.exclude)
        # Only add timestamps if user is not superuser
        if not request.user.is_superuser:
            readonly_fields.extend(['created_at', 'updated_at'])
        return tuple(readonly_fields)

@admin.register(BusinessUnit)
class BusinessUnitAdmin(BaseAdmin):
    """Admin interface for BusinessUnit model."""
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('name',)


# Check if Participant model is already registered with Unfold admin from admin_custom
@admin.register(Participant)
class ParticipantAdmin(BaseAdmin):
    """Custom admin for Participant model"""
    form = ParticipantForm
    list_display = ('full_name', 'employee_id', 'business_unit', 'email', 'created_at')
    list_filter = ('business_unit', 'created_at')
    search_fields = ('full_name', 'employee_id', 'email')
    ordering = ('full_name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Referee)
class RefereeAdmin(BaseAdmin):
    """Admin interface for Referee model."""
    list_display = ('full_name', 'contact_info', 'license_info', 'created_at')
    search_fields = ('full_name', 'contact_info')
    list_filter = ('created_at',)
    ordering = ('full_name',)


@admin.register(Venue)
class VenueAdmin(BaseAdmin):
    """Admin interface for Venue model."""
    list_display = ('name', 'address', 'created_at')
    search_fields = ('name', 'address')
    ordering = ('name',)


# Check if Event model is already registered with Unfold admin from admin_custom
@admin.register(Event)
class EventAdmin(BaseAdmin):
    """Custom admin for Event model with proper form field associations"""
    form = EventForm
    list_display = ('name', 'start_date', 'end_date', 'status', 'created_at')
    list_filter = ('status', 'start_date', 'end_date', 'created_at')
    search_fields = ('name',)
    ordering = ('-start_date',)
    filter_horizontal = ('coordinators',)
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Event Information', {
            'fields': ('name', 'logo', 'status')
        }),
        ('Event Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Coordinators', {
            'fields': ('coordinators',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related()


# Check if Club model is already registered with Unfold admin from admin_custom
@admin.register(Club)
class ClubAdmin(BaseAdmin):
    """Custom admin for Club model"""
    form = ClubForm
    list_display = ('name', 'managed_by', 'contact_person_name', 'created_at')
    list_filter = ('created_at', 'managed_by')
    search_fields = ('name', 'contact_person_name')
    ordering = ('name',)
    filter_horizontal = ('players',)  # Restore filter_horizontal for better UX
    
    fieldsets = (
        ('Club Information', {
            'fields': ('name', 'logo')
        }),
        ('Contact Information', {
            'fields': ('contact_person_name', 'contact_person_phone', 'contact_person_email')
        }),
        ('Management', {
            'fields': ('managed_by', 'players'),
        }),
    )


@admin.register(CompetitionFormat)
class CompetitionFormatAdmin(BaseAdmin):
    """Admin interface for CompetitionFormat model."""
    list_display = ('name', 'format_type', 'description', 'status', 'created_at')
    list_filter = ('format_type', 'status', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Format Information', {
            'fields': ('name', 'format_type', 'description', 'status')
        }),
    )


from unfold.admin import ModelAdmin, TabularInline

class CustomDayInline(TabularInline):
    """Inline admin for CustomDay model."""
    model = CustomDay
    extra = 3
    verbose_name = "Custom Day"
    verbose_name_plural = "Custom Days"
    classes = ['custom-day-inline']  # Add CSS class for targeted hiding/showing
    
    def get_queryset(self, request):
        """Optimize queryset for custom days."""
        qs = super().get_queryset(request)
        return qs.select_related('competition')  # Optimize for competition relation


class CompetitionAdmin(BaseAdmin):
    """Custom admin for Competition model"""
    form = CompetitionForm
    list_display = ('name', 'event', 'format', 'match_type', 'participant_type', 'number_of_clubs', 'number_of_participants', 'created_at')
    list_filter = ('event', 'format', 'match_type', 'participant_type', 'number_of_clubs', 'number_of_participants', 'is_league_with_groups', 'created_at')
    search_fields = ('name', 'event__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Competition Information', {
            'fields': ('name', 'event')
        }),
        ('Format Competition', {
            'fields': ('format', 'match_type', 'participant_type', 'has_third_place_match')
        }),
        ('League Configuration', {
            'fields': ('is_league_with_groups', 'number_of_groups', 'clubs_per_group'),
            'description': 'Configure league with groups. Only applicable if using league with groups.',
            'classes': ('league-config-fieldset',)
        }),
        ('Club Configuration', {
            'fields': ('number_of_clubs', 'enrolled_clubs'),
            'classes': ('clubs-config-fieldset',)
        }),
        ('Participant Configuration', {
            'fields': ('number_of_participants', 'enrolled_participants'),
            'description': 'Configure participants for individual competitions. Only applicable when participant type is Participants.',
            'classes': ('participants-config-fieldset',)
        }),
        ('Scheduling Configuration', {
            'fields': ('start_date', 'end_date', 'frequency_day', 'generate_bracket_button'),
            'description': 'Configure when matches should take place. When "Custom Days" is selected, specify exact dates in the section below.'
        }),
    )
    
    filter_horizontal = ('enrolled_clubs', 'enrolled_participants')
    inlines = [CustomDayInline]
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = (
            'admin/js/jquery.init.js',
            'admin/js/competition_format_handler.js',  # Custom JS for handling format-based fieldset visibility
            'js/admin_m2m_counter.js',
            'js/participant_type_handler.js',  # Custom JS for handling participant_type-dependent field visibility
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        return readonly_fields + ('generate_bracket_button',)

    def generate_bracket_button(self, obj):
        if obj and obj.format.format_type == 'SINGLE_ELIMINATION':
            bracket_url = reverse('gms:bracket_detail', args=[obj.id])
            return format_html('<a href="{}" target="_blank" class="bg-blue-600 text-white hover:bg-blue-700 font-bold py-2 px-4 rounded inline-flex items-center">Generate Bracket</a>', bracket_url)
        elif obj and obj.format.format_type in ['ROUND_ROBIN', 'LEAGUE']:
            schedule_url = reverse('gms:generate_round_robin_schedule', args=[obj.id])
            return format_html('<a href="{}" target="_blank" class="bg-green-600 text-white hover:bg-green-700 font-bold py-2 px-4 rounded inline-flex items-center">Generate Schedule</a>', schedule_url)
        return "-"
    generate_bracket_button.short_description = "Bracket Action"

    def _add_format_map_to_context(self, extra_context):
        """Helper to add format map to context for JS."""
        extra_context = extra_context or {}
        format_map = {f.id: f.format_type for f in CompetitionFormat.objects.all()}
        extra_context['format_map_json'] = json.dumps(format_map)
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = self._add_format_map_to_context(extra_context)
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = self._add_format_map_to_context(extra_context)
        return super().change_view(request, object_id, form_url, extra_context)

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('event', 'format')
    
    def save_formset(self, request, form, formset, change):
        """Validate CustomDay instances to ensure dates are within the range."""
        instances = formset.save(commit=False)
        
        competition = form.instance
        
        for instance in instances:
            if isinstance(instance, CustomDay):
                if not instance.competition_id:
                    instance.competition = competition
                instance.clean()
            
        formset.save_m2m()
        for instance in instances:
            instance.save()


class MatchResultInline(TabularInline):
    """Inline admin for MatchResult model."""
    model = MatchResult
    extra = 1
    verbose_name = "Match Result"
    verbose_name_plural = "Match Results"


@admin.register(Match)
class MatchAdmin(BaseAdmin):
    """Admin interface for Match model."""
    list_display = ('id', 'competition', 'home_team_name', 'away_team_name', 'scheduled_time', 'venue', 'status', 'round_number', 'group_number', 'bracket_type')
    list_filter = ('status', 'competition__event', 'competition', 'venue', 'round_number', 'bracket_type', 'group_number', 'scheduled_time', 'created_at')
    search_fields = ('competition__name', 'venue__name', 'home_team__name', 'away_team__name')
    ordering = ('-scheduled_time',)
    date_hierarchy = 'scheduled_time'
    filter_horizontal = ('referees',)
    
    fieldsets = (
        ('Match Information', {
            'fields': ('competition', 'round_number', 'bracket_type', 'group_number')
        }),
        ('Teams', {
            'fields': ('home_team', 'away_team'),
        }),
        ('Scheduling', {
            'fields': ('scheduled_time', 'venue', 'status'),
        }),
        ('Additional', {
            'fields': ('referees', 'streaming_link'),
            'classes': ('collapse',)
        }),
    )

    def home_team_name(self, obj):
        return obj.home_team.name if obj.home_team else "TBD"
    home_team_name.short_description = "Home Team"
    home_team_name.admin_order_field = 'home_team__name'

    def away_team_name(self, obj):
        return obj.away_team.name if obj.away_team else "TBD"
    away_team_name.short_description = "Away Team"
    away_team_name.admin_order_field = 'away_team__name'

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('competition', 'venue', 'home_team', 'away_team')


@admin.register(MatchResult)
class MatchResultAdmin(BaseAdmin):
    """Admin interface for MatchResult model."""
    list_display = ('match', 'club', 'outcome', 'score', 'created_at')
    list_filter = ('outcome', 'score', 'match__competition__event', 'match__competition', 'created_at')
    search_fields = ('match__id', 'club__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Match Result Information', {
            'fields': ('match', 'club', 'outcome', 'score', 'result_data')
        }),
        ('Documentation', {
            'fields': ('documentation_file',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('match', 'club')


@admin.register(Disqualification)
class DisqualificationAdmin(BaseAdmin):
    """Admin interface for Disqualification model."""
    list_display = ('participant', 'get_event_name', 'get_competition_name', 'reason', 'is_active', 'start_date', 'end_date')
    list_filter = ('is_active', 'start_date', 'end_date', 'event', 'competition')
    search_fields = ('participant__full_name', 'reason')
    ordering = ('-start_date',)
    
    def get_event_name(self, obj):
        return obj.event.name if obj.event else "-"
    get_event_name.short_description = 'Event'
    
    def get_competition_name(self, obj):
        return obj.competition.name if obj.competition else "-"
    get_competition_name.short_description = 'Competition'


@admin.register(Standings)
class StandingsAdmin(BaseAdmin):
    """Admin interface for Standings model."""
    list_display = ('competition', 'club', 'points', 'played', 'wins', 'draws', 'losses', 'updated_at')
    list_filter = ('competition__event', 'competition', 'updated_at')
    search_fields = ('club__name', 'competition__name')
    ordering = ('competition', '-points')
    
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('competition', 'club')


@admin.register(Medal)
class MedalAdmin(BaseAdmin):
    """Admin interface for Medal model."""
    list_display = ('event', 'competition', 'club', 'medal_type', 'created_at')
    list_filter = ('medal_type', 'event', 'competition', 'created_at')
    search_fields = ('club__name', 'competition__name', 'event__name')
    ordering = ('event', 'competition', 'medal_type')
    
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('event', 'competition', 'club')


@admin.register(Announcement)
class AnnouncementAdmin(BaseAdmin):
    """Admin interface for Announcement model."""
    list_display = ('title', 'event', 'created_at')
    list_filter = ('event', 'created_at')
    search_fields = ('title', 'content', 'event__name')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Announcement Information', {
            'fields': ('event', 'title')
        }),
        ('Content', {
            'fields': ('content',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)
        return qs.select_related('event')


# Register CompetitionAdmin for the default admin site
# This was previously done with @admin.register, but had to be moved due to dependency issues
admin.site.register(Competition, CompetitionAdmin)

@admin.register(CustomDay)
class CustomDayAdmin(BaseAdmin):
    """Admin interface for CustomDay model."""
    list_display = ('competition', 'date', 'created_at')
    list_filter = ('competition', 'date', 'created_at')
    search_fields = ('competition__name', 'date')
    ordering = ('-date',)
    date_hierarchy = 'date'
    
    # Filter competition dropdown to show only competitions with CUSTOM frequency
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "competition":
            # Only show competitions with CUSTOM frequency
            kwargs["queryset"] = Competition.objects.filter(frequency_day='CUSTOM')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
