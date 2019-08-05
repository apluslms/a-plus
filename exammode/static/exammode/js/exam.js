
/* 
 * Add an Ajax exercise event listener to correct the height of
 * the exercises inside the panel.
 */
$(".collapse").on("shown.bs.collapse", function (event) {
    console.log($(this));
    var container = $(this).find("iframe");
    console.log(container)
    var content = container.innerHTML;
    container.innerHTML = content; 
});


// Fix difficulty not being pulled to right on badges in panel
$(window).on("aplus:exercise-ready", function (event) {
    $(event.target).find(".panel-title > span.pull-right").siblings("span.difficulty").addClass("pull-right");
});