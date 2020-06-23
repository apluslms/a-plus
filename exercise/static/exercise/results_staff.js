const { Observable, Subject, concat } = rxjs;
const { map, first, count, ignoreElements } = rxjs.operators;

const tag = rxjsSpy.operators.tag;
spy = rxjsSpy.create();
spy.log("users");



(function($, document, window, undefined) {
  let currentScript = (document.currentScript ?
    $(document.currentScript) :
    $('script').last()); // Ugly solution for IE11

  const exercisesUrl = currentScript.data("exercisesUrl");
  const studentsUrl = currentScript.data("studentsUrl");
  const usertagsUrl = currentScript.data("usertagsUrl");
  const pointsUrl = currentScript.data("pointsUrl");

  let _tagSlugFilters;
  let _exerciseSelection;
  let _studentCount;
  let _studentsVisibleCount = 0;
  let _allExercises = [];
  let _exercises;
  let _students;
  let _users = {};
  let _usertags;
  let _points = {};
  let _ajaxCompleted = false;

  let storageKey = 'resultsData';
  function toStorage() {
    return {
      _students: _students,
      _usertags: _usertags,
      _allExercises: _allExercises,
      _users: _users,
      _points: _points,
    }
  }

  let tableExportVar;

  /* TODO: Use better logic for translations.
   * Currently only some translations wait for aplus:translation-ready and most of them do not,
   * since the translations become available during the script.
   */
  $(document).on("aplus:translation-ready", function() {
    // TableExport plugin
    // https://tableexport.v5.travismclarke.com/#tableexport
    TableExport.prototype.formatConfig.xlsx.buttonContent = _("Export to xlsx (Excel)");
    TableExport.prototype.formatConfig.csv.buttonContent = _("Export to csv (LibreOffice)");
    TableExport.prototype.formatConfig.txt.buttonContent = _("Export to txt");
    tableExportVar = $("#table-points").tableExport({
      "position": "top",
      "bootstrap": "true",
      "filename": _("student_results"),
    });

    // Move the default TableExport download buttons inside a single dropdown menu
    $("caption.tableexport-caption").children("button").each(function() {
      $("#export-button-menu").append($(this).detach());
    });
  });

  // Make the table headings and student IDs stick when scrolling table
  $('#table-points-div').scroll(function(ev) {
    $('thead#table-heading th').css('transform', 'translateY(' + this.scrollTop + 'px)');
    $('tbody td.stick-on-scroll').css('transform', 'translateX(' + this.scrollLeft + 'px)');
  });


  // Booleans to allow teacher to choose with checkboxes what data indicators they want to see
  let _totalSubmTrue = false;
  let _avgSubmTrue = false;
  let _maxSubmTrue = false;
  let _totalStuSubmTrue = false;
  let _totalStuMaxTrue = false;
  let _avgPTrue = false;
  let _maxPTrue = false;
  let _showOfficial = true;

  $("input.total-subm-checkbox").change(function() {
    _totalSubmTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.avg-subm-checkbox").change(function() {
    _avgSubmTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.max-subm-checkbox").change(function() {
    _maxSubmTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.total-stu-subm-checkbox").change(function() {
    _totalStuSubmTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.total-stu-max-checkbox").change(function() {
    _totalStuMaxTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.avg-p-checkbox").change(function() {
    _avgPTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.max-p-checkbox").change(function() {
    _maxPTrue = this.checked;
    exerciseSelectionChange();
  });

  $("input.official-checkbox").change(function() {
    _showOfficial = this.checked;
    exerciseSelectionChange();
  });


  // Set up the tooltip for checkboxes, look docs below for tooltip
  // https://getbootstrap.com/docs/3.3/javascript/
  $('[data-toggle="tooltip"]').tooltip({
    "trigger": "hover",
  });

  $('[data-toggle="tooltip"]').on('click', function() {
    $(this).tooltip('hide');
  })


  // Event listener for tag filters
  $('.filter-users button').on('click', function(event) {
    event.preventDefault();
    let icon = $(this).find('.glyphicon');
    if (icon.hasClass('glyphicon-unchecked')) {
      icon.removeClass('glyphicon-unchecked').addClass('glyphicon-check');
    } else {
      icon.removeClass('glyphicon-check').addClass('glyphicon-unchecked');
    }
    exerciseSelectionChange();
  });

  /*
   * Creates the html for indicator data row. This is called for each row that has
   * checkbox checked for its indicator data.
   * @param  {string} tooltipTitle The text that is shown when hovering over heading.
   * @param  {string} headingTitle The heading text.
   * @return {string} Returns the html that creates the data indicator rows in table.
   */
  function createIndicatorRow(tooltipTitle, headingTitle, dataValues) {
    // Data indicator headings have title and tooltip info that is shown when hovering mouse on the heading title
    let indicatorHeadingHtml = "";
    if (dataValues && dataValues.length > 0) {
      indicatorHeadingHtml +=
        '<tr class="no-filtering"><td style="border-right: none !important; border-bottom: none !important;"' +
        'class="indicator-heading stick-on-scroll" data-toggle="tooltip" ' +
        'title="' + tooltipTitle + '">' + headingTitle +
        '</td><td style="border-left: none !important; border-bottom: none !important;"' +
        'class="indicator-heading stick-on-scroll" data-toggle="tooltip" ' +
        'title="' + tooltipTitle + '"></td>';
    } else {
      indicatorHeadingHtml +=
        '<tr class="no-filtering"><td style="border-right: none !important;" colspan="2"' +
        'class="indicator-heading stick-on-scroll" data-toggle="tooltip" ' +
        'title="' + tooltipTitle + '">' + headingTitle +
        '</td><td style="border-left: none !important; border-top: none !important;"' +
        'class="indicator-heading stick-on-scroll" data-toggle="tooltip" ' +
        'title="' + tooltipTitle + '"></td>';
    }

    let normalValuesHtml = '';
    let pctValuesHtml =
      '<tr class="no-filtering tableexport-ignore">'
    let sumValue = 0;
    dataValues.forEach(function(value) {
      sumValue += value[0];
    });
    sumValue = Number.isInteger(sumValue) ? sumValue : sumValue.toFixed(2);

    // Empty data cells for total and tags in data indicators
    if (dataValues && dataValues.length > 0) {
      normalValuesHtml +=
        '<td class="indi-normal-val"></td>'
        + '<td class="indi-normal-val">' + sumValue + '</td>';
      pctValuesHtml +=
        '<td style="border-right: none !important; border-top: none !important;"'
        + 'class="indicator-heading stick-on-scroll" data-toggle="tooltip" '
        + 'title="' + tooltipTitle + '"></td>'
        + '<td style="border-left: none !important; border-top: none !important;"'
        + 'class="indicator-heading stick-on-scroll" data-toggle="tooltip" '
        + 'title="' + tooltipTitle + '"></td>'
        + '<td class="indi-pct-val"></td>'
        + '<td class="indi-pct-val"></td>';
      }

    // Normal and percentage values on seperate rows in data indicators
    dataValues.forEach(function(value) {
      let normalValue = Number.isInteger(value[0]) ? value[0] : value[0].toFixed(2);
      normalValuesHtml += '<td class="indi-normal-val">' + normalValue + '</td>';
      pctValuesHtml += '<td class="indi-pct-val">' + value[1].toFixed(2) + '%</td>';
    });

    normalValuesHtml += '</tr>';
    pctValuesHtml += '</tr>';

    return indicatorHeadingHtml + normalValuesHtml + pctValuesHtml;
  }


  /*
   * Creates the table with student points based on
   * selected exercises, data indicators, tags and grouping method.
   * @param {string} pointsGroupingMethod The grouping method: show all, show by difficulties, show by modules
   */

  /*
  window.createPointTable = function(pointsGroupingMethod) {
    if (!_ajaxCompleted) {
      return;
    }

    // Pick only students that have the selected tags
    // Use same logic for tag filtering as in participants.js
    let = filteredStudentPool = [];
    _students.forEach(function(student) {
      const tagSlugFilters = $.makeArray($('.filter-users button:has(.glyphicon-check)'))
      .map(function(elem) {
        return $(elem).data('tagSlug');
      });
      let studentTagSlugs = student.tag_slugs;

      // Set intercetion tags ∩ filters
      const intersect = studentTagSlugs.filter(function (tag) {
        return tagSlugFilters.indexOf(tag) >= 0;
      });

      // Only create the row for a student, if they have one of the tags that are currently selected
      if (intersect.length === tagSlugFilters.length) {
        filteredStudentPool.push(student);
      }
    });

    $("#table-heading").empty();
    $("#table-body").empty();

    let htmlTablePoints = "";
    let pointKeys = [];

    let totalSubmitters = {};
    let totalMaxSubmitters = {};
    let totalSubmissions = {};
    let maxAllowedSubmissions = {};
    let maxPoints = {};
    let maxPointsTotal = 0;
    let totalPoints = {};


    // Gather information that is same for all students from the first student for better performance
    const firstStudent = _students[0];
    const sidFirst = firstStudent.id;
    let modulesSeen = [];

    $(_exerciseSelection).each(function() {
      const moduleID = $(this).data("moduleId");
      const module = _points[sidFirst].modules.filter(
        function(m) {
          return m.id == moduleID;
      })[0];
      const exerciseID = $(this).data("exerciseId");
      const exercise = module.exercises.filter(
        function(exercise) {
          return exercise.id == exerciseID;
        }
      )[0];

      if (pointsGroupingMethod === "difficulty") {
        maxPoints[exercise.difficulty] = maxPoints[exercise.difficulty] + exercise.max_points || exercise.max_points;
        maxPointsTotal += exercise.max_points;
        if (pointKeys.indexOf(exercise.difficulty) === -1) {
          pointKeys.push(exercise.difficulty);
          pointKeys.sort();
        }
        _allExercises.forEach(function(exAll) {
          if (exAll.id === exercise.id) {
            maxAllowedSubmissions[exercise.difficulty] = maxAllowedSubmissions[exercise.difficulty] + exAll.max_submissions || exAll.max_submissions;
          }
        });
      }

      if (pointsGroupingMethod === "module") {
        if (modulesSeen.indexOf(module) === -1) {
          modulesSeen.push(module);
          pointKeys.push(module.name);
        }

        _allExercises.forEach(function(exAll) {
          if (exAll.id === exercise.id) {
            maxAllowedSubmissions[module.name] = maxAllowedSubmissions[module.name] + exAll.max_submissions || exAll.max_submissions;
            maxPoints[module.name] = maxPoints[module.name] + exercise.max_points || exercise.max_points;
            maxPointsTotal += exercise.max_points;
          }
        });

      }

      if (pointsGroupingMethod === "all") {
        maxPoints[exercise.name] = exercise.max_points;
        maxPointsTotal += exercise.max_points;
        pointKeys.push(exercise.name);

        _allExercises.forEach(function(exAll) {
          if (exAll.id === exercise.id) {
            maxAllowedSubmissions[exercise.name] = exAll.max_submissions;
          }
        });
      }

    });

    // Gather personal information for each student, eg. individual points
    filteredStudentPool.forEach(function(student) {
      let points = {};
      let unofficialPoints = {};
      const sid = student.id;

      // Calculate points for each difficulty by grouping each each difficulty category exercises together
      if (pointsGroupingMethod === "difficulty") {
        let submittedDifficulty = {};

        $(_exerciseSelection).each(function() {
          const moduleID = $(this).data("moduleId");
          const exerciseID = $(this).data("exerciseId");
          const exercise = _points[sid].modules.filter(
            function(m) {
              return m.id == moduleID;
            })[0].exercises.filter(
            function(exercise) {
              return exercise.id == exerciseID;
            }
          )[0];

          const exercisePoints = exercise.official ? exercise.points : 0;
          points[exercise.difficulty] = points[exercise.difficulty] + exercisePoints || exercisePoints;
          unofficialPoints[exercise.difficulty] = unofficialPoints[exercise.difficulty] + exercise.points || exercise.points;
          totalPoints[exercise.difficulty] = totalPoints[exercise.difficulty] + exercisePoints || exercisePoints;
          if (exercise.submission_count > 0) {
            totalSubmissions[exercise.difficulty] = totalSubmissions[exercise.difficulty] + exercise.submission_count || exercise.submission_count;
            if (submittedDifficulty[exercise.difficulty] === undefined) {
              totalSubmitters[exercise.difficulty] = totalSubmitters[exercise.difficulty] + 1 || 1;
              submittedDifficulty[exercise.difficulty] = true;
            }
            if (points[exercise.difficulty] === maxPoints[exercise.difficulty]) {
              totalMaxSubmitters[exercise.difficulty] = totalMaxSubmitters[exercise.difficulty] + 1 || 1;
            }
          }
        });
      }

      // Calculate points for each module by grouping each each module's exercises together
      if (pointsGroupingMethod === "module") {
        let modulesSeen = [];

        $(_exerciseSelection).each(function() {
          const moduleID = $(this).data("moduleId");
          const module = _points[sid].modules.filter(
            function(m) {
              return m.id == moduleID;
          })[0];
          const exerciseID = $(this).data("exerciseId");
          const exercise = module.exercises.filter(
            function(exercise) {
              return exercise.id == exerciseID;
            }
          )[0];

          const exercisePoints = exercise.official ? exercise.points : 0;
          points[module.name] = points[module.name] + exercisePoints || exercisePoints;
          unofficialPoints[module.name] = unofficialPoints[module.name] + exercise.points || exercise.points;
          totalPoints[module.name] = totalPoints[module.name] + exercisePoints || exercisePoints;

          if (modulesSeen.indexOf(module) === -1) {
            modulesSeen.push(module);
            if (module.submission_count > 0) {
              totalSubmissions[module.name] = totalSubmissions[module.name] + module.submission_count || module.submission_count;
              totalSubmitters[module.name] = totalSubmitters[module.name] + 1 || 1;
              if (points[module.name] === maxPoints[module.name]) {
                totalMaxSubmitters[module.name] = totalMaxSubmitters[module.name] + 1 || 1;
              }
            }
          }
        });
      }

      // Calculate points for each exercise
      if (pointsGroupingMethod === "all") {
        $(_exerciseSelection).each(function() {
          const moduleID = $(this).data("moduleId");
          const exerciseID = $(this).data("exerciseId");
          const exercise = _points[sid].modules.filter(
            function(m) {
              return m.id == moduleID;
            })[0].exercises.filter(
            function(exercise) {
              return exercise.id == exerciseID;
            }
          )[0];

          const exercisePoints = exercise.official ? exercise.points : 0;
          points[exercise.name] = exercisePoints;
          unofficialPoints[exercise.name] = exercise.points;
          totalPoints[exercise.name] = totalPoints[exercise.name] + exercisePoints || exercisePoints;
          if (exercise.submission_count > 0) {
            totalSubmissions[exercise.name] = totalSubmissions[exercise.name] + exercise.submission_count || exercise.submission_count;
            totalSubmitters[exercise.name] = totalSubmitters[exercise.name] + 1 || 1;
            if (exercisePoints === exercise.max_points) {
              totalMaxSubmitters[exercise.name] = totalMaxSubmitters[exercise.name] + 1 || 1;
            }
          }

        });
      }

      // Create the table row for a single student from the points above
      htmlTablePoints += '<tr><td class="student-id stick-on-scroll">' + student.student_id + '</td>';
      htmlTablePoints +=
        '<td class="student-name stick-on-scroll">'
        + '<a href="' + student.summary_html + '">'
        + _users[sid].full_name + '</td>';

      if (pointKeys.length > 0) {
        let tagHtml = "";
        const studentTags = student.tag_slugs;

        studentTags.forEach(function(tagSlug) {
          _usertags.forEach(function(usertag) {
            if (usertag.slug === tagSlug) {
              tagHtml += django_colortag_label(usertag, ' ')[0].outerHTML;
            }
          });
        });

        let allPointsTotal = 0;
        let allUnofficialTotal = 0;
        pointKeys.forEach(function(name) {
          const point = points[name] || 0;
          const unofficialPoint = unofficialPoints[name] || 0;
          allPointsTotal += point;
          allUnofficialTotal += unofficialPoint;
        });

        htmlTablePoints += '<td>' + tagHtml + '</td>';

        if (!_showOfficial && allUnofficialTotal > allPointsTotal) {
          htmlTablePoints += '<td>' + allPointsTotal + '<span class="text-danger"> (' + allUnofficialTotal + ')</span></td>';
        }
        else {
          htmlTablePoints += '<td>' + allPointsTotal + '</td>';
        }
      }

      pointKeys.forEach(function(name) {
        const point = points[name] || 0;
        const unofficialPoint = unofficialPoints[name] || 0;
        if (!_showOfficial && unofficialPoint > point) {
          htmlTablePoints += '<td>' + point + '<span class="text-danger"> (' + unofficialPoint + ')</span></td>';
        }
        else {
          htmlTablePoints += '<td>' + point + '</td>';
        }
      });
      htmlTablePoints += "</tr>";
    });

    // Calculate the data indicators, e.g. average points, max points
    // Append headings, data indicators and student points to the html table

    $("#table-heading").append('<tr id="table-heading-row"></tr>')
    $("#table-heading-row").append('<th id="student-count">' + _("Student ID") + '</th>');
    $("#table-heading-row").append('<th>' + _("Student name") + '</th>');
    if (_exerciseSelection && _exerciseSelection.length > 0) {
      $("#table-heading-row").append('<th>' + _("Tags") + '</th>');
      $("#table-heading-row").append('<th>' + _("Total") + '</th>');
    }


    pointKeys.forEach(function(name) {
      if (pointsGroupingMethod === "difficulty" && name === "") {
        $("#table-heading-row").append('<th scope="col">' + _("No difficulty") + '</th>');
      } else {
        $("#table-heading-row").append('<th scope="col">' + name + '</th>');
      }
    });


    let htmlTableIndicators = "";

    if (_totalSubmTrue) {
      let dataVals = [];
      let sumValue = 0;
      pointKeys.forEach(function(name) {
        sumValue += totalSubmissions[name] || 0;
      });

      pointKeys.forEach(function(name) {
        dataVals.push([
          totalSubmissions[name] || 0,
          totalSubmissions[name] / sumValue * 100 || 0,
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Total number of submissions. Calculates all student submission counts together.'),
        _('Total submissions'),
        dataVals
      );
    }

    if (_avgSubmTrue) {
      let dataVals = [];
      pointKeys.forEach(function(name) {
        dataVals.push([
          totalSubmissions[name] / totalSubmitters[name] || 0,
          totalSubmissions[name] / totalSubmitters[name] / maxAllowedSubmissions[name] * 100 || 0
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('How many submissions a single student has used on the exercise on average.'
          + ' Only accounts for students with one or more submissions.'
        ),
        _('Average submissions per student with submissions'),
        dataVals
      );
    }

    if (_maxSubmTrue) {
      let dataVals = [];
      let sumValue = 0;
      pointKeys.forEach(function(name) {
        sumValue += maxAllowedSubmissions[name] || 0;
      });

      pointKeys.forEach(function(name) {
        dataVals.push([
          maxAllowedSubmissions[name] || 0,
          maxAllowedSubmissions[name] / sumValue * 100 || 0,
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Maximum number of available submissions for the exercise.'),
        _('Maximum submissions'),
        dataVals
      );
    }

    if (_totalStuSubmTrue) {
      let dataVals = [];
      pointKeys.forEach(function(name) {
        dataVals.push([
          totalSubmitters[name] || 0,
          totalSubmitters[name] / _studentsVisibleCount * 100 || 0
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Number of students that have one or more exercise submissions.'),
        _('Students with submissions'),
        dataVals
      );
    }

    if (_totalStuMaxTrue) {
      let dataVals = [];
      pointKeys.forEach(function(name) {
        dataVals.push([
          totalMaxSubmitters[name] || 0,
          totalMaxSubmitters[name] / totalSubmitters[name] * 100 || 0
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Number of students that have received maximum points from the exercise.'),
        _('Students with max points'),
        dataVals
      );
    }

    if (_avgPTrue) {
      let dataVals = [];
      pointKeys.forEach(function(name) {
        dataVals.push([
          totalPoints[name] / totalSubmitters[name] || 0,
          totalPoints[name] / totalSubmitters[name] / maxPoints[name] * 100 || 0
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Average points received for the exercise.'
          + ' Only accounts for students with one or more submissions.'
        ),
        _('Average points per student with submissions'),
        dataVals
      );
    }

    if (_maxPTrue) {
      let dataVals = [];
      pointKeys.forEach(function(name) {
        dataVals.push([
          maxPoints[name] || 0,
          maxPoints[name] / maxPointsTotal * 100 || 0
        ]);
      });

      htmlTableIndicators += createIndicatorRow(
        _('Maximum points for the exercise.'),
        _('Maximum points'),
        dataVals
      );
    }

    $("#table-body").append(htmlTableIndicators);
    $("#table-body").append(htmlTablePoints);
    $(".colortag-active").css("margin-right", "5px");
    $("#student-count").append(
      ' (<span id="selected-number">' + _studentsVisibleCount + '</span> / '
      + '<span id="participants-number">'+ _students.length + '</span>'
      + _(' students selected') + ')'
    );
    tableExportVar.reset();
    $('#table-points').find("caption").remove(); // Remove the recreated TableExport buttons (they are already in dropdown)
    $('.filtered-table').aplusTableFilter();

  }
  */


  /*
   * Handles the module selection when teacher selects or unselects a module(s).
   * If a module is selected, select and show all the module's exercises in exercise selection.
   * If a module is unselected, unselect and hide all module's exercises in exercise selection.
   */
  function moduleSelectionChange() {
    const selectedModules = $('#module-selection option:selected');
    const nonSelectedModules = $('#module-selection option').filter(function() {
      return !$(this).is(':selected');
    });

    selectedModules.each(function() {
      let showModuleClass = '.' + $(this).val();
      $(showModuleClass).removeClass("hidden disabled");
      $(showModuleClass).prop("selected", true);
    });

    nonSelectedModules.each(function() {
      let hideModuleClass = '.' + $(this).val();
      $(hideModuleClass).addClass("hidden disabled");
      $(hideModuleClass).prop("selected", false);
    });

    $("#exercise-selection").multiselect('refresh');
    exerciseSelectionChange();
  }


  /*
   * Keeps the _exerciseSelection up to date with currently selected exercises.
   * Always recreates the table based on the currently active group.
   */
  /*
  function exerciseSelectionChange() {
    _exerciseSelection = $('#exercise-selection option:selected');

    if ($("#all-exercises").hasClass("active")) {
      createPointTable("all");
    } else if ($("#difficulty-exercises").hasClass("active")) {
      createPointTable("difficulty");
    } else if ($("#module-exercises").hasClass("active")) {
      createPointTable("module");
    } else {
      return;
    }
  }
  */

  /*
   * Multiselect button text
   * This is copied from TableExport plugin source code
   * and changed for translations and nothing else.

   * https://github.com/davidstutz/bootstrap-multiselect/blob/master/dist/js/bootstrap-multiselect.js
   */
  let buttonText = function(options, select) {
    if (this.disabledText.length > 0
        && (select.prop('disabled') || (options.length === 0 && this.disableIfEmpty)))  {

      return this.disabledText;
    }
    else if (options.length === 0) {
      return _("None selected");
    }
    else if (this.allSelectedText
        && options.length === $('option', $(select)).length
        && $('option', $(select)).length !== 1
        && this.multiple) {

      if (this.selectAllNumber) {
        return _("All selected") + ' (' + options.length + ')';
      }
      else {
        return _("All selected");
      }
    }
    else if (this.numberDisplayed !== 0 && options.length > this.numberDisplayed) {
      return options.length + ' ' + _("selected");
    }
    else {
      let selected = '';
      let delimiter = this.delimiterText;

      options.each(function() {
        let label = ($(this).attr('label') !== undefined) ? $(this).attr('label') : $(this).text();
        selected += label + delimiter;
      });

        return selected.substr(0, selected.length - this.delimiterText.length);
      }
  }

  /*
   * Test for storage availability. type is one of ('localStorage', 'sessionStorage')
   *
   * https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API
   */
  function storageAvailable(type) {
    var storage;
    try {
      storage = window[type];
      var x = '__storage_test__';
      storage.setItem(x, x);
      storage.removeItem(x);
      return true;
    }
    catch(e) {
      return e instanceof DOMException && (
        // everything except Firefox
        e.code === 22 ||
        // Firefox
        e.code === 1014 ||
        // test name field too, because code might not be present
        // everything except Firefox
        e.name === 'QuotaExceededError' ||
        // Firefox
        e.name === 'NS_ERROR_DOM_QUOTA_REACHED') &&
        // acknowledge QuotaExceededError only if there's something already stored
        (storage && storage.length !== 0);
    }
  }

  function storeDataLocally(type, key, obj) {
    if (!storageAvailable(type)) {
      throw Error("Storage not available");
    }
    storage = window[type]
    storage.setItem(key, JSON.stringify(obj))
  }

  function getFromStorage(type, key) {
    if (!storageAvailable(type)) {
      throw Error("Storage not available");
    }
    storage = window[type]
    return JSON.parse(localStorage.getItem(key));
  }


  let ajaxEnabled = true;

  /* Custom AJAX settings to use with jQuery.ajax()
   * - Possibility to disable AJAX
   * - Retrying and retry limits (call specific)
   */
  let ajaxSettings = {
    _retryCount: 0,
    _retryLimit: 3,
    timeout: 0,
    beforeSend: function(xhr, settings) {
      return ajaxEnabled;
    },
    error: function(xhr, statusText, errorThrown) {
      this._retryCount++;
      if (this._retryCount <= this._retryLimit) {
        console.log("Retrying ajax:", statusText);
        setTimeout($.ajax, 1000, this);
      } else {
        stopAjax = true;
        $("#ajax-failed-alert").show();
        $("#results-loading-animation").hide();
      }
    }
  };


  /* Take as the argument a single student's points
   * and populate the exercise and module selection dropdown menu
   */
  function populateExerciseSelection(singleStudentPoints) {
    const firstStudentPoints = singleStudentPoints;
    firstStudentPoints.modules.forEach(function(module) {
      $("#module-selection").append(
        '<option value="module-' + module.id + '"'
        + 'selected>'
        + module.name
        + '</option>'
      );
      $("#exercise-selection").append(
        '<optgroup class="module-' + module.id + '"'
        + 'value="module-' + module.id + '"'
        + 'label="' + module.name + '"'
        + '></optgroup'
      );
      module.exercises.forEach(function(exercise) {
        $("#exercise-selection > optgroup:last-child").append(
          '<option data-module-id="' + module.id + '"'
          + 'data-exercise-id="' + exercise.id + '"'
          + 'class="module-'+ module.id + '"'
          + 'value="exercise-'+ exercise.id + '"'
          + 'selected>'
          + exercise.name
          + '</option>'
        );
      });
    });

    $('#module-selection').multiselect({
      includeSelectAllOption: true,
      onDeselectAll: moduleSelectionChange,
      onSelectAll: moduleSelectionChange,
      echnChange: moduleSelectionChange,
      buttonText: buttonText,
      selectAllText: _("Select all"),
    });

    $('#exercise-selection').multiselect({
      includeSelectAllOption: true,
      enableClickableOptGroups: true,
      onDeselectAll: exerciseSelectionChange,
      onSelectAll: exerciseSelectionChange,
      onChange: exerciseSelectionChange,
      maxHeight: 500,
      buttonText: buttonText,
      selectAllText: _("Select all"),
    });

  }

    // Take as the argument an object representing a student
    // and return a boolean indicating whether or not the student should be shown in the results table
  function studentVisibility(student) {
    // Pick only students that have the selected tags
    // Use same logic for tag filtering as in participants.js
    let studentTagSlugs = student.tag_slugs;

    // Set intersection tags ∩ filters
    const intersect = studentTagSlugs.filter(function (tag) {
      return tagSlugFilters.indexOf(tag) >= 0;
    });

    // Only create the row for a student, if they have one of the tags that are currently selected
    return intersect.length === tagSlugFilters.length;
  };

  /*
   * Keeps the _exerciseSelection up to date with currently selected exercises.
   * Always recreates the table based on the currently active group.
   */
  function exerciseSelectionChange() {
    _exerciseSelection = $('#exercise-selection option:selected');

    _tagSlugFilters = $.makeArray($('.filter-users button:has(.glyphicon-check)'))
    .map(function(elem) {
      return $(elem).data('tagSlug');
    });
  }

  // Filter the students rows in the table, setting visibility
  function filterTable() {

    $('#table-points tr').each(function(){
      $(this).find('td').each(function(){
        //do your stuff, you can use $(this) to get current cell
      })
    })
  }

  // Return the grouping method currently in use
  function getGroupingMethod() {
    if ($("#all-exercises").hasClass("active")) {
      return "all";
    } else if ($("#difficulty-exercises").hasClass("active")) {
      return "difficulty";
    } else if ($("#module-exercises").hasClass("active")) {
      return "module";
    } else {
      return;
    }
  }

  // Create an object with given keys and initialization value for each
  function initObjectWithKeys(keys, val) {
    let obj = {};
    keys.forEach(function (key) {
      obj[key] = val;
    });
    return obj
  }


  let pointsGroupingMethods = ["difficulty", "module", "all"];

  let htmlTablePoints = "";
  let pointKeys = initObjectWithKeys(pointsGroupingMethods, []);

  let totalSubmitters = {};
  let totalMaxSubmitters = {};
  let totalSubmissions = {};
  let maxAllowedSubmissions = {};
  let maxPoints = {};
  // Initialise totals with zeros
  let maxPointsTotal = initObjectWithKeys(pointsGroupingMethods, 0);
  let totalPoints = {};

  let modulesSeen = initObjectWithKeys(pointsGroupingMethods, []);

  // Has to be called once for each grouping method to establish the assumably unchanging characteristics of the exercises and modules
  function tableDrawPreWork(firstPoints, pointsGroupingMethod) {
    // Gather information that is same for all students from the first student for better performance
    $(_exerciseSelection).each(function() {
      const moduleID = $(this).data("moduleId");
      const module = firstPoints.modules.filter(
        function(m) {
            return m.id == moduleID;
      })[0];
      const exerciseID = $(this).data("exerciseId");
      const exercise = module.exercises.filter(
        function(exercise) {
          return exercise.id == exerciseID;
        }
      )[0];

      // Grouped by difficulty
      if (pointsGroupingMethod === "difficulty") {
        maxPoints[pointsGroupingMethod][exercise.difficulty] = maxPoints[pointsGroupingMethod][exercise.difficulty] + exercise.max_points || exercise.max_points;
        maxPointsTotal[pointsGroupingMethod] += exercise.max_points;
        if (pointKeys[pointsGroupingMethod].indexOf(exercise.difficulty) === -1) {
          pointKeys[pointsGroupingMethod].push(exercise.difficulty);
          pointKeys[pointsGroupingMethod].sort();
        }
        _allExercises.forEach(function(exAll) {
          if (exAll.id === exercise.id) {
            maxAllowedSubmissions[pointsGroupingMethod][exercise.difficulty] = maxAllowedSubmissions[pointsGroupingMethod][exercise.difficulty] + exAll.max_submissions || exAll.max_submissions;
          }
        });
      }

      // Grouped by module
      if (pointsGroupingMethod === "module") {
        // Include modules corresponding to selected exercises just once in pointKeys[pointsGroupingMethod]
        // Required because multiple exercises can come from the same module
        if (modulesSeen[pointsGroupingMethod].indexOf(module) === -1) {
          modulesSeen[pointsGroupingMethod].push(module);
          pointKeys[pointsGroupingMethod].push(module.name);
        }

        // Include the exercise's particulars in the totals
        _allExercises.forEach(function(exAll) {
            if (exAll.id === exercise.id) {
              maxAllowedSubmissions[pointsGroupingMethod][module.name] = maxAllowedSubmissions[pointsGroupingMethod][module.name] + exAll.max_submissions || exAll.max_submissions;
              maxPoints[module.name] = maxPoints[module.name] + exercise.max_points || exercise.max_points;
              maxPointsTotal += exercise.max_points;
            }
        });

      }

      // Grouped by exercise
      if (pointsGroupingMethod === "all") {
        maxPoints[exercise.name] = exercise.max_points;
        maxPointsTotal += exercise.max_points;
        pointKeys[pointsGroupingMethod].push(exercise.name);

        _allExercises.forEach(function(exAll) {
          if (exAll.id === exercise.id) {
            maxAllowedSubmissions[pointsGroupingMethod][exercise.name] = exAll.max_submissions;
          }
        });
      }

    });
  }

  // Renders students rows and indicators
  // FIXME: Indicators and tags don't work
  let studentRendererObserver = {
    // Gather personal information for each student, eg. individual points
    next(studentAndPoints) {
      let student = studentAndPoints.student;
      let _points = studentAndPoints.points;
      let allPointsTotalAddedToRow = false;

      // Start the table row with the student's id, summary and full name
      htmlTablePoints += '<tr><td class="student-id stick-on-scroll">' + student.student_id + '</td>';
      htmlTablePoints +=
        '<td class="student-name stick-on-scroll">'
        + '<a href="' + student.summary_html + '">'
        + student.full_name + '</td>';

      // Run point calculations using all three methods and create the corresponding cells
      pointsGroupingMethods.forEach(function(pointsGroupingMethod) {
        let points = {};
        let unofficialPoints = {};

        // Calculate points for each difficulty by grouping exercises from each difficulty category together
        if (pointsGroupingMethod === "difficulty") {
          let submittedDifficulty = {};

          $(_exerciseSelection).each(function() {
            const moduleID = $(this).data("moduleId");
            const exerciseID = $(this).data("exerciseId");
            const exercise = _points.modules.filter(
              function(m) {
                return m.id == moduleID;
            })[0].exercises.filter(
              function(exercise) {
                return exercise.id == exerciseID;
              }
            )[0];

            const exercisePoints = exercise.official ? exercise.points : 0;
            points[exercise.difficulty] = points[exercise.difficulty] + exercisePoints || exercisePoints;
            unofficialPoints[exercise.difficulty] = unofficialPoints[exercise.difficulty] + exercise.points || exercise.points;
            totalPoints[pointsGroupingMethod][exercise.difficulty] = totalPoints[pointsGroupingMethod][exercise.difficulty] + exercisePoints || exercisePoints;
            if (exercise.submission_count > 0) {
              totalSubmissions[pointsGroupingMethod][exercise.difficulty] = totalSubmissions[pointsGroupingMethod][exercise.difficulty] + exercise.submission_count || exercise.submission_count;
              if (submittedDifficulty[exercise.difficulty] === undefined) {
                totalSubmitters[pointsGroupingMethod][exercise.difficulty] = totalSubmitters[pointsGroupingMethod][exercise.difficulty] + 1 || 1;
                submittedDifficulty[exercise.difficulty] = true;
              }
              if (points[exercise.difficulty] === maxPoints[exercise.difficulty]) {
                totalMaxSubmitters[pointsGroupingMethod][exercise.difficulty] = totalMaxSubmitters[pointsGroupingMethod][exercise.difficulty] + 1 || 1;
              }
            }
          });
        }

        // Calculate points for each module by grouping each module's exercises together
        if (pointsGroupingMethod === "module") {
          modulesSeen[pointsGroupingMethod] = [];

          $(_exerciseSelection).each(function() {
            const moduleID = $(this).data("moduleId");
            const module = _points.modules.filter(
              function(m) {
                return m.id == moduleID;
            })[0];
            const exerciseID = $(this).data("exerciseId");
            const exercise = module.exercises.filter(
              function(exercise) {
                return exercise.id == exerciseID;
              }
            )[0];

            const exercisePoints = exercise.official ? exercise.points : 0;
            points[module.name] = points[module.name] + exercisePoints || exercisePoints;
            unofficialPoints[module.name] = unofficialPoints[module.name] + exercise.points || exercise.points;
            totalPoints[pointsGroupingMethod][module.name] = totalPoints[pointsGroupingMethod][module.name] + exercisePoints || exercisePoints;

            if (modulesSeen[pointsGroupingMethod].indexOf(module) === -1) {
              modulesSeen[pointsGroupingMethod].push(module);
              if (module.submission_count > 0) {
                totalSubmissions[pointsGroupingMethod][module.name] = totalSubmissions[pointsGroupingMethod][module.name] + module.submission_count || module.submission_count;
                totalSubmitters[pointsGroupingMethod][module.name] = totalSubmitters[pointsGroupingMethod][module.name] + 1 || 1;
                if (points[module.name] === maxPoints[module.name]) {
                  totalMaxSubmitters[pointsGroupingMethod][module.name] = totalMaxSubmitters[pointsGroupingMethod][module.name] + 1 || 1;
                }
              }
            }
          });
        }

        // Calculate points for each exercise
        if (pointsGroupingMethod === "all") {
          $(_exerciseSelection).each(function() {
            const moduleID = $(this).data("moduleId");
            const exerciseID = $(this).data("exerciseId");
            const exercise = _points.modules.filter(
              function(m) {
                return m.id == moduleID;
            })[0].exercises.filter(
              function(exercise) {
                return exercise.id == exerciseID;
              }
            )[0];

            const exercisePoints = exercise.official ? exercise.points : 0;
            points[exercise.name] = exercisePoints;
            unofficialPoints[exercise.name] = exercise.points;
            totalPoints[pointsGroupingMethod][exercise.name] = totalPoints[pointsGroupingMethod][exercise.name] + exercisePoints || exercisePoints;
            if (exercise.submission_count > 0) {
              totalSubmissions[pointsGroupingMethod][exercise.name] = totalSubmissions[pointsGroupingMethod][exercise.name] + exercise.submission_count || exercise.submission_count;
              totalSubmitters[pointsGroupingMethod][exercise.name] = totalSubmitters[pointsGroupingMethod][exercise.name] + 1 || 1;
              if (exercisePoints === exercise.max_points) {
                totalMaxSubmitters[pointsGroupingMethod][exercise.name] = totalMaxSubmitters[pointsGroupingMethod][exercise.name] + 1 || 1;
              }
            }

          });
        }

        if (!allPointsTotalAddedToRow) {
          allPointsTotalAddedToRow = true;
          // Adds colortags and tally of total points
          // Must only be run with one set of keys (one pointsGroupingMethod)
          // Looking at the code, the calculation of points in points[] seems to result in the same total regardless of the method
          if (pointKeys[pointsGroupingMethod].length > 0) {
            let tagHtml = "";
            const studentTags = student.tag_slugs;

            studentTags.forEach(function(tagSlug) {
              _usertags.forEach(function(usertag) {
                if (usertag.slug === tagSlug) {
                  tagHtml += django_colortag_label(usertag, ' ')[0].outerHTML;
                }
              });
            });

            let allPointsTotal = 0;
            let allUnofficialTotal = 0;
            pointKeys[pointsGroupingMethod].forEach(function(name) {
            const point = points[name] || 0;
            const unofficialPoint = unofficialPoints[name] || 0;
              allPointsTotal += point;
              allUnofficialTotal += unofficialPoint;
            });

            htmlTablePoints += '<td>' + tagHtml + '</td>';

            if (!_showOfficial && allUnofficialTotal > allPointsTotal) {
              htmlTablePoints += '<td>' + allPointsTotal + '<span class="text-danger"> (' + allUnofficialTotal + ')</span></td>';
            }
            else {
              htmlTablePoints += '<td>' + allPointsTotal + '</td>';
            }
          }
        }


        // Adds the points calculated using the method (points for all the different difficulties for 'difficulty', modules for 'module', etc.)
        // Must be run with all sets of keys (using all pointsGroupingMethods)
        pointKeys[pointsGroupingMethod].forEach(function(name) {
          const point = points[name] || 0;
          const unofficialPoint = unofficialPoints[name] || 0;
          if (!_showOfficial && unofficialPoint > point) {
            htmlTablePoints += '<td>' + point + '<span class="text-danger"> (' + unofficialPoint + ')</span></td>';
          }
          else {
            htmlTablePoints += '<td>' + point + '</td>';
          }
        });
      });

      // Row end
      htmlTablePoints += "</tr>";
    },
    complete() {
      // Calculate the data indicators, e.g. average points, max points
      // Append headings, data indicators and student points to the html table

      $("#table-heading").append('<tr id="table-heading-row"></tr>')
      $("#table-heading-row").append('<th id="student-count">' + _("Student ID") + '</th>');
      $("#table-heading-row").append('<th>' + _("Student name") + '</th>');
      if (_exerciseSelection && _exerciseSelection.length > 0) {
        $("#table-heading-row").append('<th>' + _("Tags") + '</th>');
        $("#table-heading-row").append('<th>' + _("Total") + '</th>');
      }

      let htmlTableIndicators = "";

      pointsGroupingMethods.forEach(function(pointsGroupingMethod) {
        pointKeys[pointsGroupingMethod].forEach(function(name) {
          if (pointsGroupingMethod === "difficulty" && name === "") {
            $("#table-heading-row").append('<th scope="col">' + _("No difficulty") + '</th>');
          } else {
            $("#table-heading-row").append('<th scope="col">' + name + '</th>');
          }
        });


        if (_totalSubmTrue) {
          let dataVals = [];
          let sumValue = 0;
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            sumValue += totalSubmissions[pointsGroupingMethod][name] || 0;
          });

          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              totalSubmissions[pointsGroupingMethod][name] || 0,
              totalSubmissions[pointsGroupingMethod][name] / sumValue * 100 || 0,
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Total number of submissions. Calculates all student submission counts together.'),
            _('Total submissions'),
            dataVals
          );
        }

        if (_avgSubmTrue) {
          let dataVals = [];
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              totalSubmissions[pointsGroupingMethod][name] / totalSubmitters[pointsGroupingMethod][name] || 0,
              totalSubmissions[pointsGroupingMethod][name] / totalSubmitters[pointsGroupingMethod][name] / maxAllowedSubmissions[pointsGroupingMethod][name] * 100 || 0
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('How many submissions a single student has used on the exercise on average.'
              + ' Only accounts for students with one or more submissions.'
            ),
            _('Average submissions per student with submissions'),
            dataVals
          );
        }

        if (_maxSubmTrue) {
          let dataVals = [];
          let sumValue = 0;
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            sumValue += maxAllowedSubmissions[pointsGroupingMethod][name] || 0;
          });

          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              maxAllowedSubmissions[pointsGroupingMethod][name] || 0,
              maxAllowedSubmissions[pointsGroupingMethod][name] / sumValue * 100 || 0,
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Maximum number of available submissions for the exercise.'),
            _('Maximum submissions'),
            dataVals
          );
        }

        if (_totalStuSubmTrue) {
          let dataVals = [];
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              totalSubmitters[pointsGroupingMethod][name] || 0,
              totalSubmitters[pointsGroupingMethod][name] / _studentsVisibleCount * 100 || 0
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Number of students that have one or more exercise submissions.'),
            _('Students with submissions'),
            dataVals
          );
        }

        if (_totalStuMaxTrue) {
          let dataVals = [];
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              totalMaxSubmitters[pointsGroupingMethod][name] || 0,
              totalMaxSubmitters[pointsGroupingMethod][name] / totalSubmitters[pointsGroupingMethod][name] * 100 || 0
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Number of students that have received maximum points from the exercise.'),
            _('Students with max points'),
            dataVals
          );
        }

        if (_avgPTrue) {
          let dataVals = [];
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              totalPoints[pointsGroupingMethod][name] / totalSubmitters[pointsGroupingMethod][name] || 0,
              totalPoints[pointsGroupingMethod][name] / totalSubmitters[pointsGroupingMethod][name] / maxPoints[name] * 100 || 0
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Average points received for the exercise.'
              + ' Only accounts for students with one or more submissions.'
            ),
            _('Average points per student with submissions'),
            dataVals
          );
        }

        if (_maxPTrue) {
          let dataVals = [];
          pointKeys[pointsGroupingMethod].forEach(function(name) {
            dataVals.push([
              maxPoints[name] || 0,
              maxPoints[name] / maxPointsTotal * 100 || 0
            ]);
          });

          htmlTableIndicators += createIndicatorRow(
            _('Maximum points for the exercise.'),
            _('Maximum points'),
            dataVals
          );
        }
      });

      $("#table-body").append(htmlTableIndicators);
      $("#table-body").append(htmlTablePoints);
      $(".colortag-active").css("margin-right", "5px");
      $("#student-count").append(
        ' (<span id="selected-number">' + _studentsVisibleCount + '</span> / '
        + '<span id="participants-number">'+ _studentCount + '</span>'
        + _(' students selected') + ')'
      );
      tableExportVar.reset();
      $('#table-points').find("caption").remove(); // Remove the recreated TableExport buttons (they are already in dropdown)
      $('.filtered-table').aplusTableFilter();
      console.log("Rendering complete");
    }
  }

  // Show columns specific to a grouping method and hide others
  function choosePointsGroupingMethod(method) {

  }

  // Add a student to the table as a row
  function addStudentRowToTable(student) {
    let htmlTablePoints = "";
    htmlTablePoints += '<tr><td class="student-id stick-on-scroll">' + student.student_id + '</td>';
    htmlTablePoints += '<td class="student-name stick-on-scroll">'
                       + '<a href="' + student.summary_html + '">'
                       + student.full_name + '</td>';
    $("#table-body").append(htmlTablePoints);
  }

  // Map a student to points, calling the API
  function studentToPoints(student) {
    const sid = student.id;
    return $.ajax(
      $.extend({}, ajaxSettings, {url: pointsUrl + sid})
    ).then(function(data) {
      return data;
    });
  }

  // Stream data from a paged JSON API into an Observer
  function APIPagingStream(observer, url) {
    function stream(url) {
      return $.ajax(
        $.extend({}, ajaxSettings, {url: url})
      ).then(function(response) {
        response.results
                .forEach(function(r) { observer.next(r) });
        if (response.next) {
          stream(response.next);
        } else {
          observer.complete()
        }
      }, function(reason) {
        throw new Error("Pagination ajax failed: " + reason.statusText);
      });
    }
    this.start = function() {
      stream(url)
    };
  }

  // An object adhering to the observer interface that keeps track of loading progress and finishes rendering
  let progressObserver = {
    progress: 0,
    next() {
      this.progress++;
      $("#results-loading-progress").html(this.progress);
    },
    complete() {
      exerciseSelectionChange();
      $("#results-loading-animation").hide();
      $("#results-loading-progress").hide();
      $("#table-export-dropdown > button").removeAttr('disabled');
      $("#table-points-div").show();
      //storeDataLocally('localStorage', storageKey, toStorage())
    }
  }


  /*
   *  Setting up pipeline
   */

  // Source for pipeline
  let studentsSubject = new rxjs.Subject();
  let studentsStream = new APIPagingStream(studentsSubject, studentsUrl);

  // Students => points
  let pointsObservable = studentsSubject.pipe(
    map(studentToPoints),
  );

    // Populate exercise selection
  pointsObservable.pipe(
    first(),
    map(function(firstPoints) {
        firstPoints.then(populateExerciseSelection)
    }),
  ).subscribe();

  // Save student count
  let studentCounter = studentsSubject.pipe(count())
                                      .subscribe(function (c) { _studentCount = c });

  // Track data fetching progress
  studentsSubject.pipe(tag("students"))
                 .subscribe(progressObserver);

  // Students + points in one for rendering
  let studentsAndPointsObservable = studentsSubject.pipe(
    map(function(student) { return {student:student, points:studentToPoints(student)} }),
  );

  // Prework with the first student
  preworkObservable = studentsSubject.pipe(
    first(),
    map(function(firstOne) {
        pointsGroupingMethods.forEach(function(pointsGroupingMethod) {
          tableDrawPreWork(firstOne, pointsGroupingMethod);
        })
    }),
  );

  // Do table prework, then render
  concat(preworkObservable.pipe(ignoreElements()), studentsAndPointsObservable.pipe(tag("render")))
    .subscribe(studentRendererObserver);

  // Start pipeline
  studentsStream.start();

  // Show table (happends immediately because other calls asynchronous?)
  $("#table-points-div").show();



  /* TODO: consider using rxjs.Observable.ajax.getJSON
  */



})(jQuery, document, window);

/* vim: set et ts=4 sw=4: */
