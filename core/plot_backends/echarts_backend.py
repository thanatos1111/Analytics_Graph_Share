"""
ECharts backend: stacked bands, unified tooltip (3 lines, light yellow), white bg, crosshair, right-drag x/y pan, wheel on y zoom.
"""
from __future__ import annotations

import pandas as pd

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json

BAND_HEIGHT = 160
GAP = 8
Y_AXIS_STRIP_PX = 50
BOTTOM_X_STRIP_PX = 40


def _build_echarts_html(data_json: str, for_export: bool) -> str:
    cdn = "https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Chart</title>
<script src="{cdn}/echarts.min.js"></script>
<style>
  body {{ margin: 0; padding: 8px; font-family: system-ui, sans-serif; background: #fff; }}
  #wrap {{ position: relative; width: 100%; background: #fff; }}
  #main {{ width: 100%; height: 620px; min-height: 400px; background: #fff; }}
  #tooltip {{ position: fixed; padding: 6px 10px; background: rgba(255,255,204,0.95); border: 1px solid #ccc; border-radius: 4px; font-size: 12px; pointer-events: none; display: none; max-width: 320px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); z-index: 20; }}
  .crosshair {{ position: fixed; pointer-events: none; display: none; z-index: 10; background: rgba(0,0,0,0.5); }}
  #crossV {{ width: 1px; height: 100%; left: 0; top: 0; }}
  #crossH {{ height: 1px; width: 100%; left: 0; top: 0; }}
</style>
</head>
<body>
<div id="wrap">
<div id="main"></div>
</div>
<div id="tooltip"></div>
<div id="crossV" class="crosshair"></div>
<div id="crossH" class="crosshair"></div>
<script>
(function() {{
  var data = {data_json};
  if (!data.bands || data.bands.length === 0) {{
    document.body.innerHTML = '<p>No parameters to plot</p>';
    return;
  }}

  var timeDisplay = data.timeDisplay || data.time || [];
  function fmtTime(ms) {{
    var d = new Date(ms);
    return d.getFullYear() + '/' + (d.getMonth()+1) + '/' + d.getDate() + ' ' +
      d.getHours() + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');
  }}

  var bandHeight = {BAND_HEIGHT};
  var gap = {GAP};
  var grids = [];
  var xAxes = [];
  var yAxes = [];
  var series = [];
  var h = 0;
  var gridTops = [];

  for (var b = 0; b < data.bands.length; b++) {{
    gridTops.push(h + 24);
    grids.push({{ left: 60, right: 40, top: h + 24, bottom: 28, height: bandHeight, containLabel: false }});
    h += bandHeight + gap;
    xAxes.push({{ gridIndex: b, type: 'value', min: data.timeMs[0], max: data.timeMs[data.timeMs.length - 1], show: b === data.bands.length - 1, axisLabel: {{ formatter: function(v) {{ var d = new Date(v); return d.getFullYear() + '/' + (d.getMonth()+1) + '/' + d.getDate(); }} }} }});
    yAxes.push({{ gridIndex: b, type: 'value', min: data.bands[b].yMin, max: data.bands[b].yMax, name: data.bands[b].unit, nameGap: 50 }});
    for (var p = 0; p < data.bands[b].params.length; p++) {{
      var param = data.bands[b].params[p];
      var pts = [];
      for (var i = 0; i < data.timeMs.length; i++) {{
        var v = param.values[i];
        if (v != null && !isNaN(v)) pts.push([data.timeMs[i], v]);
      }}
      series.push({{ name: param.alias || param.name, type: 'line', xAxisIndex: b, yAxisIndex: b, data: pts, symbol: 'none', lineStyle: {{ color: param.color }}, showSymbol: false }});
    }}
  }}

  var xAxisIndices = [];
  for (var xi = 0; xi < data.bands.length; xi++) xAxisIndices.push(xi);

  var option = {{
    animation: false,
    backgroundColor: '#fff',
    tooltip: {{
      trigger: 'axis',
      confine: true,
      backgroundColor: 'rgba(255,255,204,0.95)',
      formatter: function(params) {{
        if (!params || !params.length) return '';
        var pt = params[0];
        var idx = pt.dataIndex;
        if (idx == null || idx < 0 || idx >= data.timeMs.length) return '';
        var bandIdx = pt.seriesIndex != null ? (function() {{ var o = chart.getOption(); return (o.series[pt.seriesIndex] && o.series[pt.seriesIndex].yAxisIndex) != null ? o.series[pt.seriesIndex].yAxisIndex : 0; }})() : 0;
        var band = data.bands[bandIdx];
        if (!band) return '';
        var ts = timeDisplay[idx] || fmtTime(data.timeMs[idx]);
        var html = '';
        band.params.forEach(function(pr) {{
          var v = pr.values[idx];
          var valStr = (v != null && !isNaN(v)) ? Number(v).toLocaleString() : '—';
          html += pr.name + '<br/>Time: ' + ts + '<br/>' + (pr.alias || pr.name) + ': ' + valStr + '<br/>';
        }});
        return html.replace(/<br\\/>$/, '');
      }}
    }},
    axisPointer: {{ link: [{{ xAxisIndex: 'all' }}], label: {{ backgroundColor: 'rgba(255,255,204,0.95)' }} }},
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      {{ type: 'inside', xAxisIndex: xAxisIndices, start: 0, end: 100 }},
      {{ type: 'slider', xAxisIndex: xAxisIndices, bottom: 8, height: 20, start: 0, end: 100 }}
    ],
    series: series
  }};

  var chart = echarts.init(document.getElementById('main'));
  chart.setOption(option);

  var mainEl = document.getElementById('main');
  var tooltipEl = document.getElementById('tooltip');
  var crossV = document.getElementById('crossV');
  var crossH = document.getElementById('crossH');
  var dragMode = null, dragStart = null;

  function bandAtY(clientY) {{
    var r = mainEl.getBoundingClientRect();
    var relY = clientY - r.top;
    for (var b = 0; b < grids.length; b++) {{
      var g = grids[b];
      if (relY >= g.top && relY <= g.top + g.height) return {{ b: b, relY: relY - g.top }};
    }}
    return null;
  }}
  function isInBottomStrip(clientY) {{
    var r = mainEl.getBoundingClientRect();
    return clientY >= r.bottom - {BOTTOM_X_STRIP_PX};
  }}
  function isInYAxisRuler(clientX) {{
    var r = mainEl.getBoundingClientRect();
    var x = clientX - r.left;
    return x < {Y_AXIS_STRIP_PX} || x > (r.width - {Y_AXIS_STRIP_PX});
  }}

  chart.getZr().on('mousemove', function(e) {{
    var point = [e.offsetX, e.offsetY];
    var bandInfo = bandAtY(e.event.clientY);
    if (bandInfo != null) {{
      crossV.style.display = 'block';
      crossV.style.left = e.event.clientX + 'px';
      crossV.style.top = '0';
      crossV.style.height = document.documentElement.scrollHeight + 'px';
      crossH.style.display = 'block';
      crossH.style.left = mainEl.getBoundingClientRect().left + 'px';
      crossH.style.width = mainEl.getBoundingClientRect().width + 'px';
      crossH.style.top = e.event.clientY + 'px';
    }} else {{
      crossV.style.display = 'none';
      crossH.style.display = 'none';
    }}
  }});
  chart.getZr().on('globalout', function() {{
    crossV.style.display = 'none';
    crossH.style.display = 'none';
  }});

  mainEl.addEventListener('mousedown', function(e) {{
    if (e.button !== 2) return;
    e.preventDefault();
    if (isInBottomStrip(e.clientY)) {{
      var xRange = chart.getOption().xAxis[0].min != null ? [chart.getOption().xAxis[0].min, chart.getOption().xAxis[0].max] : [data.timeMs[0], data.timeMs[data.timeMs.length-1]];
      dragMode = 'xpan';
      dragStart = {{ clientX: e.clientX, range: xRange, plotWidth: mainEl.getBoundingClientRect().width - 100 }};
    }} else if (bandInfo = bandAtY(e.clientY), bandInfo && isInYAxisRuler(e.clientX)) {{
      var opt = chart.getOption();
      var yMin = opt.yAxis[bandInfo.b].min, yMax = opt.yAxis[bandInfo.b].max;
      var conv = chart.convertFromPixel({{ seriesIndex: 0, yAxisIndex: bandInfo.b }}, [0, e.clientY - mainEl.getBoundingClientRect().top - grids[bandInfo.b].top ]);
      var dataY = conv[1];
      dragMode = 'ypan';
      dragStart = {{ bandIdx: bandInfo.b, dataY: dataY, range: [yMin, yMax] }};
    }}
  }});
  window.addEventListener('mousemove', function(e) {{
    if (!dragStart) return;
    if (dragMode === 'xpan') {{
      var dxPx = dragStart.clientX - e.clientX;
      var dataPerPx = (dragStart.range[1] - dragStart.range[0]) / dragStart.plotWidth;
      var delta = dxPx * dataPerPx;
      var newMin = dragStart.range[0] + delta, newMax = dragStart.range[1] + delta;
      var opt = chart.getOption();
      for (var i = 0; i < opt.xAxis.length; i++) {{ opt.xAxis[i].min = newMin; opt.xAxis[i].max = newMax; }}
      chart.setOption(opt);
    }} else if (dragMode === 'ypan') {{
      var bandInfo = bandAtY(e.clientY);
      if (!bandInfo || bandInfo.b !== dragStart.bandIdx) return;
      var conv = chart.convertFromPixel({{ seriesIndex: 0, yAxisIndex: dragStart.bandIdx }}, [0, e.clientY - mainEl.getBoundingClientRect().top - grids[dragStart.bandIdx].top]);
      var dataY = conv[1];
      var dy = dragStart.dataY - dataY;
      dragStart.dataY = dataY;
      dragStart.range = [dragStart.range[0] + dy, dragStart.range[1] + dy];
      var opt = chart.getOption();
      opt.yAxis[dragStart.bandIdx].min = dragStart.range[0];
      opt.yAxis[dragStart.bandIdx].max = dragStart.range[1];
      chart.setOption(opt);
    }}
  }});
  window.addEventListener('mouseup', function(e) {{ if (e.button === 2) {{ dragMode = null; dragStart = null; }} }});

  mainEl.addEventListener('wheel', function(e) {{
    var bandInfo = bandAtY(e.clientY);
    if (!bandInfo || !isInYAxisRuler(e.clientX)) return;
    e.preventDefault();
    var opt = chart.getOption();
    var yMin = opt.yAxis[bandInfo.b].min, yMax = opt.yAxis[bandInfo.b].max;
    var conv = chart.convertFromPixel({{ seriesIndex: 0, yAxisIndex: bandInfo.b }}, [0, e.clientY - mainEl.getBoundingClientRect().top - grids[bandInfo.b].top]);
    var dataY = conv[1];
    var w = yMax - yMin;
    var factor = e.deltaY > 0 ? 1.15 : 0.87;
    var newW = Math.max(w * factor, w * 0.02);
    var newR0 = dataY - (dataY - yMin) * (newW / w);
    var newR1 = dataY + (yMax - dataY) * (newW / w);
    opt.yAxis[bandInfo.b].min = newR0;
    opt.yAxis[bandInfo.b].max = newR1;
    chart.setOption(opt);
  }}, {{ passive: false }});

  document.addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>
</body>
</html>
"""


class EChartsBackend(PlotBackend):
    @property
    def id(self) -> str:
        return "echarts"

    @property
    def name(self) -> str:
        return "ECharts"

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
        return _build_echarts_html(data_json, for_export)
