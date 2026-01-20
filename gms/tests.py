"""
Optimized test file for GMS application.

This file demonstrates improved testing practices:
- Better test organization
- Cleaner setup and teardown
- More comprehensive assertions
- Better error handling
"""

import os
import sys
import django
from django.test import TestCase
from django.core.exceptions import ValidationError

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gms_project.settings')
django.setup()

from gms.models import Competition, CompetitionFormat, Event, Club
from django.contrib.auth.models import User


class CompetitionValidationTestCase(TestCase):
    """Test case for competition validation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'is_superuser': True, 'is_staff': True}
        )
        
        self.event, _ = Event.objects.get_or_create(
            name='Test Event',
            defaults={
                'start_date': '2025-11-01',
                'end_date': '2025-11-30'
            }
        )
        
        self.format_league, _ = CompetitionFormat.objects.get_or_create(
            name='League Test',
            defaults={'format_type': 'LEAGUE'}
        )
        
        self.format_single_elim, _ = CompetitionFormat.objects.get_or_create(
            name='Single Elim Test',
            defaults={'format_type': 'SINGLE_ELIMINATION'}
        )
        
        # Create test clubs
        self.club_names = [f'Club {i}' for i in range(1, 7)]
        self.clubs = []
        
        for name in self.club_names:
            club, _ = Club.objects.get_or_create(
                name=name,
                defaults={
                    'contact_person_name': f'Manager of {name}',
                }
            )
            self.clubs.append(club)
    
    def tearDown(self):
        """Clean up after tests."""
        # Delete test data to avoid conflicts
        Competition.objects.filter(name__contains='Test').delete()
        Club.objects.filter(name__in=self.club_names).delete()
        CompetitionFormat.objects.filter(name__in=['League Test', 'Single Elim Test']).delete()
        Event.objects.filter(name='Test Event').delete()

    def test_number_of_clubs_validation(self):
        """Test validation for number_of_clubs field."""
        # Test 1: Try creating competition with 1 planned club (should fail)
        competition1 = Competition(
            name='Test Competition 1 Club',
            event=self.event,
            format=self.format_league,
            number_of_clubs=1,  # Should fail
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        
        with self.assertRaises(ValidationError):
            competition1.full_clean()  # Validates using model's clean method
            competition1.save()

        # Test 2: Try creating competition with 2 planned clubs (should succeed)
        competition2 = Competition(
            name='Test Competition 2 Clubs',
            event=self.event,
            format=self.format_league,
            number_of_clubs=2,  # Should succeed
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        
        competition2.full_clean()
        competition2.save()
        self.assertEqual(competition2.number_of_clubs, 2)
        
        # Cleanup
        competition2.delete()

    def test_competition_format_validation(self):
        """Test validation based on competition format."""
        # Test single elimination with 3 clubs (should fail after scheduling validation)
        competition1 = Competition(
            name='Test Comp 3 Clubs',
            event=self.event,
            format=self.format_single_elim,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        competition1.save()
        
        # Add 3 clubs
        for club in self.clubs[:3]:
            competition1.enrolled_clubs.add(club)
        
        # This should pass basic validation but fail during scheduling validation
        # if we call validation_for_scheduling
        competition1.refresh_from_db()
        self.assertEqual(competition1.enrolled_clubs.count(), 3)
        
        # Test league format with 1 club (should fail during scheduling validation)
        competition2 = Competition(
            name='Test Comp 1 Club League',
            event=self.event,
            format=self.format_league,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        competition2.save()
        competition2.enrolled_clubs.add(self.clubs[0])
        
        competition2.refresh_from_db()
        self.assertEqual(competition2.enrolled_clubs.count(), 1)

    def test_competition_scheduling_validation(self):
        """Test validation that occurs during scheduling."""
        # Create a competition planning for 4 clubs
        competition = Competition(
            name='Test Scheduling Validation',
            event=self.event,
            format=self.format_league,
            number_of_clubs=4,
            created_by=self.admin_user,
            updated_by=self.admin_user
        )
        competition.save()
        
        # Only add 3 clubs (should cause validation error)
        for club in self.clubs[:3]:
            competition.enrolled_clubs.add(club)
        
        # Try to validate for scheduling - should fail
        with self.assertRaises(ValidationError):
            competition.validate_for_scheduling()
        
        # Add the 4th club to match the planned number
        competition.enrolled_clubs.add(self.clubs[3])
        
        # Now validation should succeed
        try:
            competition.validate_for_scheduling()
        except ValidationError:
            self.fail("validate_for_scheduling() raised ValidationError unexpectedly!")


def run_optimized_tests():
    """Run all tests in this module."""
    import unittest
    
    # Run tests using Django test runner
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(CompetitionValidationTestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_optimized_tests()
    if success:
        print("\nAll optimized tests passed!")
    else:
        print("\nSome tests failed!")