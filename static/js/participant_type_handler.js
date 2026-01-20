(function($) {
    $(document).ready(function() {
        function updateEnrolledFieldVisibility() {
            const participantType = $('#id_participant_type').val();
            
            if (participantType === 'PARTICIPANTS') {
                // Show enrolled_participants, hide enrolled_clubs
                $('.form-row.field-enrolled_clubs, div.field-enrolled_clubs').closest('.form-row').hide();
                $('.form-row.field-enrolled_participants, div.field-enrolled_participants').closest('.form-row').show();
            } else {
                // Show enrolled_clubs, hide enrolled_participants
                $('.form-row.field-enrolled_clubs, div.field-enrolled_clubs').closest('.form-row').show();
                $('.form-row.field-enrolled_participants, div.field-enrolled_participants').closest('.form-row').hide();
            }
        }

        // Function to wait for elements and apply visibility
        function waitForElementsAndApply() {
            let attempts = 0;
            const maxAttempts = 30; // Try for up to 7.5 seconds (30 * 250ms)
            
            const checkAndApply = function() {
                attempts++;
                
                // Check if both participant_type and enrolled fields exist
                const participantTypeSelect = $('#id_participant_type');
                const hasParticipantType = participantTypeSelect.length > 0;
                const hasEnrolledClubs = $('.form-row.field-enrolled_clubs, .field-enrolled_clubs').length > 0;
                const hasEnrolledParticipants = $('.form-row.field-enrolled_participants, .field-enrolled_participants').length > 0;
                
                if (hasParticipantType && hasEnrolledClubs && hasEnrolledParticipants) {
                    // Apply visibility based on current participant_type value
                    updateEnrolledFieldVisibility();
                    
                    // Set up change event listener
                    participantTypeSelect.off('change.participantTypeHandler').on('change.participantTypeHandler', function() {
                        updateEnrolledFieldVisibility();
                    });
                    
                    return; // Stop checking since elements are found
                }
                
                if (attempts < maxAttempts) {
                    setTimeout(checkAndApply, 250); // Check again in 250ms
                } else {
                    // If we've exhausted attempts, at least try to set up the event if participant type exists
                    if (hasParticipantType) {
                        participantTypeSelect.off('change.participantTypeHandler').on('change.participantTypeHandler', function() {
                            updateEnrolledFieldVisibility();
                        });
                    }
                }
            };
            
            checkAndApply();
        }

        // Start checking immediately, then again after window load
        waitForElementsAndApply();
        
        $(window).on('load', function() {
            setTimeout(waitForElementsAndApply, 500); // Additional check after full load
        });
    });
})(django.jQuery);