$(function() {
  "use strict";

  $('.search-select').aplusSearchSelect();
  $('.search-select-ajax').aplusSearchSelectAjax();

  jQuery.expr[':'].icontains = function(element, index, match) {
    /**
    * - 'element' represents the current DOM element that the filter is applied to.
    * - 'index' represents the index of the current element in the set of matched elements.
    * - 'match' is an array containing information about the filter, where match[3] is the search
    *    string provided in the filter.
    */
    return jQuery(element).text().toUpperCase().indexOf(match[3].toUpperCase()) >= 0;
  };
});

(function($) {
  /**
  * This jQuery plugin converts a <select multiple> HTML form widget
  * into a search text box. The user may select multiple search results
  * and conduct more queries before submitting the form.
  *
  * There are two versions of this plugin:
  * - AplusSearchSelect: does not use AJAX, but instead searches options from
  *   the hidden select element.
  * - AplusSearchSelectAjax: the query is sent to the API via AJAX. Use this
  *   version to avoid increasing the page size by including a large amount
  *   of data in the select element, e.g., all users in the database.
  *
  * Use the SearchSelect widget in the Django form to activate this plugin.
  * The "ajax" initialization parameter determines which version of this
  * plugin is used. The Django form fields SearchSelectField and
  * UsersSearchSelectField are designed to be used with the SearchSelect
  * widget when "ajax" is true. See the widget's code for additional
  * instructions.
  */
  "use strict";

  var defaults = {
    field_selector: 'input[type="text"]',
    search_selector: '.search-button',
    result_selector: '.search-options',
    selection_selector: '.search-selected',
    copy_options_selector: '.copy-option',
    paste_options_selector: '.paste-option',
    max_results: 10,
  };

  /**
  * This is the base class of the plugins. Do not use this class directly.
  *
  * Implement these methods in derived classes:
  *
  * - transformResult(result):
  *   Transform a result received from getSearchResults or getValuesResults
  *   into a format that's common between the different versions of this
  *   plugin, i.e. an object with properties "value", "data" and "name".
  *
  * - getSearchResults(query, callback):
  *   Find items based on a search string, and call the callback function
  *   with result the array.
  *
  * - getValuesResults(values, field, callback):
  *   Find items where the field matches one of the values exactly, and call
  *   the callback function with the result array.
  */
  function AplusSearchSelectBase(element, options) {
    this.element = $(element);
    this.timeout = null;
    this.settings = $.extend({}, defaults, options);
    this.init();
  }

  $.extend(AplusSearchSelectBase.prototype, {
    init: function() {
      this.inner_element = this.element.find("select");

      this.selection = this.element.find(this.settings.selection_selector);
      this.api_url = this.element.attr("data-search-api-url");
      this.display_fields = this.element.attr("data-display-fields").split(",");
      this.clipboard_fields = this.element.attr("data-clipboard-fields").split(",");
      this.selection_li = this.selection.find("li").remove();

      /* this.inner_element is an HTML select element that contains the
      current values of the model field.

      In the AJAX version, when the form is loaded from the server, the
      select element should only contain options that are currently
      selected because the other possible options are not used and they
      increase the page size. The user's search queries are sent to the
      API and the available choices are not limited by the initial options
      of the select element.

      The select element is hidden, hence the initial selection is shown
      to the user by creating buttons in the addSelection method. */
      var self = this;
      this.inner_element.find("option:selected").each(function(index) {
        self.addSelection({
          value: $(this).attr("value"),
          data: $(this).data(),
          name: $(this).text()
        });
      });
      this.result = this.element.find(this.settings.result_selector);
      this.field = this.element.find(this.settings.field_selector)
        .on("keydown", function(event) {
          if (event.keyCode == 40) {
            /* Down arrow: focus the first search result */
            const item = self.result.find("li:visible:first > a");
            if (item.length == 1) {
              event.preventDefault();
              item.focus();
            }
          } else if (event.keyCode == 38) {
            /* Up arrow: focus the last search result */
            const item = self.result.find("li:visible:last > a");
            if (item.length == 1) {
              event.preventDefault();
              item.focus();
            }
          } else if (event.keyCode == 13) {
            /* Enter: open the search results dropdown */
            event.preventDefault();
            self.searchOptions(true);
          }
        }).on("keyup paste", function(event) {
          if (event.keyCode != 13) {
            clearTimeout(self.timeout);
            self.timeout = setTimeout(function() {
              self.searchOptions(true);
              self.field.focus();
            }, 500);
          }
        });
      this.search = this.element.find(this.settings.search_selector)
        .on("show.bs.dropdown", function(event) {
          self.searchOptions();
        });
      this.element.parents("form").on("submit", function(event) {
        self.finish();
      });
      this.element.find(this.settings.copy_options_selector).click(function(event) {
        event.preventDefault();
        self.copy($(this).data("field"));
      });
      new ClipboardJS(this.settings.copy_options_selector);
      this.element.find(this.settings.paste_options_selector).click(function(event) {
        event.preventDefault();
        self.paste($(this).data("field"));
      });

      this.inner_element.removeAttr('required');
    },

    /* Executes the user's query and displays the results as a list. How
    the query is executed depends on the implementation of
    this.getSearchResults. */
    searchOptions: function(show_dropdown) {
      const self = this;
      const query = this.field.val().trim();
      if (query.indexOf(",") > -1) {
        /* There is a comma in the input field: offer the option to
        import a list. */
        self.result.find("li.paste-option").show();
      } else {
        self.result.find("li.paste-option").hide();
      }
      if (show_dropdown && this.result.is(":visible") === false) {
        this.search.find("button").dropdown("toggle");
        return;
      }
      this.getSearchResults(query, function (data) {
        const numOfEntries = data.length;
        self.result.find("li:not(.not-found, .paste-option)").remove();
        self.result.find("li.not-found").hide();
        if (numOfEntries > 0) {
          const shownEntries = Math.min(numOfEntries, self.settings.max_results);
          for (let i = 0; i < shownEntries; i++) {
            const result = self.transformResult(data[i]);
            /* Show search results under the text input. If the
            user clicks a result, it is added to the selected
            values of the form field. */
            self.result.append(
              $('<li>').append(
                $('<a class="dropdown-item" href="#">').text(result.name)
              ).click(function(event) {
                event.preventDefault();
                self.addSelection(result);
                self.field.val("");
                self.field.focus();
              })
            );
          }
          if (numOfEntries > shownEntries){
             self.result.append(
              $('<li>').append(
                $('<a class="dropdown-item" href="#">').text((numOfEntries - shownEntries) + _(" results more"))
              )
            );
          }
        } else {
          self.result.find("li.not-found").show();
        }
      });
    },

    /* Add a new value to the currently selected values of the form field.
    Create a button that shows the new value to the user which enables the
    user to remove the value. */
    addSelection: function(result) {
      if (!result) {
        return;
      }
      if (this.selection.find('[data-value="' + result.value + '"]').length === 0) {
        var li = this.selection_li.clone();
        li.find(".name").text(result.name);
        const button = li.find("button").attr("data-value", result.value).on('click', function(event) {
          $(this).parent("li").remove();
        });
        $.each(this.clipboard_fields, function() {
          button.attr('data-' + this, result.data[this]);
        });
        this.selection.append(li);
      }
    },

    /* Reset the current selection and add the given values to the
    selection. How the given values are added depends on the implementation
    of getValuesResults.

    The field parameter determines which field the values should match. If
    field is not provided, the values are compared to the id. */
    resetSelection: function(values, field) {
      const self = this;
      this.selection.empty();
      this.getValuesResults(values, field, function (data) {
        $.each(data, function() {
          self.addSelection(self.transformResult(this));
        });
      });
    },

    /* Copy the selected values (buttons from the addSelection method)
    into the <select> element that really submits values to the server
    when the form is submitted. */
    finish: function() {
      const select = this.inner_element.show();
      select.empty();
      this.selection.find("button").each(function(index) {
        $('<option/>', {
          value: $(this).attr("data-value"),
          "selected": 'true',
          "text": $(this).text(),
        }).appendTo(select);
      });
    },

    /* Insert the selected values as a comma separated list into the text
    field, from which Clipboard.js will copy them.

    The field parameter determines which field's values are used. If field
    is not provided, ids are used. */
    copy: function(field) {
      const attr = field ? "data-" + field : "data-value";
      const values = $.map(this.selection.find("button"), function(el) {
        return $(el).attr(attr);
      });
      if (values.length > 0) {
        this.field.val(values.join(","));
      }
    },

    /* Reads a comma separated list from the text field and resets the
    selection to those values.

    The field parameter determines which field's values are currently in
    the text field. If field is not provided, the values are assumed to be
    ids. */
    paste: function(field) {
      const values = this.field.val().split(",");
      const nonEmptyValues = values.filter(function(value) {
        return value != undefined && value !== null && value !== "";
      });
      if (nonEmptyValues.length > 0) {
        this.resetSelection(values, field);
      }
    }
  });

  /**
  * This is the basic version of the plugin. It does not use AJAX, but
  * instead searches options from the hidden select element. It works by
  * building selectors that return <option> elements matching the user's
  * queries.
  */

  function AplusSearchSelect(element, options) {
    AplusSearchSelectBase.call(this, element, options);
  }

  $.extend(AplusSearchSelect.prototype, AplusSearchSelectBase.prototype, {
    transformResult: function(result) {
      /* In AplusSearchSelect, results are <option> elements. */
      return {
        value: $(result).attr("value"),
        data: $(result).data(),
        name: $(result).text()
      };
    },

    getSearchResults: function(query, callback) {
      let selector = "option";
      if (query.length > 0) {
        selector += ":icontains(" + this.field.val() + ")";
      }
      const options = this.inner_element.find(selector);
      callback(options);
    },

    getValuesResults: function(values, field, callback) {
      const attr = field ? "data-" + field : "value";
      const selectorParts = [];
      $.each(values, function() {
        selectorParts.push('option[' + attr + '="' + this + '"]');
      });
      const options = this.inner_element.find(selectorParts.join(','));
      callback(options);
    },
  });

  const pluginName = "aplusSearchSelect";
  $.fn[pluginName] = function(options, selectValues) {
    return this.each(function() {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusSearchSelect(this, options));
      }
      if (selectValues) {
        $.data(this, "plugin_" + pluginName).resetSelection(selectValues);
      }
    });
  };

  /**
  * This is the AJAX version of the plugin. It sends the query to the API via
  * AJAX.
  */
  function AplusSearchSelectAjax(element, options) {
    AplusSearchSelectBase.call(this, element, options);
  }

  $.extend(AplusSearchSelectAjax.prototype, AplusSearchSelectBase.prototype, {
    transformResult: function(result) {
      /* In AplusSearchSelectAjax, results are objects received from the
      API. */
      return {
        value: result.id,
        data: result,
        name: this.display_fields.map(
          item => result[item]
        ).join(', ')
      };
    },

    getSearchResults: function(query, callback) {
      /* Use the API to search for users and return additional
      information about the requested items. Assume the API endpoint
      supports the "search" parameter. */
      if (query.length > 0) {
        $.ajax({
          url: this.api_url,
          data: {
            "search": query,
          },
        }).done(function(data) {
          callback(data.results);
        });
      }
    },

    getValuesResults: function(values, field, callback) {
      /* Use the API to return additional information about the requested
      items. Assume the API endpoint supports the "field" and "values"
      parameters. */
      $.ajax({
        url: this.api_url,
        data: {
          "field": field ? field : "id",
          "values": values.join(','),
        }
      }).done(function(data) {
        callback(data.results);
      });
    },
  });

  const ajaxPluginName = "aplusSearchSelectAjax";
  $.fn[ajaxPluginName] = function(options, selectValues) {
    return this.each(function() {
      if (!$.data(this, "plugin_" + ajaxPluginName)) {
        $.data(this, "plugin_" + ajaxPluginName, new AplusSearchSelectAjax(this, options));
      }
      if (selectValues) {
        $.data(this, "plugin_" + ajaxPluginName).resetSelection(selectValues);
      }
    });
  };
})(jQuery);
