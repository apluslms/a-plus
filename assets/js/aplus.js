/**
 * Add CustomEvent for IE 11
 */
(function (window, document, undefined) {
  "use strict";

  if (typeof window.CustomEvent === "function") return false;

  function CustomEvent(event, params) {
    const bubbles = params.bubbles !== undefined ? params.bubbles : false;
    const cancelable = params.cancelable !== undefined ? params.cancelable : false;
    const detail = params.detail !== undefined ? params.detail : undefined;
    const evt = document.createEvent('CustomEvent');
    evt.initCustomEvent(event, bubbles, cancelable, detail);
    return evt;
  }
  CustomEvent.prototype = window.Event.prototype;
  window.CustomEvent = CustomEvent;
})(window, document);


/**
* Copy the hl (language) query parameter from the window location to the given
* query string (type string, e.g., "?foo=bar").
* If override is true, override a potentially existing hl parameter
* in the query.
*/
function copyWindowHlParamToQuery(query, override) {
  const windowParams = new URLSearchParams(window.location.search);
  const queryParams = new URLSearchParams(query);
  const windowhl = windowParams.get('hl');
  if (windowhl !== null && (override || !queryParams.has('hl'))) {
    queryParams.set('hl', windowhl);
    return queryParams.toString(); // This does not include the question mark '?'.
  }
  return query;
}

/**
* Copy the hl (language) query parameter from the window location to the given
* URL (type string).
* If override is true, override a potentially existing hl parameter
* in the query.
*/
function copyWindowHlParamToUrl(url, override) {
  const urlObj = new URL(url, window.location);
  urlObj.search = copyWindowHlParamToQuery(urlObj.search, override);
  // As an unintended side effect, this converts any relative URL to absolute.
  return urlObj.href;
}


$(function () {
  "use strict";

  // Mark active menu item
  $("[class^=menu-] a").each(function () {
    if ($(this)[0].pathname === location.pathname) {
      $(this).addClass("active");
    }
  });

  // Mark additional menu items based on data-view-tags
  const tag = $("body").attr("data-view-tag");
  if (tag) {
    const entries = tag.split(",");
    for (var i = 0; i < entries.length; i++) {
      $(".menu-" + entries[i]).addClass("active");
    }
  }

  $('[data-bs-toggle="tooltip"]').tooltip();
  $('.menu-groups').aplusGroupSelect();
  $('.ajax-tail-list').aplusListTail();
  $('.page-modal').aplusModalLink();
  $('.file-modal').aplusModalLink({ file: true });

  // Clear notifications once opened.
  $('#notification-alert li a').on("click", function (event) {
    const link = $(this);
    if (!link.hasClass("notification-opened")) {
      link.addClass("notification-opened");
      var n = $('#notification-alert .dropdown-toggle .badge');
      var i = parseInt(n.eq(0).text()) - 1;
      n.text(i);
    }
  });

  // Keep the menu visible when scrolling
  const menuHeight = $('#main-course-menu').height() + 100;
  var menuFixed = false;
  var sidebarCollapsed = false;

  var modifyMenu = function () {
    var menu = $('#main-course-menu');
    if (!menuFixed && !sidebarCollapsed && $(window).scrollTop() > menuHeight) {
      var w = menu.width();
      menu.addClass('fixed');
      menu.css('width', "" + w + "px");
      menuFixed = true;
    } else if (menuFixed && $(window).scrollTop() < 50) {
      menu.removeClass('fixed');
      menu.css('width', '');
      menuFixed = false;
    }
  };

  var updateMenu = function () {
    var menu = $('#main-course-menu');
    if (menuFixed) {
      menu.removeClass('fixed');
      menu.css('width', '');
      menuFixed = false;
      modifyMenu();
    }
  };

  $(window).on('scroll', modifyMenu);
  $(window).on('resize', updateMenu);

  function setSidebarState(collapsed) {
    sidebarCollapsed = collapsed;
    $('#course-content').toggleClass('sidebar-collapsed', collapsed);
    $('#course-sidebar').toggleClass('d-sm-block', !collapsed);
    $('.course-sidebar-expander').toggleClass('d-none', !collapsed);
    localStorage.setItem('sidebarCollapsed', collapsed);
    if (!collapsed) {
      modifyMenu();
    }
  };

  if (localStorage.getItem('sidebarCollapsed') === 'true') {
    setSidebarState(true);
  }

  $('.course-sidebar-collapser').on('click', function () {
    setSidebarState(true);
  });

  $('.course-sidebar-expander').on('click', function () {
    setSidebarState(false);
  });

  /**
  * Warn about links that open in new windows.
  */

  function addLinkType(link, type) {
    let linkTypes = (link.getAttribute('rel') || '').split(' ');
    if (!linkTypes.includes(type)) {
      linkTypes.push(type);
    }
    link.setAttribute('rel', linkTypes.join(' ').trim());
  }

  function addExternalLinkIcon(link) {
    if (!link.querySelector('.icon')) {
      link.insertAdjacentHTML('beforeend', `<i class="icon bi-box-arrow-up-right"></i>`);
    }
  }

  function addScreenReaderMessage(link, message) {
    if (!link.querySelector('.visually-hidden')) {
      link.insertAdjacentHTML('beforeend', `<span class="visually-hidden"> (${message})</span>`);
    }
  }
  $(document).on("aplus:translation-ready", function () {
    document.querySelectorAll('a[target="_blank"]').forEach(link => {
      addLinkType(link, 'noopener');
      addExternalLinkIcon(link);
      addScreenReaderMessage(link, _('opens in a new tab'));
    });
  });

  // Simple visibility toggling: add data-bs-toggle="visibility" and
  // data-bs-target="<selector>" to toggle the visibility of all elements that
  // match <selector>.
  $(document).on('click', '[data-bs-toggle="visibility"]', function (event) {
    event.preventDefault();
    const targetSelector = $(this).data('bs-target');
    $(targetSelector).toggleClass('d-none');
  });
});

