$(document).ready(function() {
    const $pointsGoalForm = $('#pointsGoalForm');
    document.getElementById('id_personalized_points_goal_input').focus();
    $pointsGoalForm.on('submit', function(event) {
        event.preventDefault();
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
                    spanElement.className = 'personalized-points-text text-nowrap';
                    doc.body.appendChild(spanElement);
                    spanElement.innerHTML = "<br>" + $pointsGoalForm.data('personalized-points-goal-tooltip-text') + ": " + response.personalized_points_goal_points;
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
});
