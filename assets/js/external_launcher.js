/**
 * Utility for the launch of external (LTI) services or exercises:
 * - hide the notice about sensitive user data as well as the launch button
 *   when the service is launched into an iframe
 * - if the user decides to skip the warning about the external service in the future,
 *   the decision is stored in a cookie and the service is launched automatically
 *   on the next page load. This is disabled in individual exercise pages since they
 *   open services in a new tab/window, but the web browser pop-up blockers prevent
 *   JS from doing that.
 */
(function($, window, document, undefined) {
    "use strict";

    var pluginName = "aplusExternalLauncher";
    var defaults = {
        ext_serv_key: "ext-service-pk",
        ext_params_hash_key: "ext-params-hash",
        launch_form_selector: "[data-ext-launch-form]",
        auto_accept_input_selector: "input[name='auto_accept']",
        auto_accept_selector: "[data-auto-accept]",
        hide_after_launch_selector: "[data-hide-after-launch]",
    };

    function AplusExternalLauncher(element, options) {
        this.element = $(element);
        this.settings = $.extend({}, defaults, options);
        this.init();
    }

    $.extend(AplusExternalLauncher.prototype, {

        init: function() {
            this.cookieName = "aplusextlaunch" + this.element.data(this.settings.ext_serv_key);
            this.cookieValue = this.element.data(this.settings.ext_params_hash_key);
            this.launchForm = this.element.find(this.settings.launch_form_selector);

            var target = this.launchForm.attr("target");
            if (target === "_blank") {
                /* hide the automatic accept checkbox when the automatic launch
                   is disabled due to pop-up blockers */
                this.element.find(this.settings.auto_accept_selector).hide();
            }
            this.bindFormEvents();

            if (getCookie(this.cookieName) == this.cookieValue) {
                /* automatically submit accepted data, except if the target is
                   a new window/tab because it usually triggers the pop-up blocker
                   in web browsers */
                if (target !== "_blank") {
                    this.launchForm.submit();
                }
            } else {
                this.setCookie(-1); /* remove old cookie */
            }
        },

        bindFormEvents: function() {
            var self = this;
            var target = this.launchForm.attr("target");
            this.launchForm.on("submit", function() {
                /* show the iframe if the external service is opened in one */
                var iframe = undefined;
                if (target && target.charAt(0) !== '_') {
                    /* does not begin with an underscore */
                    iframe = self.element.find("iframe[name='" + target + "']");
                    iframe.show();
                }
                /* remember the accepted state via a local cookie */
                if (self.element
                        .find(self.settings.auto_accept_input_selector)
                        .prop("checked")) {
                    self.setCookie(1);
                }
                /* hide the warning and the launch button if the service
                   was opened in an iframe */
                if (iframe && iframe.length) {
                    self.element
                        .find(self.settings.hide_after_launch_selector)
                        .hide();
                }
                /* disable the submit button since the launch parameters
                   may not be reused */
                self.launchForm
                    .find("input[type='submit']")
                    .prop("disabled", true);
            });
        },

        setCookie: function(expire_years) {
            var expire = new Date();
            expire.setFullYear(expire.getFullYear() + expire_years);
            var path = document.location.href.split("/");
            document.cookie = this.cookieName + "=" + this.cookieValue
                + ";path=/" + path[3] + "/" + path[4] + "/"
                + ";expires=" + expire.toGMTString();
        },
    });

    $.fn[pluginName] = function(options) {
        return this.each(function() {
            if (!$.data(this, "plugin_" + pluginName)) {
                $.data(this, "plugin_" + pluginName, new AplusExternalLauncher(this, options));
            }
        });
    };
})(jQuery, window, document);
