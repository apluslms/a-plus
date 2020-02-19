$(function() {
    "use strict";

    $('.search-select-ajax').aplusSearchSelectAjax();
});

(function($) {
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
            this.element.find("option:selected").each(function(index) {
                $.ajax({
                    url: self.api_url + $(this).attr("value"),
                }).done(function(data) {
                    self.addSelection(
                        data['id'],
                        self.addResultInfo(self.parameter_list, data)
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
            var selector = "option";
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
                            self.result.append(
                                $('<li>').append(
                                    $('<a>').text(
                                        self.addResultInfo(self.parameter_list, result_info)
                                    )
                                ).click(function() {
                                    self.addSelection(
                                        result_info['id'],
                                        self.addResultInfo(self.parameter_list, result_info)
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

        addResultInfo: function(parameter_list, result_info) {
            return parameter_list.map(
                item => result_info[item]
            ).join(', ');
        },

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
                        self.addResultInfo(self.parameter_list, data)
                    )
                });
            });
        },

        finish: function() {
            this.widget.remove();
            var select = this.element.show();
            select.empty();
            select.find("option:selected").prop("selected", false);
            this.selection.find("button").each(function(index) {
                jQuery('<option/>', {
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
