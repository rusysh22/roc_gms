// Comprehensive approach to ensure both the button appears and Custom Days toggle properly with Unfold Admin
(function($) {
    // Main function to run when the document is ready
    function initCompetitionAdmin() {
        // Check if we're on the Competition change form page (not add page)
        var path = window.location.pathname;
        var isCompetitionChangePage = path.includes('/admin/gms/competition/') && 
            /\d+\/change\/?$/.test(path) && 
            !path.includes('/add/');
        
        // Check if we're on the Competition add form page
        var isCompetitionAddPage = path.includes('/admin/gms/competition/add/');
        
        // Check if there's a parameter to auto-generate schedule
        var urlParams = new URLSearchParams(window.location.search);
        var shouldAutoGenerate = urlParams.has('generate_schedule');
        
        // Run for both change and add pages
        if (isCompetitionChangePage || isCompetitionAddPage) {
            console.log("Competition page detected (add or change), initializing features");
            
            // Function to show/hide Custom Days based on frequency_day value
            function toggleCustomDays() {
                var selectedValue = $('#id_frequency_day').val();
                console.log("Frequency day value changed to:", selectedValue);
                
                // Hide all custom-day-inline elements by default
                $('.custom-day-inline, #customday_set-group, #customday_inline-group').hide();
                
                // Only show if 'CUSTOM' is selected
                if (selectedValue === 'CUSTOM') {
                    console.log("Showing custom day inline elements");
                    $('.custom-day-inline, #customday_set-group, #customday_inline-group').show();
                } else {
                    console.log("Hiding custom day inline elements");
                }
            }
            
            // Wait for DOM to be fully ready and Unfold to initialize
            $(window).on('load', function() {
                console.log("Window loaded, setting up Competition Admin");
                
                // Wait a bit more for any dynamic loading by Unfold
                setTimeout(function() {
                    console.log("Setting up initial state for Competition Admin");
                    
                    // Hide custom days by default
                    $('.custom-day-inline, #customday_set-group, #customday_inline-group').hide();
                    
                    // Check the current value and show/hide accordingly
                    var currentValue = $('#id_frequency_day').val();
                    console.log("Initial frequency day value:", currentValue);
                    if (currentValue && currentValue === 'CUSTOM') {
                        $('.custom-day-inline, #customday_set-group, #customday_inline-group').show();
                    }
                    
                    // Add the generate schedule button only for change page (not add page)
                    if (isCompetitionChangePage) {
                        addGenerateScheduleButton();
                    }
                    
                    // Set up the change event for frequency day
                    $('#id_frequency_day').off('change.customDayToggle').on('change.customDayToggle', function() {
                        toggleCustomDays();
                    });
                    
                    // Trigger the toggle function in case the value was already CUSTOM
                    toggleCustomDays();
                    
                    // Auto-generate schedule if parameter is present (only on change page)
                    if (shouldAutoGenerate && isCompetitionChangePage) {
                        console.log("Auto-generating schedule based on URL parameter");
                        // Confirm before auto-generating
                        if (confirm("Competition saved successfully! Would you like to generate the match schedule now?")) {
                            // Find the generate schedule button and click it programmatically
                            $('#generate-schedule-btn').click();
                        }
                    }
                }, 1000); // Longer delay to ensure Unfold components are fully loaded
            });
        }
    }
    
    // Function to add the generate schedule button - compatible with Unfold Admin
    function addGenerateScheduleButton() {
        // Check again if button already exists to prevent duplicates
        if ($('#generate-schedule-btn').length === 0) {
            console.log("Adding generate schedule button for Unfold Admin");
            
            // Create a prominent button element and make it stick to top
            var buttonHtml = '<div id="competition-generate-section" class="mt-4 p-4 border border-blue-500 rounded-lg bg-white text-blue-900 max-w-full shadow-lg sticky top-10 z-10000" style="border: 2px solid #3b82f6; background-color: white; color: #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -1px rgba(0,0,0,0.06);">' +
                '<h3 class="mb-2 text-lg font-bold text-blue-800" style="margin-top: 0; margin-bottom: 10px; color: #1e40af; font-size: 1.2em; font-weight: bold;">Generate Match Schedule</h3>' +
                '<button id="generate-schedule-btn" class="bg-blue-600 text-white border-none py-3 px-6 rounded-lg cursor-pointer text-base font-bold shadow hover:bg-blue-700 transition-colors mr-4" style="background-color: #2563eb; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: 600; margin-right: 15px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.1),0 1px 2px 0 rgba(0,0,0,0.06);">Generate Schedule</button>' +
                '<p class="mt-2 text-gray-600 text-sm" style="margin-top: 10px; color: #374151; font-size: 0.9em;">Automatically create match schedule based on competition settings</p>' +
                '</div>';
            
            // Try multiple selectors to find the right place for Unfold Admin
            var targetElement = null;
            
            // First, try to add to the placeholder in the template
            var placeholder = $('#competition-generate-section-placeholder');
            if(placeholder.length > 0) {
                placeholder.html(buttonHtml).show();
                targetElement = placeholder;
            }
            
            // If placeholder not found, try to find the main content area in Unfold
            if(!targetElement) {
                // For Unfold Admin, look for common selectors
                var unfoldContent = $('.content, #content, .container, .form-section, .form-container');
                if(unfoldContent.length > 0) {
                    targetElement = unfoldContent.first();
                    targetElement.prepend(buttonHtml);
                }
            }
            
            // If still not found, try the form element
            if(!targetElement) {
                var formElement = $('form');
                if(formElement.length > 0) {
                    formElement.prepend(buttonHtml);
                    targetElement = formElement;
                }
            }
            
            // If still not found, add to body as last resort
            if(!targetElement) {
                $('body').append(buttonHtml);
            }
            
            // Handle the click event
            $('#generate-schedule-btn').click(function() {
                if (!confirm("Are you sure you want to generate a new schedule? This will create matches based on the competition settings and may overwrite existing matches.")) {
                    return;
                }
                
                var path = window.location.pathname;
                var pathParts = path.split('/');
                var competitionId = null;
                
                // Find the competition ID in the URL path
                for(var i = 0; i < pathParts.length; i++) {
                    if(/^\d+$/.test(pathParts[i]) && pathParts[i-1] === 'competition') {
                        competitionId = pathParts[i];
                        break;
                    }
                }
                
                if(competitionId) {
                    window.location.href = window.location.origin + '/admin/gms/competition/' + competitionId + '/generate_schedule/';
                } else {
                    alert('Could not identify competition ID. Please try saving the competition first.');
                }
            });
            
            console.log("Generate schedule button added successfully");
        } else {
            console.log("Generate schedule button already exists");
        }
    }
    
    // Run the initialization when DOM is ready
    $(document).ready(function() {
        console.log("Document ready, initializing competition admin features for Unfold");
        
        // Initialize immediately
        initCompetitionAdmin();
        
        // Also run after a delay as backup for dynamically loaded content
        setTimeout(initCompetitionAdmin, 2000);
    });
    
})(django.jQuery);

