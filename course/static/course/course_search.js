function initCourseSearchClear() {
    const clearButton = document.getElementById("clear-search");
    const input = document.getElementById("search-input");
    const form = document.getElementById("course-search-form");

    if (clearButton && input && form) {
      clearButton.addEventListener("click", function () {
        input.value = "";
        form.submit();
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initCourseSearchClear);
