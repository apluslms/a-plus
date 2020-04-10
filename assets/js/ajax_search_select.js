$(function() {
    "use strict";

    $('.search-select-ajax').aplusSearchSelectAjax();
});

(function($) {
    /**
    * This jQuery plugin converts a <select multiple> HTML form widget
    * into a search text box. The user may select multiple search results
    * and conduct more queries before submitting the form. The user's
    * query is sent to the API via AJAX.
    *
    * A+ JS code includes an older jQuery plugin aplusSearchSelect which
    * this plugin is based on. The old plugin did not use AJAX, but instead
    * it searched options from a hidden select element. The page size
    * increased significantly when a large amount of data was included
    * in the select element, e.g., all users in the database.
    *
    * This plugin is activated by adding the class attribute "search-select-ajax"
    * to a <select multiple> element. The element must also have the following
    * data attributes:
    *
    * - data-search-api-url: API URL that is used for the AJAX search, e.g.,
    *   "/api/v2/users/"
    * - data-key-parameter-list: comma-separated list of fields that are shown
    *   to the user from the API search results, e.g., "full_name,student_id"
    *
    * The search API URL must support the "search" GET query parameter since
    * the user's query is sent with it.
    *
    * The Django form fields SearchSelectField and UsersSearchSelectField in
    * a-plus/lib/fields.py are designed to be used with this jQuery plugin.
    */
    "use strict";

    const pluginName = "aplusSearchSelectAjax";
    var defaults = {
        widget_selector: "#search-select-widget",
        field_selector: 'input[type="text"]',
        search_selector: '.dropdown-toggle',
        result_selector: '.search-options',
        selection_selector: '.search-selected',
    };

    function AplusSearchSelectAjax(element, options) {
        this.element = $(element);
        this.timeout = null;
        if (this.element.prop("tagName") == "SELECT" && this.element.prop("multiple")) {
            this.settings = $.extend({}, defaults, options);
            this.init();
        }
    }

    $.extend(AplusSearchSelectAjax.prototype, {

        init: function() {
            this.widget = $(this.settings.widget_selector).clone()
                .removeAttr("id").removeClass("hide").insertBefore(this.element);
            this.element.hide();
            var self = this;
            this.selection = this.widget.find(this.settings.selection_selector);
            this.api_url = self.element.attr("data-search-api-url");
            this.parameter_list = self.element.attr("data-key-parameter-list").split(",");
            this.selection_li = this.selection.find("li").remove();
            /* this.element is an HTML select element that contains the current
            values of the model field. That is to say, if the model field has
            no value, the select element is empty, and if the model field has
            values, then those values are included in the select element options.
            When the form is loaded, it must show the initial values in the
            rendered page. However, user fields are problematic because the API
            uses only user IDs while many models refer to user profiles.
            User profiles may have different IDs than the corresponding users.
            That's why user fields have user IDs in the select element without
            full user data, hence we need to retrieve user details from the API
            for each initially selected user.
            The resetSelection method has a similar hack. */
            this.element.find("option").each(function(index) {
                $.ajax({
                    url: self.api_url + $(this).attr("value"),
                }).done(function(data) {
                    self.addSelection(
                        data['id'],
                        self.resultInfo(self.parameter_list, data)
                    )
                });
            });
            this.result = this.widget.find(this.settings.result_selector);
            this.field = this.widget.find(this.settings.field_selector)
                .on("keypress", function(event) {
                    if (event.keyCode == 13) {
                        event.preventDefault();
                        self.searchOptions(true);
                    }
                }).on("keyup", function(event) {
                    if (event.keyCode != 13) {
                        clearTimeout(self.timeout);
                        self.timeout = setTimeout(function() {
                            self.searchOptions(true);
                            self.field.focus();
                        }, 500);
                    }
                });
            this.search = this.widget.find(this.settings.search_selector)
                .on("show.bs.dropdown", function(event) {
                    self.searchOptions();
                });
            this.element.parents("form").on("submit", function(event) {
                self.finish();
            });
            this.element.removeAttr('required');
        },

        searchOptions: function(show_dropdown) {
            if (show_dropdown && this.result.is(":visible") === false) {
                this.search.find("button").dropdown("toggle");
            }
            const query = this.field.val().trim();
            const self = this;
            if (query.length > 0) {
                $.ajax({
                    url: this.api_url,
                        data: {
                            "search": query,
                        },
                }).done(function(data) {
                    const numOfEntries = data.count;
                    self.result.empty();
                    if (numOfEntries > 0) {
                        var shownFields = (numOfEntries > 10) ? 5 : numOfEntries;
                        for (let i = 0; i < shownFields; i++) {
                            const result_info = data.results[i];
                            // Show search results under the text input.
                            // If the user clicks a result, it is added to
                            // the selected values of the form field.
                            self.result.append(
                                $('<li>').append(
                                    $('<a>').text(
                                        self.resultInfo(self.parameter_list, result_info)
                                    )
                                ).click(function() {
                                    self.addSelection(
                                        result_info['id'],
                                        self.resultInfo(self.parameter_list, result_info)
                                    )
                                })
                            );
                        }
                        if (numOfEntries > shownFields){
                            self.result.append(
                                $('<li>').append(
                                    $('<a>').text(numOfEntries - 5 + _(" results more"))
                                )
                            );
                        }
                    } else {
                        self.result.append(
                            $('<li>').append(
                                $('<a>').text(_("No matches!"))
                            )
                        );
                    }
                });
            }
        },

        resultInfo: function(parameter_list, result_info) {
            return parameter_list.map(
                item => result_info[item]
            ).join(', ');
        },

        /* Add a new value to the currently selected values of the form field.
        Create a button that shows the new value to the user and
        enables the user to remove the value. */
        addSelection: function(value, name) {
            if (this.selection.find('[data-value="' + value + '"]').size() === 0) {
                var li = this.selection_li.clone();
                li.find(".name").text(name);
                li.find("button").attr("data-value", value).on('click', function(event) {
                    $(this).parent("li").remove();
                });
                this.selection.append(li);
            }
        },

        resetSelection: function(values) {
            this.selection.empty();
            var self = this;
            $.each(values, function(index, value) {
                $.ajax({
                    url: self.api_url + value,
                }).done(function(data) {
                    self.addSelection(
                        value,
                        self.resultInfo(self.parameter_list, data)
                    )
                });
            });
        },

        /* Copy the selected values (buttons from the addSelection method)
        into the <select> element that really submits values to the server
        when the form is submitted. */
        finish: function() {
            this.widget.remove();
            var select = this.element.show();
            select.empty();
            this.selection.find("button").each(function(index) {
                $('<option/>', {
                    value: $(this).attr("data-value"),
                    "selected": 'true',
                }).appendTo(select);
            });
        }
    });

    $.fn[pluginName] = function(options, selectValues) {
        return this.each(function() {
            if (!$.data(this, "plugin_" + pluginName)) {
                $.data(this, "plugin_" + pluginName, new AplusSearchSelectAjax(this, options));
            }
            if (selectValues) {
                $.data(this, "plugin_" + pluginName).resetSelection(selectValues);
            }
        });
    };
})(jQuery);
