$(function() {

    // Mark active menu item
    $("[class^=menu-] a").each(function() {
       if ($(this)[0].pathname === location.pathname) {
        $(this).parent().addClass("active");
       }
    });

    // Mark additional menu items based on data-view-tags
    var tag = $("body").attr("data-view-tag");
    if (tag) {
        var entries = tag.split(",");
        for (var i = 0; i < entries.length; i++) {
            $(".menu-" + entries[i]).addClass("active");
        }
    }

    $('[data-toggle="tooltip"]').tooltip();
    $('.menu-groups').aplusGroupSelect();
    $('.ajax-tail-list').aplusListTail();
    $('.page-modal').aplusModalLink();
    $('.file-modal').aplusModalLink({file:true});
    $('.search-select').aplusSearchSelect();
    $('.filtered-table').aplusTableFilter();

    // Clear notifications once opened.
    $('#notification-alert li a').on("click", function(event) {
      var link = $(this);
      if (!link.hasClass("notification-opened")) {
        link.addClass("notification-opened");
        var n = $('#notification-alert .dropdown-toggle .badge');
        var i = parseInt(n.eq(0).text()) - 1;
        n.text(i);
      }
    });
});

$(function() {

    // Keep the menu visible when scrolling

    var menuHeight = $('#main-course-menu').height() + 100;
    var menuFixed = false;

    var modifyMenu = function() {
        var menu =  $('#main-course-menu');
        if ($(window).scrollTop() > menuHeight && !menuFixed) {
            menu.addClass('fixed');
            menuFixed = true;
        } else if ($(window).scrollTop() < 50 && menuFixed) {
            menu.removeClass('fixed');
            menuFixed = false;
        }
    };

    $(window).bind('scroll', function () {
      modifyMenu();
    });

    $(window).bind('resize', function () {
      modifyMenu();
    });

});

/**
 * Select group using ajax.
 */
(function($, window, document, undefined) {
  "use strict";

  var pluginName = "aplusGroupSelect";
  var defaults = {};

  function AplusGroupSelect(element, options) {
    this.element = $(element);
    this.selection = this.element.find(".selection");
    this.loader = this.element.find(".loader");
    this.settings = $.extend({}, defaults, options);
    this.init();
  }

  $.extend(AplusGroupSelect.prototype, {
    init: function() {
      var self = this;
      this.element.find("form").on("submit", function(event) {
        event.preventDefault();
        self.selection.hide();
        self.loader.removeClass("hidden").show();
        var form = $(this);
        $.ajax(form.attr("action"), {
          type: "POST",
          data: {
            csrfmiddlewaretoken: form.find('input[name="csrfmiddlewaretoken"]').val(),
            group: form.find('button[name="group"]').val()
          },
          dataType: "html"
        }).fail(function() {
          self.selection.show().find("small").text("Error");
          self.loader.hide();
        }).done(function(data) {
          self.selection.show().find("small").html(data);
          self.loader.hide();
          var id = self.selection.find('[data-group-id]').attr("data-group-id");
          $('.submit-group-selector option[value="' + id + '"]').prop('selected', true);
        });
      });
    }
  });

  $.fn[pluginName] = function(options) {
    return this.each(function() {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusGroupSelect(this, options));
      }
    });
  };
})(jQuery, window, document);

/**
 * Highlights code element.
 */

var copyTargetCounter = 0;

