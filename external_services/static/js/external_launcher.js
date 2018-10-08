/**
 * Utility for the launch of external links and services in menu or exercises:
 * - hide the notice about sensitive user data as well as the launch button
 *   when the service is launched into an iframe
 * - if the user decides to skip the warning about the external service in
 *   the future, the decision is stored in the local storage and the link or
 *   the service is launched automatically on the next page load.
 *   However, this is disabled if the destination is a blank page.
 */
(function($) {
    'use strict';

    const settings = {
        ext_serv_title: "ext-service-title",
        ext_serv_key: "ext-service-pk",
        ext_params_hash_key: "ext-params-hash",
        ext_service_connected: "ext-automation-done",
        auto_accept_selector: ".external-service-auto",
        message_area_selector: ".external-service-launch",
    };

    function connect_form_automation(name="<unknown>") {
        const element = $(this);
        if (element.data(settings.ext_service_connected) === "true") return;
        element.data(settings.ext_service_connected, "true");
        const ext_serv = element.data(settings.ext_serv_key);
        const ext_title = element.data(settings.ext_serv_title);
        const params_hash = element.data(settings.ext_params_hash_key);
        if (!ext_serv) {
            console.log("Invalid external service element:");
            console.dir(this);
            return;
        } else {
            console.log("Connecting external service automation to: " + name);
        }
        const storage = window.localStorage;
        const storage_key = "external_service_" + ext_serv;
        const form = element.find('form');
        const auto_accept_box = element.find(settings.auto_accept_selector);
        const auto_accept = auto_accept_box.find('input[type=checkbox]');
        const target = form.attr('target');

        form.on("submit", function() {
            if (target && target.charAt(0) !== '_') {
                const iframe = element.find("iframe[name='" + target + "']");
                /* show the iframe if the external service is opened in one */
                iframe.show();

                /* hide the warning message and the form */
                element.find(settings.message_area_selector).hide();
            }
            /* remember the accepted state via a local storage */
            if (auto_accept.prop('checked'))
                storage.setItem(storage_key, JSON.stringify({id: ext_serv, title: ext_title, hash: params_hash}));
            /* NOTE: chapter.js adds submit hook to disable submit buttons for post forms */
        });


        const local_value = JSON.parse(storage.getItem(storage_key));
        if (target === "_blank") {
            /* hide the automatic accept checkbox when the automatic launch
               is disabled due to pop-up blockers */
            auto_accept_box.hide();
        } else if (local_value !== null && local_value.hash == params_hash) {
            /* automatically submit data, if form is marked as auto accept
               and has not changed. */
            form.submit();
        } else {
            /* Remove old value */
            storage.removeItem(storage_key);
        }
    }

    function find_and_connect(dom, name) {
        $(dom).find('div.external-service').each(function() {
            connect_form_automation.call(this, name);
        });
    }

    $(document).on('aplus:exercise-ready', function(e) {
        const exercise = e.target;
        const name = exercise.dataset.aplusExercise || exercise.dataset.aplusChapter || "<unknown exercise>";
        find_and_connect(exercise, name);
    });
    $(function() {
        find_and_connect(document, "<redirect-page>");
    });
})(jQuery);
