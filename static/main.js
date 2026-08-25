/* Frontend logic: tabs, API calls, Chart.js dashboards. */
let pieChart = null;
let barChart = null;

const SENTIMENT_COLORS = {
  positive: "#30d158",
  neutral: "#ff9f0a",
  negative: "#ff453a",
};

document.addEventListener("DOMContentLoaded", () => {
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = "#86868b";

  // Tab switching
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.remove("hidden");
    });
  });

  const bind = (buttonId, statusId, fn) => {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      setStatus(statusId, "Analyzing… model inference in progress");
      try {
        await fn();
        setStatus(statusId, "");
      } catch (err) {
        setStatus(statusId, err.message, true);
      } finally {
        btn.disabled = false;
      }
    });
  };

  bind("btn-single", "status-single", async () => {
    const text = document.getElementById("single-text").value.trim();
    if (!text) throw new Error("Type something to analyze first.");
    const data = await postJSON("/analyze", new URLSearchParams({ text }));
    renderResults(data);
  });

  bind("btn-bulk", "status-bulk", async () => {
    const texts = document.getElementById("bulk-texts").value;
    const data = await postJSON("/analyze-bulk", new URLSearchParams({ texts }));
    renderResults(data);
  });

  bind("btn-csv", "status-csv", async () => {
    const fileInput = document.getElementById("csv-file");
    if (!fileInput.files.length) throw new Error("Choose a CSV file first.");
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    fd.append("column", document.getElementById("csv-column").value);
    const data = await postJSON("/analyze-csv", fd);
    renderResults(data);
  });
});

async function postJSON(url, body) {
  const res = await fetch(url, { method: "POST", body });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function setStatus(id, msg, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error-text", isError);
}

function renderResults(data) {
  const { summary, results } = data;
  document.getElementById("dashboard-section").classList.remove("hidden");
  document.getElementById("st-total").textContent = summary.total;
  document.getElementById("st-pos").textContent = summary.positive;
  document.getElementById("st-neu").textContent = summary.neutral;
  document.getElementById("st-neg").textContent = summary.negative;
  document.getElementById("st-conf").textContent =
    (summary.avg_confidence * 100).toFixed(1) + "%";

  drawPie(summary);
  drawBar(summary);

  const tbody = document.querySelector("#results-table tbody");
  tbody.innerHTML = "";
  results.slice(0, 200).forEach((r, i) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="td-num">${i + 1}</td>
      <td class="td-text"></td>
      <td><span class="badge ${r.label}">${r.label}</span></td>
      <td class="td-num">${(r.confidence * 100).toFixed(1)}%</td>`;
    const textCell = r.text.length > 140 ? r.text.slice(0, 140) + "…" : r.text;
    tr.children[1].textContent = textCell; // textContent avoids HTML injection
    tbody.appendChild(tr);
  });

  document.getElementById("dashboard-section").scrollIntoView({ behavior: "smooth" });
}

function drawPie(summary) {
  const ctx = document.getElementById("pieChart").getContext("2d");
  const values = [summary.positive, summary.neutral, summary.negative];
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Positive", "Neutral", "Negative"],
      datasets: [{
        data: values,
        backgroundColor: Object.values(SENTIMENT_COLORS),
        borderWidth: 4,
        borderColor: "#f5f5f7",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "bottom" } },
    },
  });
}

function drawBar(summary) {
  const ctx = document.getElementById("barChart").getContext("2d");
  const values = [summary.positive, summary.neutral, summary.negative];
  if (barChart) barChart.destroy();
  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Positive", "Neutral", "Negative"],
      datasets: [{
        label: "Count",
        data: values,
        backgroundColor: Object.values(SENTIMENT_COLORS),
        borderRadius: 10,
        barThickness: 54,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "rgba(0,0,0,.06)" } },
        x: { grid: { display: false } },
      },
    },
  });
}
