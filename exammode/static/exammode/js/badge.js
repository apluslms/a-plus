
// Add an Ajax exercise event listener to refresh the summary.
$(window).on("aplus:exercise-ready", function (event) {
    console.log(event)
    const exercise = event.target;
    let panel = $(exercise).closest(".module-panel");
    let badge = panel.find(".exercise-summary span.badge").first().clone();
    badge.addClass("pull-right");

    if (panel.find(".panel-title").children("span.badge").length == 0) {
        panel.find(".panel-title").prepend(badge);
    }
    else {
        console.log("else")
        panel.find(".panel-title").children("span.badge").remove();
        panel.find(".panel-title").prepend(badge);
    }

});


// Add an Ajax exercise event listener to submit to refresh the summary.
// This is really dumb way to do this, but I want not able to find any meaningful
// event that gets submitted after submission to update the badge, so we just have timeOut
$(window).on("submit", function (event) {
    console.log(event)
    const exercise = event.target;
    let panel = $(exercise).closest(".module-panel");


    setTimeout(function () {
        let badge = panel.find(".exercise-summary span.badge").first().clone();
        badge.addClass("pull-right");
        if (panel.find(".panel-title").children("span.badge").length == 0) {
            panel.find(".panel-title").prepend(badge);
        }
        else {
            console.log("else")
            panel.find(".panel-title").children("span.badge").remove();
            panel.find(".panel-title").prepend(badge);
        }
    }, 5000);

});
