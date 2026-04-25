const STORAGE_KEY = "puneWeatherElectricityDashboard";
const WEATHER_CITY = "Pune";
const PUNE_LATITUDE = 18.5204;
const PUNE_LONGITUDE = 73.8567;

const state = loadState();
let activeView = "daily";
let weatherState = {
  status: "loading",
  city: WEATHER_CITY,
  temperatureCelsius: null,
  factor: 1,
  label: "Fetching weather",
  message: "Fetching Pune weather..."
};
let lineChart;
let barChart;

const navButtons = document.querySelectorAll(".nav-btn");
const panels = {
  daily: document.getElementById("dailyPanel"),
  monthly: document.getElementById("monthlyPanel"),
  prediction: document.getElementById("predictionPanel")
};

const dailyForm = document.getElementById("dailyForm");
const monthlyForm = document.getElementById("monthlyForm");
const predictionForm = document.getElementById("predictionForm");
const alerts = document.getElementById("alerts");
const trendText = document.getElementById("trendText");
const dataTable = document.getElementById("dataTable");
const emptyState = document.getElementById("emptyState");
const recordCount = document.getElementById("recordCount");
const billBreakdown = document.getElementById("billBreakdown");

const totalUnitsEl = document.getElementById("totalUnits");
const estimatedBillEl = document.getElementById("estimatedBill");
const predictedUnitsEl = document.getElementById("predictedUnits");
const predictedBillEl = document.getElementById("predictedBill");
const insightTitle = document.getElementById("insightTitle");
const tableTitle = document.getElementById("tableTitle");
const lineTitle = document.getElementById("lineTitle");
const barTitle = document.getElementById("barTitle");
const totalLabel = document.getElementById("totalLabel");
const billLabel = document.getElementById("billLabel");

const dailyDate = document.getElementById("dailyDate");
const dailyUnits = document.getElementById("dailyUnits");
const monthlyMonth = document.getElementById("monthlyMonth");
const monthlyUnits = document.getElementById("monthlyUnits");
const monthOne = document.getElementById("monthOne");
const monthTwo = document.getElementById("monthTwo");
const monthThree = document.getElementById("monthThree");
const temperatureText = document.getElementById("temperatureText");
const weatherMessage = document.getElementById("weatherMessage");

dailyDate.value = toDateInputValue(new Date());
monthlyMonth.value = toMonthInputValue(new Date());
fillPredictionForm();

