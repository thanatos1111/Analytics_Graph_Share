(function() {
  function findPlotDiv() {
    var els = document.getElementsByClassName('plotly-graph-div');
    return els && els.length ? els[0] : null;
  }
  var BOTTOM_X_STRIP = 0.08;
  var Y_AXIS_STRIP_PX = 50;

  function runAfterPlot() {
    var gd = findPlotDiv();
    if (!gd || !gd.data) {
      setTimeout(runAfterPlot, 50);
      return;
    }
    var layout = gd.layout;
    var margin = layout.margin || { t: 36, r: 70, b: 48, l: 70 };
    var plotHeight = gd.offsetHeight;
    var plotWidth = gd.offsetWidth;
    var innerTop = margin.t;
    var innerBottom = plotHeight - margin.b;
    var innerLeft = margin.l;
    var innerRight = plotWidth - margin.r;
    var innerHeight = innerBottom - innerTop;
    var innerWidth = innerRight - innerLeft;

    function pixelToPaperY(pixelY) {
      var yFromTop = pixelY - innerTop;
      return 1 - yFromTop / innerHeight;
    }
    function pixelToPaperX(pixelX) {
      return (pixelX - innerLeft) / innerWidth;
    }
    function getYaxisKeys() {
      var keys = [];
      for (var k in layout) {
        if (k.match(/^yaxis[0-9]*$/) && layout[k].domain) keys.push(k);
      }
      return keys.sort(function(a, b) {
        var d1 = layout[a].domain[1], d2 = layout[b].domain[1];
        return d2 - d1;
      });
    }
    function getSubplotAtPaperY(paperY) {
      var keys = getYaxisKeys();
      for (var i = 0; i < keys.length; i++) {
        var d = layout[keys[i]].domain;
        if (d && paperY >= d[0] && paperY <= d[1]) return keys[i];
      }
      return null;
    }
    function paperToDataY(paperY, yaxisKey) {
      var ax = layout[yaxisKey];
      if (!ax || !ax.domain || !ax.range) return null;
      var d = ax.domain, r = ax.range;
      var t = (paperY - d[0]) / (d[1] - d[0]);
      return r[0] + t * (r[1] - r[0]);
    }
    function getAllXaxisKeys() {
      var keys = [];
      for (var k in layout) {
        if (k.match(/^xaxis[0-9]*$/) && layout[k].domain) keys.push(k);
      }
      return keys.length ? keys : ['x'];
    }
    function pixelToDataX(pixelX) {
      var keys = getAllXaxisKeys();
      var ax = layout[keys[0]];
      if (!ax || !ax.range) return null;
      var r = ax.range;
      var t = (pixelX - innerLeft) / innerWidth;
      return r[0] + t * (r[1] - r[0]);
    }
    function isInYAxisRuler(pixelX) {
      return pixelX < innerLeft || pixelX > innerRight;
    }
    function isInBottomXStrip(paperY) {
      return paperY < BOTTOM_X_STRIP;
    }

    gd.on('plotly_hover', function(ev) {
      if (!ev.points || !ev.points.length) return;
      var pt = ev.points[0];
      var yref = (pt.yaxis && pt.yaxis.id) ? pt.yaxis.id : 'y';
      var yKeys = getYaxisKeys();
      var shapes = [];
      for (var i = 0; i < yKeys.length; i += 2) {
        var d = layout[yKeys[i]].domain;
        if (d) {
          shapes.push({ type: 'line', x0: pt.x, x1: pt.x, y0: d[0], y1: d[1], xref: 'x', yref: 'paper', line: { color: 'rgba(0,0,0,0.5)', width: 1 } });
        }
      }
      shapes.push({ type: 'line', x0: 0, x1: 1, y0: pt.y, y1: pt.y, xref: 'paper', yref: yref, line: { color: 'rgba(0,0,0,0.5)', width: 1 } });
      Plotly.relayout(gd, { shapes: shapes });
    });
    gd.on('plotly_unhover', function() {
      Plotly.relayout(gd, { shapes: [] });
    });

    var dragMode = null;
    var dragStart = null;

    gd.addEventListener('wheel', function(ev) {
      var paperY = pixelToPaperY(ev.offsetY);
      if (!isInYAxisRuler(ev.offsetX)) return;
      var yaxisKey = getSubplotAtPaperY(paperY);
      if (!yaxisKey) return;
      ev.preventDefault();
      ev.stopPropagation();
      var ax = gd.layout[yaxisKey];
      if (!ax || !ax.range) return;
      var dataY = paperToDataY(paperY, yaxisKey);
      var r0 = ax.range[0], r1 = ax.range[1], w = r1 - r0;
      var factor = ev.deltaY > 0 ? 1.15 : 0.87;
      var newW = Math.max(w * factor, (r1 - r0) * 0.02);
      var newR0 = dataY - (dataY - r0) * (newW / w);
      var newR1 = dataY + (r1 - dataY) * (newW / w);
      var update = {};
      update[yaxisKey + '.range'] = [newR0, newR1];
      Plotly.relayout(gd, update);
    }, { passive: false });

    gd.addEventListener('mousedown', function(ev) {
      if (ev.button !== 2) return;
      var paperY = pixelToPaperY(ev.offsetY);
      if (isInBottomXStrip(paperY)) {
        var dataX = pixelToDataX(ev.offsetX);
        if (dataX == null) return;
        var xkeys = getAllXaxisKeys();
        var xr = gd.layout[xkeys[0]].range;
        dragMode = 'xpan';
        dragStart = { dataX: dataX, range: [xr[0], xr[1]], xkeys: xkeys };
      } else if (isInYAxisRuler(ev.offsetX)) {
        var yaxisKey = getSubplotAtPaperY(paperY);
        if (!yaxisKey) return;
        var dataY = paperToDataY(paperY, yaxisKey);
        if (dataY == null) return;
        var yr = gd.layout[yaxisKey].range;
        dragMode = 'ypan';
        dragStart = { yaxisKey: yaxisKey, dataY: dataY, range: [yr[0], yr[1]] };
      }
      ev.preventDefault();
    });

    gd.addEventListener('mousemove', function(ev) {
      if (!dragStart) return;
      if (dragMode === 'xpan') {
        var dataX = pixelToDataX(ev.offsetX);
        if (dataX == null) return;
        var dx = dragStart.dataX - dataX;
        var newRange = [dragStart.range[0] + dx, dragStart.range[1] + dx];
        var update = {};
        for (var i = 0; i < dragStart.xkeys.length; i++) {
          update[dragStart.xkeys[i] + '.range'] = newRange;
        }
        Plotly.relayout(gd, update);
      } else if (dragMode === 'ypan') {
        var paperY = pixelToPaperY(ev.offsetY);
        var dataY = paperToDataY(paperY, dragStart.yaxisKey);
        if (dataY == null) return;
        var dy = dragStart.dataY - dataY;
        var newRange = [dragStart.range[0] + dy, dragStart.range[1] + dy];
        var update = {};
        update[dragStart.yaxisKey + '.range'] = newRange;
        Plotly.relayout(gd, update);
      }
    });

    gd.addEventListener('mouseup', function(ev) {
      if (ev.button === 2) { dragMode = null; dragStart = null; }
    });
    gd.addEventListener('mouseleave', function() {
      dragMode = null;
      dragStart = null;
    });
    gd.addEventListener('contextmenu', function(ev) { ev.preventDefault(); });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(runAfterPlot, 150); });
  } else {
    setTimeout(runAfterPlot, 150);
  }
})();
