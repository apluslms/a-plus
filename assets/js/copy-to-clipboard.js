/** This function must be fired by a click button event.
 * Copy text to the clipboard
 *
 * @param {string} btnClassSelector: CSS class selector of the button that fires
 * the event, .e.g., '.btn-copy'
 * @param {string} targetIdSelector: CSS id selector of the field that contains
 * the text to be copied, e.g., '#input-text'
 *
 * This file contains translation, which are stored in the js-translation/copy-to-clipboard.json file. Therefore, you
 * must include the translations in the HTML file.
 * <link
 *  data-translation
 * 	rel="preload"
 *  as="fetch"
 *  crossorigin="anonymous"
 *  type="application/json;"
 *  hreflang="fi"
 * href="{{ STATIC_URL }}js-translations/copy-to-clipboard.fi.json"
 * >
 */
const copyToClipboard = (btnClassSelector, targetIdSelector) => {
  const clipboard = new ClipboardJS(btnClassSelector, {
    target: function () {
      return $(targetIdSelector)[0];
    },
  });
  const el = $(btnClassSelector);

  const elOriginalText = el.attr("data-bs-original-title")
    ? el.attr("data-bs-original-title")
    : "";

  clipboard.on("success", function (e) {
    var msg = _("Copied!");
    el.attr("data-bs-original-title", msg).tooltip("show");
    e.clearSelection();
    el.attr("data-bs-original-title", elOriginalText);
  });

  clipboard.on("error", function (e) {
    var msg = _("Copying failed! Use Ctrl+C to copy");
    el.attr("data-bs-original-title", msg).tooltip("show");
    el.attr("data-bs-original-title", elOriginalText);
  });
};
