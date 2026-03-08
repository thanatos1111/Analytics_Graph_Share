"""
uPlot backend: stacked bands, synced x-axis, unified tooltip/crosshair and pan/zoom (right-drag x/y, wheel on y-axis).
"""
from __future__ import annotations

import pandas as pd

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json

# Tooltip/crosshair style shared with other backends
TOOLTIP_STYLE = "position:fixed;padding:6px 10px;background:rgba(255,255,204,0.95);border:1px solid #ccc;border-radius:4px;font-size:12px;pointer-events:none;display:none;max-width:320px;box-shadow:0 2px 8px rgba(0,0,0,0.15);"
CROSSHAIR_STYLE = "position:fixed;pointer-events:none;display:none;z-index:10;"
BAND_HEIGHT = 160
Y_AXIS_STRIP_PX = 50
BOTTOM_X_STRIP_PX = 32


def _build_uplot_html(data_json: str, for_export: bool) -> str:
    cdn = "https://cdn.jsdelivr.net/npm/uplot@1.6.26/dist"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Chart</title>
<link rel="stylesheet" href="{cdn}/uPlot.min.css">
<style>
  body {{ margin: 0; padding: 8px; font-family: system-ui, sans-serif; background: #fff; }}
  .band {{ margin-bottom: 4px; background: #fff; }}
  .band-title {{ font-size: 12px; color: #555; margin-bottom: 2px; }}
  .band-chart {{ width: 100%; height: {BAND_HEIGHT}px; background: #fff; }}
  #tooltip {{ {TOOLTIP_STYLE} }}
  #crosshairV {{ left:0;top:0;width:1px;height:100%;background:rgba(0,0,0,0.5); }}
  #crosshairH {{ left:0;top:0;width:100%;height:1px;background:rgba(0,0,0,0.5); }}
</style>
</head>
<body>
<div id="charts"></div>
<div id="tooltip"></div>
<div id="crosshairV" class="crosshair" style="{CROSSHAIR_STYLE}"></div>
<div id="crosshairH" class="crosshair" style="{CROSSHAIR_STYLE}"></div>
<script src="{cdn}/uPlot.iife.min.js"></script>
<script>
(function() {{
  var data = {data_json};
  if (!data.bands || data.bands.length === 0) {{
    document.body.innerHTML = '<p>No parameters to plot</p>';
    return;
  }}

  var timeDisplay = data.timeDisplay || data.time || [];
  var charts = [];
  var chartWraps = [];
  var xScale = null;
  var tooltip = document.getElementById('tooltip');
  var crosshairV = document.getElementById('crosshairV');
  var crosshairH = document.getElementById('crosshairH');

  function syncXScale(key, val) {{
    if (key !== 'x') return;
    xScale = val;
    for (var i = 0; i < charts.length; i++) {{
      if (charts[i].cursor.left !== val[0] || charts[i].cursor.width !== val[1] - val[0]) {{
        charts[i].setScale({{ x: {{ min: val[0], max: val[1] }} }});
      }}
    }}
  }}

  function fmtTime(ms) {{
    var d = new Date(ms);
    return d.getFullYear() + '/' + (d.getMonth()+1) + '/' + d.getDate() + ' ' +
      d.getHours() + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');
  }}

  function bandAtY(clientY) {{
    var chartsEl = document.getElementById('charts');
    var rect = chartsEl.getBoundingClientRect();
    var y = clientY - rect.top;
    for (var b = 0; b < chartWraps.length; b++) {{
      var wr = chartWraps[b].getBoundingClientRect();
      var relY = clientY - wr.top;
      if (relY >= 0 && relY <= wr.height) return {{ bandIdx: b, wrap: chartWraps[b], relY: relY, u: charts[b] }};
    }}
    return null;
  }}

  function isInYAxisRuler(clientX, wrap) {{
    var r = wrap.getBoundingClientRect();
    var x = clientX - r.left;
    return x < {Y_AXIS_STRIP_PX} || x > (r.width - {Y_AXIS_STRIP_PX});
  }}

  function isInBottomXStrip(clientY) {{
    var chartsEl = document.getElementById('charts');
    var r = chartsEl.getBoundingClientRect();
    var bottom = r.bottom - {BOTTOM_X_STRIP_PX};
    return clientY >= bottom;
  }}

  for (var b = 0; b < data.bands.length; b++) {{
    var band = data.bands[b];
    var series = [{{ label: 'Time' }}];
    var plotData = [data.timeMs.slice()];
    for (var p = 0; p < band.params.length; p++) {{
      series.push({{ label: band.params[p].alias || band.params[p].name, stroke: band.params[p].color }});
      plotData.push(band.params[p].values.slice());
    }}

    var container = document.createElement('div');
    container.className = 'band';
    container.innerHTML = '<div class="band-title">' + band.unit + '</div><div class="band-chart u-wrap"></div>';
    document.getElementById('charts').appendChild(container);
    var wrap = container.querySelector('.band-chart');
    chartWraps.push(wrap);
    var w = wrap.getBoundingClientRect().width || 900;

    var opts = {{
      width: w,
      height: {BAND_HEIGHT},
      series: series,
      scales: {{
        x: {{ time: true, range: xScale ? function() {{ return xScale; }} : undefined }},
        y: {{ min: band.yMin, max: band.yMax }}
      }},
      axes: [
        {{ show: b === data.bands.length - 1, label: 'Time', incrs: [1, 60, 3600, 86400], values: function(self, splits) {{
          return splits.map(function(v) {{ return fmtTime(v); }});
        }} }},
        {{ label: band.unit, show: true }}
      ],
      cursor: {{ sync: {{ key: 'x', setSeries: false }}, points: {{ show: true, size: 4 }} }},
      hooks: {{ setScale: [syncXScale] }}
    }};

    var u = new uPlot(opts, plotData, wrap);
    charts.push(u);
  }}

  if (charts.length) xScale = [charts[0].scales.x.min, charts[0].scales.x.max];

  var containerEl = document.getElementById('charts');
  var dragMode = null, dragStart = null;

  containerEl.addEventListener('mousemove', function(e) {{
    var bandInfo = bandAtY(e.clientY);
    var idx = -1;
    var bandIdx = -1;
    var band = null;
    if (bandInfo && bandInfo.u) {{
      var left = bandInfo.u.cursor.left;
      if (left != null) {{
        idx = bandInfo.u.posToIdx(left);
        bandIdx = bandInfo.bandIdx;
        band = data.bands[bandIdx];
      }}
    }}
    if (idx >= 0 && idx < data.timeMs.length && band) {{
      var ts = timeDisplay[idx] || fmtTime(data.timeMs[idx]);
      crosshairV.style.display = 'block';
      crosshairV.style.left = e.clientX + 'px';
      crosshairV.style.top = '0';
      crosshairV.style.height = document.documentElement.scrollHeight + 'px';
      crosshairH.style.display = 'block';
      crosshairH.style.left = bandInfo.wrap.getBoundingClientRect().left + 'px';
      crosshairH.style.width = bandInfo.wrap.getBoundingClientRect().width + 'px';
      crosshairH.style.top = e.clientY + 'px';
      var html = '';
      for (var p = 0; p < band.params.length; p++) {{
        var pr = band.params[p];
        var v = pr.values[idx];
        var valStr = (v != null && v !== undefined && !isNaN(v)) ? Number(v).toLocaleString() : '—';
        html += pr.name + '<br>Time: ' + ts + '<br>' + (pr.alias || pr.name) + ': ' + valStr + '<br><br>';
      }}
      tooltip.innerHTML = html ? html.replace(/<br><br>$/, '') : '';
      tooltip.style.display = 'block';
      tooltip.style.left = (e.pageX + 12) + 'px';
      tooltip.style.top = (e.pageY + 12) + 'px';
    }} else {{
      tooltip.style.display = 'none';
      crosshairV.style.display = 'none';
      crosshairH.style.display = 'none';
    }}
  }});
  containerEl.addEventListener('mouseleave', function() {{
    tooltip.style.display = 'none';
    crosshairV.style.display = 'none';
    crosshairH.style.display = 'none';
  }});

  containerEl.addEventListener('mousedown', function(e) {{
    if (e.button !== 2) return;
    e.preventDefault();
    if (isInBottomXStrip(e.clientY)) {{
      if (!charts[0]) return;
      var bbox = charts[0].bbox;
      dragMode = 'xpan';
      dragStart = {{ clientX: e.clientX, range: [xScale[0], xScale[1]], plotWidth: bbox ? bbox.width : 400 }};
    }} else {{
      var bandInfo = bandAtY(e.clientY);
      if (bandInfo && isInYAxisRuler(e.clientX, bandInfo.wrap)) {{
        var u = bandInfo.u;
        var dataY = u.posToVal(bandInfo.relY, 'y');
        dragMode = 'ypan';
        dragStart = {{ bandIdx: bandInfo.bandIdx, dataY: dataY, range: [u.scales.y.min, u.scales.y.max] }};
      }}
    }}
  }});
  window.addEventListener('mousemove', function(e) {{
    if (!dragStart) return;
    if (dragMode === 'xpan' && charts[0]) {{
      var dxPx = dragStart.clientX - e.clientX;
      var dataPerPx = (dragStart.range[1] - dragStart.range[0]) / dragStart.plotWidth;
      var deltaData = dxPx * dataPerPx;
      xScale = [dragStart.range[0] + deltaData, dragStart.range[1] + deltaData];
      for (var i = 0; i < charts.length; i++) charts[i].setScale({{ x: {{ min: xScale[0], max: xScale[1] }} }});
    }} else if (dragMode === 'ypan' && dragStart.bandIdx != null) {{
      var u = charts[dragStart.bandIdx];
      var wrap = chartWraps[dragStart.bandIdx];
      var r = wrap.getBoundingClientRect();
      var relY = e.clientY - r.top;
      var dataY = u.posToVal(relY, 'y');
      var dy = dragStart.dataY - dataY;
      dragStart.dataY = dataY;
      var nr = [dragStart.range[0] + dy, dragStart.range[1] + dy];
      dragStart.range = nr;
      u.setScale({{ y: {{ min: nr[0], max: nr[1] }} }});
    }}
  }});
  window.addEventListener('mouseup', function(e) {{
    if (e.button === 2) {{ dragMode = null; dragStart = null; }}
  }});

  containerEl.addEventListener('wheel', function(e) {{
    var bandInfo = bandAtY(e.clientY);
    if (!bandInfo || !isInYAxisRuler(e.clientX, bandInfo.wrap)) return;
    e.preventDefault();
    var u = charts[bandInfo.bandIdx];
    var dataY = u.posToVal(bandInfo.relY, 'y');
    var r0 = u.scales.y.min, r1 = u.scales.y.max, w = r1 - r0;
    var factor = e.deltaY > 0 ? 1.15 : 0.87;
    var newW = Math.max(w * factor, (r1 - r0) * 0.02);
    var newR0 = dataY - (dataY - r0) * (newW / w);
    var newR1 = dataY + (r1 - dataY) * (newW / w);
    u.setScale({{ y: {{ min: newR0, max: newR1 }} }});
  }}, {{ passive: false }});

  document.addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
}})();
</script>
</body>
</html>
"""


class UPlotBackend(PlotBackend):
    @property
    def id(self) -> str:
        return "uplot"

    @property
    def name(self) -> str:
        return "uPlot"

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
        return _build_uplot_html(data_json, for_export)
