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
    submit_selector: ".aplus-submit"
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

        this.ui = $('<div class="submit-group-selector btn-group">'
          + '<button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"><span class="selected-group"></span> <span class="caret"></span></button>'
          + '<ul class="dropdown-menu"></ul>'
          + '<input type="hidden" name="_aplus_group" value="0" />'
          + '</div>');
        var ul = this.ui.find('ul');
        for (var i = 0; i < this.groups.length; i++) {
          var group = this.groups[i];
          ul.append($('<li><a href="#" data-group-id="' + group.id + '" data-group-size="' + group.size + '">' + group.text + '</a></li>'));
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
            ui.append(b);

            var groupFixed = $(this).attr(self.settings.group_fixed_attribute);
            if (groupFixed) {
              ui.find('li a:not([data-group-id="' + groupFixed + '"])').remove();
              ui.find('li a').on("click", self.selectGroup);
            } else {
              var groupSize = $(this).attr(self.settings.group_size_attribute).split("-");
              ui.find("li a").each(function() {
                var link = $(this);
                var size = link.attr("data-group-size");
                if (size < groupSize[0] || size > groupSize[1]) {
                  link.remove();
                } else {
                  link.on("click", self.selectGroup);
                }
              });
            }

            var selected = ui.find('[data-group-id="' + self.selected + '"]');
            if (selected.size() > 0) {
              selected.trigger('click');
            } else {
              ui.find('a').eq(0).trigger('click');
            }
          }
        });
      }
    },

    selectGroup: function(event) {
      event.preventDefault();
      var a = $(this);
      var group = a.parents('.btn-group');
      group.find('.selected-group').text(a.text());
      group.find('[name="_aplus_group"]').val(a.attr("data-group-id"));
    }
  });

  $.augmentExerciseGroup = function(object) {
    if ($.augmentExerciseGroup_class === undefined) {
      $.augmentExerciseGroup_class = new AplusExerciseGroup();
    }
    $.augmentExerciseGroup_class.decorate(object);
  };

})(jQuery, window, document);
