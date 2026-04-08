document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('planForm'); // Use specific ID for the form
    const loadingOverlay = document.getElementById('loadingOverlay');

    // Function to display an error message
    function showError(element, message) {
        const errorSpan = document.getElementById(element.id + '-error');
        if (errorSpan) {
            errorSpan.textContent = message;
            errorSpan.style.display = 'block';
            element.classList.add('input-error');
        }
    }

    // Function to clear an error message
    function clearError(element) {
        const errorSpan = document.getElementById(element.id + '-error');
        if (errorSpan) {
            errorSpan.textContent = '';
            errorSpan.style.display = 'none';
            element.classList.remove('input-error');
        }
    }

    if (form) { // Ensure the form exists before adding listeners
        const inputElements = form.querySelectorAll('input, select');
        inputElements.forEach(element => {
            element.addEventListener('input', function() {
                clearError(element);
            });
            element.addEventListener('change', function() {
                clearError(element);
            });
        });

        form.addEventListener('submit', function(event) {
            let isValid = true; // Flag to track overall form validity

            // Clear all previous errors on submit attempt
            inputElements.forEach(element => clearError(element));

            // Get references to input fields
            const age = document.getElementById('age');
            const height_cm = document.getElementById('height_cm');
            const weight_kg = document.getElementById('weight_kg');
            const gender = document.getElementById('gender');
            const activity_level = document.getElementById('activity_level');
            const dietary_preference = document.getElementById('dietary_preference');
            const fitness_goal = document.getElementById('fitness_goal');

            // --- Validate Age ---
            const ageValue = parseInt(age.value);
            if (age.value === '' || isNaN(ageValue) || ageValue < 12 || ageValue > 100) { // Updated min/max for form
                showError(age, 'Please enter a valid age (12-100).');
                isValid = false;
            }

            // --- Validate Height ---
            const heightValue = parseFloat(height_cm.value);
            if (height_cm.value === '' || isNaN(heightValue) || heightValue < 50 || heightValue > 250) { // Updated min/max for form
                showError(height_cm, 'Please enter a valid height (cm, e.g., 175).');
                isValid = false;
            }

            // --- Validate Weight ---
            const weightValue = parseFloat(weight_kg.value);
            if (weight_kg.value === '' || isNaN(weightValue) || weightValue < 20 || weightValue > 300) { // Updated min/max for form
                showError(weight_kg, 'Please enter a valid weight (kg, e.g., 70).');
                isValid = false;
            }

            // --- Validate Dropdowns (select elements) ---
            if (gender.value === '') {
                showError(gender, 'Please select your gender.');
                isValid = false;
            }

            if (activity_level.value === '') {
                showError(activity_level, 'Please select your activity level.');
                isValid = false;
            }

            // dietary_preference can be empty if 'None' is selected, so no validation needed here.
            // if (dietary_preference.value === '') {
            //     showError(dietary_preference, 'Please select your dietary preference.');
            //     isValid = false;
            // }

            if (fitness_goal.value === '') {
                showError(fitness_goal, 'Please select your fitness goal.');
                isValid = false;
            }

            // If any validation failed, prevent form submission
            if (!isValid) {
                event.preventDefault();
                const firstError = document.querySelector('.input-error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            } else {
                console.log('Form is valid. Submitting to server...');
                // --- Loading Spinner Logic (move here) ---
                if (loadingOverlay) {
                    loadingOverlay.style.display = 'flex'; // Show the overlay if form is valid
                }
            }
        });
    }

    // --- Toggle Details Function for view_plans.html ---
    window.toggleDetails = function(button) {
        const detailsDiv = button.nextElementSibling;
        if (detailsDiv.style.display === "block") {
            detailsDiv.style.display = "none";
            button.textContent = "Show Details";
        } else {
            detailsDiv.style.display = "block";
            button.textContent = "Hide Details";
        }
    };
});