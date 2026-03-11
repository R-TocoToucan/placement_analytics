const NUMERIC_AXIS = [
  "CGPA",
  "Internships",
  "Projects",
  "Workshops",
  "AptitudeTestScore",
  "SoftSkillsRating",
  "SSC_Marks",
  "HSC_Marks"
];

const NUMERIC_FILTERS = [
  "Internships",
  "Projects",
  "AptitudeTestScore",
  "SoftSkillsRating",
  "SSC_Marks",
  "HSC_Marks"
];

const CATEGORICAL_FILTERS = ["ExtracurricularActivities", "PlacementTraining"];
const FACET_OPTIONS = ["PlacementStatus", "ExtracurricularActivities", "PlacementTraining"];

let META = {};

document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("/metadata");
  META = await res.json();
  buildToolbar();
  buildControls();
  fetchData();
});

function buildToolbar() {
  const selX = d3.select("#sel-x");
  const selY = d3.select("#sel-y");
  const selF = d3.select("#sel-facet");

  selX.selectAll("option")
    .data(NUMERIC_AXIS)
    .enter().append("option")
    .attr("value", d => d)
    .text(d => d)
    .property("selected", d => d === "AptitudeTestScore");

  selY.selectAll("option")
    .data(NUMERIC_AXIS)
    .enter().append("option")
    .attr("value", d => d)
    .text(d => d)
    .property("selected", d => d === "CGPA");

  selF.selectAll("option")
    .data(FACET_OPTIONS)
    .enter().append("option")
    .attr("value", d => d)
    .text(d => d)
    .property("selected", d => d === "PlacementStatus");

  selX.on("change", fetchData);
  selY.on("change", fetchData);
  selF.on("change", fetchData);
}

function buildControls() {
  const box = d3.select("#controls");
  box.selectAll("*").remove();

  NUMERIC_FILTERS.forEach(col => {
    const m = META[col];
    const step = (col === "SoftSkillsRating") ? 0.1 : 1;

    const g = box.append("div").attr("class", "ctrl-group");
    g.append("span").attr("class", "title").text(col);

    const row = g.append("div").attr("class", "range-row");
    row.append("span").attr("class", "range-label").attr("id", "lbl-min-" + col).text(m.min);

    const slider = row.append("input")
      .attr("type", "range")
      .attr("min", m.min)
      .attr("max", m.max)
      .attr("step", step)
      .attr("value", m.max)
      .attr("id", "sl-max-" + col);

    row.append("span").attr("class", "range-label").attr("id", "lbl-max-" + col).text(m.max);

    slider.on("input", function () {
      document.getElementById("lbl-max-" + col).textContent = this.value;
      fetchData();
    });
  });

  CATEGORICAL_FILTERS.forEach(col => {
    const g = box.append("div").attr("class", "radio-group");
    g.append("span").attr("class", "title").text(col);

    const row = g.append("div").attr("class", "radio-row");
    row.append("label").html(`<input type="radio" name="${col}" value="True" checked> True`);
    row.append("label").html(`<input type="radio" name="${col}" value="False"> False`);

    row.selectAll("input[type=radio]").on("change", fetchData);
  });
}

function gatherParams() {
  const p = new URLSearchParams();

  p.set("x", document.getElementById("sel-x").value);
  p.set("y", document.getElementById("sel-y").value);
  p.set("facet", document.getElementById("sel-facet").value);

  NUMERIC_FILTERS.forEach(col => {
    const m = META[col];
    const hi = document.getElementById("sl-max-" + col);
    p.set(col + "_min", m.min);
    p.set(col + "_max", hi ? hi.value : m.max);
  });

  CATEGORICAL_FILTERS.forEach(col => {
    const checked = document.querySelector(`input[name="${col}"]:checked`);
    if (checked) p.set(col, checked.value);
  });

  return p;
}

let fetchTimer = null;
function fetchData() {
  clearTimeout(fetchTimer);
  fetchTimer = setTimeout(async () => {
    const p = gatherParams();
    const res = await fetch("/query?" + p.toString());
    const json = await res.json();
    renderCharts(json);
  }, 100);
}

const W = 420, H = 360, M = { t: 30, r: 20, b: 50, l: 55 };
const iw = W - M.l - M.r, ih = H - M.t - M.b;

function renderCharts({ data, stats, facet_values }) {
  const container = d3.select("#charts");
  container.selectAll("*").remove();

  const xCol = document.getElementById("sel-x").value;
  const yCol = document.getElementById("sel-y").value;
  const facetCol = document.getElementById("sel-facet").value;

  // Always use all known facet values so panels don't disappear when filtered to zero
  const allFacets = (META[facetCol] && META[facetCol].values)
    ? META[facetCol].values.map(v => String(v))
    : (facet_values || []).map(v => String(v));

  if (allFacets.length === 0) return;
  if (!data) data = [];

  const xm = META[xCol];
  const ym = META[yCol];

  const xDom = xm ? [Math.floor(+xm.min), Math.ceil(+xm.max)] : d3.extent(data, d => +d.x);
  const yDom = ym ? [Math.floor(+ym.min), Math.ceil(+ym.max)] : d3.extent(data, d => +d.y);

  const xScale = d3.scaleLinear().domain(xDom).nice().range([0, iw]);
  const yScale = d3.scaleLinear().domain(yDom).nice().range([ih, 0]);

  allFacets.forEach((fv) => {
    const panel = container.append("div").attr("class", "chart-panel");
    panel.append("h3").text(`${facetCol}: ${String(fv)}`);

    const svg = panel.append("svg").attr("width", W).attr("height", H);

    const plotG = svg.append("g").attr("transform", `translate(${M.l},${M.t})`);
    const axG = svg.append("g").attr("transform", `translate(${M.l},${M.t})`);

    axG.append("g")
      .attr("class", "axis")
      .attr("transform", `translate(0,${ih})`)
      .call(d3.axisBottom(xScale).ticks(6));

    axG.append("g")
      .attr("class", "axis")
      .call(d3.axisLeft(yScale).ticks(6));

    axG.append("text")
      .attr("class", "axis-label")
      .attr("x", iw / 2)
      .attr("y", ih + 40)
      .attr("text-anchor", "middle")
      .text(xCol);

    axG.append("text")
      .attr("class", "axis-label")
      .attr("transform", "rotate(-90)")
      .attr("x", -ih / 2)
      .attr("y", -42)
      .attr("text-anchor", "middle")
      .text(yCol);

    const subset = data.filter(d => String(d.facet) === String(fv));

    plotG.selectAll("circle")
      .data(subset)
      .enter().append("circle")
      .attr("class", "dot")
      .attr("cx", d => xScale(+d.x))
      .attr("cy", d => yScale(+d.y))
      .attr("r", 2.2);

    const st = (stats && stats[String(fv)]) ? stats[String(fv)] : {};
    const reg = st.regression || {};

    if (reg.slope != null && reg.intercept != null) {
      const x1 = xScale.domain()[0], x2 = xScale.domain()[1];
      const y1v = reg.slope * x1 + reg.intercept;
      const y2v = reg.slope * x2 + reg.intercept;

      plotG.append("line")
        .attr("class", "reg")
        .attr("x1", xScale(x1))
        .attr("y1", yScale(y1v))
        .attr("x2", xScale(x2))
        .attr("y2", yScale(y2v));
    }
  });
}