$(function() {

    // Mark active menu based on body attribute data-view-tag.
    var tag = $("body").attr("data-view-tag");
    if (tag) {
        $(".menu-" + tag).addClass("active");
    }

    // Activate tooltips.
    $('[data-toggle="tooltip"]').tooltip();


});
