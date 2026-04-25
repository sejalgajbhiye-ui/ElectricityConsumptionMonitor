const STORAGE_KEY = "electricityConsumptionEntries";

const form = document.getElementById("entryForm");
const dateInput = document.getElementById("dateInput");
const monthInput = document.getElementById("monthInput");
const unitsInput = document.getElementById("unitsInput");
const unitsLabel = document.getElementById("unitsLabel");
const dateField = document.getElementById("dateField");
const monthField = document.getElementById("monthField");
const entryTypeInputs = document.querySelectorAll("input[name='entryType']");
const sampleBtn = document.getElementById("sampleBtn");
const clearBtn = document.getElementById("clearBtn");
const dataTable = document.getElementById("dataTable");
const emptyState = document.getElementById("emptyState");
const recordCount = document.getElementById("recordCount");
const alerts = document.getElementById("alerts");
const trendText = document.getElementById("trendText");

const totalUnitsEl = document.getElementById("totalUnits");
const estimatedBillEl = document.getElementById("estimatedBill");
const predictedUnitsEl = document.getElementById("predictedUnits");
const predictedBillEl = document.getElementById("predictedBill");
const previousSevenEl = document.getElementById("previousSeven");
const lastSevenEl = document.getElementById("lastSeven");
const sevenDiffEl = document.getElementById("sevenDiff");
const sevenPercentEl = document.getElementById("sevenPercent");

let entries = loadEntries();
let lineChart;
let barChart;

dateInput.value = toDateInputValue(new Date());
monthInput.value = toMonthInputValue(new Date());

function loadEntries() {
  const saved = localStorage.getItem(STORAGE_KEY);
  const parsed = saved ? JSON.parse(saved) : [];
  return parsed.map((entry) => ({
    ...entry,
    periodType: entry.periodType || "daily"
  }));
}

function saveEntries() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

function getSelectedEntryType() {
  return document.querySelector("input[name='entryType']:checked").value;
}

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toMonthInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function formatPeriod(entry) {
  if (entry.periodType === "monthly") {
    return new Date(entry.date + "-01T00:00:00").toLocaleDateString("en-IN", {
      month: "short",
      year: "numeric"
    });
  }

  return new Date(entry.date + "T00:00:00").toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function getEntryDate(entry) {
  return new Date((entry.periodType === "monthly" ? `${entry.date}-01` : entry.date) + "T00:00:00");
}

function formatUnits(value) {
  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 2
  });
}

function calculateBill(units) {
  // Progressive slab billing: each range is charged at its own rate.
  if (units <= 100) return units * 3;
  if (units <= 200) return 100 * 3 + (units - 100) * 5;
  return 100 * 3 + 100 * 5 + (units - 200) * 8;
}

function sortEntries() {
  entries.sort((a, b) => getEntryDate(a) - getEntryDate(b));
}