/**
* Select group using ajax.
*/
(function ($) {
  "use strict";

  const pluginName = "aplusGroupSelect";
  var defaults = {};

  function AplusGroupSelect(element, options) {
    this.element = $(element);
    this.selection = this.element.find(".selection");
    this.loader = this.element.find(".loader");
    this.settings = $.extend({}, defaults, options);
    this.init();
  }

  $.extend(AplusGroupSelect.prototype, {
    init: function () {
      var self = this;
      this.element.find("form").on("submit", function (event) {
        event.preventDefault();
        self.selection.hide();
        self.loader.removeClass("d-none").show();
        var form = $(this);
        $.ajax(form.attr("action"), {
          type: "POST",
          data: {
            csrfmiddlewaretoken: form.find('input[name="csrfmiddlewaretoken"]').val(),
            group: form.find('button[name="group"]').val()
          },
          dataType: "html"
        }).fail(function () {
          self.selection.show().find("small").text("Error");
          self.loader.hide();
        }).done(function (data) {
          self.selection.show().find("small").html(data);
          self.loader.hide();
          var id = self.selection.find('[data-group-id]').attr("data-group-id");
          $('.submit-group-selector option[value="' + id + '"]').prop('selected', true);
        });
      });
    }
  });

  $.fn[pluginName] = function (options) {
    return this.each(function () {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusGroupSelect(this, options));
      }
    });
  };
})(jQuery);