const MSEDCL_SLABS = [
  { limit: 100, rate: 3.44, label: "0-100 units" },
  { limit: 300, rate: 7.34, label: "101-300 units" },
  { limit: 500, rate: 10.26, label: "301-500 units" },
  { limit: Infinity, rate: 12.5, label: "Above 500 units" }
];
function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved ? JSON.parse(saved) : { daily: [], monthly: [], prediction: null };
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function toDateInputValue(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function toMonthInputValue(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function formatDate(dateString) {
  return new Date(`${dateString}T00:00:00`).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

function formatMonth(monthString) {
  return new Date(`${monthString}-01T00:00:00`).toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric"
  });
}

function formatUnits(value) {
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatCurrency(value) {
  return `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function getWeatherDetails() {
  return weatherState;
}

function getWeatherFromTemperature(temperatureCelsius, city = WEATHER_CITY) {
  if (temperatureCelsius > 30) {
    return {
      status: "ready",
      city,
      temperatureCelsius,
      factor: 1.2,
      label: "Hot weather",
      icon: "🌡️",
      message: "Hot weather → usage may increase"
    };
  }

  if (temperatureCelsius < 20) {
    return {
      status: "ready",
      city,
      temperatureCelsius,
      factor: 1.1,
      label: "Cold weather",
      icon: "🌡️",
      message: "Cold weather → usage may increase"
    };
  }

  return {
    status: "ready",
    city,
    temperatureCelsius,
    factor: 1,
    label: "Normal weather",
    icon: "🌡️",
    message: "Normal weather → no extra adjustment"
  };
}

async function fetchCurrentWeather() {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${PUNE_LATITUDE}&longitude=${PUNE_LONGITUDE}&current=temperature_2m`;
    const response = await fetch(url);
    if (!response.ok) throw new Error("Weather request failed");

    const data = await response.json();
    const temperatureCelsius = data.current.temperature_2m;
    weatherState = getWeatherFromTemperature(temperatureCelsius, WEATHER_CITY);
    refreshStoredPrediction();
  } catch (error) {
    weatherState = {
      status: "error",
      city: WEATHER_CITY,
      temperatureCelsius: null,
      factor: 1,
      label: "Weather unavailable",
      icon: "🌡️",
      message: "Could not fetch Pune weather right now. Prediction is shown without weather adjustment."
    };
  }

  render();
}

function calculateBill(units) {
  let remaining = Math.max(0, units);
  let previousLimit = 0;
  let energyCharge = 0;
  const lines = [];

  for (const slab of MSEDCL_SLABS) {
    if (remaining <= 0) break;
    const slabUnits = Math.min(remaining, slab.limit - previousLimit);
    const charge = slabUnits * slab.rate;
    energyCharge += charge;
    lines.push({ ...slab, units: slabUnits, charge });
    remaining -= slabUnits;
    previousLimit = slab.limit;
  }

  const fixedCharge = getFixedCharge(units);
  const total = energyCharge + fixedCharge;
  return { energyCharge, fixedCharge, total, lines };
}

function getFixedCharge(units) {
  if (units <= 100) return 95;
  if (units <= 300) return 120;
  return 170;
}

function addOrUpdateRecord(collection, record, key) {
  const index = collection.findIndex((item) => item[key] === record[key]);
  if (index >= 0) collection[index] = record;
  else collection.push(record);
}

function sortRecords() {
  state.daily.sort((a, b) => new Date(a.date) - new Date(b.date));
  state.monthly.sort((a, b) => new Date(`${a.month}-01`) - new Date(`${b.month}-01`));
}

function predictFromThreeMonths(m1, m2, m3) {
  const weatherDetails = getWeatherDetails();
  const weighted = m1 * 0.2 + m2 * 0.3 + m3 * 0.5;
  const growth = ((m2 - m1) + (m3 - m2)) / 2;
  const trendPrediction = m3 + growth;
  const basePrediction = (weighted + trendPrediction) / 2;
  const predictedUnits = Math.max(0, basePrediction * weatherDetails.factor);
  const bill = calculateBill(predictedUnits);

  return {
    months: [m1, m2, m3],
    temperatureCelsius: weatherDetails.temperatureCelsius,
    weighted,
    growth,
    trendPrediction,
    basePrediction,
    predictedUnits,
    predictedBill: bill.total,
    trend: getTrend([m1, m2, m3]),
    createdAt: new Date().toISOString()
  };
}

function refreshStoredPrediction() {
  if (!state.prediction) return;
  const [m1, m2, m3] = state.prediction.months;
  state.prediction = predictFromThreeMonths(m1, m2, m3);
}

function getTrend(values) {
  if (values.length < 2) return "stable";
  const first = values[0];
  const last = values[values.length - 1];
  const threshold = Math.max(first * 0.05, 2);
  if (last - first > threshold) return "increasing";
  if (first - last > threshold) return "decreasing";
  return "stable";
}

function fillPredictionForm() {
  if (!state.prediction) return;
  monthOne.value = state.prediction.months[0];
  monthTwo.value = state.prediction.months[1];
  monthThree.value = state.prediction.months[2];
}

function switchView(view) {
  activeView = view;
  navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle("active", name === view));
  render();
}

function render() {
  sortRecords();
  saveState();
  const viewData = getViewData();

  totalLabel.textContent = activeView === "prediction" ? "Past 3-Month Units" : "Total Units";
  billLabel.textContent = activeView === "prediction" ? "Past Units Bill" : "Estimated Bill";
  insightTitle.textContent = viewData.title;
  tableTitle.textContent = viewData.tableTitle;
  lineTitle.textContent = viewData.lineTitle;
  barTitle.textContent = viewData.barTitle;

  totalUnitsEl.textContent = formatUnits(viewData.totalUnits);
  estimatedBillEl.textContent = formatCurrency(viewData.bill.total);
  predictedUnitsEl.textContent = formatUnits(viewData.predictedUnits);
  predictedBillEl.textContent = formatCurrency(viewData.predictedBill);
  trendText.textContent = viewData.trendText;
  renderWeatherStatus();

  renderAlerts(viewData);
  renderBreakdown(viewData.bill);
  renderTable(viewData.rows);
  updateCharts(viewData.chartLabels, viewData.chartValues);
  animateMetrics();
}

