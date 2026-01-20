(function($) {
    $(document).ready(function() {
        // Parse the format map from the data attribute
        var formatMap = {};
        try {
            formatMap = JSON.parse($('#format_map_data').text());
        } catch (e) {
            console.error("Could not parse format map data.");
        }

        // Function to clear participant type specific data when switching types
        function clearParticipantTypeData() {
            var selectedParticipantType = $('#id_participant_type').val();
            
            if (selectedParticipantType === 'CLUBS') {
                // If switching to CLUBS, clear participants fields and their M2M selections
                $('#id_enrolled_participants_to option').prop('selected', false);
                $('#id_enrolled_participants_from option').prop('selected', false);
                
                // Clear any selected values in the "to" box and move them back to "from"
                $('#id_enrolled_participants_to option').each(function() {
                    var option = $(this);
                    $('#id_enrolled_participants_from').append(option);
                });
                
                // Update the counter if it exists
                if (typeof updateCounts !== 'undefined') {
                    updateCounts();
                }
            } else if (selectedParticipantType === 'PARTICIPANTS') {
                // If switching to PARTICIPANTS, clear clubs fields and their M2M selections
                $('#id_enrolled_clubs_to option').prop('selected', false);
                $('#id_enrolled_clubs_from option').prop('selected', false);
                
                // Clear any selected values in the "to" box and move them back to "from" 
                $('#id_enrolled_clubs_to option').each(function() {
                    var option = $(this);
                    $('#id_enrolled_clubs_from').append(option);
                });
                
                // Update the counter if it exists
                if (typeof updateCounts !== 'undefined') {
                    updateCounts();
                }
            }
        }

        // Function to handle the display of league configuration fieldset
        function handleLeagueConfigVisibility() {
            var selectedFormatId = $('#id_format').val();
            var selectedFormatType = formatMap[selectedFormatId]; // Look up the type from the map
            var leagueConfigFieldset = $('.league-config-fieldset');

            if (selectedFormatType === 'LEAGUE' || selectedFormatType === 'ROUND_ROBIN') {
                leagueConfigFieldset.show();
            } else {
                leagueConfigFieldset.hide();
            }
        }

        function handleCustomDaysVisibility() {
            var selectedFrequency = $('#id_frequency_day').val();
            var customDaysInline = $('.custom-day-inline'); // Target the inline by its class

            if (selectedFrequency === 'CUSTOM') {
                customDaysInline.show();
            } else {
                customDaysInline.hide();
            }
        }

        // Function to handle the display of club/participant configuration fieldsets
        function handleParticipantTypeVisibility() {
            var selectedParticipantType = $('#id_participant_type').val();
            var clubsConfigFieldset = $('.clubs-config-fieldset');
            var participantsConfigFieldset = $('.participants-config-fieldset');

            if (selectedParticipantType === 'CLUBS') {
                clubsConfigFieldset.show();
                clubsConfigFieldset.removeClass('collapse');
                participantsConfigFieldset.hide();
                participantsConfigFieldset.addClass('collapse');
            } else if (selectedParticipantType === 'PARTICIPANTS') {
                participantsConfigFieldset.show();
                participantsConfigFieldset.removeClass('collapse');
                clubsConfigFieldset.hide();
                clubsConfigFieldset.addClass('collapse');
            } else {
                clubsConfigFieldset.hide();
                clubsConfigFieldset.addClass('collapse');
                participantsConfigFieldset.hide();
                participantsConfigFieldset.addClass('collapse');
            }
        }

        // ... (rest of the functions remain the same)

        // Initial check when page loads
        handleLeagueConfigVisibility();
        handleParticipantTypeVisibility();
        handleCustomDaysVisibility();

        // ... (rest of the event handlers remain the same)

        // Re-check when the format selection changes
        $('#id_format').change(function() {
            handleLeagueConfigVisibility();
        });

        $('#id_frequency_day').change(function() {
            handleCustomDaysVisibility();
        });

        $('#id_participant_type').change(function() {
            clearParticipantTypeData();
            handleParticipantTypeVisibility();
        });

        // --- Add sequence numbers to filter_horizontal widgets ---
        function renumberOptions(selector) {
            $(selector).find('option').each(function(index) {
                var option = $(this);
                var originalText = option.text().replace(/^\d+\.\s*/, '');
                option.text((index + 1) + '. ' + originalText);
            });
        }

        function applySequencing(fieldName) {
            var fromBox = '#' + fieldName + '_from';
            var toBox = '#' + fieldName + '_to';
            var controls = $(fromBox).closest('.selector').find('.selector-chooser a');

            // Initial numbering
            renumberOptions(fromBox);
            renumberOptions(toBox);

            // Re-number on click of the controls
            controls.on('click', function() {
                // Use a short timeout to ensure this runs after Django's own JS moves the items
                setTimeout(function() {
                    renumberOptions(fromBox);
                    renumberOptions(toBox);
                }, 50);
            });
        }

        // Apply the sequencing to both filter_horizontal widgets
        applySequencing('id_enrolled_clubs');
        applySequencing('id_enrolled_participants');
    });
})(django.jQuery);