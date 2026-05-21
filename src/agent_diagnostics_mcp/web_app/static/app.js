(function () {
  var badge = document.getElementById("live-badge");
  var liveText = document.getElementById("live-text");
  var tbody = document.getElementById("reports");
  var limitSelect = document.getElementById("limit");
  var limitLabel = document.getElementById("limit-label");
  var jsonLink = document.getElementById("json-link");
  var categories = document.getElementById("categories");
  var severityColors = {
    low: "#22c55e",
    medium: "#eab308",
    high: "#ef4444",
  };

  function currentLimit() {
    var params = new URLSearchParams(window.location.search);
    var parsed = parseInt(params.get("limit") || "20", 10);

    if (Number.isNaN(parsed)) {
      return 20;
    }

    return Math.min(Math.max(parsed, 1), 100);
  }

  var limit = currentLimit();

  function setLimit(value) {
    limit = value;
    limitLabel.textContent = String(value);
    jsonLink.href = "/api/diagnostics?limit=" + value;

    if (limitSelect.querySelector('option[value="' + value + '"]')) {
      limitSelect.value = String(value);
    }
  }

  function appendText(parent, tagName, value) {
    var element = document.createElement(tagName);
    element.textContent = value || "";
    parent.appendChild(element);
    return element;
  }

  function formatTimestamp(value) {
    return value ? value.replace("T", " ").slice(0, 19) : "";
  }

  function buildRow(report, fresh) {
    var row = document.createElement("tr");
    row.dataset.id = String(report.id);

    if (fresh) {
      row.className = "row-fresh";
    }

    appendText(row, "td", String(report.id));
    appendText(row, "td", formatTimestamp(report.created_at));
    appendText(row, "td", report.category);

    var severityCell = document.createElement("td");
    var badge = appendText(severityCell, "span", report.severity);
    badge.className = "badge";
    badge.style.background = severityColors[report.severity] || "#94a3b8";
    row.appendChild(severityCell);

    appendText(row, "td", report.summary);
    appendText(row, "td", report.suggested_fix);

    return row;
  }

  function removeEmptyRow() {
    var empty = document.getElementById("empty-row");

    if (empty) {
      empty.remove();
    }
  }

  function trimRows() {
    while (tbody.children.length > limit) {
      tbody.removeChild(tbody.lastElementChild);
    }
  }

  function prependReport(report, fresh) {
    if (tbody.querySelector('[data-id="' + report.id + '"]')) {
      return;
    }

    removeEmptyRow();
    tbody.prepend(buildRow(report, fresh));
    trimRows();
  }

  function renderReports(reports) {
    tbody.replaceChildren();

    if (!reports.length) {
      var emptyRow = document.createElement("tr");
      emptyRow.id = "empty-row";
      var cell = appendText(emptyRow, "td", "No reports yet");
      cell.colSpan = 6;
      tbody.appendChild(emptyRow);
      return;
    }

    reports.forEach(function (report) {
      tbody.appendChild(buildRow(report, false));
    });
  }

  function renderCategories(items) {
    categories.replaceChildren();

    items.forEach(function (item) {
      var card = document.createElement("div");
      card.className = "cat-card";
      appendText(card, "strong", item.name);
      card.appendChild(document.createElement("br"));
      card.appendChild(document.createTextNode(item.description));
      categories.appendChild(card);
    });
  }

  function loadInitialData() {
    return Promise.all([
      fetch("/api/diagnostics/categories").then(function (response) {
        return response.json();
      }),
      fetch("/api/diagnostics?limit=" + limit).then(function (response) {
        return response.json();
      }),
    ]).then(function (results) {
      renderCategories(results[0]);
      renderReports(results[1]);
    });
  }

  function connectStream() {
    var es = new EventSource("/api/diagnostics/stream");

    es.addEventListener("open", function () {
      badge.className = "live-indicator connected";
      liveText.textContent = "Live";
    });

    es.addEventListener("error", function () {
      badge.className = "live-indicator disconnected";
      liveText.textContent = "Reconnecting...";
    });

    es.addEventListener("diagnostic", function (event) {
      prependReport(JSON.parse(event.data), true);
    });
  }

  tbody.addEventListener("animationend", function (event) {
    if (event.animationName === "row-flash") {
      event.target.parentElement.classList.remove("row-fresh");
    }
  });

  limitSelect.addEventListener("change", function () {
    limitSelect.form.submit();
  });

  setLimit(limit);
  loadInitialData().finally(connectStream);
}());