function getViewData() {
  if (activeView === "monthly") return getMonthlyViewData();
  if (activeView === "prediction") return getPredictionViewData();
  return getDailyViewData();
}

function getDailyViewData() {
  const rows = state.daily.map((record) => ({
    period: formatDate(record.date),
    units: record.units,
    bill: calculateBill(record.units * 30).total
  }));
  const totalUnits = state.daily.reduce((sum, record) => sum + record.units, 0);
  const average = state.daily.length ? totalUnits / state.daily.length : 0;
  const predictedUnits = average * 30 * getWeatherDetails().factor;

  return {
    title: "Daily Weather Analysis",
    tableTitle: "Daily Records",
    lineTitle: "Daily Consumption Trend",
    barTitle: "Daily Units Comparison",
    rows,
    chartLabels: state.daily.map((record) => formatDate(record.date)),
    chartValues: state.daily.map((record) => record.units),
    totalUnits,
    bill: calculateBill(totalUnits * 30),
    predictedUnits,
    predictedBill: calculateBill(predictedUnits).total,
    trend: getTrend(state.daily.map((record) => record.units)),
    trendText: state.daily.length
      ? `Daily records are converted to a monthly estimate and adjusted using current Pune temperature.`
      : "Add daily units to estimate monthly bill impact using automatic Pune weather."
  };
}

function getMonthlyViewData() {
  const rows = state.monthly.map((record) => ({
    period: formatMonth(record.month),
    units: record.units,
    bill: calculateBill(record.units).total
  }));
  const totalUnits = state.monthly.reduce((sum, record) => sum + record.units, 0);
  const average = state.monthly.length ? totalUnits / state.monthly.length : 0;
  const predictedUnits = average * getWeatherDetails().factor;

  return {
    title: "Monthly Weather Analysis",
    tableTitle: "Monthly Records",
    lineTitle: "Monthly Consumption Trend",
    barTitle: "Monthly Units Comparison",
    rows,
    chartLabels: state.monthly.map((record) => formatMonth(record.month)),
    chartValues: state.monthly.map((record) => record.units),
    totalUnits,
    bill: calculateBill(totalUnits),
    predictedUnits,
    predictedBill: calculateBill(predictedUnits).total,
    trend: getTrend(state.monthly.map((record) => record.units)),
    trendText: state.monthly.length
      ? `Monthly average is adjusted using current Pune temperature.`
      : "Add monthly units to estimate next month using automatic Pune weather."
  };
}

function getPredictionViewData() {
  const data = state.prediction;
  if (!data) {
    return {
      title: "3-Month Prediction",
      tableTitle: "Prediction Inputs",
      lineTitle: "3-Month Prediction Trend",
      barTitle: "Past Units vs Prediction",
      rows: [],
      chartLabels: ["Month 1", "Month 2", "Month 3", "Predicted"],
      chartValues: [0, 0, 0, 0],
      totalUnits: 0,
      bill: calculateBill(0),
      predictedUnits: 0,
      predictedBill: 0,
      trend: "stable",
      trendText: "Enter the last 3 months to predict the next month using automatic Pune weather."
    };
  }

  const rows = data.months.map((units, index) => ({
    period: `Month ${index + 1}`,
    units,
    bill: calculateBill(units).total
  }));
  const totalUnits = data.months.reduce((sum, units) => sum + units, 0);

  return {
    title: "3-Month Weather Prediction",
    tableTitle: "Prediction Inputs",
    lineTitle: "3-Month Prediction Trend",
    barTitle: "Past Units vs Prediction",
    rows,
    chartLabels: ["Month 1", "Month 2", "Month 3", "Predicted"],
    chartValues: [...data.months, data.predictedUnits],
    totalUnits,
    bill: calculateBill(totalUnits),
    predictedUnits: data.predictedUnits,
    predictedBill: data.predictedBill,
    trend: data.trend,
    trendText: `Based on weighted usage, trend growth, and current Pune weather, next month may use ${formatUnits(data.predictedUnits)} units.`
  };
}

