(function () {
  function renderGridGraph(containerId, network) {
    const container = document.getElementById(containerId);
    if (!container) {
      return;
    }
    container.innerHTML = "";

    const nodes = (network?.nodes || []).map((node) => ({ ...node }));
    const links = (network?.edges || []).map((edge) => ({ ...edge }));
    if (!nodes.length || typeof d3 === "undefined") {
      container.innerHTML = '<div class="empty-state">No grid network data available.</div>';
      return;
    }

    const width = container.clientWidth || 920;
    const height = 420;
    const svg = d3.create("svg").attr("viewBox", `0 0 ${width} ${height}`);
    const colors = {
      substation: "#f97316",
      feeder: "#14b8a6",
      distribution_node: "#38bdf8",
      meter: "#ef4444",
    };

    const simulation = d3
      .forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => (d.target.kind === "meter" ? 42 : 86)))
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .attr("stroke", "rgba(148, 163, 184, 0.26)")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 1.2);

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => {
        if (d.kind === "substation") return 11;
        if (d.kind === "feeder") return 8;
        if (d.kind === "distribution_node") return 6;
        return Math.max(4, Math.min(8, 4 + Number(d.risk_score || 0) / 25));
      })
      .attr("fill", (d) => colors[d.kind] || "#94a3b8")
      .attr("opacity", 0.88);

    node.append("title").text((d) => `${d.id} | ${d.kind}`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);
      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    });

    container.appendChild(svg.node());
  }

  window.SmartGridGraph = {
    renderGridGraph,
  };
})();
