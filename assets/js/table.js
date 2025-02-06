$(function() {
  "use strict";

  $('.filtered-table, .ordered-table, .grouped-table').aplusTable();
});

/**
 * Table utilities: filtering, ordering and grouping.
 *
 * Use these classes on the `table` element to enable these features:
 * - `filtered-table`
 * - `ordered-table`
 * - `grouped-table`
 *
 * Use these attributes on `th` elements:
 * - `data-filter-type`:
 *   - `none`: Disable filtering for this column.
 *   - `options`: This column is filtered using a series of check boxes instead
 *     of a text field.
 *   - unspecified or any other value: This column is filtered using a text
 *     field.
 * - `data-filter-options`: The options for filtering this column when
 *   `data-filter-type` is `options`, separated by pipes (`|`).
 * - `data-order-disable`: If true, ordering is disabled for this column.
 * - `data-group-checkbox`: If true, the checkbox in this column on parent rows
 *   will match the checkboxes of child rows.
 *
 * Use these attributes on `tr` elements:
 * - `data-group-parent`: Indicates that this is the parent row of a group.
 * - `data-group-child`: Indicates that this is a child row of a group.
 *
 */
(function($, document, undefined) {
  "use strict";

  const pluginName = "aplusTable";
  var defaults = {};
  var translationsReady = false;

  function AplusTable(element, options) {
    this.element = $(element);
    this.enable_filter = this.element.hasClass('filtered-table');
    this.enable_order = this.element.hasClass('ordered-table');
    this.enable_group = this.element.hasClass('grouped-table');
    this.filters = null;
    this.timeout = null;
    if (this.element.prop("tagName") == "TABLE") {
      this.settings = $.extend({}, defaults, options);
      const self = this;

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

  $.extend(AplusTable.prototype, {

    init: function() {
      const self = this;

      const dataDefaultSortColumn = self.element.data('default-sort-column');
      const dataDefaultSortOrder = self.element.data('default-sort-order');
      if (dataDefaultSortColumn && dataDefaultSortOrder) {
        const defaultColumnHeader = self.element.find('thead > tr > th').eq(dataDefaultSortColumn);
        const orderMarker = $('<span class="order-marker gi-caret-down-fill" aria-hidden="true"></span>');
        defaultColumnHeader.append(orderMarker);
        self.orderTable(dataDefaultSortColumn, dataDefaultSortOrder === 'desc' ? true : false);
      }

      function filterDelay(event) {
        const input = $(this);
        clearTimeout(self.timeout);
        self.timeout = setTimeout(function() {
          self.filterColumn(input);
        }, 500);
      };

      function filterColumnWithOptions(event) {
        const option = $(this);
        $(this.form.elements).not(option).prop('checked', false);
        const query = option.prop('checked') ? option.prop('value') : '';
        const filter = [normalFilter, query, query, false];
        self.filters[option.data('column')] = filter;
        self.filterTable();
      };

      function orderColumn(event) {
        event.preventDefault();
        const isDescending = $(this).hasClass('desc');
        self.element.find('thead > tr > th > a > .order-marker').remove();
        const orderMarker = $('<span class="order-marker gi-caret-up-fill" aria-hidden="true"></span>');
        if (isDescending) {
          $(this).removeClass('desc');
        } else {
          $(this).addClass('desc');
          orderMarker.removeClass('gi-caret-up-fill').addClass('gi-caret-down-fill');
        }
        $(this).append(orderMarker);
        self.orderTable($(this).data('column'), !isDescending);
      };

      function expandRow(event) {
        event.preventDefault();
        const button = $(this);
        const expanded = !button.data('group-expanded');
        const groupId = button.closest('tr').data('group-parent');
        self.element
          .find('tbody > tr[data-group-child="' + groupId + '"]')
          .toggleClass('hidden-group', !expanded);
        self.updateExpandButton(button, expanded);
      };

      function expandAllRows(event) {
        event.preventDefault();
        const button = $(this);
        const expanded = !button.data('group-expanded');
        self.element
          .find('tbody > tr[data-group-child]')
          .toggleClass('hidden-group', !expanded);
        self.updateExpandButton(button, expanded);
        self.updateExpandButton(self.element.find('tbody > tr > td:first-child > button'), expanded);
      };

      if (self.enable_group) {
        const parentRows = this.element.find('tbody > tr[data-group-parent]').each(function() {
          // Add expand buttons to group parent rows
          const expandButton = $('<button></button>')
            .addClass('aplus-button--secondary aplus-button--xs')
            .on('click', expandRow);
          $(this).prepend($('<td></td>').append(expandButton));
          self.updateExpandButton(expandButton, false);
        });

        if (parentRows.length > 0) {
          // Add "expand all" button to header
          const expandButton = $('<button></button>')
            .addClass('aplus-button--secondary aplus-button--xs')
            .on('click', expandAllRows);
          this.element.find('thead > tr').prepend(
            $('<th data-filter-type="none" data-order-disable="true"></th>')
              .append(expandButton)
          );
          this.updateExpandButton(expandButton, false);

          // Add empty cells to rows that don't have an expand button
          this.element
            .find('tbody > tr:not([data-group-parent])')
            .prepend('<td></td>');
        }
      }

      let filterRow = undefined;
      if (this.enable_filter) {
        this.filters = [];
        filterRow = $('<tr class="tableexport-ignore"></tr>')
          .appendTo(this.element.find('thead'));
      }

      this.element.find('thead > tr > th').each(function(i) {
        const column = $(this);

        if (self.enable_filter) {
          self.filters.push('');
          const filterType = column.data('filter-type');
          if (filterType === 'none') {
            filterRow.append($('<td/>'));
          }
          else if (filterType === 'options') {
            const filterForm = $('<form/>');
            const filterOptions = column.data('filter-options').trim().split('|');
            filterOptions.forEach(function(option) {
              const input = $('<input type="checkbox">')
                .attr('value', option)
                .data('column', i)
                .on('change', filterColumnWithOptions);
              const label = $('<label/>')
                .append(input)
                .append('&nbsp;' + option + '&nbsp;');
              filterForm.append(label);
            });
            const filterCell = $('<td/>').append(filterForm);
            filterRow.append(filterCell);
          }
          else {
            const filterInput =
              $('<input type="text" class="form-control" data-column="' + i + '">')
              .attr({
                'placeholder': _('Filter'),
                'aria-label': _('Filter')
              })
              .on('keyup', filterDelay).on('change', filterDelay);

            const filterCell = $(
              '<td data-bs-toggle="tooltip" title="'
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
        }
        if (self.enable_order && !column.data('order-disable')) {
          if (dataDefaultSortColumn === i - 1 && dataDefaultSortOrder === 'desc') {
            column.wrapInner($('<a href="#" data-column="' + i + '" class="desc"></a>').on('click', orderColumn));
          } else {
            column.wrapInner($('<a href="#" data-column="' + i + '"></a>').on('click', orderColumn));
          }
        }

        if (self.enable_group && column.data('group-checkbox')) {
          // Synchronized checkboxes:
          // Parent checkbox will be checked if all children are checked,
          // unchecked if all children are unchecked, and indeterminate if some
          // but not all children are checked.
          self.findCheckBoxes('parent', null, i).on('click', function() {
            const groupId = $(this).closest('tr').data('group-parent');
            self.findCheckBoxes('child', groupId, i).prop('checked', $(this).prop('checked'));
          });
          self.findCheckBoxes('child', null, i).on('click', function() {
            const groupId = $(this).closest('tr').data('group-child');
            const checkboxes = self.findCheckBoxes('child', groupId, i);
            const allCount = checkboxes.length;
            const checkedCount = checkboxes.filter(':checked').length;
            const props = {
              checked: checkedCount === allCount,
              indeterminate: checkedCount > 0 && checkedCount < allCount,
            };
            self.findCheckBoxes('parent', groupId, i).prop(props);
          });
        }
      });
    },

    filterGetType: function(query) {
      var isDate = false;
      if (!query) {
        // Empty query, no filtering
        return [undefined, "", query, isDate];
      }

      if (query.startsWith("<=")) {
        isDate = checkForDate(query.slice(2));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(2))
          : requireNumber(query.slice(2));
        const filter = isDate ? lteFilterDate : lteFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.startsWith("<")) {
        isDate = checkForDate(query.slice(1));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(1))
          : requireNumber(query.slice(1));
        const filter = isDate ? ltFilterDate : ltFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.startsWith(">=")) {
        isDate = checkForDate(query.slice(2));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(2))
          : requireNumber(query.slice(2));
        const filter = isDate ? gteFilterDate : gteFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.startsWith(">")) {
        isDate = checkForDate(query.slice(1));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(1))
          : requireNumber(query.slice(1));
        const filter = isDate ? gtFilterDate : gtFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.startsWith("==")) {
        isDate = checkForDate(query.slice(2));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(2))
          : query.slice(2);
        const filter = isDate ? eFilterDate : eFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.startsWith("!=")) {
        isDate = checkForDate(query.slice(2));
        const parsedQuery = (isDate)
          ? Date.parse(query.slice(2))
          : query.slice(2);
        const filter = isDate ? neFilterDate : neFilter;
        return [filter, parsedQuery, query, isDate];
      } else if (query.match(/\//g) && query.match(/\//g).length >= 2) {
        const parts = query.split('/');
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
          .removeAttr("title data-original-title");
      }
      this.filterTable();
    },

    filterTable: function() {
      const self = this;
      const visibleGroupIds = new Set();
      this.element
        .find('tbody')
        .find('tr')
        .not('.no-filtering')
        .addClass('hidden-filter')
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
          if (pass) {
            const groupId = $(this).data('group-child');
            if (groupId) {
              visibleGroupIds.add($(this).data('group-child'));
            }
          }
          return pass;
        }).removeClass('hidden-filter');

      if (visibleGroupIds.size > 0) {
        // Show parent rows that have children that are not hidden
        const parentRows = this.element.find('tbody > tr[data-group-parent]');
        parentRows.each(function() {
          if (visibleGroupIds.has($(this).data('group-parent'))) {
            $(this).removeClass('hidden-filter');
          }
        });
      }

      // Add #selected-number to e.g. span tag to get count of rows after filter
      const visibleRows = this.element.
        find('tbody').
        find('tr:visible').
        not('.no-filtering').length;
      if ($("#selected-number").length) {
        $("#selected-number").text(visibleRows);
      }
    },

    orderTable: function(index, isDescending) {
      function compareRows(aRow, bRow) {
        const aCell = $(aRow).find('td').eq(index);
        const bCell = $(bRow).find('td').eq(index);
        const aDate = aCell.data('datetime');
        const bDate = bCell.data('datetime');
        if (aDate && bDate) {
          return isDescending ? bDate.localeCompare(aDate) : aDate.localeCompare(bDate);
        }
        const aText = aCell.text().trim();
        const bText = bCell.text().trim();
        const aNumber = Number(aText);
        const bNumber = Number(bText);
        if (!isNaN(aNumber) && !isNaN(bNumber)) {
          return isDescending ? bNumber - aNumber : aNumber - bNumber;
        }
        return isDescending ? bText.localeCompare(aText) : aText.localeCompare(bText);
      }

      // Order the top-level rows first.
      // Don't remove the rows before appending them again. It's useless
      // because append() already moves nodes instead of cloning, and
      // removing the nodes causes them to lose their event handlers.
      const rows = this.element.find('tbody > tr:not([data-group-child])');
      this.element.find('tbody').append(rows.sort(compareRows));

      // Then order each group's child rows (if the table is grouped).
      if (this.enable_group) {
        const parentRows = this.element.find('tbody > tr[data-group-parent]');
        const self = this;
        parentRows.each(function() {
          const groupId = $(this).data('group-parent');
          const childRows = self.element.find('tbody > tr[data-group-child="' + groupId + '"]');
          $(this).after(childRows.sort(compareRows));
        });
      }
    },

    updateExpandButton: function(button, expanded) {
      const label = expanded ? '-' : '+';
      const tooltip = expanded ? _('Collapse') : _('Expand');
      button
        .data('group-expanded', expanded)
        .text(label)
        .attr({
          'aria-expanded': expanded,
          'title': tooltip,
          'aria-label': tooltip
        });
    },

    findCheckBoxes: function(type, groupId, columnIndex) {
      // Builds a jQuery selector like 'tbody > tr[data-group-parent="1.1"] > td:nth-child(9) > input[type="checkbox"]'
      // Note that nth-child uses 1-based indexing.
      let selector = 'tbody > tr[data-group-' + type;
      if (groupId) {
        selector += '="' + groupId + '"';
      }
      selector += '] > td:nth-child(' + (columnIndex + 1) + ') > input[type="checkbox"]';
      return this.element.find(selector);
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
      $.data(this, "plugin_" + pluginName, new AplusTable(this, options));
    });
  };

})(jQuery, document);

/* vim: set et ts=4 sw=4: */
