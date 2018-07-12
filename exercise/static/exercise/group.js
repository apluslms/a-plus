/**
 * Display group in exercise submits.
 *
 */
;(function($, window, document, undefined) {
 	"use strict";

  var defaults = {
    menu_selector: '.menu-groups',
    current_group_selector: '.selection [data-group-id]',
    current_group_attribute: "data-group-id",
    group_choice_selector: 'button',
    group_choice_size_attribute: "data-group-size",
    group_size_attribute: "data-aplus-group",
    group_fixed_attribute: "data-aplus-group-fixed",
    applied_class: "group-augmented",
    submit_selector: 'input[type="submit"],button[type="submit"]' /* ".aplus-submit" TODO once services support */
  };

  function AplusExerciseGroup(options) {
    this.settings = $.extend({}, defaults, options);
    this.selected = 0;
    this.groups = [];
    this.ui = null;
		this.init();
	}

	$.extend(AplusExerciseGroup.prototype, {

		/**
		 * Constructs group instance.
		 */
		init: function() {
      var menu = $(this.settings.menu_selector);
      if (menu.size() > 0) {
        this.selected = menu.eq(0).find(this.settings.current_group_selector).attr(this.settings.current_group_attribute);

        var self = this;
        menu.eq(0).find(this.settings.group_choice_selector).each(function() {
          var btn = $(this);
          self.groups.push({
            "id": btn.val(),
            "size": btn.attr(self.settings.group_choice_size_attribute),
            "text": btn.text().trim()
          });
        });

        this.ui = $('<div class="submit-group-selector input-group col-md-6">'
          + '<select name="_aplus_group" class="form-control"></select>'
          + '<span class="input-group-btn"></span>'
          + '</div>');
        var list = this.ui.find('select');
        for (var i = 0; i < this.groups.length; i++) {
          var group = this.groups[i];
          list.append($('<option value="' + group.id + '" data-group-size="' + group.size + '">' + group.text + '</option>'));
        }
      }
		},

    decorate: function(object) {
      if (this.groups.length > 0) {
        var self = this;
        object.find(
          "[" + this.settings.group_size_attribute + "]:not(." + this.settings.applied_class + ")"
        ).each(function() {
          var b = $(this).addClass(self.settings.applied_class).find(self.settings.submit_selector);
          if (b.size() > 0) {
            var ui = self.ui.clone();
            b.replaceWith(ui);
            ui.find('.input-group-btn').append(b);

            var groupFixed = $(this).attr(self.settings.group_fixed_attribute);
            if (groupFixed) {
              ui.find('option:not([value="' + groupFixed + '"])').remove();
            } else {
              var groupSize = $(this).attr(self.settings.group_size_attribute).split("-");
              ui.find("option").each(function() {
                var opt = $(this);
                var size = opt.attr("data-group-size");
                if (size < groupSize[0] || size > groupSize[1]) {
                  opt.remove();
                }
              });
            }

            var opt = ui.find('option[value="' + self.selected + '"]');
            if (opt.size() > 0) {
              opt.prop('selected', true);
            }
          }
        });
      }

      object
        .find('[data-aplus-disable-submit="true"] :submit')
        .prop('disabled', true);
    }
  });

  $.augmentSubmitButton = function(object) {
    if ($.augmentSubmitButton_class === undefined) {
      $.augmentSubmitButton_class = new AplusExerciseGroup();
    }
    $.augmentSubmitButton_class.decorate(object);
  };

})(jQuery, window, document);