function getTrend(recentEntries) {
  if (recentEntries.length < 3) return "stable";

  const midpoint = Math.ceil(recentEntries.length / 2);
  const firstHalf = recentEntries.slice(0, midpoint);
  const secondHalf = recentEntries.slice(midpoint);
  const firstAverage = average(firstHalf.map((entry) => entry.units));
  const secondAverage = average(secondHalf.map((entry) => entry.units));
  const difference = secondAverage - firstAverage;

  if (Math.abs(difference) <= Math.max(firstAverage * 0.05, 3)) return "stable";
  return difference > 0 ? "increasing" : "decreasing";
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function predictUsage() {
  // Moving average gives a realistic baseline using only browser-side logic.
  if (!entries.length) {
    return { units: 0, bill: 0, trend: "stable", baseline: 0 };
  }

  const latestType = entries[entries.length - 1].periodType;
  const predictionEntries = entries.filter((entry) => entry.periodType === latestType);
  const recentEntries = predictionEntries.slice(-7);
  const movingAverageEntries = predictionEntries.slice(-5);
  const baseline = average(movingAverageEntries.map((entry) => entry.units));
  const trend = getTrend(recentEntries);
  let predictedUnits = baseline;

  if (trend === "increasing") predictedUnits *= 1.1;
  if (trend === "decreasing") predictedUnits *= 0.9;

  predictedUnits = Math.max(0, predictedUnits);

  return {
    units: predictedUnits,
    bill: calculateBill(predictedUnits),
    trend,
    baseline,
    periodType: latestType
  };
}

function getHighestUsage() {
  return entries.reduce(
    (highest, entry) => (entry.units > highest.units ? entry : highest),
    { units: -Infinity, date: "" }
  );
}

function getLatestTypeEntries() {
  if (!entries.length) return [];
  const latestType = entries[entries.length - 1].periodType;
  return entries.filter((entry) => entry.periodType === latestType);
}

function updateSummary() {
  const totalUnits = entries.reduce((sum, entry) => sum + entry.units, 0);
  const estimatedBill = calculateBill(totalUnits);
  const prediction = predictUsage();

  totalUnitsEl.textContent = formatUnits(totalUnits);
  estimatedBillEl.textContent = `₹${formatUnits(estimatedBill)}`;
  predictedUnitsEl.textContent = formatUnits(prediction.units);
  predictedBillEl.textContent = `₹${formatUnits(prediction.bill)}`;

  trendText.textContent = entries.length
    ? `Based on your recent ${prediction.periodType} usage trend, the next period may use about ${formatUnits(prediction.units)} units with an estimated bill of ₹${formatUnits(prediction.bill)}.`
    : "Based on your recent usage trend, add data to generate a prediction.";
}

function updateAlerts() {
  alerts.innerHTML = "";

  if (!entries.length) {
    addAlert("✅ Stable usage: add readings to start tracking trends.", "success");
    return;
  }

  const comparableEntries = getLatestTypeEntries();
  const latest = comparableEntries[comparableEntries.length - 1];
  const avgUnits = average(comparableEntries.map((entry) => entry.units));
  const trend = predictUsage().trend;

  if (latest.units > avgUnits) {
    addAlert(`⚠️ High usage detected: latest reading is above your average of ${formatUnits(avgUnits)} units.`, "warning");
  }

  if (trend === "increasing") addAlert("📈 Consumption increasing: recent readings are moving upward.", "warning");
  if (trend === "decreasing") addAlert("📉 Consumption decreasing: recent readings show improvement.", "success");
  if (trend === "stable") addAlert("✅ Stable usage: your recent readings are consistent.", "success");
}

function addAlert(message, type) {
  const item = document.createElement("div");
  item.className = `alert ${type}`;
  item.textContent = message;
  alerts.appendChild(item);
}

function updateComparison() {
  // Compare the most recent seven matching periods against the seven before them.
  const comparableEntries = getLatestTypeEntries();
  const lastSeven = comparableEntries.slice(-7);
  const previousSeven = comparableEntries.slice(-14, -7);
  const lastTotal = lastSeven.reduce((sum, entry) => sum + entry.units, 0);
  const previousTotal = previousSeven.reduce((sum, entry) => sum + entry.units, 0);
  const difference = lastTotal - previousTotal;
  const percent = previousTotal ? (difference / previousTotal) * 100 : 0;
  const arrow = difference > 0 ? "↑" : difference < 0 ? "↓" : "→";
  const className = difference > 0 ? "positive" : difference < 0 ? "negative" : "";

  previousSevenEl.textContent = `${formatUnits(previousTotal)} units`;
  lastSevenEl.textContent = `${formatUnits(lastTotal)} units`;
  sevenDiffEl.textContent = `${arrow} ${formatUnits(Math.abs(difference))} units`;
  sevenPercentEl.textContent = `${arrow} ${Math.abs(percent).toFixed(1)}%`;
  sevenDiffEl.className = className;
  sevenPercentEl.className = className;
}

function renderTable() {
  dataTable.innerHTML = "";
  recordCount.textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"}`;
  emptyState.classList.toggle("show", entries.length === 0);

  entries.forEach((entry) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatPeriod(entry)}</td>
      <td>${entry.periodType === "monthly" ? "Monthly" : "Daily"}</td>
      <td>${formatUnits(entry.units)}</td>
    `;
    dataTable.appendChild(row);
  });
}

function chartColors() {
  const highest = getHighestUsage();
  return entries.map((entry) => (entry.date === highest.date && entry.units === highest.units ? "#f4a62a" : "#16a878"));
}

function updateCharts() {
  // The highest usage period is colored differently in both charts.
  const labels = entries.map((entry) => formatPeriod(entry));
  const values = entries.map((entry) => entry.units);
  const colors = chartColors();

  const tooltipCallbacks = {
    label(context) {
      const value = context.raw;
      const highest = getHighestUsage();
      const suffix = value === highest.units ? " • Highest usage period" : "";
      return `${formatUnits(value)} units${suffix}`;
    }
  };

  if (!lineChart) {
    lineChart = new Chart(document.getElementById("lineChart"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Daily Units",
          data: values,
          borderColor: "#1769e0",
          backgroundColor: "rgba(23, 105, 224, 0.12)",
          pointBackgroundColor: colors,
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          pointRadius: 5,
          tension: 0.35,
          fill: true
        }]
      },
      options: getChartOptions(tooltipCallbacks)
    });
  } else {
    lineChart.data.labels = labels;
    lineChart.data.datasets[0].data = values;
    lineChart.data.datasets[0].pointBackgroundColor = colors;
    lineChart.update();
  }

  if (!barChart) {
    barChart = new Chart(document.getElementById("barChart"), {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Units",
          data: values,
          backgroundColor: colors,
          borderRadius: 10
        }]
      },
      options: getChartOptions(tooltipCallbacks)
    });
  } else {
    barChart.data.labels = labels;
    barChart.data.datasets[0].data = values;
    barChart.data.datasets[0].backgroundColor = colors;
    barChart.update();
  }
}

function getChartOptions(tooltipCallbacks) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#17324d",
          font: { family: "Poppins", weight: 600 }
        }
      },
      tooltip: {
        callbacks: tooltipCallbacks,
        backgroundColor: "#17324d",
        padding: 12,
        titleFont: { family: "Poppins", weight: 700 },
        bodyFont: { family: "Poppins" }
      }
    },
    scales: {
      x: {
        ticks: { color: "#677b8f", maxRotation: 45, minRotation: 0 },
        grid: { display: false }
      },
      y: {
        beginAtZero: true,
        ticks: { color: "#677b8f" },
        grid: { color: "rgba(103, 123, 143, 0.14)" }
      }
    }
  };
}

function animateMetrics() {
  document.querySelectorAll(".metric-card").forEach((card) => {
    card.classList.remove("updated");
    window.requestAnimationFrame(() => card.classList.add("updated"));
  });
}

function updateUI() {
  sortEntries();
  saveEntries();
  updateSummary();
  updateAlerts();
  updateComparison();
  renderTable();
  updateCharts();
  animateMetrics();
}

function addEntry(date, units, periodType) {
  const existing = entries.find((entry) => entry.date === date && entry.periodType === periodType);

  if (existing) {
    existing.units = units;
  } else {
    entries.push({ date, units, periodType });
  }

  updateUI();
}

function generateSampleData() {
  const today = new Date();
  const selectedType = getSelectedEntryType();

  if (selectedType === "monthly") {
    const monthlyUnits = [2480, 2615, 2730, 2685, 2810, 2965, 3075, 3190, 3325, 3450];

    entries = monthlyUnits.map((units, index) => {
      const date = new Date(today.getFullYear(), today.getMonth() - (monthlyUnits.length - index - 1), 1);

      return {
        date: toMonthInputValue(date),
        units,
        periodType: "monthly"
      };
    });

    updateUI();
    return;
  }

  const sampleUnits = [82, 91, 96, 108, 118, 126, 121, 134, 142, 136, 151, 158, 149, 166];

  entries = sampleUnits.map((units, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - (sampleUnits.length - index - 1));

    return {
      date: toDateInputValue(date),
      units,
      periodType: "daily"
    };
  });

  updateUI();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const periodType = getSelectedEntryType();
  const date = periodType === "monthly" ? monthInput.value : dateInput.value;
  const units = Number(unitsInput.value);

  if (!date || Number.isNaN(units) || units < 0) return;

  addEntry(date, units, periodType);
  unitsInput.value = "";
  unitsInput.focus();
});

sampleBtn.addEventListener("click", generateSampleData);

clearBtn.addEventListener("click", () => {
  if (!entries.length) return;
  const confirmed = window.confirm("Clear all saved consumption data?");
  if (!confirmed) return;

  entries = [];
  updateUI();
});

entryTypeInputs.forEach((input) => {
  input.addEventListener("change", () => {
    const isMonthly = getSelectedEntryType() === "monthly";

    dateField.classList.toggle("hidden", isMonthly);
    monthField.classList.toggle("hidden", !isMonthly);
    dateInput.required = !isMonthly;
    monthInput.required = isMonthly;
    unitsLabel.textContent = isMonthly ? "Monthly units consumed" : "Units consumed";
    unitsInput.placeholder = isMonthly ? "Example: 2850" : "Example: 135";
  });
});

updateUI();
