$(function() {
    /*$("#exercise form").submit(function(event) {
       $(this).append("<div>Sending</div>");
    });*/
   
   $("a.collapse_toggle").click(function() {
       $(this).parents('.exercise_round').toggleClass('collapsed').children('.table-container').slideToggle();
       return false;
   });
   
   $("ul.exercise_rounds li.collapsed .table-container").hide();
   // hide closed rounds by default
   if ($("ul.exercise_rounds li.closed").addClass("hide").size() > 0) {
      // show the toggle link and register a click handler
      $("#toggleOldModules").removeClass("hide").click(function(e) { 
         e.preventDefault();
         // toggle visibility of closed rounds
         var invisible = $("ul.exercise_rounds li.closed").toggleClass("hide").hasClass("hide");
         // toggle the text of the element, text from the data attributes
         $(this).text($(this).data(invisible?"show-text":"hide-text"));
      });
   }
   
   $("a.group_change_link").click(function() {
       $("#change_to_group").val($(this).attr("data-group-id"));
       $("#group-change-form").submit();
       return false;
   });
   
    // Decorate tooltips and popovers
    $('*[rel=tooltip]').tooltip({});
    $('a[rel=popover]').popover({placement: "left"});
    
    // Make the sub-menus in the main navigation into dropdown menus
    $('.dropdown-toggle').dropdown();
    
    // Prettify code examples
    //prettyPrint();
    
    /*
     * Add the class 'active' to menu links that point to the current page.
     */
    var path = location.pathname.substring(1);
    if(path) {
        $('li a[href$="' + path + '"]').parent("li").addClass('active');
        $('li.active a i[class^="icon-"]').addClass('icon-white');
    }
});


