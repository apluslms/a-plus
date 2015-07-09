/**
 * Polling for exercise status.
 *
 */
;(function($, window, document, undefined) {
	"use strict";

	var pluginName = "aplusExercisePoll";
	var defaults = {
    poll_url_attr: "data-poll-url"
  };

	function AplusExercisePoll(element, callback, options) {
		this.element = $(element);
    this.callback = callback;
		this.settings = $.extend({}, defaults, options);
    this.url = null;
		this.init();
	}

	$.extend(AplusExercisePoll.prototype, {

		/**
		 * Constructs contained exercise elements.
		 */
		init: function() {
      this.url = this.element.attr(this.settings.poll_url_attr);
      //TODO poll some times
		},

    ready: function() {
      if (this.callback) {
        this.callback(this.url.substr(0, this.url.length - "poll/".length));
      } else {
        location.reload();
      }
    }

	});

	$.fn[pluginName] = function(callback, options) {
		return this.each(function() {
			if (!$.data(this, "plugin_" + pluginName)) {
				$.data(this, "plugin_" + pluginName, new AplusExercisePoll(this, callback, options));
			}
		});
	};

  $.aplusExerciseDetectWaits = function(callback) {
    $(".exercise-wait").aplusExercisePoll(callback);
  };

})(jQuery, window, document);

jQuery.aplusExerciseDetectWaits();
