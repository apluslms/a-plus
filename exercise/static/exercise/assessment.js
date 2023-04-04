$(function () {
  $.fn.addStickyButton = function (localStorageKey) {
    // The "sticky" feature is enabled if ResizeObserver is available and there
    // are submitted files (= there are two columns)
    const canSticky =
      $(".submitted-file").length > 0 &&
      typeof window.ResizeObserver === "function";
    if (canSticky) {
      var isSticky = localStorage.getItem(localStorageKey) === "true";
      if (isSticky) {
        this.addClass("sticky");
      }
      var stickyButton = {
        action: () => {
          isSticky = localStorage.getItem(localStorageKey) === "true";
          localStorage.setItem(localStorageKey, !isSticky);

          // if this button is on a exercise submission, synchronize the buttons for multiple exercises
          if (localStorageKey === "submissionSticky") {
            $(".nav-link").each(function () {
              const element = $(this);
              const file = $(element.attr("href"));
              file.toggleClass("sticky");

              const icon = file
                .find(".aplus-button--xs")
                .filter(function () {
                  return $(this).data("data-button-name") === "sticky-button";
                })
                .find(".glyphicon");

              // scroll separately buttons for other tabs which are hidden will be out of sync
              // unless we manually sync their state to the localStorage value
              if (icon.is(":hidden")) {
                if (icon.hasClass("glyphicon-unchecked") && !isSticky) {
                  icon
                    .removeClass("glyphicon-unchecked")
                    .addClass("glyphicon-check");
                } else if (icon.hasClass("glyphicon-check") && isSticky) {
                  icon
                    .removeClass("glyphicon-check")
                    .addClass("glyphicon-unchecked");
                }
              }
            });
          }
          else {
            $("#grader-feedback").toggleClass("sticky");
          }
        },
        icon: isSticky ? "check" : "unchecked",
        text: _("Scroll separately"),
        toggle: true,
        dataAttribute: 'sticky-button',
      };

      // When the assessment bar changes size (the textarea can be resized by
      // the user), change the --sticky-top variable to adjust the stickied
      // element's size and position. See also: _assessment.scss
      const panelHeading = $(".assessment-panel .panel-heading");

      const observer = new ResizeObserver(() => {
        this.parent().css("--sticky-top", panelHeading.outerHeight() + "px");
      });
      observer.observe(panelHeading.get(0));
      return [stickyButton];
    }
    return [];
  };

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
          text.attr('data-url', fileUrl);
          element.find('.submitted-file-data').html(text);
          const extraButtons = element.addStickyButton("submissionSticky");
          text.highlightCode({extraButtons});
        })
        .fail(function () {
          element.find('.submitted-file-error').removeClass('hidden');
        })
        .always(function () {
          element.find('.submitted-file-progress').addClass('hidden');
        });
      }
    });


    const containerElement = $('.grader-container');
    containerElement.find('.grader-tab').each(function () {
      const tabElement = $(this);

      // Check if the tab contains a 'pre' element to attach buttons to
      const preElement = tabElement.children('pre');
      const extraButtons = tabElement.addStickyButton("graderFeedbackSticky");
      if (preElement.length === 1) {
        // "Highlight" the grader feedback to get line numbers and buttons
        preElement
          .addClass('hljs language-plaintext')
          .highlightCode({extraButtons: extraButtons});
      }
      else {
        tabElement.highlightCode({
          extraButtons: extraButtons,
          noHighlight: true,
          noWrap: true,
          noDownload: true,
        });
      }
    });
  });
});
