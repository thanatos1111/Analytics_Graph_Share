"""
D3.js backend: single graph frame, bands stacked inside, one x-axis at bottom,
y-axes alternating left/right with vertical param labels, right-drag pan,
wheel zoom on both axes, left-click-hold tooltip snapped to line.
"""
from __future__ import annotations

import pandas as pd

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json

MARGIN = {"top": 20, "right": 68, "bottom": 36, "left": 68}
BAND_GAP = 20
TOTAL_HEIGHT = 580
TOOLTIP_STYLE = "position:fixed;padding:6px 10px;background:rgba(255,255,204,0.95);border:1px solid #ccc;border-radius:4px;font-size:12px;pointer-events:none;display:none;max-width:320px;box-shadow:0 2px 8px rgba(0,0,0,0.15);z-index:20;"


def _build_d3_html(data_json: str, for_export: bool) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Chart</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<style>
  * {{ user-select: none; -webkit-user-select: none; }}
  body {{ margin: 0; padding: 8px; font-family: system-ui, sans-serif; background: #fff; }}
  #container {{ overflow: hidden; background: #fff; cursor: default; }}
  #chart {{ display: block; background: #fff; }}
  .y-axis .domain {{ display: none; }}
  .y-axis line {{ stroke: #999; }}
  .y-axis text {{ font-size: 10px; fill: #333; }}
  .x-axis line, .x-axis path {{ stroke: #999; }}
  .x-axis text {{ font-size: 10px; fill: #333; }}
  .grid line {{ stroke: rgba(0,0,0,0.1); stroke-dasharray: 2,2; }}
  .grid .domain {{ display: none; }}
  .line {{ fill: none; stroke-width: 1.5; }}
  .frame {{ fill: none; stroke: #000; stroke-width: 1.5; }}
  .band-label {{ font-size: 10px; fill: #555; font-weight: 500; }}
  #tooltip {{ {TOOLTIP_STYLE} }}
  #crossV {{ position: fixed; left: 0; top: 0; width: 1px; height: 100%; background: rgba(0,0,0,0.5); pointer-events: none; display: none; z-index: 10; }}
  #crossH {{ position: fixed; left: 0; top: 0; width: 100%; height: 1px; background: rgba(0,0,0,0.5); pointer-events: none; display: none; z-index: 10; }}
</style>
</head>
<body>
<div id="container"><svg id="chart"></svg></div>
<div id="tooltip"></div>
<div id="crossV"></div>
<div id="crossH"></div>
<script>
(function() {{
  var data = {data_json};
  if (!data.bands || data.bands.length === 0) {{
    document.body.innerHTML = '<p>No parameters to plot</p>';
    return;
  }}

  var timeDisplay = data.timeDisplay || data.time || [];
  function fmtHM(ms) {{
    var d = new Date(ms);
    return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
  }}
  function fmtFull(ms) {{
    var d = new Date(ms);
    return d.getFullYear() + '/' + (d.getMonth()+1) + '/' + d.getDate() + ' ' +
      d.getHours() + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');
  }}

  var margin = {{ top: {MARGIN["top"]}, right: {MARGIN["right"]}, bottom: {MARGIN["bottom"]}, left: {MARGIN["left"]} }};
  var bandGap = {BAND_GAP};
  var container = document.getElementById('container');
  var tooltip = document.getElementById('tooltip');
  var crossV = document.getElementById('crossV');
  var crossH = document.getElementById('crossH');
  var width = Math.max(400, (container && container.getBoundingClientRect().width) || 900);
  var totalHeight = {TOTAL_HEIGHT};
  var nBands = data.bands.length;
  var plotLeft = margin.left;
  var plotRight = width - margin.right;
  var plotTop = margin.top;
  var plotBottom = totalHeight - margin.bottom;
  var plotWidth = plotRight - plotLeft;
  var plotHeight = plotBottom - plotTop;
  var usableHeight = plotHeight - Math.max(0, nBands - 1) * bandGap;
  var bandHeight = usableHeight / nBands;

  var xMin = Math.min.apply(null, data.timeMs);
  var xMax = Math.max.apply(null, data.timeMs);
  var xDomainCur = [xMin, xMax];

  var bandRanges = [];
  data.bands.forEach(function(band) {{
    bandRanges.push({{ yMin: band.yMin, yMax: band.yMax }});
  }});

  function bandTopPx(bi) {{ return plotTop + bi * (bandHeight + bandGap); }}
  function bandBottomPx(bi) {{ return bandTopPx(bi) + bandHeight; }}

  function xScaleFn(dataX) {{
    return plotLeft + plotWidth * (dataX - xDomainCur[0]) / (xDomainCur[1] - xDomainCur[0]);
  }}
  function xInvert(px) {{
    return xDomainCur[0] + (px - plotLeft) / plotWidth * (xDomainCur[1] - xDomainCur[0]);
  }}

  function yScaleForBand(bi) {{
    var r = bandRanges[bi];
    return d3.scaleLinear().domain([r.yMin, r.yMax]).range([bandBottomPx(bi), bandTopPx(bi)]);
  }}

  function paramLabel(band) {{
    var pr = band.params[0];
    var name = (pr.alias && pr.alias !== pr.name) ? pr.alias : pr.name;
    if (band.unit && band.unit !== '(no unit)') name += '(' + band.unit + ')';
    return name;
  }}

  var svg = d3.select('#chart').attr('width', width).attr('height', totalHeight);

  function redraw() {{
    svg.selectAll('*').remove();

    var defs = svg.append('defs');
    for (var bi = 0; bi < nBands; bi++) {{
      defs.append('clipPath').attr('id', 'clip-band-' + bi)
        .append('rect')
        .attr('x', plotLeft).attr('y', bandTopPx(bi))
        .attr('width', plotWidth).attr('height', bandHeight);
    }}

    svg.append('rect').attr('class', 'frame')
      .attr('x', plotLeft).attr('y', plotTop).attr('width', plotWidth).attr('height', plotHeight);

    var xD3 = d3.scaleLinear().domain(xDomainCur).range([plotLeft, plotRight]);

    data.bands.forEach(function(band, bi) {{
      var yScale = yScaleForBand(bi);
      var top = bandTopPx(bi);
      var bot = bandBottomPx(bi);
      var midY = (top + bot) / 2;
      var label = paramLabel(band);

      if (bi % 2 === 0) {{
        svg.append('g').attr('class', 'y-axis')
          .attr('transform', 'translate(' + plotLeft + ',0)')
          .call(d3.axisLeft(yScale).ticks(5));
        svg.append('text').attr('class', 'band-label')
          .attr('x', 12).attr('y', midY)
          .attr('text-anchor', 'middle')
          .attr('transform', 'rotate(-90,12,' + midY + ')')
          .text(label);
      }} else {{
        svg.append('g').attr('class', 'y-axis')
          .attr('transform', 'translate(' + plotRight + ',0)')
          .call(d3.axisRight(yScale).ticks(5));
        svg.append('text').attr('class', 'band-label')
          .attr('x', width - 12).attr('y', midY)
          .attr('text-anchor', 'middle')
          .attr('transform', 'rotate(90,' + (width - 12) + ',' + midY + ')')
          .text(label);
      }}

      var g = svg.append('g').attr('clip-path', 'url(#clip-band-' + bi + ')');

      g.append('g').attr('class', 'grid')
        .attr('transform', 'translate(' + plotLeft + ',0)')
        .call(d3.axisLeft(yScale).ticks(5).tickSize(-plotWidth).tickFormat(''));

      band.params.forEach(function(p) {{
        var line = d3.line()
          .x(function(d, i) {{ return xD3(data.timeMs[i]); }})
          .y(function(d, i) {{ var v = p.values[i]; return (v != null && !isNaN(v)) ? yScale(v) : 0; }})
          .defined(function(d, i) {{ var v = p.values[i]; return v != null && !isNaN(v); }});
        var pathStr = line(data.timeMs);
        if (pathStr) {{
          g.append('path').attr('class', 'line').attr('d', pathStr).attr('stroke', p.color);
        }}
      }});

      if (bi < nBands - 1) {{
        var sep = bot + bandGap / 2;
        svg.append('line')
          .attr('x1', plotLeft).attr('x2', plotRight)
          .attr('y1', sep).attr('y2', sep)
          .attr('stroke', '#ddd').attr('stroke-dasharray', '4,3');
      }}
    }});

    svg.append('g').attr('class', 'x-axis')
      .attr('transform', 'translate(0,' + plotBottom + ')')
      .call(d3.axisBottom(xD3).ticks(10).tickFormat(function(d) {{ return fmtHM(d); }}));
    svg.append('g').attr('class', 'grid')
      .attr('transform', 'translate(0,' + plotBottom + ')')
      .call(d3.axisBottom(xD3).ticks(10).tickSize(-plotHeight).tickFormat(''));
  }}

  redraw();

  /* ── helpers ── */
  function bandAtY(clientY) {{
    var r = container.getBoundingClientRect();
    var y = clientY - r.top;
    for (var bi = 0; bi < nBands; bi++) {{
      if (y >= bandTopPx(bi) && y <= bandBottomPx(bi)) return bi;
    }}
    return -1;
  }}
  function bandNearY(clientY) {{
    var r = container.getBoundingClientRect();
    var y = clientY - r.top;
    for (var bi = 0; bi < nBands; bi++) {{
      if (y >= bandTopPx(bi) - bandGap/2 && y <= bandBottomPx(bi) + bandGap/2) return bi;
    }}
    return -1;
  }}

  function isInXAxisStrip(clientY) {{
    var r = container.getBoundingClientRect();
    return (clientY - r.top) > plotBottom;
  }}
  function isInPlotBody(clientX) {{
    var r = container.getBoundingClientRect();
    var x = clientX - r.left;
    return x >= plotLeft && x <= plotRight;
  }}
  function isInYAxisRuler(clientX, bandIdx) {{
    var r = container.getBoundingClientRect();
    var x = clientX - r.left;
    if (bandIdx >= 0 && bandIdx % 2 === 0) return x < plotLeft;
    if (bandIdx >= 0 && bandIdx % 2 === 1) return x > plotRight;
    return x < plotLeft || x > plotRight;
  }}

  function nearestDataIndex(dataX) {{
    var idx = 0;
    for (var i = 1; i < data.timeMs.length; i++) {{
      if (Math.abs(data.timeMs[i] - dataX) < Math.abs(data.timeMs[idx] - dataX)) idx = i;
    }}
    return idx;
  }}

  function distSeg(px, py, x0, y0, x1, y1) {{
    var dx = x1 - x0, dy = y1 - y0, len2 = dx*dx + dy*dy;
    if (len2 === 0) return Math.hypot(px - x0, py - y0);
    var t = Math.max(0, Math.min(1, ((px-x0)*dx + (py-y0)*dy) / len2));
    return Math.hypot(px - (x0 + t*dx), py - (y0 + t*dy));
  }}

  function findClosestParam(bi, cx, cy) {{
    var r = container.getBoundingClientRect();
    var px = cx - r.left, py = cy - r.top;
    var yScale = yScaleForBand(bi);
    var band = data.bands[bi];
    var best = 0, bestD = Infinity;
    for (var p = 0; p < band.params.length; p++) {{
      var param = band.params[p];
      var minD = Infinity;
      for (var i = 0; i < data.timeMs.length - 1; i++) {{
        var v0 = param.values[i], v1 = param.values[i+1];
        if (v0 == null || isNaN(v0) || v1 == null || isNaN(v1)) continue;
        var d = distSeg(px, py, xScaleFn(data.timeMs[i]), yScale(v0), xScaleFn(data.timeMs[i+1]), yScale(v1));
        if (d < minD) minD = d;
      }}
      if (minD < bestD) {{ bestD = minD; best = p; }}
    }}
    return best;
  }}

  /* ── state ── */
  var dragMode = null, dragStart = null;
  var tooltipMode = null;

  /* ── mousedown ── */
  container.addEventListener('mousedown', function(e) {{
    if (e.button === 0) {{
      e.preventDefault();
      var r = container.getBoundingClientRect();
      var px = e.clientX - r.left;
      var bi = bandAtY(e.clientY);
      if (bi >= 0 && px >= plotLeft && px <= plotRight) {{
        var paramIdx = findClosestParam(bi, e.clientX, e.clientY);
        tooltipMode = {{ bandIdx: bi, paramIdx: paramIdx }};
        showTooltip(e);
      }}
      return;
    }}

    if (e.button === 2) {{
      e.preventDefault();
      if (isInXAxisStrip(e.clientY)) {{
        dragMode = 'xpan';
        dragStart = {{ clientX: e.clientX, domain: xDomainCur.slice() }};
      }} else {{
        var bi = bandNearY(e.clientY);
        if (bi >= 0 && isInYAxisRuler(e.clientX, bi)) {{
          dragMode = 'ypan';
          dragStart = {{ bandIdx: bi, clientY: e.clientY, range: [bandRanges[bi].yMin, bandRanges[bi].yMax] }};
        }}
      }}
    }}
  }});

  function showTooltip(e) {{
    if (!tooltipMode) return;
    var r = container.getBoundingClientRect();
    var px = e.clientX - r.left;
    var dataX = xInvert(px);
    var idx = nearestDataIndex(dataX);
    var bi = tooltipMode.bandIdx;
    var band = data.bands[bi];
    var param = band.params[tooltipMode.paramIdx];
    var val = param.values[idx];
    var valStr = (val != null && !isNaN(val)) ? Number(val).toLocaleString() : '—';
    var ts = timeDisplay[idx] || fmtFull(data.timeMs[idx]);
    tooltip.innerHTML = param.name + '<br>Time: ' + ts + '<br>' + (param.alias || param.name) + ': ' + valStr;
    tooltip.style.display = 'block';
    tooltip.style.left = (e.pageX + 14) + 'px';
    tooltip.style.top = (e.pageY + 14) + 'px';

    var yScale = yScaleForBand(bi);
    var yPx = (val != null && !isNaN(val)) ? yScale(val) : (bandTopPx(bi) + bandHeight / 2);
    var xPx = xScaleFn(data.timeMs[idx]);
    crossV.style.display = 'block';
    crossV.style.left = (r.left + xPx) + 'px';
    crossV.style.top = (r.top + plotTop) + 'px';
    crossV.style.height = plotHeight + 'px';
    crossH.style.display = 'block';
    crossH.style.left = (r.left + plotLeft) + 'px';
    crossH.style.width = plotWidth + 'px';
    crossH.style.top = (r.top + yPx) + 'px';
  }}

  function hideTooltip() {{
    tooltipMode = null;
    tooltip.style.display = 'none';
    crossV.style.display = 'none';
    crossH.style.display = 'none';
  }}

  /* ── mousemove ── */
  window.addEventListener('mousemove', function(e) {{
    if (tooltipMode && (e.buttons & 1)) {{
      showTooltip(e);
      return;
    }}

    if (dragMode === 'xpan' && dragStart) {{
      var dxPx = dragStart.clientX - e.clientX;
      var dataPerPx = (dragStart.domain[1] - dragStart.domain[0]) / plotWidth;
      xDomainCur = [dragStart.domain[0] + dxPx * dataPerPx, dragStart.domain[1] + dxPx * dataPerPx];
      redraw();
      return;
    }}

    if (dragMode === 'ypan' && dragStart) {{
      var dyPx = e.clientY - dragStart.clientY;
      var r = dragStart.range;
      var dataPerPx = (r[1] - r[0]) / bandHeight;
      var delta = dyPx * dataPerPx;
      bandRanges[dragStart.bandIdx].yMin = r[0] + delta;
      bandRanges[dragStart.bandIdx].yMax = r[1] + delta;
      redraw();
      return;
    }}

    if (!(e.buttons & 1)) hideTooltip();
  }});

  window.addEventListener('mouseup', function(e) {{
    if (e.button === 0) hideTooltip();
    if (e.button === 2) {{ dragMode = null; dragStart = null; }}
  }});

  /* ── wheel: zoom ── */
  container.addEventListener('wheel', function(e) {{
    var r = container.getBoundingClientRect();
    var cx = e.clientX, cy = e.clientY;
    var x = cx - r.left, y = cy - r.top;

    if (isInXAxisStrip(cy) || (isInPlotBody(cx) && bandAtY(cy) >= 0)) {{
      e.preventDefault();
      var dataX = xInvert(x);
      var w = xDomainCur[1] - xDomainCur[0];
      var factor = e.deltaY > 0 ? 1.15 : 0.87;
      var newW = Math.max(w * factor, w * 0.01);
      xDomainCur[0] = dataX - (dataX - xDomainCur[0]) * (newW / w);
      xDomainCur[1] = dataX + (xDomainCur[1] - dataX) * (newW / w);
      redraw();
      return;
    }}

    var bi = bandNearY(cy);
    if (bi >= 0 && isInYAxisRuler(cx, bi)) {{
      e.preventDefault();
      var yScale = yScaleForBand(bi);
      var dataY = yScale.invert(y);
      var rr = bandRanges[bi];
      var w = rr.yMax - rr.yMin;
      var factor = e.deltaY > 0 ? 1.15 : 0.87;
      var newW = Math.max(w * factor, w * 0.01);
      rr.yMin = dataY - (dataY - rr.yMin) * (newW / w);
      rr.yMax = dataY + (rr.yMax - dataY) * (newW / w);
      redraw();
      return;
    }}
  }}, {{ passive: false }});

  container.addEventListener('mouseleave', function(e) {{
    if (!(e.buttons & 1)) hideTooltip();
  }});

  document.addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
}})();
</script>
</body>
</html>
"""


class D3Backend(PlotBackend):
    @property
    def id(self) -> str:
        return "d3"

    @property
    def name(self) -> str:
        return "D3.js"

    def build_html(
        self,
        data_df: pd.DataFrame,
        param_units: dict[str, str],
        *,
        aliases: dict[str, str] | None = None,
        plot_style: dict | None = None,
        for_export: bool = False,
    ) -> str:
        data = prepare_chart_data(data_df, param_units, aliases=aliases)
        data_json = chart_data_to_json(data)
        return _build_d3_html(data_json, for_export)
