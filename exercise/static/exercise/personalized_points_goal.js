$(document).ready(function() {
    const $pointsGoalForm = $('#pointsGoalForm');
    const $inputField = $('#id_personalized_points_goal_input');
    // If points-goal is a number then input it into the field
    if (typeof $pointsGoalForm.data('points-goal') === 'number') {
        $inputField.val($pointsGoalForm.data('points-goal'))};
    $inputField.focus();
    $pointsGoalForm.on('submit', function(event) {
        event.preventDefault();

        // Validate input
        const inputValue = $inputField.val().trim();

        const isNumber = !isNaN(inputValue) && inputValue !== '';
        const isPercentage = inputValue.endsWith('%') && !isNaN(inputValue.slice(0, -1));

        if (!isNumber && !isPercentage) {
            $('#validation-alert').show();
            setTimeout(function() {
                $('#validation-alert').hide();
            }, 5000);
            return;
        }

        $.ajax({
            type: 'POST',
            url: $pointsGoalForm.attr('action'),
            data: $pointsGoalForm.serialize(),
            success: function(response) {
                // Update page dynamically
                const $progressElement = $('#progress-' + $pointsGoalForm.data('module-url'));
                const $progressDiv = $progressElement.find('.progress');

                // Update goal indicator
                let $goalPointsElement = $progressElement.find('.goal-points');
                if ($goalPointsElement.length === 0) {
                    // Create the goal points bar if it does not exist
                    $goalPointsElement = $('<div>', {
                        id: 'goal-points',
                        class: 'goal-points',
                        css: {
                            left: response.personalized_points_goal_percentage + '%'
                        }
                    });
                    $progressDiv.append($goalPointsElement);
                } else {
                    // Update the existing element
                    $goalPointsElement.css('left', response.personalized_points_goal_percentage + '%');
                }

            // Update tooltip
            if ($progressDiv.length) {
                const tooltipTitle = $progressDiv.attr('data-original-title');
                const parser = new DOMParser();
                const doc = parser.parseFromString(tooltipTitle, 'text/html');

                let spanElement = doc.querySelector('span.personalized-points-text');
                // If the span element does not exist, create it
                if (spanElement == null) {
                    spanElement = doc.createElement('span');
                    spanElement.className = 'personalized-points-full-text text-nowrap';
                    doc.body.appendChild(spanElement);
                    spanElement.innerHTML = "<br>" + $pointsGoalForm.data('personalized-points-goal-tooltip-text') + ": " + "<span class=\"personalized-points-text text-nowrap\">" + response.personalized_points_goal_points + "</span>";
                }
                else {
                    spanElement.textContent = response.personalized_points_goal_points;
                }

                const updatedTooltipTitle = doc.body.innerHTML;
                $progressDiv.attr('data-original-title', updatedTooltipTitle);

                // Update progress-bar style
                if (response.personalized_points_goal_points <= $pointsGoalForm.data('points')) {
                    $progressDiv.find('.progress-bar').removeClass('progress-bar-warning');
                    $progressDiv.find('.progress-bar').addClass('progress-bar-primary');
                }
                else {
                    $progressDiv.find('.progress-bar').removeClass('progress-bar-primary');
                    $progressDiv.find('.progress-bar').addClass('progress-bar-warning');
                }
                // Show the success alert
                $('#success-alert').show();
                setTimeout(function() {
                    $('#success-alert').hide();
                }, 5000);
            }
        },
            error: function(xhr, status, error) {
                if (xhr.responseJSON.error === 'less_than_required') {
                    $('#danger-alert').show();
                    setTimeout(function() {
                        $('#danger-alert').hide();
                    }, 5000);	
                }
                else {
                    $('#warning-alert').show();
                    setTimeout(function() {
                        $('#warning-alert').hide();
                    }, 5000);	
                }
            }
        });
    });
    $('#deletePointsGoalForm').on('submit', function(event) {
        event.preventDefault();

        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: $(this).serialize() + '&delete=true',
            success: function(response) {
                // Update page dynamically
                const $progressElement = $('#progress-' + $pointsGoalForm.data('module-url'));
                const $progressDiv = $progressElement.find('.progress');

                // Remove goal indicator
                let $goalPointsElement = $progressElement.find('.goal-points');
                $goalPointsElement.removeClass('goal-points');

                // Update tooltip
                const tooltipTitle = $progressDiv.attr('data-original-title');
                const parser = new DOMParser();
                const doc = parser.parseFromString(tooltipTitle, 'text/html');
                    
                let spanElement = doc.querySelector('span.personalized-points-full-text');
                spanElement.remove();

                const updatedTooltipTitle = doc.body.innerHTML;
                $progressDiv.attr('data-original-title', updatedTooltipTitle);

                // Update progress-bar style
                $progressDiv.find('.progress-bar').removeClass('progress-bar-primary');

                $('#deletePointsGoalForm').hide();
                
                $('#remove-success-alert').show();
                setTimeout(function() {
                    $('#remove-success-alert').hide();
                }, 5000);

            },
            error: function(xhr, status, error) {
                // Handle error response
                $('#remove-warning-alert').show();
                setTimeout(function() {
                    $('#remove-warning-alert').hide();
                }, 5000);
            }
        });
    });
});
