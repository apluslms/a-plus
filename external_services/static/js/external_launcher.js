/**
 * Utility for the launch of external links and services in menu or exercises:
 * - hide the notice about sensitive user data as well as the launch button
 *   when the service is launched into an iframe
 * - if the user decides to skip the warning about the external service in
 *   the future, the decision is stored in the local storage and the link or
 *   the service is launched automatically on the next page load.
 *   However, this is disabled if the destination is a blank page.
 */
(function() {
    'use strict';

    function json_parse(data) {
        try {
            return JSON.parse(data);
        } catch(e) {
            return null;
        }
    }

    const settings = {
        ext_serv_title: "ext-service-title",
        ext_serv_key: "ext-service-pk",
        ext_params_hash_key: "ext-params-hash",
        ext_service_connected: "ext-automation-done",
        auto_accept_selector: ".external-service-auto",
        message_area_selector: ".external-service-launch",
    };

    function connect_form_automation(name="<unknown>") {
        const element = this;
        if (element.dataset[settings.ext_service_connected] === "true") return;
        element.dataset[settings.ext_service_connected] = "true";
        const ext_serv = element.dataset[settings.ext_serv_key];
        const ext_title = element.dataset[settings.ext_serv_title];
        const params_hash = element.dataset[settings.ext_params_hash_key];
        if (!ext_serv) {
            console.log("Invalid external service element:");
            console.dir(this);
            return;
        } else {
            console.log("Connecting external service automation to: " + name);
        }
        const storage = window.localStorage;
        const storage_key = "external_service_" + ext_serv;
        const form = element.querySelector('form');
        const auto_accept_box = element.querySelector(settings.auto_accept_selector);
        const auto_accept = auto_accept_box.querySelector('input[type=checkbox]');
        const target = form.getAttribute('target');

        form.addEventListener("submit", function() {
            if (target && target.charAt(0) !== '_') {
                const iframe = element.querySelector("iframe[name='" + target + "']");
                /* show the iframe if the external service is opened in one */
                iframe.style.display = 'block';

                /* hide the warning message and the form */
                element.querySelector(settings.message_area_selector).style.display = 'none';
            }
            /* remember the accepted state via a local storage */
            if (auto_accept.checked) {
                const local_value = json_parse(storage.getItem(storage_key)) ||
                    {id: ext_serv, title: ext_title, ok: []};
                if (local_value.ok.indexOf(params_hash) < 0) {
                    local_value.ok.push(params_hash);
                    storage.setItem(storage_key, JSON.stringify(local_value));
                }
            }
            /* NOTE: chapter.js adds submit hook to disable submit buttons for post forms */
        });

        const local_value = json_parse(storage.getItem(storage_key));
        if (local_value !== null && local_value.hash !== undefined) {
            /* migrate old storage format to new, TODO: remove this */
            local_value.ok = [local_value.hash];
            delete local_value.hash;
            storage.setItem(storage_key, JSON.stringify(local_value));
        }
        if (local_value !== null && local_value.title !== ext_title) {
            /* update title */
            local_value.title = ext_title;
            storage.setItem(storage_key, JSON.stringify(local_value));
        }

        if (target === "_blank") {
            /* hide the automatic accept checkbox when the automatic launch
               is disabled due to pop-up blockers */
            auto_accept_box.style.display = 'none';
        } else if (local_value !== null &&
                   local_value.ok.indexOf(params_hash) >= 0) {
            /* automatically submit data, if form with current data,
               has been marked as auto accept */
            form.submit();
        }
    }

    function find_and_connect(dom, name) {
        dom.querySelectorAll('div.external-service').forEach(function(element) {
            connect_form_automation.call(element, name);
        });
    }

    document.addEventListener('aplus:exercise-ready', function(e) {
        const exercise = e.target;
        const name = exercise.dataset.aplusExercise || exercise.dataset.aplusChapter || "<unknown exercise>";
        find_and_connect(exercise, name);
    });

    document.addEventListener('DOMContentLoaded', function() {
        find_and_connect(document, "<redirect-page>");
    });
})();
