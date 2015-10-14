$(function() {

    // Mark active menu based on body attribute data-view-tag.
    var tag = $("body").attr("data-view-tag");
    if (tag) {
        var entries = tag.split(",");
        for (var i = 0; i < entries.length; i++) {
            $(".menu-" + entries[i]).addClass("active");
        }
    }

    $('[data-toggle="tooltip"]').tooltip();
    $('.ajax-tail-list').aplusListTail();
    $('.file-modal').aplusFileModal();
    $('.search-select').aplusSearchSelect();
});

/**
 * Open submitted file in a modal.
 */
(function($, window, document, undefined) {
 	"use strict";

    var pluginName = "aplusFileModal";
    var defaults = {
        modal_selector: "#default-modal",
        title_selector: ".modal-title",
        content_selector: ".modal-body"
    };

    function AplusFileModal(element, options) {
		this.element = $(element);
		this.settings = $.extend({}, defaults, options);
		this.init();
	}

    $.extend(AplusFileModal.prototype, {
		init: function() {
            var link  = this.element;
            var settings = this.settings;
            link.on("click", function(event) {
                event.preventDefault();
                $.get(link.attr("href"), function(data) {
                    var modal = $(settings.modal_selector);
                    var text = $("<pre/>").text(data);
                    modal.find(settings.title_selector).text(link.text());
                    modal.find(settings.content_selector).html(text);
                    hljs.highlightBlock(text[0]);

                    // Add line numbers.
                    var lines = text.html().split(/\r\n|\r|\n/g);
                    var list = $("<table/>").addClass("src");
                    for (var i = 1; i <= lines.length; i++) {
                        list.append('<tr><td class="num">' + i + '</td><td class="src">' + lines[i - 1] + '</td></tr>');
                    }
                    text.html(list);

        			modal.modal("show");
                });
            });
        }
	});

    $.fn[pluginName] = function(options) {
		return this.each(function() {
			if (!$.data(this, "plugin_" + pluginName)) {
				$.data(this, "plugin_" + pluginName, new AplusFileModal(this, options));
			}
		});
	};
})(jQuery, window, document);

/**
 * Ajax loaded list tail.
 */
(function($, window, document, undefined) {
	"use strict";

	var pluginName = "aplusListTail";
	var defaults = {
		per_page_attr: "data-per-page",
        entry_selector: ".list-entry",
        more_selector: ".more-link",
        link_selector: "a",
        loader_selector: ".progress",
        link_page_arg: "?page=",
	};

	function AplusListTail(element, options) {
		this.element = $(element);
		this.settings = $.extend({}, defaults, options);
		this.init();
	}

	$.extend(AplusListTail.prototype, {

		init: function() {
            var settings = this.settings;
            var perPage = this.element.attr(settings.per_page_attr);
            if (this.element.find(settings.entry_selector).size() >= perPage) {
                var tail = this.element.find(settings.more_selector);
                tail.removeClass("hide").on("click", function(event) {
                    event.preventDefault();
                    var link = tail.find(settings.link_selector)
                        .hide();
                    var loader = tail.find(settings.loader_selector)
                        .removeClass("hide").show();
                    var url = link.attr("href");
                    $.get(url, function(html) {
                        loader.hide();
                        tail.before(html);
                        if ($(html).filter(settings.entry_selector).size() >= perPage) {
                            var i = url.indexOf(settings.link_page_arg) + settings.link_page_arg.length;
                            if (i >= settings.link_page_arg.length) {
                                var page = parseInt(url.substr(i));
                                link.attr("href", url.substr(0, i) + (page + 1));
                                link.show();
                            }
                        } else {
                            tail.hide();
                        }
                    });
                });
            }
        }
	});

	$.fn[pluginName] = function(options) {
		return this.each(function() {
			if (!$.data(this, "plugin_" + pluginName)) {
				$.data(this, "plugin_" + pluginName, new AplusListTail(this, options));
			}
		});
	};
})(jQuery, window, document);

/**
 * Multiple select as search and remove.
 */
(function($, window, document, undefined) {
    "use strict";

    var pluginName = "aplusSearchSelect";
    var defaults = {
        widget_selector: "#search-select-widget",
        field_selector: 'input[type="text"]',
        search_selector: '.dropdown-toggle',
        result_selector: '.search-options',
        selection_selector: '.search-selected',
    };

    function AplusSearchSelect(element, options) {
        this.element = $(element);
        this.timeout = null;
        if (this.element.prop("tagName") == "SELECT" && this.element.prop("multiple")) {
            this.settings = $.extend({}, defaults, options);
            this.init();
        }
    }

    $.extend(AplusSearchSelect.prototype, {

        init: function() {
            this.widget = $(this.settings.widget_selector).clone()
                .removeAttr("id").removeClass("hide").insertBefore(this.element);
            this.element.hide();
            var self = this;
            this.selection = this.widget.find(this.settings.selection_selector);
            this.selection_li = this.selection.find("li").remove();
            this.element.find("option:selected").each(function(index) {
                self.add_selection($(this).attr("value"), $(this).text());
            });
            this.result = this.widget.find(this.settings.result_selector);
            this.field = this.widget.find(this.settings.field_selector)
                .on("keypress", function(event) {
                    if (event.keyCode == 13) {
                        event.preventDefault();
                        self.search_options(true);
                    }
                }).on("keyup", function(event) {
                    if (event.keyCode != 13) {
                        clearTimeout(self.timeout);
                        self.timeout = setTimeout(function() {
                            self.search_options(true);
                            self.field.focus();
                        }, 500);
                    }
                });
            this.search = this.widget.find(this.settings.search_selector)
                .on("show.bs.dropdown", function(event) {
                    self.search_options();
                });
            this.element.parents("form").on("submit", function(event) {
                self.finish();
            });
        },

        search_options: function(show_dropdown) {
            if (show_dropdown && this.result.is(":visible") === false) {
                this.search.find("button").dropdown("toggle");
                return;
            }
            this.result.find("li:not(.not-found)").remove();
            this.result.find("li.not-found").hide();
            var selector = "option";
            var query = this.field.val().trim();
            if (query.length > 0) {
                selector += ":contains(" + this.field.val() + ")";
            }
            var opt = this.element.find(selector);
            if (opt.size() === 0) {
                this.result.find("li.not-found").show();
            } else {
                var self = this;
                opt.slice(0,20).each(function(index) {
                    var li = $('<li><a data-value="'+$(this).attr("value")+'">'+$(this).text()+'</a></li>');
                    li.find("a").on("click", function(event) {
                        self.add_selection($(this).attr("data-value"), $(this).text());
                    });
                    self.result.append(li);
                });
            }
        },

        add_selection: function(value, name) {
            if (this.selection.find('[data-value="'+value+'"]').size() === 0) {
                var li = this.selection_li.clone();
                var self = this;
                li.find(".name").text(name);
                li.find("button").attr("data-value", value).on('click', function(event) {
                    $(this).parent("li").remove();
                });
                this.selection.append(li);
            }
        },

        finish: function() {
            this.widget.remove();
            var select = this.element.show();
            select.find("option:selected").prop("selected", false);
            this.selection.find("button").each(function(index) {
                select.find('option[value="'+$(this).attr("data-value")+'"]').prop("selected", true);
            });
        }
    });

    $.fn[pluginName] = function(options) {
        return this.each(function() {
            if (!$.data(this, "plugin_" + pluginName)) {
                $.data(this, "plugin_" + pluginName, new AplusSearchSelect(this, options));
            }
        });
    };
})(jQuery, window, document);
