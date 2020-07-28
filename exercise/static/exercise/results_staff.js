(function($, document, window, undefined) {

  const { Observable, Subject, concat, fromEvent } = rxjs;
  const { map, first, count, find, ignoreElements } = rxjs.operators;

  const tag = rxjsSpy.operators.tag;
  spy = rxjsSpy.create();
  spy.log("users");


  const currentScript = (document.currentScript
    ? $(document.currentScript)
    : $('script').last()); // Ugly solution for IE11

  const exercisesUrl = currentScript.data("exercisesUrl");
  const studentsUrl = currentScript.data("studentsUrl");
  const usertagsUrl = currentScript.data("usertagsUrl");
  const pointsUrl = currentScript.data("pointsUrl");

  const ajaxEnabled = true;

  /* Custom AJAX settings to use with jQuery.ajax()
   * - Possibility to disable AJAX
   * - Retrying and retry limits (call specific)
   */
  const ajaxSettings = {
    _retryCount: 0,
    _retryLimit: 3,
    timeout: 0,
    beforeSend: function(xhr, settings) {
      return ajaxEnabled;
    },
    error: function(xhr, statusText, errorThrown) {
      this._retryCount += 1;
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

  let _tagSlugFilters = [];
  let _exerciseSelection;
  let _studentCount;
  let _visibleStudentSpan;
  let _participantNumberSpan;
  // let _exercises;
  // let _students;
  // let _users = {};
  let _usertags;
  // let _points = {};
  let _exerciseFilterID = 0;
  let _tagFilterID = 0;
  let _prevOfficiality = true;
  let _showOfficial = true;

  let tableExportVar;

  /**
    * Create an object with given keys and initialization value for each
    * @param {Array[String]} keys Collection of keys to initialize object with
    * @param val The value to provide for each key. If the val is an array or
    * an object, a shallow copy is mady for each key.
    */
  function initObjectWithKeys(keys, val) {
    // makes shallow copies of arrays and objects
    const clone =
      Array.isArray(val) ? (arg) => ([...arg])
      : (typeof val === 'object' && val !== 'null') ? (arg) => ({...arg})
      : (arg) => (arg);

    let obj = {};
    keys.forEach((key) => {
      obj[key] = clone(val);
    });
    return obj;
  }

  const pointsGroupingMethods = ["difficulty", "module", "all"];
  const pointKeys = initObjectWithKeys(pointsGroupingMethods, []);

  // maps exercise ID's to max point count, max submission count and difficulty
  const maxPoints = {};
  const maxSubmissions = {};
  const exerciseDifficulties = {};

  const columnIndexMap = initObjectWithKeys(pointsGroupingMethods, {}); // if we want also student-data indices: .concat('student-data')
  const columnMap = initObjectWithKeys(pointsGroupingMethods.concat('student-data'), {}); // [groupingMethod: [id: column]]

  const indicatorRows = initObjectWithKeys(['dynamic', 'static'], {});
  // Maps userIDs to table rows. Key: student.id, value: HTMLTableRowElement
  const studentRowMap = new Map();

  const hiddenCellIndices = new Set();
  hiddenCellIndices.add(2);

  // Key: jQuery object; Value: [dynamic, id]
  const indicatorCheckboxes = new Map();
  indicatorCheckboxes.set($("input.total-subm-checkbox"), [true, 'totalSubmissions']);
  indicatorCheckboxes.set($("input.avg-subm-checkbox"), [true, 'averageSubmissions']);
  indicatorCheckboxes.set($("input.max-subm-checkbox"), [false, 'maxSubmissions']);
  indicatorCheckboxes.set($("input.total-stu-subm-checkbox"), [true, 'studentsWithSubs']);
  indicatorCheckboxes.set($("input.total-stu-max-checkbox"), [true, 'studentsWithMaxPoints']);
  indicatorCheckboxes.set($("input.avg-p-checkbox"), [true, 'averagePoints']);
  indicatorCheckboxes.set($("input.max-p-checkbox"), [false, 'maxPoints']);


  // Add to the value of a key-value pair in an object
  function addTo(dict, key, value) {
    dict[key] = dict[key] + value || value
  }

  function sumReducer(acc, cur) {
    return acc + cur;
  }

  function roundToTwo(value) {
    return Number.isInteger(value) ? value : value.toFixed(2);
  }
  function percent(value) {
    return roundToTwo(value * 100) + "\u00A0%";
  }

  function createOptgroup(attrs) {
    const optgroup = document.createElement('optgroup');
    for (key in attrs) {
      optgroup.setAttribute(key, attrs[key]);
    }
    return optgroup;
  }

  function addOptionToElement(parent, text, attrs) {
    const opt = document.createElement('option');
    for (key in attrs) {
      opt.setAttribute(key, attrs[key]);
    }
    opt.textContent = text;
    parent.appendChild(opt);
  }

  function addThToRow(row, opts) {
    const cell = document.createElement('th');
    const {text, insertBefore, hidden, ...rest} = opts;
    Object.entries(rest).forEach(([attr, value]) => {
      cell.setAttribute(attr, value);
    });
    if (text){
      cell.textContent = text;
    }
    if (insertBefore) {
      row.insertBefore(cell, insertBefore)
    } else {
      row.appendChild(cell);
    }
    if (hidden) {
      cell.hidden = hidden;
    }
    return cell;
  }

  function addCellToRow(row, opts) {
    let cell = row.insertCell();
    const {text, url, hidden, ...rest} = opts;
    Object.entries(rest).forEach(([attr, value]) => {
      cell.setAttribute(attr, value);
    });
    if (text || (text === 0)) {
      if (url) {
        const anch = document.createElement('a');
        anch.href = url;
        anch.textContent = text;
        cell.appendChild(anch);
      } else {
        cell.textContent = text;
      }
    }
    if (hidden) {
      cell.hidden = hidden;
    }
    return cell;
  }

  function addColToColgroup(colgroup, opts) {
    const col = document.createElement('col');
    for (let attr of [
      'class',
      'style',
      // 'span',
    ]) {
      if (opts[attr]) {
        col.setAttribute(attr, opts[attr]);
      }
    }
    if (opts.hidden) {
      col.hidden = true;
    }
    colgroup.appendChild(col);
    if (opts.grouping && opts.id) {
      columnMap[opts.grouping][opts.id] = col;
    }
  }

  /**
    * @param {Array[HTMLTableRowElement]} rows The rows to be shown or hidden.
    * @param {Boolean} show Whether to show (true) or hide (false) the rows.
    */
  function toggleRows(rows, show) {
    rows.forEach((row) => {
      row.hidden = !show;
    });
  }

  /**
    * @param {HTMLTableRowElement} row The row whose children are shown
    * or hidden.
    * @param {Array[Number]} indices The indices of the children to be
    * shown or hidden.
    * @param {Boolean} show Whether to display (true) the specified
    * children or hide them (false).
    */
  function toggleCellsOnRow(row, indices, show) {
    const cells = row.children;
    indices.forEach((i) => {
      const cell = cells[i];
      if (cell) {
        cell.hidden = !show;
      }
    });
  }

  /**
    * Checks which exercises are selected to be displayed by the user.
    * Converts jQuery object of the selected exercise options to a map
    * listing the selected exercises so that the key is the module ID
    * and the value an array of the selected exercises' IDs. The map has
    * keys for only those modules with selected exercises.
    */
  function getExerciseSelection() {
    const $exerciseSelection = $('#exercise-selection option:selected');
    const selectedExercises = new Map();
    $exerciseSelection.each(function (i, elem) {
      const data = elem.dataset;
      const moduleID = Number(data['moduleId']);
      const exerciseID = Number(data['exerciseId']);
      if (selectedExercises.get(moduleID)) {
        selectedExercises.get(moduleID).push(exerciseID);
      } else {
        selectedExercises.set(moduleID, [exerciseID]);
      }
    });
    return selectedExercises;
  }

  // Returns all grouping methods that are currently selected
  function getGroupingMethods() {
    return $('#point-grouping-selection').find(':checked').toArray()
      .map((cb) => cb.value);
  }


  /**
    * Hides or reveals cells in the specified columns within the
    * indicator rows.
    * @param {Array[Number]} indices Indices of the colums to show or hide.
    * @param {Boolean} show Whether to reveal (true) or hide (false) the cells.
    */
  function toggleColumnsOnIndicatorRows(indices, show) {
    // account for the first cell having a colspan of 2.
    const normalIndicatorIndices = indices.map((i) => i-1);
    // account for the first cell in the row above having a colspan and rowspan of 2
    const percentIndicatorIndices = indices.map((i) => i-2);
    $('#indicator-rows tr.indi-normal-row').each((i, row) => (
      toggleCellsOnRow(row, normalIndicatorIndices, show)
    ));
    $('#indicator-rows tr.indi-pct-row').each((i, row) => (
      toggleCellsOnRow(row, percentIndicatorIndices, show)
    ));
    if (Object.keys(indicatorRows.static).length > 0) {
      scheduleIndicatorRowUpdate();
    }
  }

  /**
    * Hides or reveals cells in the specified columns within the the entire table.
    * @param {Array[Number]} indices Indices of the colums to show or hide.
    * @param {Boolean} show Whether to reveal (true) or hide (false) the cells.
    */
  function toggleColumnsByIndex(indices, show) {
    $('#table-heading, #student-rows').find('tr').each((i, row) => (
      toggleCellsOnRow(row, indices, show)
    ));
    toggleColumnsOnIndicatorRows(indices, show);
  }

  /** Hide or reveal exercise or module columns. If columns are to be
    * revealed, reveals only those indicated in the exercise selection
    * (and by the grouping method indicated in the parameters).
    * @param {Boolean} show Whether to reveal (true) some/all of the
    * columns or (false) hide all of them.
    * @param {String} groupingMethod String indicating the grouping
    * method, should be either 'module' or 'all'.
    */
  function toggleModuleOrExerciseColumns(show, groupingMethod) {
    if (show) {
      const selectedIDs = (groupingMethod === 'module')
        ? Array.from(
          _exerciseSelection,
          (([modID, exercises]) => modID)
        )
        : Array.from(
          _exerciseSelection,
          (([moduleID, exercises]) => exercises)
        ).flat();
      const selectedIndices = selectedIDs.map((id) => {
        columnMap[groupingMethod][id].hidden = false; // show col-tag
        const index = columnIndexMap[groupingMethod][id];
        hiddenCellIndices.delete(index);
        return index;
      });
      toggleColumnsByIndex(selectedIndices, true);
      const unselectedIDs = pointKeys[groupingMethod].filter((id) => (
        !selectedIDs.includes(id)
      ));
      const unselectedIndices = unselectedIDs.map((id) => {
        columnMap[groupingMethod][id].hidden = true; // hide col-tag
        const index = columnIndexMap[groupingMethod][id];
        hiddenCellIndices.add(index);
        return index;
      });
      toggleColumnsByIndex(unselectedIndices, false);
    } else { // hide all
      const indices = Object.values(columnIndexMap[groupingMethod]);
      toggleColumnsByIndex(indices, false);
      indices.forEach((i) => {
        hiddenCellIndices.add(i);
      });
      // hide respective col-tags
      Object.values(columnMap[groupingMethod]).forEach((col) => {
        col.hidden = true;
      });
    }
  }

  /**
    * Hide or reveal columns related to specified grouping method.
    */
  function toggleColumns(groupingMethod, show) {
    if (groupingMethod === 'module' || groupingMethod === 'all') {
      toggleModuleOrExerciseColumns(show, groupingMethod);
    } else {
      const indices = Object.values(columnIndexMap[groupingMethod]);
      if (show) {
        indices.forEach((i) => hiddenCellIndices.delete(i));
      } else {
        indices.forEach((i) => hiddenCellIndices.add(i));
      }
      toggleColumnsByIndex(indices, show);
      Object.values(columnMap[groupingMethod]).forEach((col) => {
        col.hidden = !show;
      })
    }
  }

  /**
    * Hide or reveal all columns related to point grouping methods
    * according to grouping and exercise selections.
    */
  function updateAllColumnVisibilities() {
    const currentGroupings = getGroupingMethods();
    pointsGroupingMethods.forEach((pgm) => {
      const show = currentGroupings.includes(pgm);
      toggleColumns(pgm, show);
    });
  }

  /**
    * Change handler for point grouping checkboxes.
    * Triggers hiding/revealing of the respective grouping method columns.
    */
  function groupingSelectionChange(event) {
    // if exercise selection hasn't been populated,
    // drawTablePrework hasn't been called either, don't do anything
    if (_exerciseSelection === undefined) {
      return;
    }
    const checkbox = event.target;
    const groupingMethod = checkbox.value;
    const shown = checkbox.checked;
    toggleColumns(groupingMethod, shown);
  }

  /**
    * Update total, difficulty and module point sums according to
    * exercise selection and officiality.
    * @param {HTMLTableRowElement} row The row on which to update sums.
    */
  function updateSumsOnStudentRow(row) {
    const rowFilterID = row.dataset.exerciseFilterId
    if (rowFilterID && rowFilterID != _exerciseFilterID) {
      const cells = row.children;
      const difficultyPointSums = {};
      const submissionsByDiff = initObjectWithKeys(pointKeys.difficulty, 0);
      _exerciseSelection.forEach((exercises, moduleID) => {
        let moduleSum = 0;
        let moduleSubmissions = 0;
        exercises.forEach((exerciseID) => {
          const exerciseCellIndex = columnIndexMap.all[exerciseID]
          const exerciseCell = cells[exerciseCellIndex];
          const cellData = exerciseCell.dataset;
          const points = Number(cellData.points);
          const subCount = Number(cellData.submissionCount);
          const difficulty = exerciseDifficulties[exerciseID];
          moduleSubmissions += subCount;
          submissionsByDiff[difficulty] += subCount;
          if (exerciseCell.classList.contains('unofficial')) {
            if (!_showOfficial) {
              addTo(difficultyPointSums, difficulty, points);
              moduleSum += points;
              exerciseCell.textContent = points;
            } else {
              exerciseCell.textContent = 0;
            }
          } else {
            addTo(difficultyPointSums, difficulty, points);
            moduleSum += points;
          }
        });
        const moduleCellIndex = columnIndexMap.module[moduleID];
        const moduleCell = cells[moduleCellIndex];
        moduleCell.textContent = moduleSum;
        moduleCell.setAttribute('data-submission-count', moduleSubmissions);
      });
      // update difficulty sums
      Object.entries(columnIndexMap.difficulty).forEach(([diffName, index]) => {
        const cell = cells[index];
        const pointSum = difficultyPointSums[diffName];
        // if none of the selected exercises have the difficulty, indicate with –
        cell.textContent = (pointSum !== undefined) ? pointSum : "–";
        const diffSubs = submissionsByDiff[diffName];
        cell.setAttribute('data-submission-count', diffSubs);
      });
      // update total points
      const totalCell = cells[columnIndexMap.total];
      const totalSum = Object.values(difficultyPointSums).reduce(sumReducer, 0);
      totalCell.textContent = totalSum;
      const totalSubs = Object.values(submissionsByDiff).reduce(sumReducer, 0);
      totalCell.setAttribute('data-submission-count', totalSubs);
      row.dispatchEvent(new Event('student row sums updated'));
    }
  }

  /**
    * Update total, difficulty and module point sums according to
    * exercise selection and officiality on all student rows.
    * Dispatches event for each row, whose listener then calls method
    * to update sums.
    */
  function updateStudentRowSums() {
    // TODO: first update visible students, then the rest
    studentRowMap.forEach((row, id) => {
      // row.dataset.exerciseFilterID doesn't have a value before points are added
      if (row.dataset.exerciseFilterId) {
        row.dispatchEvent(new Event('exercise selection changed'))
      }
    });
  }

  /**
    * Exercise selection 'change handler'.
    * Updates the value of _exerciseSelection, updates sums on student
    * rows, and toggles columns so proper exercise and module columns
    * are displayed in the table.
   */
  function exerciseSelectionChange() {
    newExerciseSelection = getExerciseSelection();
    if (
      _exerciseSelection != newExerciseSelection // exercise selection has changed
      || _prevOfficiality != _showOfficial // showOfficial has changed
    ) {
      _exerciseSelection = newExerciseSelection;
      _prevOfficiality = _showOfficial;
      _exerciseFilterID += 1;

      updateStudentRowSums();
      const groupingMethods = getGroupingMethods();
      ['module', 'all'].forEach((grouping) => {
        toggleModuleOrExerciseColumns(
          groupingMethods.includes(grouping),
          grouping,
        );
      });
    }
  }

  /*
   * Schedules timeout so when exercise selection is changed many times
   * in a row, following updates are called only once after a short delay.
  */
  let exerciseSelectionTimeout;
  function scheduleExerciseSelectionChange() {
    clearTimeout(exerciseSelectionTimeout);
    exerciseSelectionTimeout = setTimeout(
      () => document.dispatchEvent(new Event('exercise selection changed')),
      1000
    );
  }

  /*
   * Schedules timeout so when module selection is changed many times
   * in a row, following updates are called only once after a short delay.
  */
  let moduleSelectionTimeout;
  function scheduleModuleSelectionChange() {
    clearTimeout(moduleSelectionTimeout);
    moduleSelectionTimeout = setTimeout(
      () => document.dispatchEvent(new Event('module selection changed')),
      500
    );
  }

  /*
   * Handles the module selection when teacher selects or unselects a module(s).
   * If a module is selected, select and show all the module's exercises in exercise selection.
   * If a module is unselected, unselect and hide all module's exercises in exercise selection.
   */
  function moduleSelectionChange() {
    const $selectedModules = $('#module-selection option:selected');
    const $nonSelectedModules = $('#module-selection option').filter(function(i, elem) {
      return !elem.selected;
    });

    $selectedModules.each(function(i, elem) {
      const showModuleClass = '.' + elem.value;
      $(showModuleClass).removeClass("hidden disabled");
      $(showModuleClass).prop("selected", true);
    });

    $nonSelectedModules.each(function(i, elem) {
      const hideModuleClass = '.' + elem.value;
      $(hideModuleClass).addClass("hidden disabled");
      $(hideModuleClass).prop("selected", false);
    });

    $("#exercise-selection").multiselect('refresh');
    scheduleExerciseSelectionChange();
  }


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

  /* Take as the argument a single student's points
   * and populate the exercise and module selection dropdown menu
   */
  function populateExerciseSelection(firstStudentPoints) {
    const moduleSelection = document.getElementById('module-selection');
    const exerciseSelection = document.getElementById('exercise-selection');

    firstStudentPoints.modules.forEach(function(module) {
      addOptionToElement(
        moduleSelection,
        module.name,
        {
          'data-module-id': module.id,
          'value': 'module-' + module.id,
          'selected': ""
        }
      );
      const optgroup = createOptgroup({
        'class': 'module-' + module.id,
        'value': 'module-' + module.id,
        'label': module.name,
      });
      exerciseSelection.appendChild(optgroup);
      module.exercises.forEach(function(exercise) {
        addOptionToElement(
          optgroup,
          exercise.name,
          {
            'data-module-id': module.id,
            'data-exercise-id': exercise.id,
            'class': 'module-' + module.id,
            'value': 'exercise-' + exercise.id,
            'selected': ""
          }
        );
      });
    });

    $(moduleSelection).multiselect({
      includeSelectAllOption: true,
      onDeselectAll: scheduleModuleSelectionChange,
      onSelectAll: scheduleModuleSelectionChange,
      onChange: scheduleModuleSelectionChange,
      buttonText: buttonText,
      selectAllText: _("Select all"),
    });
    $(exerciseSelection).multiselect({
      includeSelectAllOption: true,
      enableClickableOptGroups: true,
      onDeselectAll: scheduleExerciseSelectionChange,
      onSelectAll: scheduleExerciseSelectionChange,
      onChange: scheduleExerciseSelectionChange,
      maxHeight: 500,
      buttonText: buttonText,
      selectAllText: _("Select all"),
    });

    _exerciseSelection = getExerciseSelection();

    document.addEventListener(
      'module selection changed',
      moduleSelectionChange
    );
    document.addEventListener(
      'exercise selection changed',
      exerciseSelectionChange
    );
  }

  /**
    * Renders the table other than the student and indicator rows.
    * Adds column headings and col tags to points table.
    * Also stores information about exercises, point keys, etc.
    * @param {Object} firstPoints The points of a student from the API
    *   based on which the general information in the table can be
    *   rendered.
    * @param {RxJS.Subject} exerciseCountSubject A subject to which the
    *   number of exercises can be passed to.
    */
  function drawTablePrework(firstPoints, exerciseCountSubject) {
    const headingRow = document.getElementById('table-heading-row');
    const studentDataColgroup = document.getElementById('cg-student-data');
    const difficultyColgroup = document.getElementById('cg-difficulty');
    const modAndExColgroup = document.getElementById('cg-modules-exercises');

    addThToRow(headingRow, {
      class: 'stick-on-scroll',
      scope: 'col',
      text: _("Student ID"),
    });
    addColToColgroup(studentDataColgroup, {
      style: 'min-width: 6em',
      grouping: 'student-data',
      id: 'id',
    });
    addThToRow(headingRow, {
      class: 'stick-on-scroll',
      scope: 'col',
      text: _("Student name"),
    });
    addColToColgroup(studentDataColgroup, {
      grouping: 'student-data',
      id: 'name',
    });
    addThToRow(headingRow, {
      scope: 'col',
      text: _("Email address"),
      hidden: true,
    });
    addColToColgroup(studentDataColgroup, {
      grouping: 'student-data',
      id: 'email',
      hidden: true,
    });
    addThToRow(headingRow, {
      scope: 'col',
      text: _("Tags"),
    });
    addColToColgroup(studentDataColgroup, {
      grouping: 'student-data',
      id: 'tags',
    });
    // columnIndexMap.studentData = {
    //   'id': 0,
    //   'name': 1,
    //   'email': 2,
    //   'tags': 3,
    // }
    addThToRow(headingRow, {
      scope: 'col',
      text: _("Total"),
    });
    columnIndexMap.total = 4;

    // temporary storage for calculating indices
    const modAndExColumnArray = [];

    firstPoints.modules.forEach((module) => {
      // General data and grouping by modules
      // modulesMap.set(module.id, module)
      pointKeys.module.push(module.id);
      addThToRow(headingRow, {
        scope: 'col',
        class: 'pt-module',
        text: module.name,
      });
      addColToColgroup(modAndExColgroup, {
        grouping: 'module',
        id: module.id,
        class: 'pt-module',
      });
      modAndExColumnArray.push(['module', module.id]);

      module.exercises.forEach((exercise) => {
        exerciseDifficulties[exercise.id] = exercise.difficulty;
        if (!pointKeys.difficulty.includes(exercise.difficulty)) {
          pointKeys.difficulty.push(exercise.difficulty);
        };

        // Grouped by exercise
        maxPoints[exercise.id] = exercise.max_points;
        pointKeys.all.push(exercise.id);
        addThToRow(headingRow, {
          scope: 'col',
          class: 'pt-all',
          text: exercise.name,
        });
        addColToColgroup(modAndExColgroup, {
          grouping: 'all',
          id: exercise.id,
          class: 'pt-all',
        });
        modAndExColumnArray.push(['all', exercise.id]);
      });
    });
    // Add difficulty cells
    const firstModuleCell = headingRow.children[5];
    pointKeys.difficulty = pointKeys.difficulty.sort();
    pointKeys.difficulty.forEach((name) => {
      const text = name ? name : _("No difficulty");
      addThToRow(headingRow, {
        insertBefore: firstModuleCell,
        scope: 'col',
        class: 'pt-difficulty',
        text: text,
      });
      addColToColgroup(difficultyColgroup, {
        grouping: 'difficulty',
        id: name,
      });
      const diffColumnArray = pointKeys.difficulty.map((name) => (
        ['difficulty', name]
      ));
      const pointGroupingsColumnArray = diffColumnArray.concat(modAndExColumnArray);
      pointGroupingsColumnArray.forEach(([group, id], i) => {
        // Array doesn't include 4 student data cells nor the total points
        columnIndexMap[group][id] = i + 5;
      });
    });
    updateAllColumnVisibilities();

    const exerciseCount = pointKeys.all.length;
    exerciseCountSubject.next(exerciseCount);
    exerciseCountSubject.complete();

    // TODO: get aplusTableFilter working with results page
    // $('#table-points').aplusTableFilter();
  }

  // STUDENT ROWS

  /** Takes a HTMLElement of a student row and list of tag slugs to
    * filter by as arguments and returns a boolean indicating whether
    * the row should be shown (thus the student has all the tags that
    * are required).
    * @param {HTMLTableRowElement} row The row to check whether it has
    *   all the tags.
    * @param {Array[String]} tagSlugFilter Array consisting of tag
    *   slugs of the tags that are required.
    */
  function studentRowHasAllTags(row, tagSlugFilters) {
    const $row = $(row);
    // Pick only students that have the selected tags
    // Use same logic for tag filtering as in participants.js
    const studentTagSlugs = $.makeArray(
      $row.find('.colortag').map((i, tag) => (
        tag.getAttribute('data-tagslug')
      ))
    );
    // check if row contains all colortags that are filtered with
    const hasAll = tagSlugFilters.every((tagSlug) => (
      studentTagSlugs.includes(tagSlug)
    ));
    return hasAll;
  };

  /**
    * Check whether the row should be visible according to filtering
    * by colortags, and update visibility respectively.
    * @param {HTMLTableRowElement} row The row whose visiblity to update
    */
  function updateStudentRowVisibility(row) {
    row.dataset.tagFilterId = _tagFilterID;
    // cannot use jQuery methods show() and hide() as aplusTableFilter
    // uses them and would reveal rows.
    // jQuery uses 'display: none', so we use 'hidden' here.
    row.hidden = !studentRowHasAllTags(row, _tagSlugFilters);
    row.dispatchEvent(new Event('visibility updated')); // not necessarily, but we're too lazy to actually check.
  }

  // Filter the students rows in the table, setting visibility
  function filterStudentRows() {
    studentRowMap.forEach((row, id) => {
      if (row.dataset.tagFilterID != _tagFilterID) {
        updateStudentRowVisibility(row);
      }
      // row.dispatchEvent(new Event('tagfilters updated'));
    });
  }

  /** Add a student to the table as a row.
    * Adds all info except points and submissions.
    * @param {Object} student Student data
    * @param {RxJs.Subject} studentTagSubject A subject to which
    *   student tag slugs are passed with the student id to await processing
    */
  function addStudentRowToTable(student, studentTagSubject) {
    const rowgroup = document.getElementById('student-rows'); // should this be saved in a const somewhere at the beginning of this file?
    let row = rowgroup.insertRow();
    row.dataset.id = student.id;
    studentRowMap.set(student.id, row); // Note: NOT student id
    addCellToRow(row, {
      class: 'student-id stick-on-scroll',
      text: student.student_id,
    });
    addCellToRow(row, {
      class: 'student-name stick-on-scroll',
      text: student.full_name,
      url: student.summary_html,
    })
    addCellToRow(row, {
      text: student.email,
      hidden: true,
    })
    // create cell for tags, generate colortags and add them to the cell
    const tagCell = addCellToRow(row, {});
    studentTagSubject.next([tagCell, student.tag_slugs]);
    // return row;
  }

  /**
    * Add the respective usertag to the cell for each tagslug the
    * student has.
    * @param {HTMLTableDataCellElement} cell The cell to which the
    *   colortags should be added.
    * @param {Array[String]} studentTagSlugs The slugs of the tags that
    *   the student has.
    * @param {Array[Object]} usertags Array of all usertags with their data.
    */
  function addTagsToCell(cell, studentTagSlugs, usertags) {
    $(cell).empty() // empty the cell in case there is something there already
    studentTagSlugs.forEach((tagSlug) => {
      const usertag = usertags.find((tag) => tag.slug == tagSlug);
      // TODO: do we need to check if the tag is found
      const colortag = django_colortag_label(usertag, {})[0]; // jQuery object -> DOM element
      cell.appendChild(colortag);
    });
    const row = cell.parentNode;
    row.dataset.tagFilterId = 0; // no filtering
    row.dispatchEvent(new Event('student tags updated')); // or should the parent row dispatch it?
  }

  function addPointsToStudentRow(studPoints) {
    const row = studentRowMap.get(studPoints.id);
    // Total points:
    const totalCell = addCellToRow(row, {
      text: studPoints.points,
    });
    // Points by difficulty:
    const pointsByDiff = studPoints.points_by_difficulty;
    const difficultyCells = pointKeys.difficulty.map((diff) => {
      const numberOfPoints = pointsByDiff[diff] ? pointsByDiff[diff] : 0;
      const diffCell = addCellToRow(row, {
        class: 'pt-difficulty',
        text: numberOfPoints,
      });
      return [diff, diffCell];
    });
    const submissionsByDiff = initObjectWithKeys(pointKeys.difficulty, 0);
    // Points by module and exercise:
    studPoints.modules.forEach((module) => {
      const moduleCell = addCellToRow(row, {
        class: 'pt-module',
        text: module.points,
      });
      let moduleSubmissions = 0;
      module.exercises.forEach((exercise) => {
        moduleSubmissions += exercise.submission_count;
        submissionsByDiff[exercise.difficulty] += exercise.submission_count;
        const opts = {
          'data-submission-count': exercise.submission_count,
          // 'data-difficulty': exercise.difficulty,  // TODO: is it smart to save this to every single student?
          'data-points': exercise.points,
          class: 'pt-all',
          text: exercise.official ? exercise.points : 0,
        };
        if (!exercise.official && exercise.points) { // unofficial submission has points
          opts.class = 'unofficial';
        }
        addCellToRow(row, opts);
      });
      moduleCell.setAttribute('data-submission-count', moduleSubmissions);
    });
    difficultyCells.forEach(([diffName, cell]) => {
      const diffSubs = submissionsByDiff[diffName];
      cell.setAttribute('data-submission-count', diffSubs);
    })
    const totalSubs = Object.values(submissionsByDiff).reduce(sumReducer, 0);
    totalCell.setAttribute('data-submission-count', totalSubs);
    row.dataset.exerciseFilterId = 0; // initially all exercises are shown and only official points
    row.dispatchEvent(new Event('points updated'));
    // hide cells in hidden columsn
    toggleCellsOnRow(row, hiddenCellIndices, false);
  }


  // INDICATOR ROWS

  /**
    * Calculate data for indicated column to generate summaries of the
    * visible student rows.
    * @param {jQuery object} studentRows Rows from which to calculate
    *   values (visible rows)
    * @param {Number} index The index of the column whose data to calculate
    * @param {Number} maxPoints Maximum possible amout of points of the
    *   exercise(s) in the column
    */
  function calculateColumnDataForIndicators(studentRows, index, maxPoints) {
    // gatherers
    let studentsWithSubmissions = 0;
    let totalSubmissions = 0;
    let totalPoints = 0;
    let studentsWithMaxPoints = 0;

    studentRows.each((i, row) => {
      const cell = row.children[index];
      if (!cell) { // if student row doesn't have points yet, skip for now
        return true;
      }
      const subCount = Number(cell.dataset.submissionCount);
      if (subCount) {
        studentsWithSubmissions += 1;
        totalSubmissions += subCount;
        const studPoints = Number(cell.textContent);
        totalPoints += studPoints;
        if (studPoints == maxPoints) {
          studentsWithMaxPoints += 1;
        }
      }
    });
    return {
      studentsWithSubmissions,
      totalSubmissions,
      totalPoints,
      studentsWithMaxPoints,
      maxPoints,
    }
  }

  // Function for calculating different summary values
  function calculateTotalSubmissionsIndicatorCells(colData, rowCount) {
    // const percentValue = percent(colData.totalSubmissions / (colData.maxSubmissions * rowCount));
    return [colData.totalSubmissions, ""];
  }
  function calculateStudentsWithSubmissionsIndicatorCells(colData, rowCount) {
    const percentValue = percent(colData.studentsWithSubmissions / rowCount);
    return [colData.studentsWithSubmissions, percentValue];
  }
  function calculateStudentsWithMaxPointsIndicatorCells(colData, rowCount) {
    const percentValue = percent(colData.studentsWithMaxPoints / rowCount);
    return [colData.studentsWithMaxPoints, percentValue]
  }
  function calculateAverageSubmissionsIndicatorCells(colData, rowCount) {
    if (colData.studentsWithSubmissions) {
      const avgSubCount = roundToTwo(colData.totalSubmissions / colData.studentsWithSubmissions);
      const percentValue = percent(avgSubCount / colData.maxSubmissions);
      return [avgSubCount, percentValue]
    }
    return ["–", "–\u00A0%"]
  }
  function calculateAveragePointsIndicatorCells(colData, rowCount) {
    if (colData.studentsWithSubmissions) {
      const avgPoints = roundToTwo(colData.totalPoints / colData.studentsWithSubmissions);
      const percentValue = colData.maxPoints
        ? percent(avgPoints / colData.maxPoints)
        : "–\u00A0%";
      return [avgPoints, percentValue]
    }
    return ["–", "–\u00A0%"]
  }

  const indicatorCalculators = {
    totalSubmissions: calculateTotalSubmissionsIndicatorCells,
    studentsWithSubs: calculateStudentsWithSubmissionsIndicatorCells,
    studentsWithMaxPoints: calculateStudentsWithMaxPointsIndicatorCells,
    averageSubmissions: calculateAverageSubmissionsIndicatorCells,
    averagePoints: calculateAveragePointsIndicatorCells,
  }

  /**
   * Calculates the percentages each normal cell is of the total and
   * updates the percentage values in the table.
   * Can be called for the following indicator rows:
   * Total submissions, maximum submissions, maximum points
   * @param {Array[HTMLElement]} rowPair An array consisting of two
   *   tr-elements, the first referring to the normal indicator row,
   *   the second to the percent row.
   * @param {number} total An optional parameter indicating the total compared
   *   to which percentages should be calculated.
   *   If the parameter is not given, the value is fetched from the table.
   */
  function updateIndicatorRowPercentagesOfTotal([normalRow, percentRow], total) {
    const normalCells = normalRow.children;
    const percentCells = percentRow.children;
    const totalSum = (total !== undefined)
      ? total
      : normalCells[columnIndexMap.total - 1].textContent;

    const modAndExIndices = Array.from(_exerciseSelection, (([moduleID, exercises]) => {
      const modIndex = columnIndexMap.module[moduleID];
      const exIndices = exercises.map((id) => columnIndexMap.all[id]);
      return [modIndex, ...exIndices];
    })).flat();
    const indicesToUpdate = Object.values(columnIndexMap.difficulty).concat(modAndExIndices);
    if (totalSum) {
      indicesToUpdate.forEach((index) => {
        const normalValue = normalCells[index - 1].textContent;
        // index is shifted by 2 due to the cell in the row above with colspan and rowspan of 2
        const percentCell = percentCells[index - 2];
        percentCell.textContent = (normalValue !== "–")
          ? percent(Number(normalValue) / totalSum)
          : "–\u00A0%";
      })
    } else { // can't divide by zero
      indicesToUpdate.forEach((index) => {
        const percentCell = percentCells[index - 2];
        percentCell.textContent = "–\u00A0%";
      })
    }
  }

  /**
    * Calculate summary values for the dynamic indicator rows.
    */
  function updateDynamicIndicatorRows() {
    const studentRows = $('#student-rows tr').filter(':visible');
    const studentRowCount = studentRows.length;
    // update "selected students" count
    _visibleStudentSpan.textContent = studentRowCount;
    // static indicator rows for calculations
    const [maxPointsNormalRow, ] = indicatorRows.static.maxPoints;
    const maxPointsNormalCells = maxPointsNormalRow.children;
    const [maxSubsNormalRow, ] = indicatorRows.static.maxSubmissions;
    const maxSubsNormalCells = maxSubsNormalRow.children;

    const diffIndices = Object.values(columnIndexMap.difficulty);
    const modAndExIndices = Array.from(_exerciseSelection, (([moduleID, exercises]) => {
      const modIndex = columnIndexMap.module[moduleID];
      const exIndices = exercises.map((id) => columnIndexMap.all[id]);
      return [modIndex, ...exIndices];
    })).flat();
    const indicesToUpdate = diffIndices.concat(columnIndexMap.total, modAndExIndices);
    indicesToUpdate.forEach((index) => {
      // indicator row indeces
      const normalIndex = index - 1;
      const percentIndex = index - 2;

      const maxPointsString = maxPointsNormalCells[normalIndex].textContent;
      if (studentRowCount && maxPointsString !== "–") {
        const maxPoints = Number(maxPointsString);
        const maxSubmissions = Number(maxSubsNormalCells[normalIndex].textContent);
        const calculatedColData = calculateColumnDataForIndicators(studentRows, index, maxPoints);
        const colData = {...calculatedColData, maxSubmissions};

        Object.entries(indicatorRows.dynamic).forEach(([id, [normalRow, percentRow]]) => {
          const [normalVal, percentVal] = indicatorCalculators[id](colData, studentRowCount);
          normalRow.children[normalIndex].textContent = normalVal;
          percentRow.children[percentIndex].textContent = percentVal;
        });

      } else { // TODO: consider switching to an object and having static and dynamic -groups
        Object.entries(indicatorRows.dynamic).forEach(([id, [normalRow, percentRow]]) => {
          normalRow.children[normalIndex].textContent = "–";
          percentRow.children[percentIndex].textContent = "–\u00A0%";
          // percentRow.children[percentIndex].innerHTML = "–\u00A0%";
        });
      }
    });
    updateIndicatorRowPercentagesOfTotal(indicatorRows.dynamic.totalSubmissions);
  }

  /**
   * Calculates row sums according to exercise selection based on values
   * in the same row in the exercises section.
   * @param {Array[HTMLElement]} rowPair An array consisting of two
   *   tr-elements, the first referring to the normal indicator row,
   *   the second to the percent row.
   */
  function updateSumsOnStaticIndicatorRow([normalRow, percentRow]) {
    const normalCells = normalRow.children;
    const percentCells = percentRow.children;
    const difficultySums = {};
    let totalSum = 0;

    // calculate module, difficulty and total sums
    _exerciseSelection.forEach((exercises, moduleID) => {
      let moduleSum = 0;
      exercises.forEach((exerciseID) => {
        // indeces are shifted by one due to the cell with colspan of 2
        const exerciseCellIndex = columnIndexMap.all[exerciseID];
        const normalCell = normalCells[exerciseCellIndex - 1];
        const cellValue = Number(normalCell.textContent);
        const difficulty = exerciseDifficulties[exerciseID];
        addTo(difficultySums, difficulty, cellValue);
        moduleSum += cellValue;
      });
      const moduleCellIndex = columnIndexMap.module[moduleID];
      const normalModuleCell = normalCells[moduleCellIndex - 1];
      normalModuleCell.textContent = moduleSum;
      totalSum += moduleSum;
    });
    // insert difficulty sums and percentages
    Object.entries(columnIndexMap.difficulty).forEach(([diffName, index]) => {
      const normalCell = normalCells[index - 1];
      const percentCell = percentCells[index - 2];
      const diffSum = difficultySums[diffName];
      // if none of the selected exercises have the difficulty, indicate with –
      normalCell.textContent = (diffSum !== undefined) ? diffSum : "–";
    });
    // update total points
    const totalPointsCell = normalCells[columnIndexMap.total - 1];
    totalPointsCell.textContent = totalSum;
    // update percentages
    updateIndicatorRowPercentagesOfTotal([normalRow, percentRow]), totalSum;
  }

  /**
   * Fills in the data for those indicator rows whose values aren't
   * affected by the number of students displayed (such as maximum
   * sumbissions and maximum points). Should be called only once.
   */
  function fillStaticIndicatorRows() {
    const [maxSubNormal, maxSubPercent] = indicatorRows.static.maxSubmissions;
    const maxSubNormalCells = maxSubNormal.children;
    const maxSubPercentCells = maxSubPercent.children;
    const [maxPointsNormal, maxPointsPercent] = indicatorRows.static.maxPoints;
    const maxPointsNormalCells = maxPointsNormal.children;
    const maxPointsPercentCells = maxPointsPercent.children;
    Object.entries(columnIndexMap.all).forEach(([id, index]) => {
      const maxSubCount = maxSubmissions[id];
      const maxPointsCount = maxPoints[id];
      // indeces are shifted by one due to the cell with colspan 2
      maxSubNormalCells[index - 1].textContent = maxSubCount;
      maxPointsNormalCells[index - 1].textContent = maxPointsCount;
    });
    Object.values(indicatorRows.static).forEach((rowPair) => {
      updateSumsOnStaticIndicatorRow(rowPair);
    })
  }

  /**
    * Update values on indicator rows according to exercise selection
    * and visible student rows
    */
  function updateIndicatorRows() {
    const indicatorRowData = document.getElementById('indicator-rows').dataset;
    if (indicatorRowData.exerciseFilterId != _exerciseFilterID) {
      indicatorRowData.exerciseFilterId = _exerciseFilterID
      Object.values(indicatorRows.static).forEach((rowPair) => {
        updateSumsOnStaticIndicatorRow(rowPair);
      });
    }
    updateDynamicIndicatorRows();
  }

  /**
   * Adds an empty indicator row with cells to the table and adds the
   * array consisting of the normal and percentage rows to the
   * indicatorRowMap. The method is called for each indicator row.
   * @param  {string} headingTitle The heading text.
   * @param  {string} normalTooltip The first part of the text that is shown when hovering over heading, description of the indicator.
   * @param  {string} percentTooltip The second part of the text that is shown when hovering over heading, description of the percentage.
   * @param  {boolean} value indicating whether the indicator row is dynamic or not
   * @param  {string} id The id used for the mapping of indicatorRows
   */
  function addEmptyIndicatorRow(headingTitle, normalTooltip, percentTootip, dynamic, id) {
   // Data indicator headings have title and tooltip info that is shown when hovering mouse on the heading title
   const rowgroup = document.getElementById('indicator-rows')
   const normalRow = rowgroup.insertRow();
   normalRow.setAttribute('class', 'no-filtering indi-normal-row');
   const percentRow = rowgroup.insertRow();
   percentRow.setAttribute('class', 'no-filtering indi-pct-row tableexport-ignore');
   const dynamicity = dynamic ? 'dynamic' : 'static';
   indicatorRows[dynamicity][id] = [normalRow, percentRow];
   addCellToRow(normalRow, {
     class: 'indicator-heading stick-on-scroll',
     colspan: 2,
     rowspan: 2,
     'data-toggle': 'tooltip',
     'data-container': 'body',
     title: normalTooltip + "\n" + percentTootip,
     text: headingTitle,
   })
   // empty cells for email and tags
   for (let i = 0; i < 2; i += 1) {
     addCellToRow(normalRow, {
       class: 'indi-normal-val',
       hidden: (i === 0), // hide email cell
     });
     addCellToRow(percentRow, {
       class: 'indi-pct-val',
       hidden: (i === 0), // hide email cell
     });
   }
   // add cell for each difficulty, module and exercise cell + one for total
   for (let i = 0; i <= Object.values(pointKeys).flat().length; i++) {
     addCellToRow(normalRow, {
       class: 'indi-normal-val',
     });
     addCellToRow(percentRow, {
       // ...percentTooltipOpts,
       class: 'indi-pct-val',
     });
   }
   const normalCells = normalRow.children;
   const percentCells = percentRow.children;
   pointsGroupingMethods.forEach((pgm) => {
     Object.values(columnIndexMap[pgm]).forEach((index) => {
       const norCell = normalCells[index - 1];
       norCell.className = norCell.className + " pt-" + pgm;
       const pctCell = percentCells[index - 2];
       pctCell.className = pctCell.className + " pt-" + pgm;
     });
   });
  }

  /**
    * Add change handlers to indicator checkboxes.
    * Also updates current visibility of indicator rows.
    */
  function connectCheckboxesWithIndicatorRows() {
    indicatorCheckboxes.forEach((idPair, checkbox) => {
      const [dynamicity, id] = idPair;
      const dynamicityStr = dynamicity ? 'dynamic' : 'static';
      const rowPair = indicatorRows[dynamicityStr][id];
      checkbox.change(function (event) {
        toggleRows(rowPair, event.target.checked);
      });
      // update current visibility
      toggleRows(rowPair, checkbox.is((i, elem) => elem.checked));
    });
  }

  /**
    * Create indicator rows, add text and tooltips, hide cells in
    * hidden columns, and enables toggling indicator rows.
    */
  function createIndicatorRows() {
    const percentOfTotalTooltip = _("The percentage indicates the distribution of the total.")
    addEmptyIndicatorRow(
      _("Total submissions"),
      _("Total number of submissions. Calculates all student submission counts together."
        + " (Accounts for both official and unoffical submissions.)"
      ),
      percentOfTotalTooltip,
      true,
      'totalSubmissions',
    );
    addEmptyIndicatorRow(
      _("Average submissions per student with submissions"),
      _("How many submissions a single student has used on average on the exercise or group of exercises."
        + " Only accounts for students with one or more submissions."
        + " (Accounts for both official and unoffical submissions.)"
      ),
      _("The percentage indicates what proportion of allowed submissions have been used on average."),
      true,
      'averageSubmissions',
    );
    addEmptyIndicatorRow(
       _("Maximum submissions"),
       _("Maximum number of available submissions for the exercise or group of exercises."),
       percentOfTotalTooltip,
       false,
       'maxSubmissions',
    );
    addEmptyIndicatorRow(
      _("Students with submissions"),
      _("Number of students that have one or more exercise submissions."
        + " (Accounts for both official and unoffical submissions.)"
      ),
      _("The percentage indicates what proportion of the students shown have submssions."),
      true,
      'studentsWithSubs'
    );
    addEmptyIndicatorRow(
      _("Students with max points"),
      _("Number of students that have received maximum points from the exercise or group of exercises."),
      _("The percentage indicates what proportion of the students shown have received maximum points."),
      true,
      'studentsWithMaxPoints',
    );
    addEmptyIndicatorRow(
      _("Average points per student with submissions"),
      _("Average points received for the exercise or group of exercises."
        + " Only accounts for students with one or more submissions."
      ),
      _("The percentage indicates what propoprtion of the maximum points the students have recieved on average."),
      true,
      'averagePoints',
    );
    addEmptyIndicatorRow(
      _("Maximum points"),
      _("Maximum points for the exercise or group of exercises."),
      percentOfTotalTooltip,
      false,
      'maxPoints',
    );
    // hide cells in hidden columns
    toggleColumnsOnIndicatorRows(Array.from(hiddenCellIndices), false);
    // fill in static rows' data
    fillStaticIndicatorRows();
    // add handlers to checkboxes and update row visibility
    connectCheckboxesWithIndicatorRows();

    // Set up the tooltip for checkboxes and indicator rows, look docs below for tooltip
    // https://getbootstrap.com/docs/3.3/javascript/
    const $tooltippedElems = $('[data-toggle="tooltip"]');
    $tooltippedElems.tooltip({
      "trigger": "hover",
    });
    $tooltippedElems.on('click', function() {
      $(this).tooltip('hide');
    });
  }

  // Set timeout so if when several things happen in a row that would
  // trigger indicator row updates, there is a small delay to decrease
  // the amout of vain resulting updates.
  let indicatorRowUpdateTimeout;
  function scheduleIndicatorRowUpdate() {
    clearTimeout(indicatorRowUpdateTimeout);
    indicatorRowUpdateTimeout = setTimeout(
      updateIndicatorRows,
      500
    );
  }

  $("input.official-checkbox").change(function() {
    _showOfficial = this.checked;
    scheduleExerciseSelectionChange();
  });

  let tagFilterChangeTimeout;
  // Event listener for tag filters
  $('.filter-users button').on('click', (event) => {
    event.preventDefault();
    let icon = $(event.target).find('.glyphicon');
    if (icon.hasClass('glyphicon-unchecked')) {
      icon.removeClass('glyphicon-unchecked').addClass('glyphicon-check');
    } else {
      icon.removeClass('glyphicon-check').addClass('glyphicon-unchecked');
    }
    clearTimeout(tagFilterChangeTimeout);
    tagFilterChangeTimeout = setTimeout(
      // checks whether tag filters actually changed and updates them if they did
      () => {
        const newTagSlugFilters = $.makeArray($('.filter-users button:has(.glyphicon-check)'))
          .map((elem) => elem.dataset['tagSlug']);
        if (newTagSlugFilters != _tagSlugFilters) {
          _tagSlugFilters = newTagSlugFilters;
          _tagFilterID += 1;
          event.target.dispatchEvent(new Event('tagfilters updated'));
        }
      },
      1000
    )
  });

  fromEvent(
    document.querySelectorAll('.filter-users button'),
    'tagfilters updated'
  ).subscribe(
    filterStudentRows
  );


  // Replace grouping checkboxes with toggle buttons
  $('#point-grouping-selection').replaceInputsWithMultiStateButtons({
    nocolor: true,
    buttonClass: 'aplus-button--secondary aplus-button--sm',
    groupClass: '',
  });
  // Add change handlers to grouping checkboxes
  $('#point-grouping-selection').find(':checkbox').change(groupingSelectionChange);


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
    const exportButtonMenu = document.getElementById('export-button-menu');
    $("caption.tableexport-caption").children("button").each(function(i, elem) {
      // $("#export-button-menu").append($(elem).detach());
      exportButtonMenu.appendChild(elem);
    });
  });

// NOT REALLY STARTED: STORING TO LOCAL STORAGE

  let storageKey = 'resultsData';
  function toStorage() {
    return {
      // _students: _students,
      _usertags: _usertags,
      // _allExercises: _allExercises,
      // _points: _points,
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



// REACTIVE IMPLEMENTATION

  // Stream data from a paged JSON API into an Observer
  function APIPagingStream(url, resultsObserver, countObserver) {
    // recursive helper function
    function stream(url, countNeeded) {
      return $.ajax(
        url,
        ajaxSettings
      ).then(function(response) {
        response.results.forEach((r) => resultsObserver.next(r));
        if (countNeeded) {
          countObserver.next(response.count);
          countObserver.complete();
        }
        if (response.next) {
          console.log("next page")
          stream(response.next, false);
        } else {
          console.log("APIPagingStream complete")
          resultsObserver.complete();
        }
      }, (reason) => {
        throw new Error("Pagination ajax failed: " + reason.statusText);
      });
    }

    this.start = function() {
      stream(url, !!countObserver);
    };
  }


  // An object adhering to the observer interface that keeps track of loading progress and finishes rendering
  const progressObserver = {
    progress: 0,
    next() {
      this.progress += 1;
      // $("#results-loading-progress").html(this.progress);
      document.getElementById('results-progress-cumulative').textContent = this.progress;
    },
    complete() {
      $("#results-loading-animation").hide();
      $("#results-loading-progress").hide();
      $("#table-export-dropdown > button").removeAttr('disabled');
      //storeDataLocally('localStorage', storageKey, toStorage())
    }
  }


  /*
   *  Setting up pipeline
   */

  // Source for pipeline
  const usertagsSubject = new rxjs.Subject();
  const usertagsStream = new APIPagingStream(usertagsUrl, usertagsSubject);
  const studentTagSubject = new rxjs.Subject();

  const studentsSubject = new rxjs.Subject();
  const studentCountSubject = new rxjs.Subject();
  const studentsStream = new APIPagingStream(studentsUrl, studentsSubject, studentCountSubject);
  const pointsSubject = new rxjs.Subject();

  const modulesSubject = new rxjs.Subject();
  const modulesStream = new APIPagingStream(exercisesUrl, modulesSubject);
  const exercisesSubject = new rxjs.Subject();
  const exerciseCountSubject = new rxjs.Subject();

  // Get usertag info, after we have all of them, start adding tags to students
  const usertagArray = [];
  usertagsSubject.subscribe({
    next(usertag) {
      // should they be pushed directly to the _usertags? temp variable here in case of local storage use
      usertagArray.push(usertag);
    },
    error(err) {},
    complete() {
      _usertags = usertagArray;
      // go through students' tags, generate colortags and add to cells
      studentTagSubject.subscribe({
        next([cell, tagslugs]) {
          addTagsToCell(cell, tagslugs, _usertags);
        },
      });
    }
  });

  // Track data fetching progress
  studentsSubject.pipe(tag("students"))
                 .subscribe(progressObserver);

  // for each student, add the row to the table, fetch points and
  // provide tem to the pointsSubject.
  // When all student rows are added, add event listeners to rows.
  let studentPointCount = 0
  studentsSubject.subscribe({
    next(student) {
      addStudentRowToTable(student, studentTagSubject);
      $.ajax(
        pointsUrl + student.id,
        ajaxSettings
      ).then((points) => {
        // addPointsToStudentRow(row, points);
        pointsSubject.next(points);
        // if ajax calls would be done in a different observable, we could call that complete
        // method and that complete method could call studentSubject.complete()
        studentPointCount += 1;
        if (studentPointCount == _studentCount) {
          pointsSubject.complete();
        }
      });
    },
    error(err) {},
    complete() {
      const studentRows = document.querySelectorAll('#student-rows tr');
      // EVENT HANDLERS
      // when the points on the row are added or updated
      fromEvent(studentRows, 'points updated').subscribe((e) => {
        updateSumsOnStudentRow(e.target);
      });
      fromEvent(studentRows, 'exercise selection changed').subscribe((e) => {
        updateSumsOnStudentRow(e.target);
      });
      // visibility may need to be adjusted if there is filtering according to points
      fromEvent(studentRows, 'student row sums updated').subscribe((e) => {
        updateStudentRowVisibility(e.target);
      })
      // when the students' tags are added or updated
      fromEvent(studentRows, 'tags updated').subscribe((e) => {
        updateStudentRowVisibility(e.target);
      });
      // fromEvent(studentRows, 'tagfilters updated').subscribe((e) => {
      //   const row = e.target;
      //   if (row.dataset.tagFilterId != _tagFilterID) {
      //     updateStudentRowVisibility(row);
      //   }
      // });
      fromEvent(studentRows, 'visibility updated').subscribe((e) => {
        scheduleIndicatorRowUpdate();
      });
    }
  });

  // Add text indicating how many students are displayed in the table
  // and provide student count to the progress loading text.
  studentCountSubject.subscribe({
    next(count) {
      _studentCount = count;
      document.getElementById('results-progress-total').textContent = count;
      const tableDiv = document.getElementById('table-points-div');
      const displayedStudentsInfo = document.createElement('p');
      tableDiv.parentNode.insertBefore(displayedStudentsInfo, tableDiv);
      _visibleStudentSpan = document.createElement('span');
      _participantNumberSpan = document.createElement('span');
      _participantNumberSpan.textContent = count;
      displayedStudentsInfo.append(
        _visibleStudentSpan,
        " / ",
        _participantNumberSpan,
        _(" students selected"),
      );
    },
  });

  pointsSubject.pipe(first()).subscribe({
    next(firstPoints) {
      populateExerciseSelection(firstPoints);
      drawTablePrework(firstPoints, exerciseCountSubject);
    },
  });

  pointsSubject.subscribe({
    next(studentPoints) {
      addPointsToStudentRow(studentPoints);
    },
    error(err) {},
    complete() {
      // updateStudentRowSums = updateStudentRowSumsWhenDone;
      // update indicator rows
    }
  });


  let exerciseCount;
  let ajaxExerciseCallCount = 0;

  exerciseCountSubject.subscribe({
    next(count) {
      exerciseCount = count;
    },
    complete() {
      modulesStream.start();
    }
  });

  // Go through the modules and make AJAX requests of each exercise to
  // find out the max submissions.
  modulesSubject.subscribe({
    next(module) {
      module.exercises.forEach(function(ex) {
        $.ajax(
          ex.url,
          ajaxSettings
        ).then(function (exData) {
          exercisesSubject.next(exData);
          ajaxExerciseCallCount += 1;
          if (ajaxExerciseCallCount === exerciseCount) {
            exercisesSubject.complete();
          }
        });
      });
    },
  });

  exercisesSubject.subscribe({
    next(exData) {
      maxSubmissions[exData.id] = exData.max_submissions;
    },
    complete() {
      createIndicatorRows();
      scheduleIndicatorRowUpdate();
    }
  });


  // Start pipeline
  usertagsStream.start();
  studentsStream.start();

  // Show table (happends immediately because other calls asynchronous?)
  $("#table-points-div").show();


  /* TODO: consider using rxjs.Observable.ajax.getJSON
  */

})(jQuery, document, window);

/* vim: set et ts=4 sw=4: */