// Comprehensive fix for accessibility issues with labels and form elements
function fixLabelForIssues() {
    // Fix label-for mismatches by creating proper associations
    const labels = document.querySelectorAll('label[for]');
    labels.forEach(function(label) {
        const targetId = label.getAttribute('for');
        const targetElement = document.getElementById(targetId);
        
        // If the target element doesn't exist, look for elements with matching name attribute
        if (!targetElement) {
            const nameBasedElements = document.querySelectorAll(`[name="${targetId}"]`);
            if (nameBasedElements.length > 0) {
                // Update the label's for attribute to match the actual IDs
                const actualId = nameBasedElements[0].id || nameBasedElements[0].name;
                if (actualId && nameBasedElements[0].id !== targetId) {
                    label.setAttribute('for', actualId);
                    console.log('Fixed label-for mismatch:', targetId, '->', actualId);
                }
            }
        }
    });
    
    // Ensure all inputs have proper IDs for accessibility
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(function(input) {
        if (!input.id) {
            // Generate a unique ID if one doesn't exist
            const uniqueId = 'auto-generated-id-' + Date.now() + '-' + Math.floor(Math.random() * 1000000);
            input.id = uniqueId;
            
            // Look for a nearby label that might be associated with this input
            const parent = input.closest('.form-row, .field-box, .form-group');
            if (parent) {
                const label = parent.querySelector('label');
                if (label && !label.getAttribute('for')) {
                    label.setAttribute('for', uniqueId);
                }
            }
        }
    });
    
    // Fix for any custom days related elements that might have label issues
    const customDayInputs = document.querySelectorAll('.custom-day-inline input[type="date"], #customday_set-group input[type="date"], #customday_inline-group input[type="date"]');
    customDayInputs.forEach(function(input, index) {
        if (!input.id) {
            input.id = 'custom-day-date-' + index;
        }
        
        // If there's a related label without a for attribute, connect them
        const relatedLabel = input.parentNode.querySelector('label');
        if (relatedLabel && !relatedLabel.getAttribute('for')) {
            relatedLabel.setAttribute('for', input.id);
        }
    });
    
    // Special fix for Django admin inline formsets which often have label issues
    const inlineForms = document.querySelectorAll('.inline-related');
    inlineForms.forEach(function(inlineForm) {
        const inputs = inlineForm.querySelectorAll('input, select, textarea');
        inputs.forEach(function(input) {
            if (!input.id) {
                const uniqueId = 'inline-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                input.id = uniqueId;
                
                // Look for label inside the same inline form
                const label = inlineForm.querySelector(`label[for="${input.name}"]`);
                if (label) {
                    label.setAttribute('for', uniqueId);
                }
            }
        });
    });
}

