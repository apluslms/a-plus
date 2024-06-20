(function ($) {
  function escapeHtml(text) {
    // Source: https://stackoverflow.com/a/4835406
    // License: CC BY-SA 3.0, https://creativecommons.org/licenses/by-sa/3.0/#
    // No changes made to the original code.
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
  }


  $(document).on("aplus:translation-ready", function () {
    function json_parse(data) {
      try {
        return JSON.parse(data);
      } catch (e) {
        return null;
      }
    }

    /**
     * Change the instruction message of the automatic redirection.
     * @param  {number} number of automatic redirections stored in the localStorage
     * @param  {string} event that triggers the changeMessage() function
     */
    const changeMessage = function (items, event) {
      const automaticRedirectionMsg =
        "You have enabled automatic redirection to these services on this device. You may remove the automatic " +
        "redirection here. The privacy information will be shown to you next time you open the service.";
      switch (event) {
        case "remove":
          if (items > 0) {
            $("#services-instructions")[0].innerHTML = _(
              automaticRedirectionMsg
            );
          } else {
            $("#services-instructions")[0].innerHTML = _(
              "No services enabled for automatic redirection on this device."
            );
          }
          break;
        case "load":
          if (items > 0) {
            $("#services-instructions")[0].innerHTML = _(
              automaticRedirectionMsg
            );
          }
          break;
        default:
          break;
      }
    };

    // translations
    const ariaLabelPrefix = _("Forget automatic redirection");
    const btnText = _("Forget");

    $(".local-storage-fields").each(function () {
      const ul = $(this);
      ul.addClass("list-group");
      const tooltip = ul.data("forget-text");
      const ls = window.localStorage;
      let found = 0;
      for (let i = 0; i < ls.length; i++) {
        const key = ls.key(i);
        const data = json_parse(ls.getItem(key));
        if (key.indexOf("external_service_") != 0 || data === null) continue;
        const externalService = escapeHtml(data.title);
        const li = $(
          `<li aria-label="${externalService}">` +
            (data.title === undefined ? escapeHtml(key) : externalService) +
            "</li>"
        );
        li.addClass("list-group-item clearfix");
        const btn = $(
          `<button aria-label="${ariaLabelPrefix}" class="aplus-button--danger aplus-button--sm float-end"><i class="bi-remove"></i>${btnText}</button>`
        );
        btn.on("click", function () {
          li.remove();
          ls.removeItem(key);
          found--;
          changeMessage(found, "remove");
        });
        btn.tooltip({ placement: "left", title: tooltip });
        li.append(btn);
        ul.append(li);
        found++;
      }
      changeMessage(found, "load");
    });
  });
})(jQuery);
