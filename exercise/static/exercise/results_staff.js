(function($, document, window, undefined) {
    let currentScript = (document.currentScript ?
        $(document.currentScript) :
        $('script').last()); // Ugly solution for IE11

    /**
     * Simple hack to select DataTables language file depending on the HTML body class
     */
    var pageLanguageUrl = '';

    /**
     * URL to fetch exercise data from
     */
    const exercisesUrl = currentScript.data("exercisesUrl");

    /**
     * URL to fetch usertags from
     */
    const usertagsUrl = currentScript.data("usertagsUrl");

    /**
     * URL to fetch student data and submission results from
     * TODO: slip in the format parameter in a more elegant fashion
     */
    var pointsUrl = currentScript.data("pointsUrl") + '?format=json';
    var pointsBestUrl = currentScript.data("pointsBestUrl") + '?format=json';

    /**
     * URL template for user results page (with user_id=0 as placeholder)
     */
    const userResultsUrlTemplate = currentScript.data("userResultsUrl");

    /**
     * Stores the exercise data loaded via ajax call
     */
    let _exercises;

    /**
     * Stores the raw points data from backend (with both official and unofficial data)
     */
    let _rawPointsData = null;

    /**
     * Stores the usertags data loaded via ajax call
     */
    let _usertags = [];

    /**
     * Stores all difficulty levels of current course instance
     * with an array of exercise ids belonging to that difficulty level
     * { difficulty_level(str): [exercise_id(int)] }
     */
    let _difficulties = {};

    /**
     * Difficulty levels lookup table in reverse (for performance),
     * i.e. from exercise id to difficulty level
     * { exercise_id(int): difficulty_level(str) }
     */
    let _reverseDifficulties = {};

    /**
     * Stores confirmation requirements for exercises
     * { exercise_id(int): {requires_confirmation: bool, parent_id: int|null, module_id: int} }
     */
    let _confirmationMap = {};

    /**
     * Difficulty levels present in the user-filtered data
     * [difficulty_level(str)]
     */
    let _activeDifficulties = [];

    /**
     * Global to store the currently visible summary item ids as strings
     * [summary_item(str)]
     */
    let _activeSummaryItems = [];

    /**
     * Enum for _displayMode
     */
    const dm = { DIFFICULTY: 1, MODULE: 2, EXERCISE: 3 }

    /**
     * We need a string version of the enum when creating a css class name
     */
    const dmRev = { 1: 'difficulty', 2: 'module', 3: 'exercise' }

    /**
     * Global to store the current display mode: difficulty, module, or exercise
     * This is implemented as enum for better performance, but probably does
     * not save that many ms compared to using a string index.
     */
    let _displayMode = dm.DIFFICULTY;

    /**
     * The DataTables jQuery plugin instance is stored here. This is actually used only
     * when reloading data from backend due to toggling official/unofficial points, while
     * most of the code uses dtVar which gets defined in the initComplete callback of DataTables.
     */
    var dtApi;

    /**
     * Due to issues with getting the DataTables custom search work with dynamic columns,
     * we keep the points columns search values in this object. The custom search plugin
     * compares each active column with the data value for each row.
     */
    var colSearchVals = {};

    /**
     * Summary row enumerations, faster to evaluate than string indices so why not
     */
    const sv = {
        TOTAL_SUBS: 1,
        AVG_SUBS_PER_STUD: 2,
        MAX_SUBS: 3,
        STUDS_WITH_SUBS: 4,
        STUDS_WITH_MAX_POINTS: 5,
        AVG_PTS_PER_STUD: 6,
        MAX_PTS: 7
    }

    const percentOfTotalTooltip = "The percentage indicates the distribution of the total."
    /**
     * A look-up table of summary rows available for the user to select
     *
     * TITLE   defines the row header text in table
     * ROW     defines the order these are presented in the table
     * INITVAL is either an integer for integer-valued properties,
     *         empty array for array variables that are combined as unions
     *         and array with a string for array variables combined as intersections
     */
    const summaries = {
        [sv.TOTAL_SUBS]: {
            TITLE: "Total submissions",
            TOOLTIP: "Total number of submissions. Calculates all student submission counts together.",
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip,
            ROW: 0,
            INITVAL: 0
        },
        [sv.AVG_SUBS_PER_STUD]: {
            TITLE: "Average submissions per student with submissions",
            TOOLTIP: (
                "How many submissions a single student has used on the assignment or group of assignments on average. " +
                "Only accounts for students with one or more submissions."
            ),
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip, // should be replaced if the percentage calculation is changed
            ROW: 1,
            INITVAL: 0
        },
        [sv.MAX_SUBS]: {
            TITLE: "Maximum submissions",
            TOOLTIP: "Maximum number of available submissions for the assignment or group of assignments.",
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip,
            ROW: 2,
            INITVAL: 0
        },
        [sv.STUDS_WITH_SUBS]: {
            TITLE: "Students with submissions",
            TOOLTIP: "Number of students that have one or more assignment submissions.",
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip, // should be replaced if the percentage calculation is changed
            ROW: 3,
            INITVAL: []
        },
        [sv.STUDS_WITH_MAX_POINTS]: {
            TITLE: "Students with max points",
            TOOLTIP: "Number of students that have received maximum points from the assignment or group of assignments.",
            ROW: 4,
            INITVAL: ['no_ex']
        },
        [sv.AVG_PTS_PER_STUD]: {
            TITLE: "Average points per student with submissions",
            TOOLTIP: (
                "Average points received for the assignment or group of assignments. " +
                "Only accounts for students with one or more submissions."
            ),
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip, // should be replaced if the percentage calculation is changed
            ROW: 5,
            INITVAL: 0
        },
        [sv.MAX_PTS]: {
            TITLE: "Maximum points",
            TOOLTIP: "Maximum points for the assignment or group of assignments.",
            PERCENTAGE_TOOLTIP: percentOfTotalTooltip,
            ROW: 6,
            INITVAL: 0
        },
    }

    /**
     * The index of our "Tags" column (some operations depend on this)
     * TODO: make it better
     */
    const TAGS_COL_ID = 4;

    /**
     * The index of our "Total" column (some operations depend on this)
     * TODO: make it better
     */
    const TOTAL_COL_ID = 16;

    /**
     * Holds the contents of summary rows which are recreated from this data
     * on every DataTable redraw.
     */
    var summArray = [];
    for(var s in summaries) {
        summArray[s] = [];
    }

    /**
     * Save DOM references as constants for fewer jQuery lookups
     */
    const pointsTableRef = $('#table-points'); // Main points table
    // Initial selects to build multiselects from
    const moduleSelectRef = $("#module-selection");
    const exerciseSelectRef = $("#exercise-selection");
    // Summary Checkboxes and tag buttons references
    const summaryCheckboxesRef = $("input.summary-checkbox");
    const tagButtonsRef = $("button.tag-button");

    /**
     * Holds the selector for manipulating multiselect items
     * after they are added into the DOM
     */
    let multiSelectSelector;

    /**
     * Stores the getBoundingClientRect() result
     * (the initial Y-location of the data table headers).
     * Needed to make the headers remain visible when scrolling down.
     */
    let initialTableYOffset;

    /**
     * A debounce function from Underscore.js, taken from
     * https://davidwalsh.name/javascript-debounce-function
     * Used in some operations that we don't want to perform too often
     * with large tables, so the browser can keep up.
     */
    // Returns a function, that, as long as it continues to be invoked, will not
    // be triggered. The function will be called after it stops being called for
    // N milliseconds. If `immediate` is passed, trigger the function on the
    // leading edge, instead of the trailing.
    function debounce(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    };

    /**
     * Search function for individual columns
     * This is made a separate function so it can be easily debounced
     * @param {number} col column to target the search to
     * @param {string} search string to search for
     */
    function bigColumnSearch(col,search) {
        dtVar.column(col).search(search);
        recalculateTable(); // draw() is called at the end of this
        $('th.col-' + col + '.sorting').find('input').focus(); // return focus to search box after searching
    }

    /**
     * Due to the complexity of recalculateTable, we debounce the point
     * columns' value searches so that in large courses the UI remains
     * responsive.
     */
    var recalculateTableDebounced = debounce(bigColumnSearch, 500);

    /**
     * Clears all search fields in column headers and DataTables internals
     */
    function clearSearch() {
        colSearchVals = {}; // clear our custom search columns bookkeeping
        $( 'thead#table-heading input').val(''); // clear column search box values
        // clear checked tag filters
        tagButtonsRef.children('span').removeClass('glyphicon-unchecked').removeClass('glyphicon-check').addClass('glyphicon-unchecked');
        $('.withsubs-checkbox').prop('checked', false); // clear "show only students with submissions" checkbox
        $('div.filter-users input.tags-operator').first().prop('checked',true); // reset tags search operator to first option (AND)
        dtVar.search(''); // clear general DataTables search
        dtVar.columns().search(''); // clear ALL column-specific searches
        recalculateTableDebounced(); // finally refresh the table with no filtering
    }

    /**
     * Clears search fields related to dynamically generated columns
     */
     function clearPointsSearch() {
         // clear our custom search columns bookkeeping for dynamic columns
        /*const colSearchValsAsArray = Object.entries(colSearchVals);
        const staticColsArray = dtVar.columns('.static');
        colSearchVals = colSearchValsAsArray.filter(([key,val]) => staticColsArray.includes(key));*/
        colSearchVals = {}; // clear our custom search columns bookkeeping

        // clear column search boxes for non-text columns (the first three columns)
        $( 'thead#table-heading input').not('.textval').val('');
        // clear searches of points columns
        dtVar.columns('.points').search('');
        recalculateTableDebounced(); // finally refresh the table
    }

    /**
     * Does a search on the tags column based on the tag selections by user
     */
    function searchForSelectedTags() {
        let activeTags = [];
        tagButtonsRef.each(function() {
            //if($(this).children('span').hasClass('glyphicon-check')) activeTags.push(_reverseUsertags[$(this).data('tag-slug')]);
            if($(this).children('i').hasClass('bi-check-square')) activeTags.push($(this).data('tag-name'));
        })
        if($('input[name="tags-operator"]:checked').val() === 'and') {
            dtVar.column(TAGS_COL_ID).search(activeTags.join(" "), false, true );
        } else {
            dtVar.column(TAGS_COL_ID).search(activeTags.join("|"), true, false );
        }
        recalculateTableDebounced();
        //dtVar.draw();
    }


    /**
     * Recreates summary rows html and append it to the datatable header
     * based on which summary items are selected via checkboxes
     */
    function recreateSummaryRows() {
        let rowStart = '<tr class="summaryitem">';
        let rowEnd = '</tr>';
        var tableheading = $('thead#table-heading');
        var newHeading = '';
        tableheading.find('tr.summaryitem').remove(); // Remove existing summary rows

        for(var i in _activeSummaryItems) {
            let cells = '';

            /**
             * TODO: This indexing is somewhat hacky, but at least at this time the sv enum
             * (1,2,3,..) is just off by one from summary row numbering (0,1,2,...)
             */
            let item = parseInt(_activeSummaryItems[i]) + 1;

            let header = (
                '<th class="stick-on-scroll indicator-heading table-info" colspan="2" ' +
                'data-bs-toggle="tooltip" data-container="body" title="' +
                _(summaries[item]['TOOLTIP']) +
                (summaries[item]['PERCENTAGE_TOOLTIP']
                    ? '\n' + _(summaries[item]['PERCENTAGE_TOOLTIP'])
                    : ''
                ) +
                '">' +
                _(summaries[item]['TITLE']) +
                '</th>'
            );

            var cols = dtVar.columns('.' + dmRev[_displayMode]);

            for(var d in cols[0]) {
                if(summArray[item] !== undefined) {
                    // Only add cell if the column is currently visible
                    if(dtVar.columns(cols[0][d]).visible()[0]) {
                        cells += '<td>' + summArray[item][cols.indexes()[d]] + '</td>';
                    }
                }
            }
            newHeading += (rowStart + header + '</td><td></td><td></td><td>' + summArray[item][TOTAL_COL_ID] + '</td>' + cells + rowEnd);
        }
        // Append all summary rows' html at once for better performance
        tableheading.append($(newHeading));
    }

    /**
     * Recalculates the whole datatable (row and column sums and summary rows)
     * when any of the filtering parameters or the display mode changes.
     * We keep track of summaries of each display mode separately, and finally
     * assign the calculated totals for the current displaymode.
     * As this function is ran each time we change the displaymode, we only
     * do calculations and assignments required for that mode.
     */
    function recalculateTable() {
        let selectedModules = moduleSelectRef.val();
        let selectedExercises = exerciseSelectRef.val();
        var pointsGrandTotal = 0;
        var pointsModuleTotal = [];

        /**
         * Initialize arrays to store total summaries. Some summaries need to keep
         * track of unique students, and are therefore initialized as arrays.
         */
        let tSummaries = [];
        for(var s in summaries) {
            if(summaries[s]['INITVAL'] === 0) {
                tSummaries[s] = summaries[s]['INITVAL'];
            } else {
                tSummaries[s] = [];
            }
        }

        // Initialize arrays to store module summaries
        let mSummaries = [];
        for(var s in summaries) {
            mSummaries[s] = [];
        }

        // Initialize arrays to store exercise summaries
        let eSummaries = [];
        for(var s in summaries) {
            eSummaries[s] = [];
        }

        if(_displayMode === dm.DIFFICULTY) {
            var pointsDifficultyTotal = [];
            var dSummaries = [];
            // Reset the active difficulties
            _activeDifficulties = [];
            // Initialize arrays to store summaries per difficulty level
            for(var s in summaries) {
                dSummaries[s] = [];
                for(diff in _difficulties) {
                    pointsDifficultyTotal[diff] = 0;
                    if(summaries[s]['INITVAL'] === 0) {
                        dSummaries[s][diff] = summaries[s]['INITVAL'];
                    } else {
                        dSummaries[s][diff] = (summaries[s]['INITVAL'].length > 0 ? ['no_ex'] : []);
                    }
                }
            }
        }

        // No need to go through modules, if no exercises selected
        if(selectedModules !== null && selectedExercises !== null) {
            // The main loop through all modules
            for(moduleIdx in _exercises) {
                var modId = _exercises[moduleIdx].id; // Unique module id
                pointsModuleTotal[modId] = 0;

                var moduleScores = []; // array of all students' cumulative points per module

                // Only take into account the modules currently selected from the menu
                if(selectedModules.includes('mod-m' + modId)) {
                    // Get the "physical" index id of this module in our datatable
                    var modIdx = dtVar.column('.mod-m' + modId).index();

                    /**
                     * Cannot assign the array values directly as these are passed by reference.
                     */
                    for(var s in summaries) {
                        if(summaries[s]['INITVAL'] === 0) {
                            mSummaries[s][modId] = summaries[s]['INITVAL'];
                        } else {
                            // Only init if empty array
                            if(summaries[s]['INITVAL'].length === 0) {
                                mSummaries[s][modId] = [];
                            }
                        }
                    }

                    // Only need to process exercises if there are some
                    if(_exercises[moduleIdx].exercises.length > 0) {

                        // Loop through the exercises in current module
                        for(exerciseIdx in _exercises[moduleIdx].exercises) {
                            var exId = _exercises[moduleIdx].exercises[exerciseIdx].id; // Unique exercise id

                            // Only take into account the exercises currently selected from the menu
                            if(selectedExercises.includes('ex-' + exId)) {
                                /**
                                 * Get the "physical" column index id on datatable for this exercise.
                                 * Note, that this is always required for filtering the table to calculate sums.
                                 */
                                var exIdx = dtVar.column('.ex-' + exId).index();

                                for(var s in summaries) {
                                    if(summaries[s]['INITVAL'] === 0) {
                                        eSummaries[s][exId] = summaries[s]['INITVAL'];
                                    } else {
                                        // Only initialize this if INITVAL array is zero-length
                                        if(summaries[s]['INITVAL'].length === 0) {
                                            eSummaries[s][exId] = [];
                                        }
                                    }
                                }

                                // Maximum submissions (constant, has been fetched from the exercises API)
                                var maxSubs = _exercises[moduleIdx].exercises[exerciseIdx].max_submissions;

                                // Maximum points (constant, has been fetched from the exercises API)
                                var maxPoints = _exercises[moduleIdx].exercises[exerciseIdx].max_points;

                                /**
                                 * Calculate a sum of submission count column
                                 * (excluding rows filtered out by searching for string/tag).
                                 * Note, that this column is always hidden in the datatable and used for calculations only
                                 */
                                var totalSubs = dtVar.column(exIdx - 1, {search: 'applied'}).data().sum();

                                /**
                                 * Calculate a sum of total points column
                                 * (excluding rows filtered out by searching for string/tag).
                                 */
                                var totalPoints = dtVar.column(exIdx, {search: 'applied'}).data().sum();

                                /**
                                 * Filter the visible student rows with submission count > 0.
                                 * Save these students into an array studentsWithSubs
                                 * and the amount (array length) to numStudentsWithSubs
                                 */
                                let studentsWithSubs = [];
                                const numStudentsWithSubs = dtVar
                                    .column(exIdx - 1, {search: 'applied'})
                                    .data()
                                    .filter( function ( value, index ) {
                                        if(value > 0) {
                                            studentsWithSubs.push(dtVar.column(0).data()[index]);
                                            return true;
                                        } else return false;
                                    }
                                ).length;

                                /**
                                 * Calculate the submission averages based on the previous filtering operations
                                 */
                                let avgSubsPerStudent;
                                let avgPointsPerStudentWithSubs;
                                if(numStudentsWithSubs > 0) {
                                    avgSubsPerStudent = parseFloat((totalSubs / numStudentsWithSubs).toFixed(2));
                                    avgPointsPerStudentWithSubs = parseFloat((totalPoints / numStudentsWithSubs).toFixed(2));
                                    // Also add points to the module total
                                    pointsModuleTotal[modId] += totalPoints;
                                } else {
                                    avgSubsPerStudent = 0;
                                    avgPointsPerStudentWithSubs = 0;
                                }

                                /**
                                 * Filter visible student rows and compare each with the maximum points
                                 * from this exercise. Add matching students to maxPointsStudents array.
                                 */
                                let maxPointsStudents = [];
                                if(maxPoints > 0) {
                                    studentsWithMaxPoints = dtVar
                                        .column(exIdx, {search: 'applied'})
                                        .data()
                                        .filter( function ( value, index ) {
                                            if(value === maxPoints) {
                                                maxPointsStudents.push(dtVar.column(0).data()[index]);
                                                return true;
                                            } else return false;
                                        }
                                    );
                                } else {
                                    studentsWithMaxPoints = [];
                                    // If no max points in this exercise, no max points for the module, either
                                    mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] = [];
                                }

                                /**
                                 * If exercise mode chosen from GUI, put the per-exercise stats in place to datatable.
                                 * Note, that exercise points are always calculated as they are required in other modes.
                                 */
                                if(_displayMode === dm.EXERCISE) {
                                    // Fill in the summary cells for this exercise
                                    summArray[sv.MAX_SUBS][exIdx] = maxSubs;
                                    summArray[sv.MAX_PTS][exIdx] = maxPoints;
                                    summArray[sv.TOTAL_SUBS][exIdx] = totalSubs;
                                    summArray[sv.AVG_SUBS_PER_STUD][exIdx] = avgSubsPerStudent;
                                    summArray[sv.AVG_PTS_PER_STUD][exIdx] = avgPointsPerStudentWithSubs;
                                    summArray[sv.STUDS_WITH_SUBS][exIdx] = numStudentsWithSubs;
                                    summArray[sv.STUDS_WITH_MAX_POINTS][exIdx] = studentsWithMaxPoints.length;
                                }

                                /**
                                 * If module mode chosen from GUI, calculate the per-module stats
                                 * and put them in place to datatable.
                                 */
                                if(_displayMode === dm.MODULE) {
                                    // Calculate per module total points for students

                                    // First assignment for a module
                                    if(!moduleScores.length) {
                                        moduleScores = dtVar.column(exIdx, {search: 'applied'})
                                        .data();
                                    } else {
                                        // If we already have points from exercises of this module, sum points by student
                                        var sum = dtVar.column(exIdx, {search: 'applied'}).data()
                                        .map(function (num, idx) {
                                            return num + moduleScores[idx];
                                        });
                                        moduleScores = sum; // TODO: assign by value?????
                                    }

                                    // Add the maximum submissions of this exercise to module totals
                                    mSummaries[sv.MAX_SUBS][modId] += maxSubs;
                                    // Add the maximum points of this exercise to module totals
                                    mSummaries[sv.MAX_PTS][modId] += maxPoints;
                                    // Add the total submissions of this exercise to module totals
                                    mSummaries[sv.TOTAL_SUBS][modId] += totalSubs;

                                    // Only count distinct students for the module stats
                                    if(studentsWithSubs.length > 0) {
                                        studentsWithSubs.forEach(value => {
                                            if(!mSummaries[sv.STUDS_WITH_SUBS][modId].includes(value)) {
                                                mSummaries[sv.STUDS_WITH_SUBS][modId].push(value);
                                            }
                                        });
                                    }

                                    /**
                                     * Calculate the total students with max points for the current module.
                                     * If this is the first exercise of this module, initialize the students array
                                     * and if there are students with maximum points, add them into it
                                     */
                                    if(mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] === undefined) {
                                        mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] = [];
                                        if(maxPointsStudents.length > 0) {
                                            maxPointsStudents.forEach(value => {
                                                mSummaries[sv.STUDS_WITH_MAX_POINTS][modId].push(value);
                                            });
                                        }
                                    } else {
                                        // Only proceed if there are still candidates for full points for this module
                                        if(mSummaries[sv.STUDS_WITH_MAX_POINTS][modId].length > 0) {
                                            if(maxPointsStudents.length > 0) {
                                                // Remove any students from the existing list who don't have max points from this exercise
                                                var intersectionArray = mSummaries[sv.STUDS_WITH_MAX_POINTS][modId].filter(function(n) {
                                                    return maxPointsStudents.indexOf(n) !== -1;
                                                });
                                                mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] = intersectionArray;
                                            } else {
                                                // No full points from this exercise, remove all candidates
                                                mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] = [];
                                            }
                                        }
                                    }
                                }

                                /**
                                 * If difficulty mode chosen from GUI, calculate the per-difficulty stats.
                                 */
                                if(_displayMode === dm.DIFFICULTY) {
                                    // Get the difficulty level of current exercise
                                    const exDifficulty = _exercises[moduleIdx].exercises[exerciseIdx].difficulty;
                                    if(!_activeDifficulties.includes(exDifficulty)) {
                                        _activeDifficulties.push(exDifficulty);
                                    }
                                    pointsDifficultyTotal[exDifficulty] += parseInt(totalPoints);

                                    // Summaries that are simple sums of values
                                    dSummaries[sv.TOTAL_SUBS][exDifficulty] += totalSubs;
                                    dSummaries[sv.MAX_SUBS][exDifficulty] += maxSubs;
                                    dSummaries[sv.MAX_PTS][exDifficulty] += maxPoints;

                                                                    /**
                                     * Calculate the total students with max points for the current module.
                                     * If this is the first exercise of this module, initialize the students array
                                     * and if there are students with maximum points, add them into it
                                     */
                                    if(dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty].includes('no_ex')) {
                                        dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty] = [];
                                        if(maxPointsStudents.length > 0) {
                                            maxPointsStudents.forEach(value => {
                                                dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty].push(value);
                                            });
                                        }
                                    } else {
                                        // Only proceed if there are still candidates for full points for this difficulty
                                        if(dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty].length > 0) {
                                            if(maxPointsStudents.length > 0) {
                                                // Remove any students from the existing list who don't have max points from this exercise
                                                var intersectionArray = dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty].filter(function(n) {
                                                    return maxPointsStudents.indexOf(n) !== -1;
                                                });
                                                dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty] = intersectionArray;
                                            } else {
                                                // No full points from this exercise, remove all candidates
                                                dSummaries[sv.STUDS_WITH_MAX_POINTS][exDifficulty] = [];
                                            }
                                        }
                                    }

                                    // Students with submissions: create union of all distinct students
                                    if(studentsWithSubs.length > 0) {
                                        studentsWithSubs.forEach(value => {
                                            if(!dSummaries[sv.STUDS_WITH_SUBS][exDifficulty].includes(value)) {
                                                dSummaries[sv.STUDS_WITH_SUBS][exDifficulty].push(value);
                                            }
                                        });
                                    }
                                }

                                /**
                                 * Calculate total summaries (regardless of mode)
                                 */
                                tSummaries[sv.MAX_SUBS] += maxSubs;
                                tSummaries[sv.MAX_PTS] += maxPoints;
                                tSummaries[sv.TOTAL_SUBS] += totalSubs;

                                if(tSummaries[sv.STUDS_WITH_SUBS] === undefined) {
                                    tSummaries[sv.STUDS_WITH_SUBS] = [];
                                }
                                if(studentsWithSubs.length > 0) {
                                    studentsWithSubs.forEach(value => {
                                        if(!tSummaries[sv.STUDS_WITH_SUBS].includes(value)) {
                                            tSummaries[sv.STUDS_WITH_SUBS].push(value);
                                        }
                                    });
                                }

                                //console.log('done with exercise ' + exId + ' of module ' + modId);
                            }
                        }

                    // Need to clear the students array from 'no_ex' if no exercises found for this module
                    } else {
                        mSummaries[sv.STUDS_WITH_MAX_POINTS][modId] = ['no_ex'];
                    }

                    /**
                     * Put the calculated module summaries in place to datatable, if in module mode
                     */
                    if(_displayMode === dm.MODULE && modIdx > 0) {

                        /**
                         * Calculate averages for this module
                         */
                        if(mSummaries[sv.STUDS_WITH_SUBS][modId].length > 0) {
                            mSummaries[sv.AVG_SUBS_PER_STUD][modId] = parseFloat((mSummaries[sv.TOTAL_SUBS][modId] / mSummaries[sv.STUDS_WITH_SUBS][modId].length).toFixed(2));
                        } else mSummaries[sv.AVG_SUBS_PER_STUD][modId] = 0;

                        if(mSummaries[sv.STUDS_WITH_SUBS][modId].length > 0) {
                            mSummaries[sv.AVG_PTS_PER_STUD][modId] = parseFloat((pointsModuleTotal[modId] / mSummaries[sv.STUDS_WITH_SUBS][modId].length).toFixed(2));
                        } else mSummaries[sv.AVG_PTS_PER_STUD][modId] = 0;

                        // Put per-module sums in place to datatable
                        if(moduleScores[0] !== undefined) {
                            // Get rows which are currently visible (matching the search parameters)
                            const rows = dtVar.rows({search: 'applied'}).indexes();
                            dtVar.column(modIdx,{search: 'applied'})
                                .data()
                                .each(function(value, index) {
                                    dtVar.cell(rows[index],modIdx).data(moduleScores[index]);
                                });
                        }

                        for(var s in summaries) {
                            if(summaries[s]["INITVAL"] === 0) {
                                if(mSummaries[s][modId] === undefined) mSummaries[s][modId] = 0;
                                // Init value is integer, use the value directly
                                summArray[s][modIdx] = mSummaries[s][modId];
                            } else {
                                // Init value is array, use the array size
                                if(mSummaries[s][modId] === undefined) {
                                    mSummaries[s][modId] = [];
                                    summArray[s][modIdx] = 0;
                                } else {
                                    if(mSummaries[s][modId].includes('no_ex')) {
                                        summArray[s][modIdx] = 0;
                                    } else {
                                        summArray[s][modIdx] = mSummaries[s][modId].length;
                                    }
                                }
                            }
                        }
                    }
                }
                pointsGrandTotal += pointsModuleTotal[modId];
            } // End loop for each module
        }
        /**
         * Do the difficulty stuff if in this mode
         */
        if(_displayMode === dm.DIFFICULTY) {

            /**
             * First calculate averages for each difficulty
             */
            for(var d in _difficulties) {
                if(dSummaries[sv.STUDS_WITH_SUBS][d].length > 0) {
                    dSummaries[sv.AVG_SUBS_PER_STUD][d] = parseFloat((dSummaries[sv.TOTAL_SUBS][d] / dSummaries[sv.STUDS_WITH_SUBS][d].length).toFixed(2));
                } else dSummaries[sv.AVG_SUBS_PER_STUD][d] = 0;

                if(dSummaries[sv.STUDS_WITH_SUBS][d].length > 0) {
                    dSummaries[sv.AVG_PTS_PER_STUD][d] = parseFloat((pointsDifficultyTotal[d] / dSummaries[sv.STUDS_WITH_SUBS][d].length).toFixed(2));
                } else dSummaries[sv.AVG_PTS_PER_STUD][d] = 0;
            }

            /**
             * Then put the calculated difficulty summaries in place to datatable
             */
            for(var d in _difficulties) {
                const diffIdx = dtVar.column('.diff-' + d).index(); // difficulty index id in datatable
                if(diffIdx > 0) {
                    for(var s in summaries) {
                        if(summaries[s]["INITVAL"] === 0) {
                            if(dSummaries[s][d] === undefined) dSummaries[s][d] = 0;
                            // Init value is integer, use the value directly
                            summArray[s][diffIdx] = dSummaries[s][d];
                        } else {
                            // Init value is array, use the array size
                            if(dSummaries[s][d] === undefined) {
                                dSummaries[s][d] = [];
                                summArray[s][diffIdx] = 0;
                            } else {
                                summArray[s][diffIdx] = dSummaries[s][d].length;
                            }
                        }
                    }
                }
            }
        }

        /**
         * Calculate the total students with max points for all items, depending on mode.
         */
        tSummaries[sv.STUDS_WITH_MAX_POINTS] = ['no_ex'];

        if(_displayMode === dm.MODULE) {
            for(var m in mSummaries[sv.STUDS_WITH_MAX_POINTS]) {
                if(tSummaries[sv.STUDS_WITH_MAX_POINTS].length > 0) {
                    // If this module had exercises, it needs to be counted for totals
                    if(!mSummaries[sv.STUDS_WITH_MAX_POINTS][m].includes('no_ex')) {
                        // Remove any students from the existing list who don't have max points from this exercise
                        var intersectionArray = mSummaries[sv.STUDS_WITH_MAX_POINTS][m].filter(function(n) {
                            return tSummaries[sv.STUDS_WITH_MAX_POINTS].indexOf(n) !== -1;
                        });
                        tSummaries[sv.STUDS_WITH_MAX_POINTS] = intersectionArray;
                    }
                }
            }
        }

        /**
         * Handle the case where no exercises were processed (=> show 0 students with max points)
         */
        if(tSummaries[sv.STUDS_WITH_MAX_POINTS].includes('no_ex')) {
            tSummaries[sv.STUDS_WITH_MAX_POINTS] = [];
        };

        /**
         * Calculate total averages
         */
        tSummaries[sv.AVG_SUBS_PER_STUD] = (tSummaries[sv.STUDS_WITH_SUBS].length > 0 ? parseFloat((tSummaries[sv.TOTAL_SUBS] / tSummaries[sv.STUDS_WITH_SUBS].length).toFixed(2)) : 0);
        tSummaries[sv.AVG_PTS_PER_STUD] = (tSummaries[sv.STUDS_WITH_SUBS].length > 0 ? parseFloat((pointsGrandTotal / tSummaries[sv.STUDS_WITH_SUBS].length).toFixed(2)) : 0);

        /**
         * Put the calculated totals in place to datatable, regardless of mode
         */
        for(var s in summaries) {
            if(summaries[s]["INITVAL"] === 0) {
                if(tSummaries[s] === undefined) tSummaries[s] = 0;
                // Init value is integer, use the value directly
                summArray[s][TOTAL_COL_ID] = tSummaries[s];
            } else {
                // Init value is array, use the array size
                if(tSummaries[s] === undefined) {
                    tSummaries[s] = [];
                    summArray[s][TOTAL_COL_ID] = 0;
                } else {
                    if(tSummaries[s].includes('no_ex')) {
                        summArray[s][TOTAL_COL_ID] = 0;
                    } else {
                        summArray[s][TOTAL_COL_ID] = tSummaries[s].length;
                    }
                }
            }
            /**
             * Calculate percentages of total for the summary columns
             */
            const componentCols = dtVar.columns('.' + dmRev[_displayMode]);
            for(var c in componentCols[0]) {
                const compVal = summArray[s][componentCols[0][c]];
                let totalVal;
                if(s === sv.STUDS_WITH_MAX_POINTS || s === sv.STUDS_WITH_SUBS) {
                    totalVal = dtVar.rows({search: 'applied'})[0].length;
                } else {
                    totalVal = summArray[s][TOTAL_COL_ID];
                }
                const ratio = totalVal > 0 ? parseFloat(compVal * 100 / totalVal).toFixed(2) : 0;
                //console.log(ratio);
                if(ratio > 0) {
                    summArray[s][componentCols[0][c]] = compVal + '<div class="ratio">' + ratio + '</div>';
                }
            };
        }

        /**
         * Hide all columns and then show the currently active ones, depending on display mode
         */
        dtVar.columns('.module').visible( false,false );
        dtVar.columns('.exercise').visible( false,false );
        dtVar.columns('.difficulty').visible( false,false );

        switch(_displayMode) {
            case dm.DIFFICULTY:
                _activeDifficulties.forEach(function(value) {
                    dtVar.columns('.difficulty.diff-' + value ).visible( true,false );
                });
                break;
            case dm.EXERCISE:
                if(selectedExercises !== null) {
                    selectedExercises.forEach(function(value) {
                        dtVar.columns( '.exercise.' + value  ).visible( true,false );
                    });
                }
                break;
            case dm.MODULE:
                if(selectedModules !== null) {
                    selectedModules.forEach(function(value) {
                        // We don't want to show modules with no exercises even if selected
                        let moduleId = parseInt(value.replace('mod-m',''));
                        if(moduleId > 0) {
                            let moduleInfo =_exercises.find((x) => x.id === moduleId);
                            if(moduleInfo.exercises.length > 0) {
                                dtVar.columns( '.module.' + value  ).visible( true,false );
                            }
                        }
                    });
                }
                break;
        }

        // Force table width to match the currently visible columns
        // see https://stackoverflow.com/questions/5109831/how-to-resize-a-jquery-datatable-after-hiding-columns
        pointsTableRef.width("99%");

        // Finally redraw table
        dtVar.draw();
    }

    /**
     * Change display mode (difficulty, module or exercise view)
     * @param {string} newMode display mode to change to
     */
    window.changeDisplayMode = function(newMode) {
        if(newMode != _displayMode) {
            // Clear existing points column searches to not confuse user with hidden search options
            // (do not clear searches in student id, name or tags fields)
            for(var i in colSearchVals) {
                dtVar.columns(i).search('');
            }
            colSearchVals = {};
            $( 'thead#table-heading input.numval').val('');
            // Scroll table sideways to starting position in case we have fewer columns to display than before
            $("#table-points-div").scrollLeft(0);
            _displayMode = newMode;
        }

        changeExerciseSelection();
    }

    /**
     * Return html for tags separated with pipe (|) characters
     * @param {array} tags array of tags to use
     * @returns parsed html string for user tags display
     */
    function userTagsToHTML(tags) {
        if(tags.length) {
            let html = '';
            tags.split('|').forEach(function(tag) {
                html += '<span class="colortag colortag-active badge" style="color: ' + _usertags[tag].font_color + '; background-color: ' + _usertags[tag].color + '; margin-right: 5px;">' + _usertags[tag].name + '</span>';
            })
            return html;
        } else return '';
    }

    /**
     * Things to do when user makes changes in the modules popup menu
     */
    function changeModuleSelection() {
        // Show all popup-selected modules and assignments and hide unselected ones
        const selectedModules = moduleSelectRef.find('option:selected');
        const nonSelectedModules = moduleSelectRef.find('option').filter(function() {
            return !$(this).is(':selected');
        });

        selectedModules.each(function() {
            let showModuleClass = '.' + $(this).val();
            multiSelectSelector.find(showModuleClass).removeClass("d-none disabled");
            multiSelectSelector.find(showModuleClass).prop("selected", true);
            exerciseSelectRef.find(showModuleClass).prop("selected", true);
            if(_displayMode === dm.MODULE) {
                dtVar.columns( showModuleClass ).visible( true,false );
            }
        });

        nonSelectedModules.each(function() {
            let hideModuleClass = '.' + $(this).val();
            multiSelectSelector.find(hideModuleClass).addClass("d-none disabled");
            multiSelectSelector.find(hideModuleClass).prop("selected", false);
            exerciseSelectRef.find(hideModuleClass).prop("selected", false);
        });
        exerciseSelectRef.multiselect('refresh');

        changeExerciseSelection();
    }

    /**
     * Things to do when user makes changes in the exercises popup menu
     */
    function changeExerciseSelection() {
        // If we have changed the selected exercises, we need to clear any filters for
        // dynamically generated columns, as these may no longer give correct results
        clearPointsSearch();
        // Nothing much here, just refresh the table
        pointsTableRef.width('99%');
        recalculateTable();
    }

    /* TODO: Use better logic for translations.
     * Currently only some translations wait for aplus:translation-ready and most of them do not,
     * since the translations become available during the script.
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

            return selected.substring(0, selected.length - this.delimiterText.length);
        }
    }

    /**
     * Parse the search string of points column headers
     * @param {string} input user-typed string to search for
     * @returns
     */
    function parsePointsSearchVal(input) {
        if(input.length > 1) {
            var val = input.split('>');

            if (val.length === 2) {
                return ['>',val[1]];
            }

            val = input.split('<');

            if (val.length === 2) {
                return ['<',val[1]];
            }
        }
        // Plain value
        return [null, input];
    }

    /**
     * Add search fields to each header row (excluding the always hidden cols
     * containing submission counts and other helper columns).
     */
    function addHeaderSearchInputs() {
        $('#table-points thead tr:eq(0) th').not('.always-hidden').each( function (i) {
            /**
             * We need to find the column index with 'always-hidden' columns skipped.
             * Since this is not provided us, let's dig it from the column header
             * where the current search box lives.
             * TODO: Find a better way to do this
             */
            var realIndex = 0;
            const colClasses = $(this)[0].className.split(/\s+/);
            idx = colClasses.findIndex(function(item) { return item.startsWith('col-') });
            if(idx > -1) {
                realIndex = colClasses[idx].split('-')[1];
            }

            // Set vertical-align on the th to bottom so content aligns to the bottom
            $(this).css('vertical-align', 'bottom');

            // Remove table-info class from header cells to match the earlier A+ styling
            $(this).removeClass('table-info');

            // DataTables 2.3+: Wrap title and sort icon, then add input below
            const $header = $(this).find('.dt-column-header');

            // Set flex-direction to column and justify-content to flex-end to align items to bottom
            $header.css({
                'flex-direction': 'column',
                'justify-content': 'flex-end'
            });

            // Wrap the title and sort icon in a flex row container
            const $title = $header.find('.dt-column-title');
            const $order = $header.find('.dt-column-order');

            // Apply CSS ellipsis to truncate long titles
            $title.css({
                'overflow': 'hidden',
                'text-overflow': 'ellipsis',
                'white-space': 'nowrap',
                'max-width': '20ch'
            });
            // Set title attribute for full text on hover
            $title.attr('title', $title.text());

            $title.wrap('<div style="display: flex; align-items: center; width: 100%;"></div>');
            $title.parent().append($order);

            if(realIndex < TOTAL_COL_ID) {
                /**
                 * Create column search boxes for other than points columns
                 */
                $header.append( '<input type="text" class="form-control-sm input textval" style="z-index: 4; margin-top: 4px; width: 100%;" placeholder="' + _("Search") + '" />' );
                $( 'input.textval', this ).on( 'keyup change clear', function () {
                    if ( dtVar.column(realIndex).search() !== this.value ) {
                        recalculateTableDebounced(realIndex, this.value);
                    }
                } );
            } else {
                /**
                 * Create search boxes for points columns
                 */
                $header.append( '<input type="text" class="form-control-sm input numval" style="margin-top: 4px; width: 100%;" placeholder="' + _("Search") + '" />' );
                $( 'input.numval', this ).on('keyup change clear', function () {
                    if(this.value === '') delete colSearchVals[realIndex];
                    else colSearchVals[realIndex] = parsePointsSearchVal(this.value);
                    recalculateTableDebounced(realIndex, '');
                });
            }

            // Prevent resorting when clicking the search box
            $( 'input', this ).click(function(e) {
                e.stopPropagation();
            });
        });
    }


    /**
     * Recalculates points data from cached raw data based on show_unofficial, show_unconfirmed, and ignore_last_grading_mode flags.
     * Transforms nested format to flat format for DataTables.
     * @param {Array} rawDataArray - Array of student objects with nested format
     * @param {boolean} show_unofficial - Whether to include unofficial points
     * @param {boolean} show_unconfirmed - Whether to include unconfirmed points
     * @param {boolean} ignore_last_grading_mode - Whether to use best grades (true) or last grades (false)
     * @returns {Array} Array of student objects in flat format for DataTables
     */
    function recomputeAggregateColumns(points) {
        if(points['Count'] === undefined) {
            return;
        }

        let studentTotalPoints = 0;

        Object.keys(_difficulties).forEach(function(diff) {
            points[diff] = 0;
        });

        _exercises.forEach(function(module) {
            let moduleSubmissions = 0;
            let moduleTotalPoints = 0;

            if(module.exercises.length > 0) {
                module.exercises.forEach(function(exercise) {
                    const exId = exercise.id;

                    if(points[exId + ' Count'] === undefined) {
                        points[exId + ' Count'] = 0;
                    }
                    if(points[exId + ' Total'] === undefined) {
                        points[exId + ' Total'] = 0;
                    }

                    moduleSubmissions += points[exId + ' Count'];
                    moduleTotalPoints += points[exId + ' Total'];

                    const diffKey = _reverseDifficulties[exId];
                    if(diffKey !== undefined) {
                        points[diffKey] = (points[diffKey] || 0) + points[exId + ' Total'];
                    }
                });
            }

            points['m' + module.id + ' Count'] = moduleSubmissions;
            points['m' + module.id + ' Total'] = moduleTotalPoints;
            studentTotalPoints += moduleTotalPoints;
        });

        points['Total'] = studentTotalPoints;
    }

    function recalculatePointsData(rawDataArray, show_unofficial, show_unconfirmed, ignore_last_grading_mode) {
        // Create a deep copy to avoid modifying the cached data
        const recalculatedData = JSON.parse(JSON.stringify(rawDataArray));
        
        recalculatedData.forEach(function(points) {
            // Convert new nested format to flat format
            // New format: { exercises: { "22": {c: 3, tb: 10, tl: 8, uc: 1, utb: 5, utl: 3} }, totals: {c: 12, tb: 117, tl: 100} }
            // Old format: { "22 Count": 3, "22 Total": 10, Count: 12, Total: 117 }
            
            if(points.exercises !== undefined) {
                // Convert exercises object to flat format
                // Choose between best (tb/utb) and last (tl/utl) grades based on ignore_last_grading_mode
                for(let exId in points.exercises) {
                    const ex = points.exercises[exId];
                    if (show_unofficial) {
                        // Use official + unofficial (all counts)
                        points[exId + ' Count'] = (ex.c || 0) + (ex.uc || 0);
                        // Use best or last grade based on grading mode
                        if (ignore_last_grading_mode) {
                            points[exId + ' Total'] = (ex.tb || 0) + (ex.utb || 0);
                        } else {
                            points[exId + ' Total'] = (ex.tl || 0) + (ex.utl || 0);
                        }
                    } else {
                        // Use only official counts
                        points[exId + ' Count'] = ex.c || 0;
                        // Use best or last grade based on grading mode
                        if (ignore_last_grading_mode) {
                            points[exId + ' Total'] = ex.tb || 0;
                        } else {
                            points[exId + ' Total'] = ex.tl || 0;
                        }
                    }
                }
                
                // Convert totals object to flat format
                if(points.totals !== undefined) {
                    if (show_unofficial) {
                        points['Count'] = (points.totals.c || 0) + (points.totals.uc || 0);
                        // Use best or last grade based on grading mode
                        if (ignore_last_grading_mode) {
                            points['Total'] = (points.totals.tb || 0) + (points.totals.utb || 0);
                        } else {
                            points['Total'] = (points.totals.tl || 0) + (points.totals.utl || 0);
                        }
                    } else {
                        points['Count'] = points.totals.c || 0;
                        // Use best or last grade based on grading mode
                        if (ignore_last_grading_mode) {
                            points['Total'] = points.totals.tb || 0;
                        } else {
                            points['Total'] = points.totals.tl || 0;
                        }
                    }
                }
            }

            // Apply confirmation logic if show_unconfirmed is false
            if (points['Count'] !== undefined && !show_unconfirmed) {
                // Find all mandatory exercises (requires_confirmation = true)
                const mandatoryExercises = Object.keys(_confirmationMap).filter(
                    exId => _confirmationMap[exId].requires_confirmation
                );

                // For each mandatory exercise, check if student has passed it
                mandatoryExercises.forEach(function(mandatoryExId) {
                    const mandatoryInfo = _confirmationMap[mandatoryExId];
                    const studentPoints = points[mandatoryExId + ' Total'] || 0;

                    // If student has 0 points on mandatory exercise, zero out all siblings
                    if (studentPoints === 0) {
                        // Find all siblings (exercises with same parent_id and module_id)
                        Object.keys(_confirmationMap).forEach(function(exId) {
                            const exInfo = _confirmationMap[exId];
                            if (exInfo.parent_id === mandatoryInfo.parent_id && 
                                exInfo.module_id === mandatoryInfo.module_id) {
                                // Zero out this sibling exercise
                                points[exId + ' Count'] = 0;
                                points[exId + ' Total'] = 0;
                            }
                        });
                    }
                });
            }

            recomputeAggregateColumns(points);
        });
        
        return recalculatedData;
    }

    /**
     * Loads new data on page load, and when checkboxes are toggled.
     * For unofficial points, we use cached data instead of refetching from backend.
     * @param {*} show_unofficial
     */
    function loadStudentData(show_unofficial, show_unconfirmed, ignore_last_grading_mode) {
        if(show_unofficial == undefined) {
            show_unofficial = $('input.unofficial-checkbox').prop('checked')
        }
        if(show_unconfirmed == undefined) {
            show_unconfirmed = $('input.unconfirmed-checkbox').prop('checked')
        }
        if(ignore_last_grading_mode == undefined) {
            ignore_last_grading_mode = $('#ignore-last-mode-checkbox').prop('checked');
        }

        // Disable all checkboxes during processing to prevent multiple clicks
        $('input.unofficial-checkbox').prop('disabled', true);
        $('input.unconfirmed-checkbox').prop('disabled', true);
        $('input.withsubs-checkbox').prop('disabled', true);
        $('#ignore-last-mode-checkbox').prop('disabled', true);
        
        // Use setTimeout to allow the browser to update the DOM (disable checkbox) before heavy processing
        setTimeout(function() {
            // If we have cached data and table already exists, just update the data in place
            if(_rawPointsData !== null && dtApi !== undefined) {
                // Recalculate points from cached data with new show_unofficial, show_unconfirmed, and ignore_last_grading_mode settings
                const updatedData = recalculatePointsData(_rawPointsData, show_unofficial, show_unconfirmed, ignore_last_grading_mode);

                // Update DataTable data without destroying it
                dtApi.clear();
                dtApi.rows.add(updatedData);
                // Draw first to update the table data, then recalculate summaries
                dtApi.draw(false); // false = stay on current page

                // Now recalculate summaries and totals based on new data
                recalculateTable();

                // Re-enable checkboxes
                $('input.unofficial-checkbox').prop('disabled', false);
                $('input.unconfirmed-checkbox').prop('disabled', false);
                $('.withsubs-checkbox').prop('disabled', false);
                $('#ignore-last-mode-checkbox').prop('disabled', false);
                return;
            }

            // If we have cached data but no table yet (shouldn't happen), do full render
            if(_rawPointsData !== null) {
                // Destroy old data table if it exists
                if(dtApi !== undefined) {
                    dtApi.destroy();
                    moduleSelectRef.multiselect('destroy');
                    exerciseSelectRef.multiselect('destroy');
                    moduleSelectRef.find('option').remove();
                    exerciseSelectRef.find('option').remove();
                    pointsTableRef.find('tr').remove();
                    $('.filter-users button').off('click');
                    $('#difficulty-exercises').tab('show');
                }
                // Process cached data with new show_unofficial, show_unconfirmed, and ignore_last_grading_mode settings
                processAndRenderData(_exercises, _rawPointsData, _usertags, show_unofficial, show_unconfirmed, ignore_last_grading_mode);
                return;
            }
        
        // Destroy old data table if it exists before fetching new data
        // Also multiselects and event handlers that will be recreated
        if(dtApi !== undefined) {
            dtApi.destroy();
            moduleSelectRef.multiselect('destroy');
            exerciseSelectRef.multiselect('destroy');
            moduleSelectRef.find('option').remove();
            exerciseSelectRef.find('option').remove();
            pointsTableRef.find('tr').remove();
            $('.filter-users button').off('click');
            $('#difficulty-exercises').tab('show');
        }

        let pUrl = pointsBestUrl;
        if (!ignore_last_grading_mode) pUrl = pointsUrl;
        // Always fetch all data (official + unofficial + unconfirmed) from backend
        // We'll filter on the frontend based on show_unofficial and show_unconfirmed checkboxes
        pUrl = pUrl + "&show_unconfirmed=true";
        $.when(
            $.ajax(exercisesUrl),
            $.ajax(pUrl),
            $.ajax(usertagsUrl)
        ).done(function(exerciseJson, pointsJson, userTags) {
            // Cache the raw data for future use
            _rawPointsData = pointsJson[0];
            processAndRenderData(exerciseJson[0].results, pointsJson[0], userTags[0].results, show_unofficial, show_unconfirmed, ignore_last_grading_mode);
        }).fail(function(jqXHR, textStatus, errorThrown) {
            console.error("Loading student data failed.");
            console.error(errorThrown);
        });
        }, 0); // End of setTimeout - allows DOM update before processing
    }

    /**
     * Process and render the data table with the given parameters
     */
    function processAndRenderData(exercises, pointsData, userTagsData, show_unofficial, show_unconfirmed, ignore_last_grading_mode) {
        const exerciseJson = [{results: exercises}];
        const pointsJson = [pointsData];
        // userTagsData is either an array of results (from AJAX) or already processed _usertags object (from cache)
        const userTagsArray = Array.isArray(userTagsData) ? userTagsData : [];
        
        // Reset global objects that accumulate data on each render
        _difficulties = {};
        _reverseDifficulties = {};

        // Only process user tags if we have an array (first load from AJAX)
        if (userTagsArray.length > 0) {
            userTagsArray.forEach(function(entry) {
                if(entry.id === null) {
                    // TODO: usertags are rendered in an Aalto-specific way as there's no API to return them?
                    _usertags[entry.name.toLowerCase()] = {color: entry.color, font_color: entry.font_color, name: entry.name, slug: entry.slug};
                } else {
                    _usertags[entry.id] = {color: entry.color, font_color: entry.font_color, name: entry.name, slug: entry.slug};
                }
                // Just save the bare minimum for rendering at this point
            });
        }

            /**
             * Builds HTML link to user profile for a table row, to be used as
             * renderer attribute in table setup
             * @param {*} data content shown in the table cell.
             * @param {*} type not used
             * @param {*} row results item currently being processed
             * @returns HTML string used in table cell
             */
            function renderParticipantLink(data, type, row) {
                if (row['UserID'] > 0 && userResultsUrlTemplate) {
                    // Replace the placeholder user_id (0) with actual user ID
                    const link = userResultsUrlTemplate.replace('/0', '/' + row['UserID']);
                    return '<a href="' + link + '">' + (!data ? '—' : data) + '</a>';
                }
                return (!data ? '—' : data);
            }

            let columns = [
                {data: "UserID", title: "UserID", className: "always-hidden col-0", type: "num", searchable: false},
                {data: "Email", name: "Email", title: "Email", className: "always-hidden col-1", type: "string", searchable: true},
                {data: "StudentID", title: _("Student ID"), type: "string", className: "student-id table-info stick-on-scroll col-2", render: renderParticipantLink},
                {data: "Name", title: _("Student name"), className: "student-name table-info stick-on-scroll col-3 ", type: "html", render: renderParticipantLink},
                {data: "Tags", title: _("Tags"), className: "tags col-4", render: function(data) { return userTagsToHTML(data); }, type: "html" },
                {data: "Organization", title: _("Organization"), className: "col-5", type: "string"},

                // SISU columns. These are only visible in SISU CSV.
                // Column headers must be exactly correct, and hence not translated.
                {data: "StudentID", title: "studentNumber", type: "string", className: "always-hidden sisu stick-on-scroll col-6"},
                {data: "Grade", title: "grade", className: "always-hidden sisu col-7", type: "string", defaultContent: ""},
                {data: "Credits", title: "credits", className: "always-hidden sisu col-8", type: "string", defaultContent: ""},
                {data: "AssessmentDate", title: "assessmentDate", className: "always-hidden sisu col-9", type: "string", defaultContent: ""},
                {data: "CompletionLanguage", title: "completionLanguage", className: "always-hidden sisu col-10", type: "string", defaultContent: ""},
                {data: "Comment", title: "comment", className: "always-hidden sisu col-11", type: "string", defaultContent: ""},
                {data: "AdditionalInfo-fi", title: "additionalInfo-fi", className: "always-hidden sisu col-12", type: "string", defaultContent: ""},
                {data: "AdditionalInfo-sv", title: "additionalInfo-sv", className: "always-hidden sisu col-13", type: "string", defaultContent: ""},
                {data: "AdditionalInfo-en", title: "additionalInfo-en", className: "always-hidden sisu col-14", type: "string", defaultContent: ""},

                {data: "Count", title: "Count", className: "col-15", visible: false, defaultContent: 0, type: "num"},
                {data: "Total", title: _("Total"), className: "points total col-16 dt-type-numeric", defaultContent: 0, type: "num", render: function(data) { return data; }}
            ];

            // Store exercises globally
            _exercises = exerciseJson[0].results;

            // Create select boxes for modules and exercises
            // Add the actual data columns for datatable
            // Add column numbers so these can be used when searching by column
            exerciseJson[0].results.forEach(function(module) {
                columns.push({data: 'm' + module.id + ' Count', title: 'm' + module.id + ' Count', className: "always-hidden col-" + columns.length + '"', type: "num", defaultContent: 0, searchable: false, visible: false});
                columns.push({data: 'm' + module.id + ' Total', title: module.display_name, className: 'points module ' + 'mod-m' + module.id + ' col-' + columns.length, type: "num", defaultContent: 0, visible: true});

                moduleSelectRef.append(
                    '<option value="mod-m' + module.id + '"'
                    + 'selected>'
                    + module.display_name
                    + '</option>'
                );
                if(module.exercises.length > 0) {
                    exerciseSelectRef.append(
                        '<optgroup class="mod-m' + module.id + '"'
                        + 'value="mod-m' + module.id + ' col-' + columns.length + '"'
                        + 'label="' + module.display_name + '"'
                        + '></optgroup'
                    );
                    module.exercises.forEach(function(exercise) {
                        columns.push({data: exercise.id + ' Count', title: exercise.id + ' Count', className: "always-hidden col-" + columns.length, type: "num", defaultContent: 0, searchable: false, visible: false});
                        columns.push({data: exercise.id + ' Total', title: exercise.display_name, className: 'points exercise ' + 'ex-' + exercise.id + ' col-' + columns.length, type: "num", defaultContent: 0, visible: true});
                        $("#exercise-selection > optgroup:last-child").append(
                            '<option data-mod-id="m' + module.id + '"'
                            + 'data-ex-id="' + exercise.id + '"'
                            + 'class="mod-m'+ module.id + '"'
                            + 'value="ex-'+ exercise.id + '"'
                            + 'selected>'
                            + exercise.display_name
                            + '</option>'
                        );
                        if(_difficulties[exercise.difficulty] !== undefined) {
                            _difficulties[exercise.difficulty].push(exercise.id);
                        } else {
                            _difficulties[exercise.difficulty] = [exercise.id];
                        }
                        // Store confirmation requirements for this exercise
                        _confirmationMap[exercise.id] = {
                            requires_confirmation: exercise.requires_confirmation || false,
                            parent_id: exercise.parent_id || null,
                            module_id: module.id
                        };
                    })
                 }
            });

            // Create reverse lookup array for _difficulties (check difficulty by exercise id)
            for(let propName in _difficulties)
            {
                let numsArr = _difficulties[propName];
                numsArr.forEach(function(num){
                    _reverseDifficulties[num]=propName;
                });
            }

            // Add columns for difficulty levels. Empty difficulty is labeled as 'No difficulty' in the datatable
            if(Object.keys(_difficulties).length) {
                for(diff in _difficulties) {
                    columns.push({data: diff, title: (diff === '' ? _('No difficulty') : diff), className: 'points difficulty diff-' + diff + ' col-' + columns.length, type: "num", defaultContent: 0, visible: true});
                }
            }

            // Augment the raw points received from the API by
            // converting nested format to flat format and adding columns for modules/difficulties
            pointsJson[0].forEach(function(points, index) {
                // Convert new nested format to flat format for backward compatibility
                // New format: { exercises: { "22": {c: 3, tb: 10, tl: 8, uc: 1, utb: 5, utl: 3} }, totals: {c: 12, tb: 117, tl: 100} }
                // Old format: { "22 Count": 3, "22 Total": 10, Count: 12, Total: 117 }
                
                if(points.exercises !== undefined) {
                    // Convert exercises object to flat format
                    // Choose between best (tb/utb) and last (tl/utl) grades based on ignore_last_grading_mode
                    for(let exId in points.exercises) {
                        const ex = points.exercises[exId];
                        if (show_unofficial) {
                            // Use official + unofficial (all counts)
                            points[exId + ' Count'] = (ex.c || 0) + (ex.uc || 0);
                            // Use best or last grade based on grading mode
                            if (ignore_last_grading_mode) {
                                points[exId + ' Total'] = (ex.tb || 0) + (ex.utb || 0);
                            } else {
                                points[exId + ' Total'] = (ex.tl || 0) + (ex.utl || 0);
                            }
                        } else {
                            // Use only official counts
                            points[exId + ' Count'] = ex.c || 0;
                            // Use best or last grade based on grading mode
                            if (ignore_last_grading_mode) {
                                points[exId + ' Total'] = ex.tb || 0;
                            } else {
                                points[exId + ' Total'] = ex.tl || 0;
                            }
                        }
                    }
                    
                    // Convert totals object to flat format
                    if(points.totals !== undefined) {
                        if (show_unofficial) {
                            points['Count'] = (points.totals.c || 0) + (points.totals.uc || 0);
                            // Use best or last grade based on grading mode
                            if (ignore_last_grading_mode) {
                                points['Total'] = (points.totals.tb || 0) + (points.totals.utb || 0);
                            } else {
                                points['Total'] = (points.totals.tl || 0) + (points.totals.utl || 0);
                            }
                        } else {
                            points['Count'] = points.totals.c || 0;
                            // Use best or last grade based on grading mode
                            if (ignore_last_grading_mode) {
                                points['Total'] = points.totals.tb || 0;
                            } else {
                                points['Total'] = points.totals.tl || 0;
                            }
                        }
                    }
                }
                
                if(points['Count'] !== undefined && !show_unconfirmed) {
                    // Find all mandatory exercises (requires_confirmation = true)
                    const mandatoryExercises = Object.keys(_confirmationMap).filter(
                        exId => _confirmationMap[exId].requires_confirmation
                    );

                    // For each mandatory exercise, check if student has passed it
                    mandatoryExercises.forEach(function(mandatoryExId) {
                        const mandatoryInfo = _confirmationMap[mandatoryExId];
                        const studentPoints = points[mandatoryExId + ' Total'] || 0;

                        // If student has 0 points on mandatory exercise, zero out all siblings
                        if (studentPoints === 0) {
                            // Find all siblings (exercises with same parent_id and module_id)
                            Object.keys(_confirmationMap).forEach(function(exId) {
                                const exInfo = _confirmationMap[exId];
                                if (exInfo.parent_id === mandatoryInfo.parent_id && 
                                    exInfo.module_id === mandatoryInfo.module_id) {
                                    // Zero out this sibling exercise
                                    points[exId + ' Count'] = 0;
                                    points[exId + ' Total'] = 0;
                                }
                            });
                        }
                    });
                }

                recomputeAggregateColumns(points);
            });

            /**
             * If the body has class 'lang-fi', use the Finnish translation for DataTables
             */
            pageLanguageUrl = $('body').hasClass('lang-fi') ? 'https://cdn.datatables.net/plug-ins/2.2.1/i18n/fi.json' : '';

            /**
             * Removes HTML from Tags and Name columns.
             * The tags column needs special treatment as we need to replace
             * the html tags with commas for exporting. Also Name column needs HTML cleanup.
             * The regexp takes any number of consecutive tags and converts them into a single comma.
             * After that, the first and last commas are sliced away.
             */
            function removeHtmlFromColumns( data, row, column, node ) {
                if (typeof(data) === "string") {
                    // Column 4 is expected to be the Tags column
                    // The other HTML - rendered columns (name, studentID)
                    // are just cleaned up of HTML
                    return column === 4 ?
                    data.replace( /(<[^>]*>)+/g, ',' ).slice(1,-1) :
                    $.fn.dataTable.util.stripHtml(data);
                }
                else return data;
            }

            /**
             * Define common options for DataTables buttons (CSV, Copy, Excel), as they all use the
             * same logic and export only visible columns.
             */
            var buttonCommon = {
                exportOptions: {
                    columns: ['Email:name', ':visible'],
                    format: {
                        body: removeHtmlFromColumns
                    }
                }
            }

            if (!window.jQuery) {
                console.error('jQuery not loaded before DataTables initialization.');
            } else if (!$.fn.DataTable && window.DataTable) {
                console.warn('jQuery loaded but DataTables jQuery plugin missing; falling back.');
                // Optional fallback (lets you proceed without refactor):
                $.fn.DataTable = function(opts){ return new DataTable(this[0], opts); };
            } else if (!$.fn.DataTable) {
                console.error('DataTables plugin not present.');
            }

            /**
             * Initialize the DataTables plugin for the main table
             */
            dtApi = $('#table-points').DataTable( {
                data: pointsJson[0],
                renderer: "bootstrap",
                columns: columns,
                deferRender: true,
                //fixedHeader: true, // cannot use fixedHeader as it doesn't work with sideways scrolling
                //"scrollX": true, // not using scrollX as we do this manually via JavaScript translateX
                lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, "All"]],
                pageLength: 50, // Set the length to 50 for faster initial load time
                language: {
                    paginate: {
                        first: '<i class="bi-chevron-double-left"></i>',
                        last: '<i class="bi-chevron-double-right"></i>',
                        next: '<i class="bi-chevron-right"></i>',
                        previous: '<i class="bi-chevron-left"></i>'
                    },
                    url: pageLanguageUrl
                },
                /**
                 * When DataTables has initialized itself, we need to present the initial view for the user.
                 * For this, we need to make sure some things are prepared:
                 * - Search boxes for columns need to be rendered before hiding other than difficulty columns
                 * - Active difficulties are initialized to include all available difficulties
                 * After that, we change the display mode to trigger table values calculations etc.
                 */
                initComplete: function() {
                    dtVar = this.api();
                    addHeaderSearchInputs(); // need to be added when columns of all modes are still in DOM
                    for(diff in _difficulties) {
                        _activeDifficulties.push(diff);
                    }
                    // Make sure all hidden columns are hidden
                    dtVar.columns('.always-hidden').visible(false,false);
                    changeDisplayMode(dm.DIFFICULTY);
                    // Add note in our custom div in DataTables DOM template
                    $(".dt-note").html(_('You can use &lt; and &gt; in points columns search fields.'));
                },
                /**
                 * Calculate the Total column for all students in DataTables row callback
                 * based on all columns visible after the total column
                 */
                rowCallback: function( row, data, displayNum, displayIndex, dataIndex ) {
                    var totalValue = parseFloat(data['Total']);
                    if (isNaN(totalValue)) {
                        totalValue = 0;
                    }
                    this.api().cell(dataIndex, TOTAL_COL_ID).data(totalValue);
                },
                /**
                 * On each table redraw, also recreate the summary rows
                 */
                drawCallback: function( settings ) {
                    if(_activeSummaryItems.length > 0) {
                        recreateSummaryRows();
                    }
                },
                /**
                 * Configure the DataTables-generated DOM (order of elements and Bootstrap classes)
                 * Note that we have a custom "dt-note" div that is used to display a note about
                 * using the < and > operators in number column search fields.
                 */
                dom: "<'row'<'col-md-3 col-sm-6'l><'col-md-6 col-sm-6'B><'col-md-3 col-sm-12'f>>" +
                        "<'row'<'col-sm-6'i><'col-sm-6 dt-note'>>" +
                        "<'row'<'#table-points-div.col-sm-12'tr>>" +
                        "<'row'<'col-sm-5'i><'col-sm-7'p>>",
                /**
                 * Data export buttons
                 */
                 buttons: [
                    $.extend( true, {}, {
                        exportOptions: {
                            columns: [ ':visible', '.sisu' ],
                            format: {
                                body: removeHtmlFromColumns
                            }
                        }}, {
                        text: '<i class="bi-file-earmark-arrow-down"></i> Sisu',
                        extend: 'csvHtml5'
                    } ),
                    $.extend( true, {}, buttonCommon, {
                        text: '<i class="bi-filetype-csv"></i> CSV',
                        extend: 'csvHtml5'
                    } ),
                    $.extend( true, {}, buttonCommon, {
                        text: '<i class="bi-clipboard"></i> ' + _('Copy to clipboard'),
                        extend: 'copyHtml5'
                    } ),
                    {
                        text: '<i class="bi-arrow-counterclockwise"></i> ' + _('Reset filters'),
                        action: function ( e, dt, node, config ) {
                            clearSearch();
                        }
                    }
                ]
            });

            /**
             * Custom search plugin for handling the range search for points columns.
             * Parsing of the search string to operator/value is offloaded to
             * parsePointsSearchVal function so it does not need to be done on each comparison
             */
            $.fn.dataTable.ext.search.push(
                function(settings, data) {
                    for(var c in colSearchVals) {
                        var colVal = parseFloat(data[c]) || 0;
                        var operator = colSearchVals[c][0];
                        var searchVal = parseFloat(colSearchVals[c][1]) || 0;

                        if(operator === '>') {
                            if (colVal > searchVal) {
                                continue;
                            } else return false;
                        }
                        if(operator === '<') {
                            if (colVal < searchVal) {
                                continue;
                            } else return false;
                        }
                        if(colVal === searchVal) continue;
                        else return false;
                    }
                    return true; // if no objections, row should be included
                }
            );

            // Initialize the bootstrap-multiselect plugin for module selection
            moduleSelectRef.multiselect({
                includeSelectAllOption: true,
                onDeselectAll: changeModuleSelection,
                onSelectAll: changeModuleSelection,
                onChange: changeModuleSelection,
                buttonText: buttonText,
                selectAllText: _("Select all"),
            });
            // Show the module select now that multiselect is built
            moduleSelectRef.show();

            // Initialize the bootstrap-multiselect plugin for exercise selection
            exerciseSelectRef.multiselect({
                includeSelectAllOption: true,
                enableClickableOptGroups: true,
                onDeselectAll: changeExerciseSelection,
                onSelectAll: changeExerciseSelection,
                onChange: changeExerciseSelection,
                maxHeight: 500,
                buttonText: buttonText,
                selectAllText: _("Select all"),
            });
            // Show the exercise select now that multiselect is built
            exerciseSelectRef.show();

            // Save the jQuery DOM instance for later
            multiSelectSelector = $(".multiselect-container");

            /**
             * Event handlers for (de)selecting all summary rows at once
             */
            $('#summary-all').change(function() {
                if($(this).prop('checked')) {
                    summaryCheckboxesRef.prop('checked', true);
                    _activeSummaryItems = ["0","1","2","3","4","5","6"];
                } else {
                    summaryCheckboxesRef.prop('checked', false);
                    _activeSummaryItems = [];
                    recreateSummaryRows();
                }
                dtVar.draw();
            });

            /**
             * Event handlers for summary row selection checkboxes
             */
            $('.summary-checkbox').change(function() {
                _activeSummaryItems = [];
                summaryCheckboxesRef.each(function() {
                    if($(this).prop('checked')) _activeSummaryItems.push($(this).val());
                });
                /**
                 * If this was the last summary item checked, need to force summary rows
                 * removal as the DataTables draw callback is not called for some reason.
                 */
                if(_activeSummaryItems.length === 0) {
                    $('thead#table-heading').find('tr.summaryitem').remove();
                    $('#summary-all').prop('checked', false); // also uncheck the "All" box
                }
                dtVar.draw();
            });

            /**
             * Show only students with submissions checkbox is handled by
             * dynamically creating/removing this DataTables search filter.
             * We store a reference to the specific filter function so we can remove
             * exactly the right one, not just the last item in the array.
             */
            var onlySubsFilter = function( settings, searchData ) {
                var subs = parseInt( searchData[15] ) || 0; // Number of submissions of student (column 15)
                return subs > 0;
            };
            
            $('.withsubs-checkbox').change(function() {
                if($(this).prop('checked')) {
                    // Add the "only students with submissions" filter
                    $.fn.dataTable.ext.search.push(onlySubsFilter);
                } else {
                    // Remove the specific filter by reference
                    var index = $.fn.dataTable.ext.search.indexOf(onlySubsFilter);
                    if (index > -1) {
                        $.fn.dataTable.ext.search.splice(index, 1);
                    }
                }
                // Make a dummy search with empty string so the newly added plugin is applied
                dtVar.search('');
                recalculateTableDebounced();
            });

            /**
             * Event listener and display logic for tag filters
             */
            $('.filter-users button').on('click', function(event) {
                event.preventDefault();
                let icon = $(this).find('i');
                if (icon.hasClass('bi-square')) {
                    icon.removeClass('bi-square').addClass('bi-check-square');
                } else {
                    icon.removeClass('bi-check-square').addClass('bi-square');
                }
                searchForSelectedTags();
            });
            
            // Re-enable all checkboxes after table is ready
            $('input.unofficial-checkbox').prop('disabled', false);
            $('input.unconfirmed-checkbox').prop('disabled', false);
            $('input.withsubs-checkbox').prop('disabled', false);
            $('#ignore-last-mode-checkbox').prop('disabled', false);
        }

    // Event listener for AND/OR tag operator
    $('input.tags-operator').change(function(){
        searchForSelectedTags();
    });

    /**
     * To toggle unofficial points, we recalculate from cached data.
     * For unconfirmed and grading mode changes, we refetch from backend.
     */
    $('input.unofficial-checkbox').change(() => {
        if (_rawPointsData !== null) {
            // Recalculate from cached data
            const show_unofficial = $('input.unofficial-checkbox').prop('checked');
            const show_unconfirmed = $('input.unconfirmed-checkbox').prop('checked');
            loadStudentData(show_unofficial, show_unconfirmed, $('#ignore-last-mode-checkbox').prop('checked'));
        } else {
            loadStudentData();
        }
    });
    $('input.unconfirmed-checkbox').change(() => {
        if (_rawPointsData !== null) {
            // Recalculate from cached data - frontend handles unconfirmed filtering
            const show_unofficial = $('input.unofficial-checkbox').prop('checked');
            const show_unconfirmed = $('input.unconfirmed-checkbox').prop('checked');
            loadStudentData(show_unofficial, show_unconfirmed, $('#ignore-last-mode-checkbox').prop('checked'));
        } else {
            loadStudentData();
        }
    });
    $('#ignore-last-mode-checkbox').change(() => {
        if (_rawPointsData !== null) {
            // Recalculate from cached data - frontend handles best/last grade selection
            const show_unofficial = $('input.unofficial-checkbox').prop('checked');
            const show_unconfirmed = $('input.unconfirmed-checkbox').prop('checked');
            const ignore_last_grading_mode = $('#ignore-last-mode-checkbox').prop('checked');
            loadStudentData(show_unofficial, show_unconfirmed, ignore_last_grading_mode);
        } else {
            loadStudentData();
        }
    });
    $(document).on("aplus:translation-ready", () => loadStudentData());

})(jQuery, document, window);

/* vim: set et ts=4 sw=4: */
