var summaryjs = function ($element, model) {
  var defaults = {
    height: 200,
    maxBandWidth: 50,
    bandPadding: 0.2,
    histogramBands: 25,
    ticksY: 4,
    margin: {
      top: 10,
      left: 40,
      right: 30,
      bottom: 30,
    },
  };
  model = $.extend({}, defaults, model);
  var draw = d3draw(model);
  var help = helpers();

  loadArray(model.fields, onFormFields);
  return {
    model: model,
    redraw: redraw,
  };

  function onFormFields(error) {
    if (error) console.log(error);
    loadArray(model.posts, onFormPosts);
  }

  function onFormPosts(error) {
    if (error) console.log(error);
    redraw();
  }

  function redraw() {
    $element.filter('.summaryjs-display').remove();
    $element.append(display(
      model,
      model.width || $element.width(),
      model.height)
    );
  }

  /* summaryjs_display: */

  function display(model, width, height) {
    var $display = $('<div class="summaryjs-display"></div>');
    var fields = model.fields.data;
    for (var i = 0; i < fields.length; i++) {
      if (fields[i].type != 'static') {
        $display.append(displayField(fields[i], width, height));
      }
    }

    return $display;

    function displayField(field, width, height) {
      var $display = $('<div class="summaryjs-field-display"></div>');

      var vals = model.posts.data
        .map(help.pick(field.key))
        .filter(help.isNonEmpty);
      $display.append(
        '<p>' +
          '(N=' + vals.length + ') ' +
          (field.title || field.key) +
        '</p>'
      );

      if (help.isIn(field.type, ['number'])) {
        field.display = draw.histogram($display[0], width, height, vals);
      } else if (help.isIn(field.type, ['radio', 'dropdown', 'checkbox'])) {
        field.options = optionsArray(field);
        field.display = draw.bars($display[0], width, height, vals, field.options);
      } else if (help.isIn(field.type, ['text', 'textarea'])) {
        field.display = draw.texts($display[0], width, height, vals);
      }

      return $display;
    }

    function optionsArray(field) {
      var opts = [].concat(field.enum) || [];
      var titles = field.titleMap || {};
      return opts.map(function (key) {
        return { key: key, title: titles[key] || key };
      });
    }
  }

  /* summaryjs_d3draw */

  function d3draw(model) {
    return {

      histogram: function (element, outWidth, outHeight, vals) {
        return init(element, outWidth, outHeight, update, vals);

        function update(vals) {
          vals = vals.map(help.toNumber).filter(help.isNotNaN);
          var min = d3.min(vals), max = d3.max(vals), d = max - min;
          var bins = d3.histogram()
            .domain([d > 0 ? min : (min - 0.5), d > 0 ? max : (max + 0.5)])
            .thresholds(model.histogramBands)
            (vals);
          var width = inWidth(outWidth, bins.length);
          var height = inHeight(outHeight);

          var x = d3.scaleLinear().range([0, width]).domain([
            d3.min(bins, help.pick('x0')),
            d3.max(bins, help.pick('x1')),
          ]).nice();
          var y = d3.scaleLinear().range([height, 0]).domain([
            0,
            d3.max(bins, help.pick('length')),
          ]);

          var g = selectPlotWithAxis(element, x, y, bins.length, height);
          g.selectAll('.d3-bin')
            .data(bins)
          .enter()
            .append('rect')
            .attr('class', 'd3-bin')
            .attr('shape-rendering', 'crispEdges')
            .attr('x', function (d) { return x(d.x0) })
            .attr('y', function (d) { return y(d.length) })
            .attr('width', function (d) { return x(d.x1) - x(d.x0); })
            .attr('height', function (d) { return height - y(d.length); })
          .exit()
            .remove();
        }
      },

      bars: function (element, outWidth, outHeight, vals, opts) {
        return init(element, outWidth, outHeight, update, vals);

        function update(vals) {
          var counts = help.countEach(help.splitEach(vals, '|'));
          var width = inWidth(outWidth, opts.length);
          var height = inHeight(outHeight);

          var x = d3.scaleBand().range([0, width])
            .padding(model.bandPadding)
            .domain(opts.map(help.pick('title')));
          var y = d3.scaleLinear().range([height, 0]).domain([
            0,
            d3.max(help.values(counts)),
          ]);

          var g = selectPlotWithAxis(element, x, y, opts.length, height);
          g.selectAll('.d3-bar')
            .data(opts)
          .enter()
            .append('rect')
            .attr('class', 'd3-bar')
            .attr('shape-rendering', 'crispEdges')
            .attr('x', function (d) { return x(d.title); })
            .attr('y', function (d) { return y(counts[d.key] || 0); })
            .attr('width', x.bandwidth())
            .attr('height', function (d) { return height - y(counts[d.key] || 0); })
          .exit()
            .remove();
        }
      },

      texts: function (element, outWidth, outHeight, vals) {
        update(vals);
        return { update: update };

        function update(vals) {
          var $e = $(element).find('.text-values');
          if ($e.length === 0) {
            $e = $('<div class="text-values text-values-minimized"></div>');
            $e.append(
              $('<a class="handle" href="#"><span class="glyphicon glyphicon-option-horizontal"></span></a>')
                .on('click', onHandleClick)
            );
            $(element).append($e);
          } else {
            $e.empty();
          }

          var texts = [];
          var counts = {};
          for (var i = 0; i < vals.length; i++) {
            var t = vals[i];
            var n = (counts[t] || 0) + 1;
            counts[t] = n;
            if (n === 1) {
              texts.push(t);
            }
          }

          for (i = 0; i < texts.length; i++) {
            var t = texts[i];
            var n = counts[t];
            var $t = $('<pre></pre>');
            $t.text(t);
            if (n > 1) {
              $t.append('<span class="count">x ' + n + '</span>');
            }
            $e.append($t);
          }
        }

        function onHandleClick(event) {
          event.preventDefault();
          $(this).parent().toggleClass('text-values-minimized');
        }
      },

    };

    function inWidth(outWidth, bandCount) {
      return Math.min(
        outWidth - model.margin.left - model.margin.right,
        bandCount ? bandCount * model.maxBandWidth : outWidth,
      );
    }

    function inHeight(outHeight) {
      return outHeight - model.margin.top - model.margin.bottom;
    }

      function init(element, width, height, update, vals) {
      var svg = d3.select(element).append('svg')
        .attr('class', 'd3')
        .attr('width', width)
        .attr('height', height);
      svg.append('g')
        .attr('class', 'd3-plot')
        .attr('transform', 'translate(' + model.margin.left + ',' + model.margin.top + ')');
      update(vals);
      return {
        update: update,
      };
    }

    function selectPlotWithAxis(element, x, y, bandCount, height) {
      var g = d3.select(element).selectAll('.d3-plot');
      var d = x.domain();
      g.append('g')
        .attr('transform', 'translate(0,' + height + ')')
        .call(d3.axisBottom(x).ticks(bandCount));
      g.append('g')
        .call(d3.axisLeft(y).ticks(model.ticksY));
      return g;
    }
  }

  /* summaryjs_helpers */

  function helpers() {
    return {

      isNonEmpty: function (val) {
        return val && (val.trim === undefined || val.trim() !== '');
      },

      toNumber: function (val) {
        return parseFloat(val);
      },

      isNotNaN: function (val) {
        return !isNaN(val);
      },

      isIn: function (value, list) {
        return list.indexOf(value) >= 0;
      },

      pick: function (key) {
        return function (obj) {
          return obj[key];
        };
      },

      values: function (obj) {
        var vals = [];
        for (var key in obj) {
          vals.push(obj[key]);
        }
        return vals;
      },

      splitEach: function (list, sep) {
        var vals = [];
        for (var i = 0; i < list.length; i++) {
          vals = vals.concat(list[i].split(sep));
        }
        return vals;
      },

      countEach: function (vals) {
        var counts = {};
        for (var i = 0; i < vals.length; i++) {
          counts[vals[i]] = (counts[vals[i]] || 0) + 1;
        }
        return counts;
      },

    };
  }

  /* summaryjs_load: */

  function loadArray(model, callback) {
    model.data = [];

    if (model.url) {
      $.getJSON(model.url).fail(onJsonError).done(onJsonLoad);
    } else {
      onArray();
    }

    function onJsonError() {
      callback('Failed to request data');
    }

    function onJsonLoad(data) {
      if (model.navigate) {
        var parts = model.navigate.split('.');
        for (var i = 0; i < parts.length; i++) {

          if (data[parts[i]] === undefined) {
            callback('Failed to navigate data: ' + parts[i]);
            return;
          }

          data = data[parts[i]];
        }
      }

      model.data = [].concat(data);
      onArray();
    }

    function onArray() {

      if (model.prepend) {
        model.data = model.prepend.concat(model.data);
      }

      if (model.append) {
        model.data = model.data.concat(model.append);
      }

      callback();
    }
  }

};