/**
* Highlights code element.
*/
(function ($) {
  "use strict";

  var copyTargetCounter = 0;

  // Helper function that adds a button based on a configuration
  function addButton(buttonContainer, buttonOptions) {
    const button = $('<button class="aplus-button--secondary aplus-button--xs"></button>');
    if (buttonOptions.action) {
      button.on('click', buttonOptions.action);
    }
    if (buttonOptions.attrs) {
      button.attr(buttonOptions.attrs);
    }
    if (buttonOptions.icon) {
      const buttonContent = $('<i class="bi-' + buttonOptions.icon + '" aria-hidden="true"></i>');
      buttonContent.appendTo(button);
      if (buttonOptions.toggle) {
        button.on('click', function () {
          buttonContent.toggleClass('bi-square bi-check-square');
        });
      }
    }
    if (buttonOptions.text) {
      const buttonText = $('<span></span>').text(' ' + buttonOptions.text);
      buttonText.appendTo(button);
    }
    button.appendTo(buttonContainer);
    buttonContainer.append(' ');
  }

  $.fn.highlightCode = function (options) {

    return this.each(function () {
      const codeBlock = $(this).clone();
      const wrapper = $('<div></div>');
      wrapper.append(codeBlock);
      $(this).replaceWith(wrapper);

      const buttonContainer = $('<p></p>').prependTo(wrapper);

      // Use $(element).highlightCode({noCopy: true}) to prevent copy button
      if (!options || !options.noCopy) {
        const hiddenTextarea = $('<textarea id="clipboard-content-' + copyTargetCounter + '" style="display: none; width: 1px; height: 1px;"></textarea>').text(codeBlock.text());
        hiddenTextarea.appendTo(buttonContainer);

        addButton(buttonContainer, {
          action: function () {
            // clipboard.js cannot copy from invisible elements
            hiddenTextarea.show();
          },
          attrs: {
            'data-clipboard-target': '#clipboard-content-' + copyTargetCounter,
            'id': 'copy-button-' + copyTargetCounter
          },
          icon: 'copy',
          text: _('Copy to clipboard')
        });

        const clipboard = new ClipboardJS('#copy-button-' + copyTargetCounter);
        clipboard.on("error", function (e) {
          hiddenTextarea.hide();
        });
        clipboard.on("success", function (e) {
          hiddenTextarea.hide();
        });

        copyTargetCounter += 1;
      }

      // If the URL ends with a file extension or "Dockerfile", set language for highlight.js manually.
      // The programming language is detected automatically if highlight.js does not know the file extension or
      // the URL does not end with a file extension.
      const url = codeBlock.attr('data-url');
      if (url) {
        let fileExtOrAlias = "";
        const splitUrl = url.split('.');
        if (splitUrl.length > 1) { // Has file extension
          fileExtOrAlias = splitUrl.pop().split('?')[0];
        } else if (splitUrl.pop().endsWith("Dockerfile")) {
          fileExtOrAlias = "dockerfile";
        }
        if (fileExtOrAlias === "m") {
          fileExtOrAlias = "matlab";
        }
        if (fileExtOrAlias) {
          codeBlock.addClass('hljs language-' + fileExtOrAlias);
        }
      }

      const pre = $(codeBlock);
      const table = $('<table/>').addClass('src');

      if (!options || !options.noHighlight) {
        hljs.highlightElement(codeBlock[0]);

        // Add line numbers
        const lines = pre.html().split(/\r\n|\r|\n/g);
        const textLines = pre.text().split(/\r\n|\r|\n/g);
        const maxLinesToShow = Math.min(lines.length, 5000);
        let currentLinesToShow = maxLinesToShow; // Initial number of lines to show
        let testLineNumber = 0, comparedLineNumber = 0, originalLineNumber = 0;
        const filename = pre.data('filename');

        const testId = () => {
          testLineNumber++;
          return `data-testid="${filename}-line-${testLineNumber}"`;
        }

        const getNormalRow = (lineNumber, lineContent) => {
          return `<td class="num unselectable">${lineNumber}</td><td class="src" ${testId()}>${lineContent}</td>`;
        }

        const getDiffRow = (lineNumber, lineContent, textContent) => {
          const diffCode = textContent.slice(0, 2);
          let backgroundColorClass;
          if (diffCode === '+ ') {
            originalLineNumber++;
            backgroundColorClass = 'new';
          } else if (diffCode === '- ') {
            comparedLineNumber++;
            backgroundColorClass = 'old';
          } else {
            comparedLineNumber++;
            originalLineNumber++;
            backgroundColorClass = '';
          }
          const showComparedLineNumber = (diffCode === '  ' || diffCode === '- ') ? comparedLineNumber : '';
          const showOriginalLineNumber = (diffCode === '  ' || diffCode === '+ ') ? originalLineNumber : '';
          return `
            <td class="num unselectable ${backgroundColorClass}">${showComparedLineNumber}</td>
            <td class="num unselectable ${backgroundColorClass}">${showOriginalLineNumber}</td>
            <td class="src ${backgroundColorClass}" ${testId()}>${lineContent}</td>
          `
        }

        const getRow = options.compareMode ? getDiffRow : getNormalRow;

        const getLines = (start, end) => {
          const fragment = document.createDocumentFragment();

          for (let i = start; i <= end; i++) {
            const row = $('<tr>').append(getRow(i, lines[i - 1], textLines[i - 1]));
            fragment.appendChild(row[0]);
          }

          return fragment;
        };

        const showMoreLines = (button) => {
          const fragment = getLines(currentLinesToShow + 1, Math.min(currentLinesToShow + maxLinesToShow, lines.length));
          table.append(fragment);
          currentLinesToShow += maxLinesToShow;

          if (currentLinesToShow >= lines.length) {
            // All lines loaded, hide the "Load more" button
            button.hide();
          }
        };

        const initialLines = getLines(1, maxLinesToShow);
        table.append(initialLines);
        pre.html(table);

        if (lines.length > maxLinesToShow) {
          const loadMoreButton = $('<button class="aplus-button--default aplus-button--sm" style="width: 100%;">').text(_('Load more'));
          loadMoreButton.click(() => showMoreLines(loadMoreButton));
          pre.after(loadMoreButton);
        }
      } else if (!options || !options.noWrap) {
        table.append('<tr><td class="src">' + pre.html() + '</td></tr>');
        pre.html(table);
      }

      if (!options || !options.noWrap) {
        const toggleWrap = function (parent, iconSelector, localStorageKey) {
          const doWrap = localStorage.getItem(localStorageKey) === 'true';
          localStorage.setItem(localStorageKey, !doWrap);

          const tabPanes = parent.children('.tab-pane');
          tabPanes.each(function () {
            const element = $(this);
            element.find('table.src').toggleClass('no-wrap');

            // 'Word wrap' buttons for other tabs will be out of sync unless we manually sync their state
            if (!element.hasClass('active')) {
              element
                .find(iconSelector)
                .toggleClass('bi-square')
                .toggleClass('bi-check-square');
            }
          });
        };

        let action, iconSelector, localStorageKey;
        if ($('.submission-container').find(buttonContainer).length > 0) {
          // buttonContainer is related to submitted files on inspect submission page
          iconSelector = `.submitted-file-data > div > p > button:contains(${_("Word wrap")}) > i`;
          localStorageKey = 'fileWrap';
          action = () => toggleWrap($('.submission-container'), iconSelector, localStorageKey);
        } else if ($('.grader-container').find(buttonContainer).length > 0) {
          // buttonContainer is related to feedback and errors on inspect submission page
          iconSelector = `div > p > button:contains(${_("Word wrap")}) > i`;
          localStorageKey = 'graderFeedbackWrap';
          action = () => toggleWrap($('.grader-container'), iconSelector, localStorageKey);
        } else {
          // buttonContainer is not on inspect submission page
          localStorageKey = 'fileWrap';
          action = () => {
            const doWrap = localStorage.getItem('fileWrap') === 'true';
            localStorage.setItem(localStorageKey, !doWrap);
            table.toggleClass('no-wrap');
          };
        }

        const doWrap = localStorage.getItem(localStorageKey) === 'true';
        if (!doWrap) {
          table.addClass('no-wrap');
        }

        addButton(buttonContainer, {
          action: action,
          icon: doWrap ? 'check-square' : 'square',
          text: _('Word wrap'),
          toggle: true,
        });
      }

      if (!options || !options.noDownload) {
        addButton(buttonContainer, {
          action: function () {
            const url = pre.data('url');
            if (url) {
              // Add the query parameter "download" to the URL and redirect the window there.
              window.location.href = url + (url.indexOf('?') === -1 ? '?' : '&') + 'download=yes';
            } else {
              console.error("Download button clicked, but there is no data-url set on the downloadable pre content. Can not download.");
            }
          },
          icon: 'download',
          text: _('Download'),
        });
      }

      if (options && options.extraButtons) {
        for (var i in options.extraButtons) {
          addButton(buttonContainer, options.extraButtons[i]);
        }
      }
    });
  };
})(jQuery);