// Run the fix when document is loaded and after a delay to ensure all elements are rendered
document.addEventListener('DOMContentLoaded', function() {
    // First run when DOM is loaded
    fixLabelForIssues();
    
    // Run again after a delay to ensure Django/Unfold dynamic elements are loaded
    setTimeout(fixLabelForIssues, 1000);
    setTimeout(fixLabelForIssues, 3000); // Additional timeout to handle any dynamic loading
    
    // Also run the fix when any new content is added to the page
    const observer = new MutationObserver(function(mutations) {
        let shouldRunFix = false;
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                shouldRunFix = true;
            }
        });
        
        if (shouldRunFix) {
            setTimeout(fixLabelForIssues, 500); // Small delay to let elements fully render
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Prevent any dynamic CSS injection that might cause the error
document.addEventListener('DOMContentLoaded', function() {
    // Ensure no link elements with malformed href attributes are added
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.tagName === 'LINK' && node.href && 
                        (node.href === window.location.origin + '/admin/' || 
                        node.href === window.location.origin + '/admin' ||
                        node.href.endsWith('/admin/') ||
                        node.href.endsWith('/admin'))) {
                        console.warn('Prevented insertion of malformed CSS link:', node);
                        if (node.parentNode) {
                            node.parentNode.removeChild(node);
                        }
                    }
                });
            }
        });
    });
    
    observer.observe(document.head, {
        childList: true,
        subtree: true
    });
});

// Additional comprehensive fix that runs periodically to address persistent issues
setInterval(function() {
    fixLabelForIssues();
}, 5000); // Run every 5 seconds to catch any dynamically added elements with label issues

// Final check after everything is loaded
window.addEventListener('load', function() {
    setTimeout(function() {
        fixLabelForIssues();
        console.log('Final accessibility check completed');
    }, 5000);
});