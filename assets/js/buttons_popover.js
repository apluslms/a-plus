$.fn.extend({
  /**
   * Add a popover containing buttons
   * @example $('.colortag').buttons_popover(...)
   *
   * @param {List<Object>|Function} buttons - If a function, should produce the
            buttons list when called with each element in `this` as an argument.
   * @param {String} buttons.id - The button element's id
   * @param {string} buttons.classes - Extra classes separated by spaces.
   *        Should include at least button type (default, primary, warning etc)
   * @param {String} buttons.extra_attrs - Any extra attributes of the element
   * @param {String} buttons.text - The text shown inside the button
   * @param {Function} buttons.onclick - The click handler
   * @param {Object} options - see {@link https://getbootstrap.com/docs/3.3/javascript/#popovers-options}
   */
  buttons_popover: function (buttons, options) {
    this.each(function (i, elem) {
      const this_buttons = typeof buttons === "function" ? buttons(elem) : buttons;
      const default_options = {
        html: true,
        sanitize: false,
        placement: 'bottom',
        trigger: 'focus',
        container: 'body',
      };
      const all_options = $.extend({}, default_options, options);

      const buttons_html = this_buttons.map(function (btn) {
        return ('<button id="' + btn.id + '" class="btn ' + btn.classes +
                '" ' + (btn.extra_attrs || "") + ">" + btn.text + "</button>")
      }).join(' ');

      const $elem = $(elem);
      // Make focusable for trigger: 'focus'
      $elem.attr({ 'tabindex': 0 });

      // Attach delegated handlers for dynamically created buttons
      // Namespace per-button id to avoid duplicate handlers on re-init
      this_buttons.forEach(function (btn) {
        const ev = 'click.buttonsPopover.' + btn.id;
        $('body')
          .off(ev, 'button#' + btn.id)
          .on(ev, 'button#' + btn.id, function () {
            // Hide popover then execute action
            try {
              const inst = bootstrap.Popover.getInstance($elem[0]);
              if (inst) inst.hide();
            } catch (e) { /* ignore */ }
            return btn.onclick();
          });
      });

      // Initialize Bootstrap 5 popover (idempotent)
      try {
        const existing = bootstrap.Popover.getInstance($elem[0]);
        if (!existing) {
          new bootstrap.Popover($elem[0], $.extend({}, all_options, { content: buttons_html }));
        } else {
          // Update content attribute for existing instance
          $elem.attr('data-bs-content', buttons_html);
        }
      } catch (e) {
        // As a fallback, set data attributes for any legacy initializers
        $elem.attr({ 'data-bs-toggle': 'popover', 'data-bs-content': buttons_html });
      }
    });
  },
});
