$(window).on("aplus:exercise-ready", function (event) {
    // Fix difficulty not being pulled to right on badges in panel
    $(event.target).find(".panel-title > span.pull-right").siblings("span.difficulty").addClass("pull-right");

    // Split exercises instructions and form side-by-side columns with Bootstrap grid system
    let exercise = $(event.target).find("#exercise")

    if (exercise.length && exercise.children("form").length == 1 && exercise.children("div").length == 1) {
        exercise.addClass("row");
        exercise.children("form").addClass("col-xs-6");
        exercise.children("div").addClass("col-xs-6");
    }
});

$(window).on('shown.bs.collapse', function(event) {
    // Reload iframe after opening panel to reset height
    let iframe = $(event.target).find("iframe");
    if (iframe.length) {
        iframe[0].src = iframe[0].src
    }
})
