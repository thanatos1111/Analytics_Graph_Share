"""
Observable Plot backend: faceted plot (fy = unit band), shared x, built-in tooltip and zoom.
"""
from __future__ import annotations

import pandas as pd

from core.plot_backends.base import PlotBackend, prepare_chart_data, chart_data_to_json


def _build_observable_plot_html(data_json: str, for_export: bool) -> str:
    # Observable Plot from CDN (esm.sh or unpkg)
    plot_src = "https://esm.sh/@observablehq/plot@0.6.13"
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Chart</title>
<style>
  body {{ margin: 0; padding: 8px; font-family: system-ui, sans-serif; background: #fff; }}
  #plot-container {{ min-height: 400px; }}
</style>
</head>
<body>
<div id="plot-container"></div>
<script type="importmap">
{{ "imports": {{ "plot": "{plot_src}" }} }}
</script>
<script type="module">
import * as Plot from "plot";

var data = {data_json};
if (!data.bands || data.bands.length === 0) {{
  document.body.innerHTML = '<p>No parameters to plot</p>';
}} else {{
  var timeDisplay = data.timeDisplay || data.time || [];
  var rows = [];
  for (var b = 0; b < data.bands.length; b++) {{
    var band = data.bands[b];
    for (var i = 0; i < data.timeMs.length; i++) {{
      for (var p = 0; p < band.params.length; p++) {{
        var v = band.params[p].values[i];
        if (v != null && !isNaN(v)) {{
          rows.push({{
            time: data.timeMs[i],
            value: v,
            param: band.params[p].alias || band.params[p].name,
            paramName: band.params[p].name,
            timeDisplay: timeDisplay[i] || '',
            unit: band.unit,
            color: band.params[p].color
          }});
        }}
      }}
    }}
  }}

  var chart = Plot.plot({{
    marginTop: 20,
    marginBottom: 40,
    marginLeft: 50,
    marginRight: 20,
    height: Math.max(120 * data.bands.length, 300),
    grid: true,
    fy: {{ padding: 0.05, label: null }},
    x: {{ type: "linear", label: "Time", tickFormat: function(ms) {{
      var d = new Date(ms);
      return d.getFullYear() + "/" + (d.getMonth()+1) + "/" + d.getDate();
    }} }},
    y: {{ label: null }},
    color: (function() {{ var m = {{}}; rows.forEach(function(d) {{ if (!m[d.param]) m[d.param] = d.color; }}); var k = Object.keys(m); return {{ domain: k, range: k.map(function(kk) {{ return m[kk]; }}) }}; }})(),
    marks: [
      Plot.frame(),
      Plot.line(rows, {{ x: "time", y: "value", fy: "unit", stroke: "param" }})
    ]
  }});

  document.getElementById("plot-container").appendChild(chart);
}}
</script>
</body>
</html>
"""


class ObservablePlotBackend(PlotBackend):
    @property
    def id(self) -> str:
        return "observable_plot"

    @property
    def name(self) -> str:
        return "Observable Plot"

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
        return _build_observable_plot_html(data_json, for_export)
