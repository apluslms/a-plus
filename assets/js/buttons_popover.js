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
      const this_buttons = typeof buttons === "function" ?
        buttons(elem) :
        buttons;
      const default_options = {
        html: true,
        placement: 'bottom',
        trigger: 'focus',
      }
      const all_options = $.extend({}, default_options, options);

      const buttons_html = this_buttons.map(function (btn) {
        return ('<button id="' + btn.id + '" class="btn ' + btn.classes +
                '" ' + (btn.extra_attrs || "") + ">" + btn.text + "</button>")
      }).join(' ');
      // We have to attach the event handlers to body because the buttons are
      // created only when the popover is open and are destroyed when it is closed
      const $elem = $(elem);
      this_buttons.forEach(function (btn) {
        $('body').on('click', 'button#' + btn.id, function () {
          // Close this popover by triggering a click
          $elem.trigger('click');
          return btn.onclick();
        });
      });

      $elem.attr({
        'data-toggle': 'popover',
        'data-content': buttons_html,
        'tabindex': 0
      });
      $elem.popover(all_options);
    });
  },
});
