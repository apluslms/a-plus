function checkButton(button) {
  button
    .attr("aria-pressed", "true")
    .find("i")
    .removeClass("bi-square")
    .addClass("bi-check-square");
}

function uncheckButton(button) {
  button
    .attr("aria-pressed", "false")
    .find("i")
    .removeClass("bi-check-square")
    .addClass("bi-square");
}

function expandModules(skipAnimation) {
  if (skipAnimation) {
    $(".module-panel > div").addClass("in"); // addClass("in") skips the expand animation
  }
  $(".module-panel > div").collapse("show");
  checkButton($("#toggle-expand-all-modules"));
}

function collapseModules() {
  $(".module-panel, .module-to-collapse > div").collapse("d-none");
  uncheckButton($("#toggle-expand-all-modules"));
}

function startListen(course) {
  const currentPath = window.location.pathname;
  $("a.deviations-link").attr("href", function(i, href) {
    return `${href}&previous=${currentPath}`;
  });

  $(".filter-categories button").on("click", function(event) {
    const button = $(this);
    const id = button.attr("data-category");
    if (button.attr("aria-pressed") === "false") {
      checkButton(button);
      $('.module-panel tr[data-category="' + id + '"]').removeClass("d-none");
    } else {
      uncheckButton(button);
      $('.module-panel tr[data-category="' + id + '"]').addClass("d-none");
    }
    $('.module-panel').each(function(index, panel) {
      const mod = $(panel);
      if (mod.find("tr:not(.hide)").length > 0) {
        mod.removeClass("d-none");
      } else {
        mod.addClass("d-none");
      }
    });
  });

  if ($(".module-to-collapse").length > 0) {
    // Show the "Expand all modules" button if some modules are collapsed
    $("#toggle-expand-all-modules").show();
    // Check local storage and expand all modules if the variable "expandAllModules" is set to true
    const expandAllModules = localStorage.getItem("expandAllModules") === "true";
    if (expandAllModules) {
      expandModules(true);
    }

    // Register an event handler to the "Expand all modules" button
    $("#toggle-expand-all-modules").on("click", function(event) {
      const expandAllModules = localStorage.getItem("expandAllModules") === "true";
      if (expandAllModules) {
        collapseModules();
        localStorage.setItem("expandAllModules", false);
      } else {
        expandModules(false);
        localStorage.setItem("expandAllModules", true);
      }
    });

    // Check if automatic scrolling is enabled and initialize the local storage variable
    $("#toggle-auto-scroll").show();
    const autoScrollEnabled = localStorage.getItem("autoScrollEnabled");
    if (autoScrollEnabled === "false") {
      uncheckButton($("#toggle-auto-scroll"));
    } else if (!autoScrollEnabled) {
      localStorage.setItem("autoScrollEnabled", true); // Scroll automatically by default
    }

    // Check if automatic scrolling behavior is set to "instant" and initialize the local storage variable
    if (autoScrollEnabled !== "false") {
      $("#auto-scroll-behavior-instant").show();
    }
    const autoScrollBehavior = localStorage.getItem("autoScrollBehavior");
    if (autoScrollBehavior === "instant") {
      checkButton($("#auto-scroll-behavior-instant"));
    } else if (!autoScrollBehavior) {
      localStorage.setItem("autoScrollBehavior", "smooth"); // Scroll smoothly by default
    }

    // Register event handlers to both buttons related to automatic scrolling
    $("#toggle-auto-scroll").on("click", function(event) {
      const autoScrollEnabled = localStorage.getItem("autoScrollEnabled");
      if (autoScrollEnabled === "false") {
        checkButton($("#toggle-auto-scroll"));
        $("#auto-scroll-behavior-instant").show();
        localStorage.setItem("autoScrollEnabled", "true");
      } else {
        uncheckButton($("#toggle-auto-scroll"));
        $("#auto-scroll-behavior-instant").hide();
        localStorage.setItem("autoScrollEnabled", "false");
      }
    });

    $("#auto-scroll-behavior-instant").on("click", function(event) {
      const autoScrollBehavior = localStorage.getItem("autoScrollBehavior");
      if (autoScrollBehavior === "instant") {
        uncheckButton($("#auto-scroll-behavior-instant"));
        localStorage.setItem("autoScrollBehavior", "smooth");
      } else {
        checkButton($("#auto-scroll-behavior-instant"));
        localStorage.setItem("autoScrollBehavior", "instant");
      }
    });
  }

  // Get current course news from the document and previously shown course news from local storage
  const news = [];
  $(".news-panel > .list-group > .list-group-item").each(function() {
    const title = $(this).children(".list-group-item-heading").children(".list-group-item-title")[0].innerText || "";
    const body = $(this).children(".list-group-item-text")[0].innerText || "";
    news.push({ [title]: body });
  });
  const allPreviousNews = JSON.parse(localStorage.getItem("courseNews")) || {};
  const previousNews = course in allPreviousNews ? allPreviousNews[course] : [];
  const currentNews = news.length > 0 ? news : previousNews;
  if (news.length > 0) {
    const allCurrentNews = { ...allPreviousNews, [course]: currentNews };
    localStorage.setItem("courseNews", JSON.stringify(allCurrentNews));
  }

  function autoScroll() {
    const autoScrollEnabled = localStorage.getItem("autoScrollEnabled");
    if (autoScrollEnabled === "true" && $(".module-to-collapse").length > 0) {
      const autoScrollBehavior = localStorage.getItem("autoScrollBehavior");
      // Scroll to the first open module if there are no new news items
      const openModules = $(".module-panel:not(.module-to-collapse)");
      if (openModules.length > 0 && JSON.stringify(currentNews) === JSON.stringify(previousNews)) {
        openModules[0].querySelector(".panel-heading").scrollIntoView({ behavior: autoScrollBehavior });
      }
    }
  }

  setTimeout(autoScroll, 10); // Instant automatic scrolling does not work without a small delay
}
