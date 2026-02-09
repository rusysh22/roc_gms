/* Homepage specific JS extracted from homepage.html */

document.addEventListener('DOMContentLoaded', function () {
    // Month navigation functionality
    const monthCalendars = document.querySelectorAll('.month-calendar');
    const prevButton = document.getElementById('prev-month');
    const nextButton = document.getElementById('next-month');
    const monthDisplay = document.querySelector('.current-month-display');
    let currentMonthIndex = 0;

    // Month Data is expected to be defined in homepage.html via a script tag
    // window.homepageMonthData = [...]

    function showMonth(index) {
        // Hide all calendars
        monthCalendars.forEach(calendar => {
            calendar.style.display = 'none';
        });

        // Show current calendar
        if (monthCalendars[index]) {
            monthCalendars[index].style.display = 'block';

            // Update month display
            if (window.homepageMonthData && window.homepageMonthData[index]) {
                monthDisplay.textContent = window.homepageMonthData[index].month_name + ' ' + window.homepageMonthData[index].year;
            }
        }

        // Update button states
        if (prevButton && nextButton) {
            prevButton.disabled = (index <= 0);
            nextButton.disabled = (index >= monthCalendars.length - 1);

            // Update button visual state for disabled
            if (index <= 0) {
                prevButton.classList.add('opacity-50', 'cursor-not-allowed');
                prevButton.classList.remove('hover:bg-gray-300', 'dark:hover:bg-gray-600');
            } else {
                prevButton.classList.remove('opacity-50', 'cursor-not-allowed');
                prevButton.classList.add('hover:bg-gray-300', 'dark:hover:bg-gray-600');
            }

            if (index >= monthCalendars.length - 1) {
                nextButton.classList.add('opacity-50', 'cursor-not-allowed');
                nextButton.classList.remove('hover:bg-gray-300', 'dark:hover:bg-gray-600');
            } else {
                nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
                nextButton.classList.add('hover:bg-gray-300', 'dark:hover:bg-gray-600');
            }
        }
    }

    // Show initial month if we have calendars
    if (monthCalendars.length > 0) {
        showMonth(currentMonthIndex);
    }

    // Next button event
    if (nextButton) {
        nextButton.addEventListener('click', function () {
            if (currentMonthIndex < monthCalendars.length - 1) {
                currentMonthIndex++;
                showMonth(currentMonthIndex);
            }
        });
    }

    // Previous button event  
    if (prevButton) {
        prevButton.addEventListener('click', function () {
            if (currentMonthIndex > 0) {
                currentMonthIndex--;
                showMonth(currentMonthIndex);
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
    // Hero Slider Functionality - Auto sliding only
    const slider = document.getElementById('heroSlider');
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.slide-dot');
    const captions = document.querySelectorAll('.slide-caption');

    let currentSlide = 0;
    let slideInterval;

    function showSlide(n) {
        // Hide all slides and captions
        slides.forEach(slide => slide.classList.remove('active'));
        if (dots.length > 0) {
            dots.forEach(dot => dot.classList.remove('active'));
        }
        captions.forEach(caption => caption.classList.add('hidden'));

        // Calculate new slide index
        if (slides.length > 0) {
            currentSlide = (n + slides.length) % slides.length;

            // Show the selected slide
            if (slides[currentSlide]) {
                slides[currentSlide].classList.add('active');
            }

            // Update active dot if dots exist
            if (dots.length > 0 && dots[currentSlide]) {
                dots[currentSlide].classList.add('active');
            }

            // Show corresponding caption
            if (captions[currentSlide]) {
                captions[currentSlide].classList.remove('hidden');
            }
        }
    }

    function nextSlide() {
        showSlide(currentSlide + 1);
    }

    // Start automatic slideshow
    function startSlideShow() {
        if (slides.length > 1) { // Only start if we have more than 1 slide
            slideInterval = setInterval(nextSlide, 5000); // Change slide every 5 seconds
        }
    }

    // Stop automatic slideshow (on hover)
    function stopSlideShow() {
        clearInterval(slideInterval);
    }

    // Initialize the slider
    if (slider && slides.length > 0) {
        showSlide(currentSlide);
        startSlideShow();

        // Add mouse events to pause/resume slideshow
        slider.addEventListener('mouseenter', stopSlideShow);
        slider.addEventListener('mouseleave', startSlideShow);
    }

    // Scroll animations
    const animatedElements = document.querySelectorAll('.scroll-animate');

    if (animatedElements.length > 0 && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });

        animatedElements.forEach(el => {
            observer.observe(el);
        });
    }

    // Stats counter animation
    const counters = document.querySelectorAll('.stats-counter');
    if (counters.length > 0 && 'IntersectionObserver' in window) {
        const observer2 = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const target = entry.target;
                    const text = target.textContent;
                    const isNumeric = /\d/.test(text);

                    if (isNumeric) {
                        const finalValue = text.replace(/[^\d]/g, '');
                        let current = 0;
                        const increment = finalValue / 100; // This might be problematic if finalValue is small
                        const duration = 2000;

                        // Safe increment
                        const safeIncrement = increment < 1 ? 1 : increment;
                        const stepTime = duration / (finalValue / safeIncrement);

                        const timer = setInterval(() => {
                            current += safeIncrement;
                            if (current >= finalValue) {
                                target.textContent = text.replace(/\d+/, finalValue);
                                clearInterval(timer);
                            } else {
                                target.textContent = text.replace(/\d+/, Math.floor(current));
                            }
                        }, stepTime);
                    }
                    observer2.unobserve(target);
                }
            });
        }, {
            threshold: 0.5
        });

        counters.forEach(counter => {
            observer2.observe(counter);
        });
    }


    // Prevent auto-scrolling on page load by clearing any existing hash
    if (window.location.hash && window.location.hash !== '#') {
        // Remove the hash from the URL without scrolling
        history.replaceState(null, null, window.location.pathname + window.location.search);
    }

});
