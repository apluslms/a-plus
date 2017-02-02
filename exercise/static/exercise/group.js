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
    group_size_attribute: "data-aplus-group",
    applied_class: "group-augmented",
    submit_selector: ".aplus-submit"
  };

  function AplusExerciseGroup(options) {
    this.settings = $.extend({}, defaults, options);
    this.selected = 0;
    this.groups = [];
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
            "text": btn.text()
          });
        });
      }
		},

    decorate: function(object) {
      if (this.groups.length > 0) {
        var self = this;
        object.find(
          "[" + this.settings.group_size_attribute
          + "]:not(." + this.settings.applied_class + ")"
        ).each(function() {
          var b = $(this).find(self.settings.submit_selector);
          if (b.size() > 0) {

            // TODO replace with group selector
            console.log(b, self.groups);

          }
          $(this).addClass(self.settings.applied_class);
        });
      }
    }
  });

  $.augmentExerciseGroup = function(object) {
    if ($.augmentExerciseGroup_class === undefined) {
      $.augmentExerciseGroup_class = new AplusExerciseGroup();
    }
    $.augmentExerciseGroup_class.decorate(object);
  };

})(jQuery, window, document);
