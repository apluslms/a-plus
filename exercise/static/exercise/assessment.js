$(function () {
  $.fn.addStickyButton = function (localStorageKey) {
    // The "sticky" feature is enabled if ResizeObserver is available and there
    // are submitted files (= there are two columns)
    const canSticky = $('.submitted-file').length > 0 && typeof window.ResizeObserver === 'function';
    if (!canSticky) {
      return [];
    }

    let isSticky = localStorage.getItem(localStorageKey) === 'true';
    if (isSticky) {
      this.addClass('sticky');
    }

    const stickyButton = {
      action: () => {
        isSticky = localStorage.getItem(localStorageKey) === 'true';
        localStorage.setItem(localStorageKey, !isSticky);

        const toggleSticky = function (parent, iconSelector) {
          const tabPanes = parent.children('.tab-pane');
          tabPanes.each(function () {
            const element = $(this);
            element.toggleClass('sticky');

            // 'Scroll separately' buttons for other tabs will be out of sync unless we manually sync their state
            if (!element.hasClass('active')) {
              element
                .find(iconSelector)
                .toggleClass('bi-square')
                .toggleClass('bi-check-square');
            }
          });
        };

        // Synchronize the 'Scroll separately' buttons
        let iconSelector;
        if (localStorageKey === 'submissionSticky') {
          iconSelector = `.submitted-file-data > div > p > button:contains(${_("Scroll separately")}) > i`;
        } else {
          iconSelector = `div > p > button:contains(${_("Scroll separately")}) > i`;
        }
        toggleSticky(this.parent(), iconSelector);
      },
      icon: isSticky ? 'check-square' : 'square',
      text: _('Scroll separately'),
      toggle: true,
    };

    // When the assessment bar changes size (the textarea can be resized by
    // the user), change the --sticky-top variable to adjust the stickied
    // element's size and position. See also: _assessment.scss
    const panelHeading = $('.assessment-panel .card-body');
    const observer = new ResizeObserver(() => {
      $(this).parent().css('--sticky-top', panelHeading.outerHeight() + 'px');
    });
    observer.observe(panelHeading.get(0));

    return [stickyButton];
  }

  $(document).on('aplus:translation-ready', function() {
    const currentPath = window.location.pathname;
    $("a.deviations-link").attr("href", function(i, href) {
      return `${href}&previous=${currentPath}`;
    });

    // Activate the first tab
    $('.grader-container-tabs').find('li a').first().tab('show');

    // Create links for switching between assistant feedback and grader
    // feedback in the assessment bar
    const feedback1 = $('#id_assistant_feedback').parent();
    const feedback2 = $('#id_feedback').parent();
    feedback1.addClass('feedback-toggle');
    feedback2.addClass('feedback-toggle d-none');
    const label1 = feedback1.find('label');
    const label2 = feedback2.find('label');
    const feedbackToggleButton = $('<button class="aplus-button--secondary aplus-button--xs"></button>')
      .attr({
        'data-bs-toggle': 'visibility',
        'data-bs-target': '.feedback-toggle'
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
          const text = $('<pre/>').text(data);
          text.attr('data-url', fileUrl);
          text.attr('data-filename', element.data('filename'));
          element.find('.submitted-file-data').html(text);
          const extraButtons = element.addStickyButton('submissionSticky');
          text.highlightCode({extraButtons, compareMode: fileUrl.includes('compare_to=')});
        })
        .fail(function () {
          element.find('.submitted-file-error').removeClass('d-none');
        })
        .always(function () {
          element.find('.submitted-file-progress').addClass('d-none');
        });
      }
    });

    const containerElement = $('.grader-container');
    containerElement.find('.grader-tab').each(function () {
      const tabElement = $(this);
      // Check if the tab contains a 'pre' element to attach buttons to
      const preElement = tabElement.children('pre');
      const extraButtons = tabElement.addStickyButton('graderFeedbackSticky');
      if (preElement.length === 1) {
        // "Highlight" the grader feedback to get line numbers and buttons
        preElement
          .addClass('hljs language-plaintext')
          .highlightCode({
            extraButtons: extraButtons,
            noDownload: true,
          });
      } else {
        tabElement.children().wrapAll('<div class="grader-html-output"></div>');
        $('.grader-html-output').highlightCode({
          extraButtons: extraButtons,
          noHighlight: true,
          noWrap: true,
          noDownload: true,
          noCopy: true,
        });
      }
    });
  });
});
