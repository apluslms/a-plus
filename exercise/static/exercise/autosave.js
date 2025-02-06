/**
 * Autosave functionality for exercises.
 */
(function(window) {
  "use strict";

  const pluginName = "aplusAutoSave";
  const defaults = {
    autoSaveIndicatorClasses: "small",
    autoSaveInterval: 10000, // ms
  };

  function AplusAutoSave(element, options) {
    this.dom_element = element;
    this.settings = Object.assign({}, defaults, options);
    this.autoSaveTimeoutHandle = null;
    this.autoSaveRequest = null;
    this.autoSaveUrl = null;
    this.autoSaveIndicator = null;
    this.init();
  }

  AplusAutoSave.prototype = {
    /**
     * Initializes the autosave functionality for this form.
     */
    init: function() {
      const self = this;

      const submitUrl = new URL(self.dom_element.getAttribute("action"), window.location);
      self.autoSaveUrl = new URL("draft/", submitUrl).href;

      self.autoSaveIndicator = document.createElement("div");
      self.autoSaveIndicator.className = self.settings.autoSaveIndicatorClasses;
      self.dom_element.appendChild(self.autoSaveIndicator);

      const timestamp = self.dom_element.dataset.draftTimestamp;
      if (timestamp) {
        self.setIndicatorSaveDate(new Date(timestamp));
      }

      self.dom_element.addEventListener("input", function() {
        self.scheduleAutoSave();
      });
      self.dom_element.addEventListener("submit", function() {
        // Cancel the autosave (if it was scheduled) when an actual submission
        // is made.
        clearTimeout(self.autoSaveTimeoutHandle);
        self.autoSaveIndicator.textContent = "";
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
        self.autoSaveRequest.finally(scheduleAutoSaveInternal);
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
      self.autoSaveIndicator.textContent = "Saving draft...";

      self.autoSaveRequest = fetch(self.autoSaveUrl, {
        method: "POST",
        body: new FormData(self.dom_element),
      }).then(function(response) {
        if (!response.ok) {
          throw new Error("Failed to save draft");
        }
        self.setIndicatorSaveDate(new Date());
      }).catch(function() {
        self.autoSaveIndicator.textContent = "Failed to save draft";
      }).finally(function() {
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
      this.autoSaveIndicator.textContent = "Draft saved " + dateString;
    },
  };

  window[pluginName] = function(element, options) {
    if (!element[pluginName]) {
      element[pluginName] = new AplusAutoSave(element, options);
    }
  };
})(window);
