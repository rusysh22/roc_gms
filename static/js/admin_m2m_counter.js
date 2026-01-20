(function($) {
    $(document).ready(function() {
        function setupCounterWhenReady(fieldId) {
            let attempts = 0;
            const maxAttempts = 30; // Try for up to 7.5 seconds (30 * 250ms)
            
            const interval = setInterval(function() {
                attempts++;
                const $fromBox = $(`#${fieldId}_from`);
                const $toBox = $(`#${fieldId}_to`);

                // Check if the SelectFilter boxes have been created by Django's JS yet
                if ($fromBox.length && $toBox.length) {
                    clearInterval(interval); // Stop polling, we found the elements

                    // Find existing header elements to avoid duplication
                    let $fromHeader = $fromBox.closest('.selector-available').find('h2, h3, .selector-available label, .selector-filter').first();
                    if ($fromHeader.length === 0) {
                        $fromHeader = $fromBox.parent().find('h2, h3, label').first();
                    }
                    
                    let $toHeader = $toBox.closest('.selector-chosen').find('h2, h3, .selector-chosen label, .selector-filter').first();
                    if ($toHeader.length === 0) {
                        $toHeader = $toBox.parent().find('h2, h3, label').first();
                    }

                    // Prevent duplicate counters by checking if they already exist
                    if ($fromHeader.find('.counter-badge').length === 0) {
                        // Create counter elements with improved Tailwind classes for Unfold theme
                        const $fromCounter = $('<span class="counter-badge bg-gray-200 text-gray-800 text-xs font-medium px-2.5 py-0.5 rounded-full ml-2 dark:bg-gray-600 dark:text-gray-200">0 items</span>');
                        $fromHeader.append($fromCounter);
                    }
                    
                    if ($toHeader.find('.counter-badge').length === 0) {
                        const $toCounter = $('<span class="counter-badge bg-indigo-100 text-indigo-800 text-xs font-medium px-2.5 py-0.5 rounded-full ml-2 dark:bg-indigo-700 dark:text-indigo-100">0 items</span>');
                        $toHeader.append($toCounter);
                    }
                    
                    // Get the counter elements that were just added or already existed
                    const $fromCounter = $fromHeader.find('.counter-badge').first();
                    const $toCounter = $toHeader.find('.counter-badge').first();

                    // Add classes to enable flexbox alignment if needed
                    if (!$fromHeader.hasClass('flex') && !$fromHeader.parent().hasClass('flex')) {
                        $fromHeader.addClass('flex items-center');
                    }
                    if (!$toHeader.hasClass('flex') && !$toHeader.parent().hasClass('flex')) {
                        $toHeader.addClass('flex items-center');
                    }

                    function updateCounts() {
                        const fromCount = $fromBox.find('option').length;
                        const toCount = $toBox.find('option').length;
                        $fromCounter.text(`${fromCount} items`);
                        $toCounter.text(`${toCount} items`);
                    }

                    // Initial count after a small delay to ensure everything is loaded
                    setTimeout(updateCounts, 300);

                    // Patch the original SelectBox functions to update counts after items are moved.
                    // This is the correct way for widgets with the 'selectfilter' class.
                    const originalMove = window.SelectBox ? window.SelectBox.move : null;
                    if (originalMove) {
                        window.SelectBox.move = function(from, to) {
                            originalMove.apply(this, arguments);
                            setTimeout(updateCounts, 10); // Small delay to ensure DOM updates
                        };
                    }

                    const originalMoveAll = window.SelectBox ? window.SelectBox.move_all : null;
                    if (originalMoveAll) {
                        window.SelectBox.move_all = function(from, to) {
                            originalMoveAll.apply(this, arguments);
                            setTimeout(updateCounts, 10); // Small delay to ensure DOM updates
                        };
                    }

                    // Also patch the filter function to update counts when searching
                    const originalFilter = window.SelectBox ? window.SelectBox.filter : null;
                    if (originalFilter) {
                        window.SelectBox.filter = function(id, text) {
                            originalFilter.apply(this, arguments);
                            // We need a delay for the DOM to update after filtering
                            setTimeout(updateCounts, 50);
                        };
                    }
                } else if (attempts >= maxAttempts) {
                    // Stop trying after max attempts
                    clearInterval(interval);
                }
            }, 250); // Poll every 250ms for the elements to appear
        }

        // Wait for the page to fully load and admin widgets to be initialized
        $(window).on('load', function() {
            setTimeout(function() {
                setupCounterWhenReady('id_enrolled_clubs');
                setupCounterWhenReady('id_enrolled_participants');
            }, 1000); // Wait 1 second after page load
        });
        
        // Also try without waiting for window load in case that's too late
        setTimeout(function() {
            setupCounterWhenReady('id_enrolled_clubs');
            setupCounterWhenReady('id_enrolled_participants');
        }, 1500);
    });
})(django.jQuery);