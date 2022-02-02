$(function () {
  $(document).on('aplus:translation-ready', function() {
    // Activate the first tab
    $('.grader-container-tabs').find('li a').first().tab('show');

    // Create links for switching between assistant feedback and grader
    // feedback in the assessment bar
    const feedback1 = $('#id_assistant_feedback').closest('.form-group');
    const feedback2 = $('#id_feedback').closest('.form-group');
    feedback1.addClass('feedback-toggle');
    feedback2.addClass('feedback-toggle hidden');
    const label1 = feedback1.find('label');
    const label2 = feedback2.find('label');
    const feedbackToggleButton = $('<button class="aplus-button--secondary aplus-button--xs"></button>')
      .attr({
        'data-toggle': 'visibility',
        'data-target': '.feedback-toggle'
      });
    label1.after(feedbackToggleButton.clone().text(label2.text())).after(' | ');
    label2.before(feedbackToggleButton.clone().text(label1.text())).before(' | ');

    // Load the submitted files
    const loadedFiles = new Set();
    $('.submitted-file').each(function () {
      const element = $(this);
      const fileId = element.data('id');
      const fileViewable = element.data('viewable');
      const fileUrl = element.data('url');
      if (fileUrl && fileViewable && !loadedFiles.has(fileId)) {
        loadedFiles.add(fileId);
        $.get(fileUrl, function (data) {
          const text = $("<pre/>").text(data);
          element.find('.submitted-file-data').html(text);
          const downloadButton = {
            action: function() {
              window.location.href = fileUrl + '?download=yes';
            },
            icon: 'download-alt',
            text: _('Download'),
          };
          text.highlightCode({extraButtons: [downloadButton]});
        })
        .fail(function () {
          element.find('.submitted-file-error').removeClass('hidden');
        })
        .always(function () {
          element.find('.submitted-file-progress').addClass('hidden');
        });
      }
    });

    // The "sticky" feature is enabled if ResizeObserver is available and there
    // are submitted files (= there are two columns)
    const canSticky = $('.submitted-file').length > 0 && typeof window.ResizeObserver === 'function';

    const containerElement = $('.grader-container');
    containerElement.find('.grader-tab').each(function () {
      const tabElement = $(this);

      // Check if the tab contains a 'pre' element to attach buttons to
      const preElement = tabElement.children('pre');
      if (preElement.length === 1) {
        const extraButtons = [];
        if (canSticky) {
          var isSticky = localStorage.getItem('graderFeedbackSticky') === 'true';
          if (isSticky) {
            tabElement.addClass('sticky');
          }
          var stickyButton = {
            action: function() {
              isSticky = !isSticky;
              tabElement.toggleClass('sticky', isSticky);
              localStorage.setItem('graderFeedbackSticky', isSticky);
            },
            icon: isSticky ? 'check' : 'unchecked',
            text: _('Scroll separately'),
            toggle: true,
          };
          extraButtons.push(stickyButton);
        }

        // "Highlight" the grader feedback to get line numbers and buttons
        preElement
          .addClass('hljs language-plaintext')
          .highlightCode({extraButtons: extraButtons});
      }
    });

    if (canSticky) {
      // When the assessment bar changes size (the textarea can be resized by
      // the user), change the --sticky-top variable to adjust the stickied
      // element's size and position. See also: _assessment.scss
      const panelHeading = $('.assessment-panel .panel-heading');
      const observer = new ResizeObserver(function () {
        containerElement.css('--sticky-top', panelHeading.outerHeight() + 'px');
      });
      observer.observe(panelHeading.get(0));
    }
  });
});