/**
* Handle common modal dialog.
*/
(function ($) {
  "use strict";

  const pluginName = "aplusModal";
  var defaults = {
    loader_selector: ".modal-progress",
    loader_text_selector: ".aplus-progress-bar",
    alert_text_selector: ".modal-submit-error",
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

    init: function () {
      this.loader = this.element.find(this.settings.loader_selector);
      this.loaderText = this.loader.find(this.settings.loader_text_selector);
      this.alertText = this.loader.find(this.settings.alert_text_selector);
      this.title = this.element.find(this.settings.title_selector);
      this.content = this.element.find(this.settings.content_selector);
      this.messages = {
        loading: this.loaderText.text(),
        error: this.loaderText.attr(this.settings.error_message_attribute)
      };
    },

    run: function (command, data) {
      switch (command) {
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

    open: function (data) {
      this.title.hide();
      this.content.hide();
      this.alertText.hide();
      this.loaderText
        .removeClass('aplus-progress-bar-danger').addClass('active')
        .text(data || this.messages.loading);
      this.loader.show();
      this.element.on("hidden.bs.modal", function (event) {
        $(".dropdown-toggle").dropdown();
      });
      this.element.modal("show");
    },

    showError: function (data) {
      if (data) {
        this.alertText.text(data).show();
      }
      this.loaderText.removeClass('active').addClass('aplus-progress-bar-danger').text(this.messages.error);
    },

    showContent: function (data) {
      this.loader.hide();
      if (data.title) {
        this.title.text(data.title);
        this.title.show();
      }
      if (data.content instanceof $) {
        this.content.empty().append(data.content);
      } else {
        this.content.html(data.content);
      }
      this.content.show();
      return this.content;
    }
  });

  $.fn[pluginName] = function (command, data, options) {
    return this.each(function () {
      var modal = $.data(this, "plugin_" + pluginName);
      if (!modal) {
        modal = new AplusModal(this, options);
        $.data(this, "plugin_" + pluginName, modal);
      }
      return modal.run(command, data);
    });
  };
})(jQuery);

/**
* Open links in a modal.
*/
(function ($, window) {
  "use strict";

  const pluginName = "aplusModalLink";
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
    init: function () {
      var link = this.element;
      var settings = this.settings;
      link.on("click", function (event) {
        event.preventDefault();
        var url = link.attr("href");
        if (url === "" || url == "#") {
          return false;
        }
        var modal = $(settings.file ? settings.file_modal_selector : settings.modal_selector);
        modal.aplusModal("open");
        $.get(url, function (data) {
          if (settings.file) {
            var text = $("<pre/>").text(data);
            text.attr('data-url', url);
            modal.aplusModal("content", {
              title: link.data('modalTitle') || link.text(),
              content: text,
            });
            text.highlightCode();
          } else {
            var match = data.match(settings.body_regexp);
            if (match !== null && match.length == 2) {
              data = match[1];
            }
            var c = modal.aplusModal("content", { content: data });
            c.find('.file-modal').aplusModalLink({ file: true });
            c.find('pre.hljs').highlightCode();
            modal.trigger("opened.aplus.modal");
            // render math in the modal
            if (typeof window.MathJax !== "undefined") {
              modal.aplusTypesetMath();
            }
          }
        }).fail(function () {
          modal.aplusModal("error");
        });
      });
    }
  });

  $.fn[pluginName] = function (options) {
    return this.each(function () {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusModalLink(this, options));
      }
    });
  };
})(jQuery, window);