$.fn.highlightCode = function(options) {

  return this.each(function() {
    var codeBlock = $(this).clone();
    var wrapper = $('<div></div>');
    wrapper.append(codeBlock);
    $(this).replaceWith(wrapper);

    // Use $(element).highlightCode{noCopy: true} to prevent copy button
    if (!options || !options.noCopy) {
      var buttonContainer = $('<p></p>').prependTo(wrapper);
      var copyButtonContent = $('<span class="glyphicon glyphicon-copy" aria-hidden="true"></span>');
      var copyButtonText = $('<span></span>').text('Copy to clipboard');
      var copyButton = $('<button data-clipboard-target="#clipboard-content-' + copyTargetCounter + '" class="btn btn-xs btn-primary" id="copy-button-' + copyTargetCounter + '"></button>');
      copyButtonContent.appendTo(copyButton);
      copyButtonText.appendTo(copyButton);
      copyButton.appendTo(buttonContainer);

      var hiddenTextarea = $('<textarea id="clipboard-content-' + copyTargetCounter + '" style="display: none; width: 1px; height: 1px;"></textarea>').text(codeBlock.text());
      hiddenTextarea.appendTo(buttonContainer);

      // clipboard.js cannot copy from invisible elements
      copyButton.click(function() {
        hiddenTextarea.show();
      });

      var clipboard = new Clipboard('#copy-button-' + copyTargetCounter);
      clipboard.on("error", function(e) {
          hiddenTextarea.hide();
      });
      clipboard.on("success", function(e) {
          hiddenTextarea.hide();
      });

      copyTargetCounter += 1;

    }

    hljs.highlightBlock(codeBlock[0]);

    // Add line numbers.
    var pre = $(codeBlock);
    var lines = pre.html().split(/\r\n|\r|\n/g);
    var list = $("<table/>").addClass("src");
    for (var i = 1; i <= lines.length; i++) {
        list.append('<tr><td class="num unselectable">' + i + '</td><td class="src">' + lines[i - 1] + '</td></tr>');
    }
    pre.html(list);
  });
};

/**
 * Handle common modal dialog.
 */
(function($, window, document, undefined) {
  "use strict";

  var pluginName = "aplusModal";
  var defaults = {
    loader_selector: ".modal-progress",
    loader_text_selector: ".progress-bar",
    title_selector: ".modal-title",
    content_selector: ".modal-body",
    error_message_attribute: "data-msg-error",
  };

  function AplusModal(element, options) {
    this.element = $(element);
    this.settings = $.extend({}, defaults, options);
    this.init();
  }

  $.extend(AplusModal.prototype, {

    init: function() {
      this.loader = this.element.find(this.settings.loader_selector);
      this.loaderText = this.loader.find(this.settings.loader_text_selector);
      this.title = this.element.find(this.settings.title_selector);
      this.content = this.element.find(this.settings.content_selector);
      this.messages = {
        loading: this.loaderText.text(),
        error: this.loaderText.attr(this.settings.error_message_attribute)
      };
    },

    run: function(command, data) {
      switch(command) {
        case "open":
          this.open(data);
          break;
        case "error":
          this.showError(data);
          break;
        case "content":
          this.showContent(data);
          break;
      }
    },

    open: function(data) {
      this.title.hide();
      this.content.hide();
      this.loaderText
        .removeClass('progress-bar-danger').addClass('active')
        .text(data || this.messages.loading);
      this.loader.show();
      this.element.on("hidden.bs.modal", function(event) {
        $(".dropdown-toggle").dropdown();
      });
      this.element.modal("show");
    },

    showError: function(data) {
      this.loaderText
        .removeClass('active').addClass('progress-bar-danger')
        .text(data || this.messages.error);
    },

    showContent: function(data) {
      this.loader.hide();
      if (data.title) {
        this.title.text(data.title);
        this.title.show();
      }
      if (data.content instanceof jQuery) {
        this.content.empty().append(data.content);
      } else {
        this.content.html(data.content);
      }
      this.content.show();
      return this.content;
    }
  });

  $.fn[pluginName] = function(command, data, options) {
    return this.each(function() {
      var modal = $.data(this, "plugin_" + pluginName);
      if (!modal) {
        modal = new AplusModal(this, options);
        $.data(this, "plugin_" + pluginName, modal);
      }
      return modal.run(command, data);
    });
  };
})(jQuery, window, document);

/**
 * Open links in a modal.
 */
