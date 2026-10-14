/**
 * Event handlers for the personalized points goal form.
 *
 * This script tag is at the top of the module goal modal template, which is
 * normally loaded into the page modal via AJAX. jQuery injects the modal
 * content into the document and only then evaluates this script. Because the
 * document has already been loaded at that point, jQuery runs $(document).ready
 * callbacks asynchronously. That leaves a window where the form is visible but
 * its submit handler is not attached yet, and a submission made during that
 * window (by a fast user or an e2e test) posts the form natively, navigating
 * the browser away from the results page to the raw JSON response.
 *
 * To make the timing irrelevant, the submit handlers are registered with event
 * delegation on the document. They are attached once (the script is evaluated
 * every time the modal is opened) and they intercept submissions of the goal
 * forms no matter when the forms are inserted into the document.
 */
(function ($) {
    "use strict";

    // Prefill the input with the previously saved goal and focus it. This runs
    // on every script evaluation, i.e. every time the modal content is injected
    // into the page. It must stay above the once-only handler guard below: the
    // guard returns early when the script is re-evaluated, and a prefill placed
    // after it would only run on the first modal open after a page load.
    function initModuleGoalForm() {
        const $pointsGoalForm = $('#pointsGoalForm');
        const $inputField = $('#id_module_goal_input');
        // If points-goal is a number then input it into the field
        if (typeof $pointsGoalForm.data('points-goal') === 'number') {
            $inputField.val($pointsGoalForm.data('points-goal'));
        }
        $inputField.trigger('focus');
    }

    if (document.readyState === 'loading') {
        // Regular page load: wait until the form markup below this script tag
        // has been parsed before prefilling the input.
        $(document).ready(initModuleGoalForm);
    } else {
        // The script was injected into an already loaded document (the module
        // goal modal is loaded into the page modal via AJAX).
        initModuleGoalForm();
    }

    // The script is evaluated every time the modal is opened, but the delegated
    // submit handlers must be registered only once.
    if ($(document).data("moduleGoalHandlers")) {
        return;
    }
    $(document).data("moduleGoalHandlers", true);

    function hideAfterTimeout(selector, timeout) {
        setTimeout(function() {
            $(selector).hide();
        }, timeout);
    }

    $(document).on("submit", "#pointsGoalForm", function(event) {
        event.preventDefault();

        const $pointsGoalForm = $(this);
        const $inputField = $pointsGoalForm.find("#id_module_goal_input");

        // Validate input
        const inputValue = $inputField.val().trim();

        const isNumber = !isNaN(inputValue) && inputValue !== '';
        const isPercentage = inputValue.endsWith('%') && !isNaN(inputValue.slice(0, -1));

        if (!isNumber && !isPercentage) {
            $('#validation-alert').show();
            hideAfterTimeout('#validation-alert', 5000);
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
                            left: response.goal_percentage + '%'
                        }
                    });
                    $progressDiv.append($goalPointsElement);
                } else {
                    // Update the existing element
                    $goalPointsElement.css('left', response.goal_percentage + '%');
                }

                // Update tooltip
                if ($progressDiv.length) {
                    const tooltipTitle = $progressDiv.attr('data-bs-original-title');
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(tooltipTitle, 'text/html');

                    let spanElement = doc.querySelector('span.personalized-points-text');
                    // If the span element does not exist, create it
                    if (spanElement == null) {
                        spanElement = doc.createElement('span');
                        spanElement.className = 'personalized-points-full-text text-nowrap';
                        doc.body.appendChild(spanElement);
                        spanElement.innerHTML = "<br>" + $pointsGoalForm.data('personalized-points-goal-tooltip-text') + ": " + "<span class=\"personalized-points-text text-nowrap\">" + response.goal_points + "</span>";
                    }
                    else {
                        spanElement.textContent = response.goal_points;
                    }

                    const updatedTooltipTitle = doc.body.innerHTML;
                    $progressDiv.attr('data-bs-original-title', updatedTooltipTitle);

                    // Update progress-bar style
                    if (response.goal_points <= $pointsGoalForm.data('points')) {
                        $progressDiv.find('.aplus-progress-bar').removeClass('aplus-progress-bar-warning');
                        $progressDiv.find('.aplus-progress-bar').addClass('aplus-progress-bar-primary');
                    }
                    else {
                        $progressDiv.find('.aplus-progress-bar').removeClass('aplus-progress-bar-primary');
                        $progressDiv.find('.aplus-progress-bar').addClass('aplus-progress-bar-warning');
                    }
                    // Show the success alert
                    $('#success-alert').show();
                    hideAfterTimeout('#success-alert', 5000);
                }
            },
            error: function(xhr, status, error) {
                if (xhr.responseJSON.error === 'less_than_required') {
                    $('#danger-alert').show();
                    hideAfterTimeout('#danger-alert', 5000);
                }
                else {
                    $('#warning-alert').show();
                    hideAfterTimeout('#warning-alert', 5000);
                }
            }
        });
    });

    $(document).on("submit", "#deletePointsGoalForm", function(event) {
        event.preventDefault();

        const $pointsGoalForm = $('#pointsGoalForm');
        $.ajax({
            type: 'DELETE',
            url: $(this).attr('action'),
            data: $(this).serialize() + '&delete=true',
            success: function(response) {
                // Update page dynamically
                const $progressElement = $('#progress-' + $pointsGoalForm.data('module-url'));
                const $progressDiv = $progressElement.find('.progress');

                // Remove goal indicator
                const $goalPointsElement = $progressElement.find('.goal-points');
                $goalPointsElement.remove();

                // Update tooltip
                const tooltipTitle = $progressDiv.attr('data-bs-original-title');
                const parser = new DOMParser();
                const doc = parser.parseFromString(tooltipTitle, 'text/html');

                let spanElement = doc.querySelector('span.personalized-points-full-text');
                if (spanElement) {
                    spanElement.remove();
                }

                const updatedTooltipTitle = doc.body.innerHTML;
                $progressDiv.attr('data-bs-original-title', updatedTooltipTitle);

                // Update progress-bar style
                $progressDiv.find('.aplus-progress-bar').removeClass('aplus-progress-bar-primary');

                // The Remove button lives in the save form's button row (it is
                // associated with the delete form via the "form" attribute), so
                // hide the button as well as the now empty delete form.
                $('#deletePointsGoalForm').hide();
                $('#remove-points-goal-button').hide();

                $('#remove-success-alert').show();
                hideAfterTimeout('#remove-success-alert', 5000);

            },
            error: function(xhr, status, error) {
                // Handle error response
                $('#remove-warning-alert').show();
                hideAfterTimeout('#remove-warning-alert', 5000);
            }
        });
    });
})(jQuery);