(function ($, window) {
  "use strict";

  const pluginName = "aplusTypesetMath";
  $.fn[pluginName] = function () {
    if (typeof window.MathJax === "undefined") {
      return;
    }
    switch (window.MathJax.version[0]) {
      case "2":
        window.MathJax.Hub.Queue(["Typeset", window.MathJax.Hub, this.get()]);
        break;
      case "3":
        window.MathJax.typesetPromise(this.get()).catch((err) =>
          console.error(err)
        );
        break;
      default:
        console.error("Unsupported version of MathJax, use 2.x or 3.x!");
    }
  };
})(jQuery, window);

/**
* Ajax loaded list tail.
*/
(function ($) {
  "use strict";

  const pluginName = "aplusListTail";
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

    init: function () {
      var settings = this.settings;
      const perPage = this.element.attr(settings.per_page_attr);
      if (this.element.find(settings.entry_selector).length >= perPage) {
        var tail = this.element.find(settings.more_selector);
        tail.removeClass("d-none").on("click", function (event) {
          event.preventDefault();
          var link = tail.find(settings.link_selector)
            .hide();
          var loader = tail.find(settings.loader_selector)
            .removeClass("d-none").show();
          var url = link.attr("href");
          $.get(url, function (html) {
            loader.hide();
            tail.before(html);
            if ($(html).filter(settings.entry_selector).length >= perPage) {
              var i = url.indexOf(settings.link_page_arg) + settings.link_page_arg.length;
              if (i >= settings.link_page_arg.length) {
                const page = parseInt(url.substr(i));
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

  $.fn[pluginName] = function (options) {
    return this.each(function () {
      if (!$.data(this, "plugin_" + pluginName)) {
        $.data(this, "plugin_" + pluginName, new AplusListTail(this, options));
      }
    });
  };
})(jQuery);

/**
* Common setup for AJAX requests.
*
* Add CSRF token on AJAX requests, copied from
* https://docs.djangoproject.com/en/2.0/ref/csrf/#ajax
*
* Copy the language hl query parameter from the window location so that
* the server responds to AJAX requests in the same language.
*/
(function ($, document) {
  "use strict";

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = $.trim(cookies[i]);
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
      }

      if (!this.crossDomain) {
        this.url = copyWindowHlParamToUrl(this.url, false);
      }
    }
  });
})(jQuery, document);

/*
* Listen to link click events and copy the hl query parameter from
* the current url to the next.
* Note! The hl parameter is used to force translations to a certain language
* in the response.
*/
(function (window, document) {
  // Ignore links whose href starts with a '#', or Bootstrap tabs will break
  $(document).on("click mousedown contextmenu", 'a[href]:not([href^="#"])', function (event) {
    if (
      // The click event is only triggered for the primary mouse button
      // (usually left). The mousedown event is needed for the middle mouse
      // button (which == 2), which usually opens the link in a new tab.
      // The contextmenu event is triggered when the context menu is opened
      // (mouse right click or context menu key on the keyboard).
      // The link may be opened from the context menu too, thus the hl parameter
      // should be copied.
      (event.type != "mousedown" || event.which == 2) &&
      $(this).attr("data-bs-toggle") != "dropdown" &&
      this.protocol === window.location.protocol &&
      this.host === window.location.host // hostname:port
    ) {
      this.search = copyWindowHlParamToQuery(this.search, false);
    }
  });

})(window, document);


function changeLanguage(lang) {
    const url = new URL(window.location.href);
    url.searchParams.set('hl', lang);
    window.location.href = url.toString();
}

// Some automatic conversion for material that is not yet updated to BS5
$(document).ready(function() {
  // Change any old-style data-toggle attributes to BS5 namespaced format
  $('[data-toggle]').each(function() {
    const value = $(this).attr('data-toggle');
    $(this).attr('data-bs-toggle', value);
    $(this).removeAttr('data-toggle');
  });
  // Change "collapse in" to "collapse show" to correct initial visibility with BS5
  $('.collapse.in').removeClass('in').addClass('show');
});