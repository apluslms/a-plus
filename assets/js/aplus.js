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
});


/**
 * Ajax loaded list tail.
 */
 ;(function($, window, document, undefined) {
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