(function($, window, document, undefined) {
   "use strict";

    var pluginName = "aplusModalLink";
    var defaults = {
        modal_selector: "#page-modal",
        file_modal_selector: "#file-modal",
        body_regexp: /<body[^>]*>([\s\S]*)<\/body>/i,
        file: false
    };

    function AplusModalLink(element, options) {
    this.element = $(element);
    this.settings = $.extend({}, defaults, options);
    this.init();
  }

  $.extend(AplusModalLink.prototype, {
    init: function() {
      var link = this.element;
      var settings = this.settings;
      link.on("click", function(event) {
        event.preventDefault();
        var url = link.attr("href");
        if (url === "" || url == "#") {
          return false;
        }
        var modal = $(settings.file ? settings.file_modal_selector : settings.modal_selector);
        modal.aplusModal("open");
        $.get(url, function(data) {
          if (settings.file) {
            var text = $("<pre/>").text(data);
            modal.aplusModal("content", {
              title: link.text(),
              content: text,
            });
            text.highlightCode();
          } else {
            var match = data.match(settings.body_regexp);
            if (match !== null && match.length == 2) {
              data = match[1];
            }
            var c = modal.aplusModal("content", { content: data });
            c.find('.file-modal').aplusModalLink({file:true});
            c.find('pre.hljs').highlightCode();
            modal.trigger("opened.aplus.modal");
          }
        }).fail(function() {
          modal.aplusModal("error");
        });
      });
    }
  });

  $.fn[pluginName] = function(options) {
    return this.each(function() {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusModalLink(this, options));
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
                self.addSelection($(this).attr("value"), $(this).text());
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
            /* Browser can't validate if valid selection is done, so leave that work for django
             * FIXME: instead of setting the selection in the end, we should add selection in .addSelection
             *        and we should remove it when li button is clicked (anom. in .addSelection).
             */
            this.element.removeAttr('required');
        },

        searchOptions: function(show_dropdown) {
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
                        self.addSelection($(this).attr("data-value"), $(this).text());
                    });
                    self.result.append(li);
                });
            }
        },

        addSelection: function(value, name) {
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

        resetSelection: function(values) {
          this.selection.empty();
          var self = this;
          $.each(values, function(index, value) {
            var opt = self.element.find('option[value="' + value + '"]');
            if (opt.size() == 1) {
              self.addSelection(value, opt.text());
            }
          });
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
})(jQuery, window, document);

/**
 * Table row filter.
 */
(function($, window, document, undefined) {
    "use strict";

    var pluginName = "aplusTableFilter";
    var defaults = {};

    function AplusTableFilter(element, options) {
        this.element = $(element);
        this.filters = null;
        this.timeout = null;
        if (this.element.prop("tagName") == "TABLE") {
            this.settings = $.extend({}, defaults, options);
            this.init();
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
          var filterRow = $('<tr></tr>');
          for (var i = 0; i < columnCount; i++) {
            this.filters.push('');
            var filterInput = $('<input type="text" data-column="'+i+'">')
              .on('keyup', filterDelay).on('change', filterDelay);
            var filterCell = $('<td></td>');
            filterCell.append(filterInput);
            filterRow.append(filterCell);
          }
          this.element.find('thead').append(filterRow);
        },

        filterColumn: function(input) {
          var column = input.attr('data-column');
          var query = input.val();
          this.filters[column] = query.trim();
          this.filterTable();
        },

        filterTable: function() {
          var self = this;
          this.element.find('tbody').find('tr').hide().filter(function() {
            var pass = true;
            $(this).find('td').each(function(i) {
              if (self.filters[i] && $(this).text().toLowerCase().indexOf(self.filters[i].toLowerCase()) < 0) {
                pass = false;
                return false;
              }
            });
            return pass;
          }).show();
        }
    });

    $.fn[pluginName] = function(options) {
        return this.each(function() {
            if (!$.data(this, "plugin_" + pluginName)) {
                $.data(this, "plugin_" + pluginName, new AplusTableFilter(this, options));
            }
        });
    };
})(jQuery, window, document);


/**
 * prevent double submit of exercise forms
 */

$(function () {
    $('#exercise-page-content form, #exercise form').each(function () {
        $(this).on('submit', function (e) {
            var $form = $(this)
            //disable the button
            $form.find('[type="submit"]').prop('disabled', true)
            // Keep chainability
            return this;
        });
    });
});
