$(function() {
    "use strict";

    $('.filtered-table').aplusTableFilter();
});

/**
 * Table row filter.
 */
(function($, document, undefined) {
    "use strict";

    const pluginName = "aplusTableFilter";
    var defaults = {};
    var translationsReady = false;

    function AplusTableFilter(element, options) {
        this.element = $(element);
        this.filters = null;
        this.timeout = null;
        if (this.element.prop("tagName") == "TABLE") {
            this.settings = $.extend({}, defaults, options);
            var self = this;

            // translationsReady allows us to use the plugin multiple times on same page
            if (translationsReady) {
                self.init();
            } else {
                $(document).on("aplus:translation-ready", function() {
                    translationsReady = true;
                    self.init();
                });
            }
        }
    }

    $.extend(AplusTableFilter.prototype, {

        init: function() {
            var columnCount = 0;
            this.element.find('thead').find('tr').each(function() {
                var count = $(this).find('th').size();
                columnCount = count > columnCount ? count : columnCount;
            });

            var self = this;
            var filterDelay = function(event) {
                var input = $(this);
                clearTimeout(self.timeout);
                self.timeout = setTimeout(function() {
                    self.filterColumn(input);
                }, 500);
            };

            this.filters = [];
            var filterRow = $('<tr class="tableexport-ignore"></tr>');
            for (var i = 0; i < columnCount; i++) {
                this.filters.push('');
                var filterInput =
                    $('<input type="text" data-column="' + i + '">')
                    .on('keyup', filterDelay).on('change', filterDelay);


                var filterCell = $(
                    '<td data-toggle="tooltip" title="'
                    + _(
                        "Comparison operators >, <, >=, <=, !=, == are available — e.g. >=200."
                        + " Datetime comparison is available in format yyyy-mm-dd hh:mm"
                        + " — e.g. >=0918-09-20 15:00."
                        + " Regex is available — e.g. /^\\d+$/g."
                        + " Use dot as decimal seperator — e.g. 2.1."
                        )
                    + '"></td>'
                );
                filterCell.append(filterInput);
                filterRow.append(filterCell);
            }
            this.element.find('thead').append(filterRow);
        },

        filterGetType: function(query) {
            var isDate = false;
            if (!query) {
                // Empty query, no filtering
                return [undefined, "", query, isDate];
            }

            if (query.startsWith("<=")) {
                isDate = checkForDate(query.slice(2));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(2))
                    : requireNumber(query.slice(2));
                var filter = isDate ? lteFilterDate : lteFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.startsWith("<")) {
                isDate = checkForDate(query.slice(1));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(1))
                    : requireNumber(query.slice(1));
                var filter = isDate ? ltFilterDate : ltFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.startsWith(">=")) {
                isDate = checkForDate(query.slice(2));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(2))
                    : requireNumber(query.slice(2));
                var filter = isDate ? gteFilterDate : gteFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.startsWith(">")) {
                isDate = checkForDate(query.slice(1));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(1))
                    : requireNumber(query.slice(1));
                var filter = isDate ? gtFilterDate : gtFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.startsWith("==")) {
                isDate = checkForDate(query.slice(2));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(2))
                    : query.slice(2);
                var filter = isDate ? eFilterDate : eFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.startsWith("!=")) {
                isDate = checkForDate(query.slice(2));
                var parsedQuery = (isDate)
                    ? Date.parse(query.slice(2))
                    : query.slice(2);
                var filter = isDate ? neFilterDate : neFilter;
                return [filter, parsedQuery, query, isDate];
            } else if (query.match(/\//g) && query.match(/\//g).length >= 2) {
                var parts = query.split('/');
                var regex = query;
                var options = "";

                if (parts.length > 1) {
                    regex = parts[1];
                    options = parts[2];
                }
                try {
                    // If no error is thrown here, the query is valid regex
                    return [regexFilter, new RegExp(regex, options), query, isDate];
                } catch (e) {
                    // If the query is not valid regex, use normal filter
                    isDate = checkForDate(query);
                    return [normalFilter, undefined, query, isDate];
                }
            } else {
                isDate = checkForDate(query);
                return [normalFilter, query, query, isDate];
            }
        },

        filterColumn: function(input) {
            const column = input.data('column');
            const query = input.val();
            const popoverTitle =
                _("There might be something wrong with the filter."
                + " Some comparison operators only accept numbers."
                + " If you are using datetime, make sure the format is correct."
                + " If you are using regex, make sure it is correct.");
            this.filters[column] = this.filterGetType(query.trim());
            if (this.filters[column][1] === undefined) {
                input.popover("destroy")
                    .popover({
                        trigger: "manual",
                        title: popoverTitle,
                        placement: "top"
                    })
                    .popover("toggle");

                input.on('hide.bs.popover', function(event) {
                    event.preventDefault();
                });
            } else {
                input.off('hide.bs.popover');
                input.popover("destroy")
                    .removeAttr("class title data-original-title");
            }
            this.filterTable();
        },

        filterTable: function() {
            const self = this;
            this.element
                .find('tbody')
                .find('tr')
                .not('.no-filtering')
                .hide()
                .filter(function() {
                    var pass = true;
                    $(this).find('td').each(function(i) {
                        const filter = self.filters[i][0];
                        const parsedQuery = self.filters[i][1]
                        const origQuery = self.filters[i][2];
                        const isDate = self.filters[i][3];
                        const tdData = isDate ?
                            $(this).data("datetime")
                            : $(this).text().trim();
                        if (
                            filter !== undefined &&
                            parsedQuery !== undefined &&
                            !filter.apply(
                                this,
                                [tdData, parsedQuery, origQuery]
                            )
                        ) {
                            pass = false;
                            return false;
                        }
                    });
                    return pass;
                }).show();

            // Add #selected-number to e.g. span tag to get count of rows after filter
            var visibleRows = this.element.
                find('tbody').
                find('tr:visible').
                not('.no-filtering').length;
            if ($("#selected-number").length) {
                $("#selected-number").text(visibleRows);
            }
        },
    });

    function checkForDate(query) {
        return isNaN(query) && !isNaN(Date.parse(query));
    }

    function requireNumber(query) {
        return isNaN(query) || query === "" ? undefined : parseFloat(query);
    }

    function lteFilter(text, parsedQuery, origQuery) {
        return parseFloat(text) <= parsedQuery;
    }

    function lteFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) <= parsedQuery;
    }

    function ltFilter(text, parsedQuery, origQuery) {
        return parseFloat(text) < parsedQuery;
    }

    function ltFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) < parsedQuery;
    }

    function gteFilter(text, parsedQuery, origQuery) {
        return parseFloat(text) >= parsedQuery;
    }

    function gteFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) >= parsedQuery;
    }

    function gtFilter(text, parsedQuery, origQuery) {
        return parseFloat(text) > parsedQuery;
    }

    function gtFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) > parsedQuery;
    }

    function eFilter(text, parsedQuery, origQuery) {
        return text == parsedQuery;
    }

    function eFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) == parsedQuery;
    }

    function neFilter(text, parsedQuery, origQuery) {
        return text != parsedQuery;
    }

    function neFilterDate(text, parsedQuery, origQuery) {
        return Date.parse(text) != parsedQuery;
    }

    function regexFilter(text, regExp, origQuery) {
        return regExp.test(text);
    }

    function normalFilter(text, parsedQuery, origQuery) {
        return text.toLowerCase().indexOf(origQuery.toLowerCase()) >= 0;
    }

    $.fn[pluginName] = function(options) {
        return this.each(function() {
            $.data(this, "plugin_" + pluginName, new AplusTableFilter(this, options));
        });
    };

})(jQuery, document);

/* vim: set et ts=4 sw=4: */
