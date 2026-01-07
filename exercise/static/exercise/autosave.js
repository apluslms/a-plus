/**
 * Autosave functionality for exercises.
 */
 (function($, window) {
  "use strict";

  const pluginName = "aplusAutoSave";
  var defaults = {
    autoSaveIndicatorClasses: "small",
    autoSaveInterval: 10000, // ms
  };

  function AplusAutoSave(element, options) {
    this.dom_element = element;
    this.element = $(element);
    this.settings = $.extend({}, defaults, options);
    this.autoSaveTimeoutHandle = null;
    this.autoSaveRequest = null;
    this.autoSaveUrl = null;
    this.autoSaveIndicator = null;
    this.init();
  }

  $.extend(AplusAutoSave.prototype, {
    /**
     * Initializes the autosave functionality for this form.
     */
    init: function() {
      const self = this;

      const submitUrl = new URL(self.element.attr("action"), window.location);
      self.autoSaveUrl = new URL("draft/", submitUrl).href;

      self.autoSaveIndicator = $("<div></div>")
        .addClass(self.settings.autoSaveIndicatorClasses)
        .appendTo(self.element);

      const timestamp = self.element.data("draft-timestamp");
      if (timestamp) {
        self.setIndicatorSaveDate(new Date(timestamp));
      }

      self.element.on("input", function() {
        self.scheduleAutoSave();
      });
      self.element.on("submit", function() {
        // Cancel the autosave (if it was scheduled) when an actual submission
        // is made.
        clearTimeout(self.autoSaveTimeoutHandle);
        self.autoSaveIndicator.text("");
      });
    },

    /**
     * Schedules an autosave for a suitable time in the future.
     */
    scheduleAutoSave: function() {
      const self = this;

      // Check if a save has already been scheduled. Only one save can be
      // scheduled at a time.
      if (self.autoSaveTimeoutHandle !== null) {
        return;
      }

      function scheduleAutoSaveInternal() {
        self.autoSaveTimeoutHandle = setTimeout(function() {
          self.doAutoSave();
        }, self.settings.autoSaveInterval);
      }

      // If a save HTTP request is currently active, wait until it's done
      // before scheduling the next save.
      if (self.autoSaveRequest) {
        self.autoSaveRequest.always(scheduleAutoSaveInternal);
      } else {
        scheduleAutoSaveInternal();
      }
    },

    /**
     * Saves a draft instantly. Use scheduleAutoSave instead of this to avoid
     * unnecessarily frequent or simultaneous autosaves.
     */
    doAutoSave: function() {
      const self = this;
      self.autoSaveIndicator.text(_("Saving draft..."));

      self.autoSaveRequest = $.ajax({
        url: self.autoSaveUrl,
        type: "POST",
        data: new FormData(self.dom_element),
        contentType: false,
        processData: false,
      }).fail(function() {
        self.autoSaveIndicator.text(_("Failed to save draft"));
      }).done(function() {
        self.setIndicatorSaveDate(new Date());
      }).always(function() {
        // Allow new autosave requests.
        self.autoSaveRequest = null;
      });

      // Allow new autosaves to be scheduled.
      self.autoSaveTimeoutHandle = null;
    },

    /**
     * Sets the save date displayed in the autosave indicator below the
     * exercise form.
     */
    setIndicatorSaveDate: function(date) {
      let language = document.documentElement.lang || undefined;
      if (language === "en") {
        // The "lang" attribute uses short language codes. In toLocaleString,
        // "en" defaults to "en-US", so change it to "en-GB".
        language = "en-GB";
      }
      const dateString = date.toLocaleString(language);
      this.autoSaveIndicator.text(_("Draft saved") + " " + dateString);
    },
  });

  $.fn[pluginName] = function(options) {
    return this.each(function() {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusAutoSave(this, options));
      }
    });
  };
})(jQuery, window);
