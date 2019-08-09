// Fix difficulty not being pulled to right on badges in panel
$(window).on("aplus:exercise-ready", function (event) {
    $(event.target).find(".panel-title > span.pull-right").siblings("span.difficulty").addClass("pull-right");
});
