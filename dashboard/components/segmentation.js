(function () {
  const SEGMENT_COLORS = {
    Residential: "#14b8a6",
    Commercial: "#38bdf8",
    Industrial: "#f97316",
    "Suspicious cluster": "#ef4444",
  };

  function renderSegmentationScatter(containerId, records) {
    const grouped = {};
    (records || []).forEach((record) => {
      const segment = record.segment || "Unknown";
      grouped[segment] = grouped[segment] || [];
      grouped[segment].push(record);
    });

    const traces = Object.entries(grouped).map(([segment, items]) => ({
      x: items.map((item) => Number(item.avg_consumption_kwh || 0)),
      y: items.map((item) => Number(item.night_usage_ratio || 0)),
      text: items.map((item) => `${item.meter_id} | ${item.area}`),
      mode: "markers",
      type: "scatter",
      name: segment,
      marker: {
        size: items.map((item) => 10 + Number(item.power_factor_loss || 0) * 120),
        color: SEGMENT_COLORS[segment] || "#94a3b8",
        opacity: 0.8,
      },
    }));

    SmartGridCharts.renderPlotly(containerId, traces, {
      xaxis: { title: "Average Consumption (kWh)", gridcolor: "rgba(147, 164, 187, 0.12)" },
      yaxis: { title: "Night Usage Ratio", gridcolor: "rgba(147, 164, 187, 0.12)" },
      legend: { orientation: "h" },
    });
  }

  function renderSegmentationSummary(containerId, summary) {
    SmartGridCharts.renderPlotly(
      containerId,
      [
        {
          type: "pie",
          labels: (summary || []).map((item) => item.segment),
          values: (summary || []).map((item) => Number(item.meter_count || 0)),
          hole: 0.55,
          marker: { colors: (summary || []).map((item) => SEGMENT_COLORS[item.segment] || "#94a3b8") },
          textinfo: "label+percent",
        },
      ],
      { showlegend: false }
    );
  }

  window.SmartGridSegmentation = {
    renderSegmentationScatter,
    renderSegmentationSummary,
  };
})();
