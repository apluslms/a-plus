/**
 * Schedule visualization for the course module edit form.
 *
 * Renders two live d3 charts above the schedule fields:
 *  1. A general timeline of the module's main dates (reading opening time,
 *     assignment opening time, early submission deadline, module deadline and
 *     late submission deadline), drawn to scale, with a "now" marker.
 *  2. A points-over-time graph showing the early submission bonus plateau and
 *     its tapering steps, the normal 100% points level, and the late
 *     submission penalty plateau.
 *
 * Hides the early bonus / late penalty fields until their enabling
 * checkboxes are checked, and moves the decay steps input into the
 * bonus settings row.
 *
 * Requires the messages dictionary rendered by the template into a
 * <script type="application/json" id="module-schedule-messages"> element and
 * the chart containers rendered by the template. Without the step hours
 * input the script does nothing (i.e. it is inert on other model edit forms).
 */
(function () {
    'use strict';

    var IDS = {
        enabled: 'id_early_submission_bonus_in_use',
        earlyDeadline: 'id_early_submission_deadline',
        bonus: 'id_early_submission_bonus',
        decaySteps: 'id_bonus_decay_steps',
        opening: 'id_opening_time',
        readingOpening: 'id_reading_opening_time',
        closing: 'id_closing_time',
        lateAllowed: 'id_late_submissions_allowed',
        lateDeadline: 'id_late_submission_deadline',
        latePenalty: 'id_late_submission_penalty',
        readingEnabled: 'id_reading_opening_in_use',
        container: 'module-schedule-charts',
        timeline: 'module-schedule-timeline',
        points: 'module-schedule-points',
        messages: 'module-schedule-messages',
    };

    var HOUR_MS = 60 * 60 * 1000;
    // Shared plot margins so both charts use the identical x scale and the
    // timelines line up with each other.
    var PLOT_LEFT = 44;
    var PLOT_RIGHT = 16;
    // Keep the number of taper steps in the graph manageable.
    var MAX_GRAPH_STEPS = 48;

    var messages = {};

    function getMessages() {
        var el = document.getElementById(IDS.messages);
        if (!el) {
            return {};
        }
        try {
            return JSON.parse(el.textContent) || {};
        } catch (e) {
            return {};
        }
    }

    function rowOf(input) {
        if (!input) {
            return null;
        }
        return input.closest('.form-group, .row.mb-3, .row, .mb-3') || input.parentElement;
    }

    function setRowVisible(input, visible) {
        var row = rowOf(input);
        if (row) {
            row.classList.toggle('d-none', !visible);
        }
    }

    function parseDateTimeLocal(value) {
        if (!value) {
            return null;
        }
        var date = new Date(value);
        return isNaN(date.getTime()) ? null : date;
    }

    function parseFloatOrNull(value) {
        var num = parseFloat(value);
        return isNaN(num) ? null : num;
    }

    function formatNumber(num, maxDecimals) {
        if (!isFinite(num)) {
            return String(num);
        }
        var factor = Math.pow(10, maxDecimals === undefined ? 2 : maxDecimals);
        return String(Math.round(num * factor) / factor);
    }

    // Format dates using the site language (the <html lang> attribute set
    // by Django) rather than the browser locale, e.g. "Ke 4.11. 16:13" in
    // Finnish and "Wed, 4 Nov, 16:13" in English.
    function siteLocale() {
        return document.documentElement.lang || undefined;
    }

    // withYear: include the year in the date part (used for timelines
    // longer than a year).
    function formatDateTime(date, withYear) {
        try {
            var locale = siteLocale() || 'en';
            var weekday = date.toLocaleDateString(locale, { weekday: 'short' });
            weekday = weekday.charAt(0).toUpperCase() + weekday.slice(1);
            var day = date.getDate();
            var dayMonth;
            if (/^fi/i.test(locale)) {
                // Finnish style: "4.11." or "4.11.2026"
                dayMonth = day + '.' + (date.getMonth() + 1) + '.';
                if (withYear) {
                    dayMonth += date.getFullYear();
                }
            } else {
                // English style: "4 Nov" or "4 Nov 2026"
                var month = date.toLocaleDateString(locale, { month: 'short' });
                dayMonth = day + ' ' + month;
                if (withYear) {
                    dayMonth += ' ' + date.getFullYear();
                }
            }
            function p(n) {
                return (n < 10 ? '0' : '') + n;
            }
            var time = p(date.getHours()) + ':' + p(date.getMinutes());
            var sep = /^fi/i.test(locale) ? ' ' : ', ';
            return weekday + sep + dayMonth + sep + time;
        } catch (e) {
            return date.toString();
        }
    }

    function toDateTimeLocal(date) {
        function p(n) {
            return (n < 10 ? '0' : '') + n;
        }
        return date.getFullYear() + '-' + p(date.getMonth() + 1) + '-'
            + p(date.getDate()) + 'T' + p(date.getHours()) + ':' + p(date.getMinutes());
    }

    function clear(node) {
        while (node.firstChild) {
            node.removeChild(node.firstChild);
        }
    }

    function showMessage(container, text, danger) {
        clear(container);
        var p = document.createElement('p');
        p.className = 'small mb-0 ' + (danger ? 'text-danger' : 'text-body-secondary');
        p.textContent = text;
        container.appendChild(p);
    }

    // ------------------------------------------------------------------
    // Field state
    // ------------------------------------------------------------------

    function readState() {
        var enabledInput = document.getElementById(IDS.enabled);
        var lateAllowedInput = document.getElementById(IDS.lateAllowed);
        var readingEnabledInput = document.getElementById(IDS.readingEnabled);
        var decaySteps = parseFloatOrNull(
            (document.getElementById(IDS.decaySteps) || {}).value);
        return {
            enabled: Boolean(enabledInput && enabledInput.checked),
            lateAllowed: Boolean(lateAllowedInput && lateAllowedInput.checked),
            readingEnabled: Boolean(readingEnabledInput && readingEnabledInput.checked),
            reading: parseDateTimeLocal(
                (document.getElementById(IDS.readingOpening) || {}).value),
            opening: parseDateTimeLocal(
                (document.getElementById(IDS.opening) || {}).value),
            early: parseDateTimeLocal(
                (document.getElementById(IDS.earlyDeadline) || {}).value),
            closing: parseDateTimeLocal(
                (document.getElementById(IDS.closing) || {}).value),
            late: parseDateTimeLocal(
                (document.getElementById(IDS.lateDeadline) || {}).value),
            bonus: parseFloatOrNull((document.getElementById(IDS.bonus) || {}).value),
            decaySteps: decaySteps === null ? 0 : decaySteps,
            latePenalty: parseFloatOrNull(
                (document.getElementById(IDS.latePenalty) || {}).value),
        };
    }

    // ------------------------------------------------------------------
    // Shared x scale: both charts use the same domain and pixel range so
    // their timelines line up with each other. Dates that would stretch
    // the axis far beyond the important core dates (a late submission
    // deadline months away, reading material opening long before) are
    // clipped: they are marked at the chart edges instead of squishing
    // the rest of the schedule.
    // ------------------------------------------------------------------

    // Clip an outlier date when it extends more than twice the core span
    // (at least 4 hours) beyond the core dates.
    function clipThreshold(coreSpanMs) {
        return 2 * Math.max(coreSpanMs, 4 * HOUR_MS);
    }

    function computeXDomain(state) {
        var core = [];
        [state.opening, state.enabled ? state.early : null, state.closing]
            .forEach(function (date) {
                if (date) {
                    core.push(date.getTime());
                }
            });
        if (!core.length) {
            return null;
        }
        var coreMin = Math.min.apply(null, core);
        var coreMax = Math.max.apply(null, core);
        var threshold = clipThreshold(coreMax - coreMin);

        var readingClipped = Boolean(state.reading
            && state.reading.getTime() < coreMin - threshold);
        var lateClipped = Boolean(state.late
            && state.late.getTime() > coreMax + threshold);

        var times = core.slice();
        if (state.reading && !readingClipped) {
            times.push(state.reading.getTime());
        }
        if (state.late && !lateClipped) {
            times.push(state.late.getTime());
        }
        var now = Date.now();
        if (now >= coreMin - threshold && now <= coreMax + threshold) {
            times.push(now);
        }
        var minT = Math.min.apply(null, times);
        var maxT = Math.max.apply(null, times);
        var span = Math.max(maxT - minT, 60 * 1000);
        minT -= span * 0.04;
        maxT += span * 0.04;
        return {
            domain: [new Date(minT), new Date(maxT)],
            readingClipped: readingClipped,
            lateClipped: lateClipped,
        };
    }

    // ------------------------------------------------------------------
    // Chart 1: general timeline of the main dates
    // ------------------------------------------------------------------

    function renderTimelineChart(state, x, clipped, withYear) {
        var container = document.getElementById(IDS.timeline);
        if (!container) {
            return;
        }
        clear(container);

        var events = [];
        if (state.readingEnabled && state.reading) {
            events.push({ date: state.reading, label: messages.readingLabel,
                field: IDS.readingOpening, clipped: clipped.readingClipped });
        }
        if (state.opening) {
            events.push({ date: state.opening, label: messages.openingLabel,
                field: IDS.opening });
        }
        if (state.enabled && state.early) {
            events.push({ date: state.early, label: messages.earlyLabel,
                field: IDS.earlyDeadline });
        }
        if (state.closing) {
            events.push({ date: state.closing, label: messages.closingLabel,
                field: IDS.closing });
        }
        if (state.lateAllowed && state.late) {
            events.push({ date: state.late, label: messages.lateLabel,
                field: IDS.lateDeadline, clipped: clipped.lateClipped });
        }
        if (!events.length) {
            showMessage(container, messages.invalid);
            return;
        }

        var width = Math.max(container.clientWidth || 0, 320);
        var height = 92;
        var padX = PLOT_LEFT;
        var now = new Date();

        // Event markers. Labels alternate above and below the axis, and
        // within each row labels that would overlap are staggered onto
        // further rows. The level search is capped so that pathological
        // inputs (e.g. many labels clamped to the same position) cannot
        // loop forever.
        var MAX_LABEL_ROWS = 4;
        var rows = { above: [], below: [] };
        events.forEach(function (event, idx) {
            var above = idx % 2 === 0;
            var halfWidth = Math.max(event.label.length, 16) * 5.5 / 2 + 4;
            var lx = Math.min(Math.max(x(event.date), padX + halfWidth),
                width - padX - halfWidth);
            var row = rows[above ? 'above' : 'below'];
            var level = 0;
            while (level < MAX_LABEL_ROWS && row.some(function (placed) {
                return Math.abs(placed.lx - lx) < (placed.halfWidth + halfWidth);
            })) {
                level++;
            }
            row.push({ lx: lx, halfWidth: halfWidth, level: level });
            event._lx = lx;
            event._halfWidth = halfWidth;
            event._above = above;
            event._level = level;
        });
        // Grow the SVG so that staggered label rows fit.
        var maxAbove = 0;
        var maxBelow = 0;
        events.forEach(function (event) {
            if (event._above) {
                maxAbove = Math.max(maxAbove, event._level);
            } else {
                maxBelow = Math.max(maxBelow, event._level);
            }
        });
        var axisY = Math.max(height / 2, 34 + maxAbove * 24 + 12);
        height = axisY + 26 + (maxBelow + 1) * 24 + 4;

        var svg = d3.select(container).append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('role', 'img')
            .attr('aria-label', messages.timelineTitle);

        // Axis line.
        svg.append('line')
            .attr('x1', padX).attr('x2', width - padX)
            .attr('y1', axisY).attr('y2', axisY)
            .attr('stroke', 'var(--bs-border-color)')
            .attr('stroke-width', 2);

        // "Now" marker, spanning the full chart height.
        svg.append('line')
            .attr('x1', x(now)).attr('x2', x(now))
            .attr('y1', 0).attr('y2', height)
            .attr('stroke', 'var(--bs-danger)')
            .attr('stroke-dasharray', '4,3')
            .attr('stroke-width', 1.5);
        svg.append('text')
            .attr('x', x(now)).attr('y', 10)
            .attr('text-anchor', 'middle')
            .attr('font-size', 10)
            .attr('fill', 'var(--bs-danger)')
            .text(messages.now);

        events.forEach(function (event) {
            var ex = x(event.date);
            var above = event._above;
            var level = event._level;
            var labelY = above
                ? axisY - 22 - level * 24
                : axisY + 26 + level * 24;
            if (event.clipped) {
                // The date is far outside the visible range: draw a
                // continuation marker at the chart edge instead of the
                // actual position.
                var atStart = event.date.getTime() < x.domain()[0].getTime();
                ex = atStart ? padX : width - padX;
                svg.append('text')
                    .attr('x', ex + (atStart ? 4 : -4))
                    .attr('y', axisY + (above ? -6 : 14))
                    .attr('text-anchor', atStart ? 'start' : 'end')
                    .attr('font-size', 12)
                    .attr('fill', 'var(--bs-link-hover-color)')
                    .text(atStart ? '\u00AB' : '\u00BB');
                var clippedText = svg.append('text')
                    .attr('x', ex + (atStart ? 4 : -4))
                    .attr('y', axisY + (above ? -6 : 14))
                    .attr('text-anchor', atStart ? 'start' : 'end')
                    .attr('font-size', 10)
                    .attr('fill', 'var(--bs-body-color)');
                clippedText.append('tspan')
                    .attr('x', ex + (atStart ? 4 : -4))
                    .attr('dy', above ? -14 : 26)
                    .text(event.label + ' \u00AB' + formatDateTime(event.date, withYear) + '\u00BB');
                return;
            }
            svg.append('line')
                .attr('x1', ex).attr('x2', ex)
                .attr('y1', above ? axisY - 8 : axisY + 4)
                .attr('y2', above ? axisY - 4 : axisY + 8)
                .attr('stroke', 'var(--bs-link-hover-color)');
            var tick = svg.select('line:last-of-type');
            var marker = svg.append('circle')
                .attr('cx', ex).attr('cy', axisY)
                .attr('r', 5)
                .attr('fill', 'var(--bs-link-hover-color)');
            var text = svg.append('text')
                .attr('x', event._lx)
                .attr('y', labelY)
                .attr('text-anchor', 'middle')
                .attr('font-size', 10)
                .attr('fill', 'var(--bs-body-color)');
            text.append('tspan')
                .attr('x', event._lx)
                .attr('dy', 0)
                .text(event.label);
            text.append('tspan')
                .attr('x', event._lx)
                .attr('dy', 11)
                .attr('fill', 'var(--bs-secondary-color)')
                .text(formatDateTime(event.date, withYear));

            if (!event.field) {
                return;
            }
            // Draggable marker: dragging snaps to full hours and updates the
            // corresponding datetime input (horizontal only). While dragging,
            // only the marker and its timestamp label move; the charts are
            // re-rendered on drag end (re-rendering during the drag would
            // destroy the node being dragged).
            var input = document.getElementById(event.field);
            if (!input || input.disabled || input.readOnly) {
                return;
            }
            marker.attr('cursor', 'ew-resize');
            var timeLabel = text.select('tspan:last-of-type');
            var drag = d3.drag()
                .on('start', function () {
                    marker.raise().attr('r', 7);
                })
                .on('drag', function () {
                    // d3 v4: the current pointer position is in d3.event.
                    var t = x.invert(d3.event.x);
                    t.setMinutes(0, 0, 0);
                    input.value = toDateTimeLocal(t);
                    timeLabel.text(formatDateTime(t, withYear));
                    marker.attr('cx', x(t));
                    tick.attr('x1', x(t)).attr('x2', x(t));
                })
                .on('end', function () {
                    marker.attr('r', 5);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                });
            marker.call(drag);
        });
    }

    // ------------------------------------------------------------------
    // Chart 2: points over time
    // ------------------------------------------------------------------

    // Mirrors CourseModule.get_early_submission_bonus_tier/taper_steps.
    // Returns a step-function: each point is the level held from its time
    // until the next point's time.
    function buildBonusPoints(state, bonusPct) {
        var points = [];
        var early = state.early;
        var closing = state.closing;

        var windowMs = closing.getTime() - early.getTime();
        var fullSteps = Math.floor(state.decaySteps);
        if (fullSteps <= 0) {
            // Linear decay from the full bonus at the early deadline to no
            // bonus at the module deadline.
            points.push({ t: early.getTime(), v: 100 + bonusPct });
            points.push({ t: closing.getTime(), v: 100 });
            return points;
        }

        if (fullSteps > MAX_GRAPH_STEPS) {
            // Too many steps to draw individually: sample the ramp.
            var samples = MAX_GRAPH_STEPS;
            for (var i = 0; i <= samples; i++) {
                var frac = i / samples;
                points.push({
                    t: early.getTime() + frac * windowMs,
                    v: 100 + bonusPct * (1 - frac),
                });
            }
            return points;
        }

        // Staircase: the full bonus holds from the opening time until the
        // early deadline; the bonus then drops in equal steps so that it
        // reaches zero exactly at the module deadline.
        points.push({ t: early.getTime(), v: 100 + bonusPct });
        var prevT = early.getTime();
        var stepMs = windowMs / fullSteps;
        for (var step = 0; step < fullSteps; step++) {
            var fraction = (fullSteps - step - 1) / fullSteps;
            var stepEnd = early.getTime() + (step + 1) * stepMs;
            points.push({ t: prevT, v: 100 + bonusPct * fraction });
            points.push({ t: stepEnd, v: 100 + bonusPct * fraction });
            prevT = stepEnd;
        }
        return points;
    }

    // ------------------------------------------------------------------
    // Validation: mirrors CourseModule.clean() so the teacher sees the
    // same errors client-side that the server would raise on submit.
    // Returns a list of { field, message } for the invalid fields.
    // ------------------------------------------------------------------

    function validateOrder(state) {
        var errors = [];
        if (!state.opening || !state.closing) {
            return errors;
        }
        if (state.opening.getTime() > state.closing.getTime()) {
            errors.push({ field: IDS.opening, message: messages.errors.opening_time });
        }
        if (state.enabled && state.early) {
            if (state.early.getTime() <= state.opening.getTime()) {
                errors.push({
                    field: IDS.earlyDeadline,
                    message: messages.errors.early_submission_deadline[0],
                });
            } else if (state.early.getTime() >= state.closing.getTime()) {
                errors.push({
                    field: IDS.earlyDeadline,
                    message: messages.errors.early_submission_deadline[1],
                });
            }
        }
        if (state.lateAllowed && state.late
                && state.late.getTime() <= state.closing.getTime()) {
            errors.push({
                field: IDS.lateDeadline,
                message: messages.errors.late_submission_deadline,
            });
        }
        if (state.readingEnabled && state.reading
                && state.reading.getTime() > state.opening.getTime()) {
            errors.push({
                field: IDS.readingOpening,
                message: messages.errors.reading_opening_time,
            });
        }
        return errors;
    }

    // Mark the invalid inputs with the Bootstrap "is-invalid" class and
    // show the error message under each field.
    function applyValidationErrors(errors) {
        var fields = [
            IDS.readingOpening, IDS.opening, IDS.earlyDeadline,
            IDS.closing, IDS.lateDeadline,
        ];
        fields.forEach(function (id) {
            var input = document.getElementById(id);
            if (!input) {
                return;
            }
            var error = errors.find(function (e) { return e.field === id; });
            input.classList.toggle('is-invalid', Boolean(error));
            var row = rowOf(input);
            var old = row ? row.querySelector('.module-schedule-error') : null;
            if (old) {
                old.remove();
            }
            if (error && row) {
                var feedback = document.createElement('div');
                feedback.className = 'module-schedule-error invalid-feedback d-block';
                feedback.textContent = error.message;
                row.appendChild(feedback);
            }
        });
    }

    function renderPointsChart(state, x, clipped, withYear) {
        var container = document.getElementById(IDS.points);
        if (!container) {
            return;
        }
        clear(container);

        if (!state.opening || !state.closing
                || state.closing.getTime() <= state.opening.getTime()) {
            showMessage(container, messages.invalid);
            return;
        }

        var bonusActive = state.enabled && state.bonus !== null && state.bonus > 0
            && state.early && state.early.getTime() > state.opening.getTime()
            && state.early.getTime() < state.closing.getTime();
        var bonusPct = bonusActive ? state.bonus * 100 : 0;

        var lateActive = state.lateAllowed && state.late
            && state.late.getTime() > state.closing.getTime()
            && state.latePenalty !== null && state.latePenalty >= 0;
        var lateLevel = lateActive ? Math.max(0, 100 * (1 - state.latePenalty)) : 0;

        var xStart = state.opening.getTime();
        var xEnd = lateActive ? state.late.getTime() : state.closing.getTime();
        // When the late deadline is clipped, the plateau is truncated at the
        // chart edge and marked as continuing beyond it.
        var lateClipped = clipped.lateClipped;
        if (lateClipped) {
            xEnd = x.domain()[1].getTime();
        }

        var series = [];
        var peak = 100;
        if (bonusActive) {
            series.push({ t: xStart, v: 100 + bonusPct });
            series = series.concat(buildBonusPoints(state, bonusPct));
            peak = 100 + bonusPct;
        } else {
            series.push({ t: xStart, v: 100 });
            series.push({ t: state.closing.getTime(), v: 100 });
        }
        if (lateActive) {
            series.push({ t: state.closing.getTime(), v: 100 });
            if (lateLevel < 100) {
                // The penalty reduces the points during the late period.
                series.push({ t: state.closing.getTime(), v: lateLevel });
                series.push({ t: xEnd, v: lateLevel });
                if (!lateClipped) {
                    // No points are awarded after the late submission deadline.
                    series.push({ t: xEnd, v: 0 });
                }
            } else {
                // Zero penalty: full points until the late deadline.
                series.push({ t: xEnd, v: 100 });
                if (!lateClipped) {
                    series.push({ t: xEnd, v: 0 });
                }
            }
        }

        var warnings = validateOrder(state);

        var width = Math.max(container.clientWidth || 0, 320);
        var height = 172;
        var margin = { top: 14, right: PLOT_RIGHT, bottom: 26, left: PLOT_LEFT };

        var yMax = Math.max(100, Math.ceil(peak / 25) * 25);
        var y = d3.scaleLinear()
            .domain([0, yMax])
            .range([height - margin.bottom, margin.top]);

        var svg = d3.select(container).append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('role', 'img')
            .attr('aria-label', messages.pointsTitle);

        // Horizontal gridlines and the 100% reference line.
        var gridValues = [];
        for (var gv = 0; gv <= yMax; gv += 25) {
            gridValues.push(gv);
        }
        svg.selectAll('line.grid').data(gridValues).enter().append('line')
            .attr('class', 'grid')
            .attr('x1', margin.left).attr('x2', width - margin.right)
            .attr('y1', function (d) { return y(d); })
            .attr('y2', function (d) { return y(d); })
            .attr('stroke', function (d) {
                return d === 100 ? 'var(--bs-body-color)' : 'var(--bs-border-color)';
            })
            .attr('stroke-dasharray', function (d) { return d === 100 ? 'none' : '3,3'; })
            .attr('stroke-width', function (d) { return d === 100 ? 1 : 0.75; })
            .attr('opacity', function (d) { return d === 100 ? 0.5 : 1; });

        // Area under the curve and the curve itself.
        var area = d3.area()
            .x(function (d) { return x(d.t); })
            .y0(y(0))
            .y1(function (d) { return y(d.v); });
        var line = d3.line()
            .x(function (d) { return x(d.t); })
            .y(function (d) { return y(d.v); });

        svg.append('path')
            .datum(series)
            .attr('d', area)
            .attr('fill', 'var(--bs-link-hover-color)')
            .attr('opacity', 0.15);
        svg.append('path')
            .datum(series)
            .attr('d', line)
            .attr('fill', 'none')
            .attr('stroke', 'var(--bs-link-hover-color)')
            .attr('stroke-width', 2);

        // Annotations: bonus peak and late plateau level.
        if (bonusActive) {
            svg.append('text')
                .attr('x', Math.min(x(state.early.getTime()) + 5,
                    width - margin.right - 40))
                .attr('y', y(100 + bonusPct) - 5)
                .attr('font-size', 10)
                .attr('fill', 'var(--bs-link-hover-color)')
                .text('+' + formatNumber(bonusPct, 1) + '%');
        }
        if (lateActive) {
            svg.append('text')
                .attr('x', width - margin.right - 4)
                .attr('y', y(lateLevel) - 5)
                .attr('text-anchor', 'end')
                .attr('font-size', 10)
                .attr('fill', 'var(--bs-secondary-color)')
                .text(formatNumber(lateLevel, 1) + '%');
            if (lateClipped) {
                // The plateau continues beyond the visible range.
                svg.append('text')
                    .attr('x', width - margin.right - 4)
                    .attr('y', y(lateLevel) + 14)
                    .attr('text-anchor', 'end')
                    .attr('font-size', 12)
                    .attr('fill', 'var(--bs-link-hover-color)')
                    .text('\u00BB');
            }
        }

        // Axes. d3's default axis styling uses near-black fills; override
        // with theme variables so the axes stay visible in dark mode.
        var axisColor = 'var(--bs-secondary-color)';
        var axisLine = 'var(--bs-border-color)';
        svg.append('g')
            .attr('transform', 'translate(0,' + (height - margin.bottom) + ')')
            .call(d3.axisBottom(x).ticks(6).tickFormat(function (d) {
                return formatDateTime(d, withYear);
            }))
            .call(function (g) {
                g.selectAll('text').attr('font-size', 10).attr('fill', axisColor);
                g.selectAll('line, path').attr('stroke', axisLine);
            });
        svg.append('g')
            .attr('transform', 'translate(' + margin.left + ',0)')
            .call(d3.axisLeft(y).tickValues(gridValues).tickFormat(function (d) {
                return d + '%';
            }))
            .call(function (g) {
                g.selectAll('text').attr('font-size', 10).attr('fill', axisColor);
                g.selectAll('line, path').attr('stroke', axisLine);
            });

        if (warnings.length) {
            var p = document.createElement('p');
            p.className = 'small text-danger mb-0 mt-1';
            p.textContent = warnings.map(function (e) { return e.message; }).join(' ');
            container.appendChild(p);
        }
    }

    // ------------------------------------------------------------------
    // Decay steps input: moved into the "Decay in N steps" radio label.
    // ------------------------------------------------------------------

    // ------------------------------------------------------------------
    // Decay steps input: rebuilt as an inline sentence
    // "After the early deadline, bonus drops to zero in [N] steps."
    // using translated fragments around the input.
    // ------------------------------------------------------------------

    function installDecayStepsSentence() {
        var input = document.getElementById(IDS.decaySteps);
        if (!input) {
            return;
        }
        var row = rowOf(input);
        if (!row) {
            return;
        }
        // Remove the field's own label and help text; the custom structure
        // below replaces them.
        var label = row.querySelector('label');
        if (label) {
            label.remove();
        }
        var help = row.querySelector('.form-text');
        if (help) {
            help.remove();
        }
        input.classList.add('form-control');
        input.style.minWidth = '4.5rem';
        input.removeAttribute('required');

        // Label above the input group.
        var labelEl = document.createElement('label');
        labelEl.className = 'form-label';
        labelEl.setAttribute('for', input.id);
        labelEl.textContent = messages.decayLabel || '';

        // Input group: prefix text, input, suffix text.
        var group = document.createElement('div');
        group.className = 'input-group input-group-sm';
        var prefix = document.createElement('span');
        prefix.className = 'input-group-text';
        prefix.textContent = messages.decayPrefix || '';
        var suffix = document.createElement('span');
        suffix.className = 'input-group-text';
        suffix.textContent = messages.decaySuffix || '';
        group.appendChild(prefix);
        group.appendChild(input);
        group.appendChild(suffix);

        // Help text below, preserving the line break.
        var helpEl = document.createElement('div');
        helpEl.className = 'form-text';
        helpEl.textContent = messages.decayHelp || '';
        helpEl.style.whiteSpace = 'pre-line';

        var col = input.closest('.col') || row;
        col.appendChild(labelEl);
        col.appendChild(group);
        col.appendChild(helpEl);
    }

    // ------------------------------------------------------------------
    // Copy schedule from another module: fills the schedule fields from
    // the selected module's serialized schedule.
    // ------------------------------------------------------------------

    var COPY_FIELDS = [
        'readingOpening', 'opening', 'earlyDeadline', 'closing', 'late',
    ];

    function installCopyControl() {
        var dataEl = document.getElementById('module-schedule-copy-data');
        var select = document.getElementById('module-copy-source');
        var row = document.getElementById('module-schedule-copy');
        var apply = document.getElementById('module-copy-apply');
        if (!dataEl || !select || !row || !apply) {
            return;
        }
        var schedules;
        try {
            schedules = JSON.parse(dataEl.textContent) || [];
        } catch (e) {
            schedules = [];
        }
        if (!schedules.length) {
            return;
        }
        schedules.forEach(function (schedule) {
            var option = document.createElement('option');
            option.value = String(schedule.id);
            option.textContent = schedule.name;
            select.appendChild(option);
        });
        row.hidden = false;
        apply.addEventListener('click', function () {
            var schedule = schedules.find(
                function (s) { return String(s.id) === select.value; });
            if (!schedule) {
                return;
            }
            var fields = {
                readingOpening: schedule.reading_opening_time,
                opening: schedule.opening_time,
                earlyDeadline: schedule.early_submission_deadline,
                closing: schedule.closing_time,
                late: schedule.late_submission_deadline,
            };
            COPY_FIELDS.forEach(function (key) {
                var input = document.getElementById(IDS[key]);
                if (!input) {
                    return;
                }
                var value = fields[key];
                if (value) {
                    input.value = value.slice(0, 16);
                }
            });
            var bonusEnabled = document.getElementById(IDS.enabled);
            var lateAllowed = document.getElementById(IDS.lateAllowed);
            var readingEnabled = document.getElementById(IDS.readingEnabled);
            if (bonusEnabled) {
                bonusEnabled.checked = Boolean(schedule.early_submission_bonus_in_use);
            }
            if (lateAllowed) {
                lateAllowed.checked = Boolean(schedule.late_submissions_allowed);
            }
            if (readingEnabled) {
                readingEnabled.checked = Boolean(schedule.reading_opening_time);
            }
            var bonus = document.getElementById(IDS.bonus);
            if (bonus) {
                bonus.value = String(schedule.early_submission_bonus);
            }
            var steps = document.getElementById(IDS.decaySteps);
            if (steps) {
                steps.value = String(schedule.bonus_decay_steps);
            }
            var penalty = document.getElementById(IDS.latePenalty);
            if (penalty) {
                penalty.value = String(schedule.late_submission_penalty);
            }
            renderAll();
        });
    }

    // ------------------------------------------------------------------
    // Orchestration
    // ------------------------------------------------------------------

    // Find the common row that contains both the given input and the
    // given checkbox, if any (fields sharing a row with their enabling
    // checkbox are hidden per column instead of per row).
    function rowSharing(input, checkbox) {
        var el = input.parentElement;
        while (el && el !== document.body) {
            if (el.contains(checkbox)) {
                return el;
            }
            el = el.parentElement;
        }
        return null;
    }

    function applyVisibility(state) {
        // Fields sharing a row with their enabling checkbox (the bonus and
        // late penalty groups) are hidden per column; standalone rows
        // (the reading opening time) are hidden as whole rows.
        document.querySelectorAll('[data-early-bonus-dependent]').forEach(function (input) {
            if (input.id === IDS.enabled) {
                return;
            }
            var sharedRow = rowSharing(input, document.getElementById(IDS.enabled));
            if (sharedRow) {
                var col = input.closest('.col');
                if (col) {
                    col.classList.toggle('d-none', !state.enabled);
                }
            } else {
                setRowVisible(input, state.enabled);
            }
        });
        document.querySelectorAll('[data-late-penalty-dependent]').forEach(function (input) {
            var sharedRow = rowSharing(input, document.getElementById(IDS.lateAllowed));
            if (sharedRow) {
                var col = input.closest('.col');
                if (col) {
                    col.classList.toggle('d-none', !state.lateAllowed);
                }
            } else {
                setRowVisible(input, state.lateAllowed);
            }
        });
        document.querySelectorAll('[data-reading-opening-dependent]').forEach(function (input) {
            setRowVisible(input, state.readingEnabled);
        });
        // The decay steps input lives inside its own label and is hidden
        // while the bonus is disabled.
        var stepsInput = document.getElementById(IDS.decaySteps);
        if (stepsInput) {
            stepsInput.disabled = !state.enabled;
            stepsInput.classList.toggle('d-none', !state.enabled);
        }
    }

    function renderAll() {
        var container = document.getElementById(IDS.container);
        if (!container) {
            return;
        }
        var state = readState();
        applyVisibility(state);
        var anyDates = Boolean(state.opening || state.closing);
        container.hidden = !anyDates;
        var shiftRow = document.getElementById('module-schedule-shift');
        if (shiftRow) {
            shiftRow.hidden = !anyDates;
        }
        var copyRow = document.getElementById('module-schedule-copy');
        if (copyRow) {
            copyRow.hidden = !anyDates;
        }
        if (!anyDates) {
            return;
        }
        var clipInfo = computeXDomain(state);
        if (!clipInfo) {
            return;
        }
        var width = Math.max(
            (document.getElementById(IDS.timeline) || {}).clientWidth || 0, 320);
        var x = d3.scaleTime()
            .domain(clipInfo.domain)
            .range([PLOT_LEFT, width - PLOT_RIGHT]);
        // Show years in the dates only when the timeline spans more than
        // a year.
        var withYear = clipInfo.domain[1].getTime()
            - clipInfo.domain[0].getTime() > 365 * 24 * HOUR_MS;
        renderTimelineChart(state, x, clipInfo, withYear);
        renderPointsChart(state, x, clipInfo, withYear);
        applyValidationErrors(validateOrder(state));
    }

    // ------------------------------------------------------------------
    // Shift buttons: move all displayed dates by one hour or one day.
    // ------------------------------------------------------------------

    function shiftDates(deltaMs) {
        var fields = [
            IDS.readingOpening, IDS.opening, IDS.earlyDeadline,
            IDS.closing, IDS.lateDeadline,
        ];
        fields.forEach(function (id) {
            var input = document.getElementById(id);
            if (!input || !input.value) {
                return;
            }
            var date = parseDateTimeLocal(input.value);
            if (!date) {
                return;
            }
            date.setTime(date.getTime() + deltaMs);
            input.value = toDateTimeLocal(date);
        });
    }

    function bindShiftButton(buttonId, deltaMs) {
        var button = document.getElementById(buttonId);
        if (!button) {
            return;
        }
        button.addEventListener('click', function () {
            shiftDates(deltaMs);
            renderAll();
        });
    }

    // Set the time part of all dates to the selected time, keeping each
    // field's date unchanged.
    function bindResetControl() {
        var apply = document.getElementById('module-reset-apply');
        var input = document.getElementById('module-reset-time');
        if (!apply || !input) {
            return;
        }
        apply.addEventListener('click', function () {
            var match = /^(\d{1,2}):(\d{2})$/.exec(input.value);
            if (!match) {
                return;
            }
            var hours = parseInt(match[1], 10);
            var minutes = parseInt(match[2], 10);
            [IDS.readingOpening, IDS.opening, IDS.earlyDeadline,
                IDS.closing, IDS.lateDeadline].forEach(function (id) {
                var field = document.getElementById(id);
                if (!field || !field.value) {
                    return;
                }
                if (id === IDS.readingOpening) {
                    var readingEnabled = document.getElementById(IDS.readingEnabled);
                    if (!readingEnabled || !readingEnabled.checked) {
                        return;
                    }
                }
                var date = parseDateTimeLocal(field.value);
                if (!date) {
                    return;
                }
                date.setHours(hours, minutes, 0, 0);
                field.value = toDateTimeLocal(date);
            });
            renderAll();
        });
    }

    function init() {
        var decayStepsInput = document.getElementById(IDS.decaySteps);
        if (!decayStepsInput) {
            return; // not the module edit form
        }
        messages = getMessages();
        installDecayStepsSentence();
        installCopyControl();

        // Move the charts panel from the scripts block (rendered in <head>)
        // into the schedule fieldset, right below its legend. The copy
        // row (also from the scripts block) is placed just above it.
        var container = document.getElementById(IDS.container);
        var closingInput = document.getElementById(IDS.closing);
        var copyRow = document.getElementById('module-schedule-copy');
        if (container && closingInput) {
            var fieldset = closingInput.closest('fieldset');
            if (fieldset) {
                var legend = fieldset.querySelector('legend');
                if (legend) {
                    legend.parentNode.insertBefore(container, legend.nextSibling);
                    if (copyRow) {
                        legend.parentNode.insertBefore(copyRow, container);
                    }
                } else {
                    fieldset.insertBefore(container, fieldset.firstChild);
                    if (copyRow) {
                        fieldset.insertBefore(copyRow, container);
                    }
                }
            }
        }

        var watched = [
            IDS.enabled, IDS.lateAllowed, IDS.readingEnabled, IDS.earlyDeadline,
            IDS.bonus, IDS.decaySteps, IDS.opening, IDS.readingOpening, IDS.closing,
            IDS.lateDeadline, IDS.latePenalty,
        ];
        watched.forEach(function (id) {
            var input = document.getElementById(id);
            if (input) {
                input.addEventListener('change', renderAll);
                input.addEventListener('input', renderAll);
            }
        });

        var resizeTimer = null;
        window.addEventListener('resize', function () {
            if (resizeTimer) {
                clearTimeout(resizeTimer);
            }
            resizeTimer = setTimeout(renderAll, 150);
        });

        bindShiftButton('module-shift-hour-back', -HOUR_MS);
        bindShiftButton('module-shift-hour-forward', HOUR_MS);
        bindShiftButton('module-shift-day-back', -24 * HOUR_MS);
        bindShiftButton('module-shift-day-forward', 24 * HOUR_MS);
        bindShiftButton('module-shift-week-back', -7 * 24 * HOUR_MS);
        bindShiftButton('module-shift-week-forward', 7 * 24 * HOUR_MS);
        bindResetControl();

        renderAll();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