function renderAlerts(viewData) {
  alerts.innerHTML = "";
  const weather = getWeatherDetails();
  const weatherType = weather.factor > 1 ? "warning" : "success";
  addAlert(`${weather.icon} ${weather.message}`, weatherType);

  if (viewData.predictedUnits > 300) addAlert("⚠️ High usage alert: prediction may enter expensive MSEDCL slabs.", "warning");
  if (viewData.trend === "increasing") addAlert("📈 Increasing trend detected in recent usage.", "warning");
  else if (viewData.trend === "decreasing") addAlert("📉 Decreasing trend detected in recent usage.", "success");
  else addAlert("✅ Stable usage trend.", "success");
}

function addAlert(message, type) {
  const item = document.createElement("div");
  item.className = `alert ${type}`;
  item.textContent = message;
  alerts.appendChild(item);
}

function renderBreakdown(bill) {
  billBreakdown.innerHTML = "";
  const activeLines = bill.lines.length ? bill.lines : [{ label: "0 units", units: 0, rate: 0, charge: 0 }];

  activeLines.forEach((line) => {
    const item = document.createElement("div");
    item.innerHTML = `<span>${line.label}</span><strong>${formatUnits(line.units)} x ₹${line.rate} = ${formatCurrency(line.charge)}</strong>`;
    billBreakdown.appendChild(item);
  });

  const fixed = document.createElement("div");
  fixed.innerHTML = `<span>Fixed charge</span><strong>${formatCurrency(bill.fixedCharge)}</strong>`;
  billBreakdown.appendChild(fixed);

}

function renderTable(rows) {
  dataTable.innerHTML = "";
  emptyState.classList.toggle("show", rows.length === 0);
  recordCount.textContent = `${rows.length} ${rows.length === 1 ? "record" : "records"}`;

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.period}</td>
      <td>${formatUnits(row.units)}</td>
      <td>${formatCurrency(row.bill)}</td>
    `;
    dataTable.appendChild(tr);
  });
}

function renderWeatherStatus() {
  const weather = getWeatherDetails();
  if (weather.temperatureCelsius === null) {
    temperatureText.textContent = "🌡️ Pune weather unavailable";
  } else {
    temperatureText.textContent = `🌡️ ${Math.round(weather.temperatureCelsius)}°C in ${weather.city}`;
  }
  weatherMessage.textContent = weather.message;
}

function updateCharts(labels, values) {
  const colors = values.map((_, index) => (index === values.length - 1 && activeView === "prediction" ? "#f4a62a" : "#16a878"));
  const tooltipCallbacks = {
    label(context) {
      return `${context.dataset.label}: ${formatUnits(context.raw)} units`;
    }
  };

  if (!lineChart) {
    lineChart = new Chart(document.getElementById("lineChart"), {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Units",
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
        datasets: [{ label: "Units", data: values, backgroundColor: colors, borderRadius: 8 }]
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
      legend: { labels: { color: "#17324d", font: { family: "Poppins", weight: 600 } } },
      tooltip: { callbacks: tooltipCallbacks, backgroundColor: "#17324d", padding: 12 }
    },
    scales: {
      x: { ticks: { color: "#677b8f" }, grid: { display: false } },
      y: { beginAtZero: true, ticks: { color: "#677b8f" }, grid: { color: "rgba(103, 123, 143, 0.14)" } }
    }
  };
}

function animateMetrics() {
  document.querySelectorAll(".metric-card").forEach((card) => {
    card.classList.remove("updated");
    window.requestAnimationFrame(() => card.classList.add("updated"));
  });
}

dailyForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const units = Number(dailyUnits.value);
  if (Number.isNaN(units) || units < 0) return;
  addOrUpdateRecord(state.daily, { date: dailyDate.value, units }, "date");
  dailyUnits.value = "";
  render();
});

monthlyForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const units = Number(monthlyUnits.value);
  if (Number.isNaN(units) || units < 0) return;
  addOrUpdateRecord(state.monthly, { month: monthlyMonth.value, units }, "month");
  monthlyUnits.value = "";
  render();
});

predictionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const values = [Number(monthOne.value), Number(monthTwo.value), Number(monthThree.value)];
  if (values.some((value) => Number.isNaN(value) || value < 0)) return;
  state.prediction = predictFromThreeMonths(values[0], values[1], values[2]);
  render();
});

document.querySelectorAll("[data-clear]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = button.dataset.clear;
    if (target === "daily") state.daily = [];
    if (target === "monthly") state.monthly = [];
    if (target === "prediction") {
      state.prediction = null;
      predictionForm.reset();
    }
    render();
  });
});

navButtons.forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

render();
fetchCurrentWeather();
