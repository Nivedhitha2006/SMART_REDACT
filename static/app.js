"use strict";

let currentDownloadToken = null;

const tabs              = document.querySelectorAll(".tab");
const tabContents       = document.querySelectorAll(".tab-content");
const inputText         = document.getElementById("input-text");
const fileInput         = document.getElementById("file-input");
const fileDropZone      = document.getElementById("file-drop-zone");
const dropFilename      = document.getElementById("drop-filename");
const btnRedact         = document.getElementById("btn-redact");
const errorMsg          = document.getElementById("error-msg");
const outputPlaceholder = document.getElementById("output-placeholder");
const outputResults     = document.getElementById("output-results");
const summaryGrid       = document.getElementById("summary-grid");
const outputHighlighted = document.getElementById("output-highlighted");
const outputPlain       = document.getElementById("output-plain");
const btnViewHighlight  = document.getElementById("btn-view-highlight");
const btnViewPlain      = document.getElementById("btn-view-plain");
const btnDownload       = document.getElementById("btn-download");
const btnLoadHistory    = document.getElementById("btn-load-history");
const historyTableWrap  = document.getElementById("history-table-wrap");
const historyTbody      = document.getElementById("history-tbody");

// Tab switching
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => { t.classList.remove("active"); t.setAttribute("aria-selected","false"); });
    tabContents.forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    tab.setAttribute("aria-selected","true");
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
  });
});

// File drag & drop
fileDropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) dropFilename.textContent = `✓ ${fileInput.files[0].name}`;
});
["dragover","dragenter"].forEach(evt =>
  fileDropZone.addEventListener(evt, e => { e.preventDefault(); fileDropZone.classList.add("drag-over"); })
);
["dragleave","dragend"].forEach(evt =>
  fileDropZone.addEventListener(evt, () => fileDropZone.classList.remove("drag-over"))
);
fileDropZone.addEventListener("drop", e => {
  e.preventDefault();
  fileDropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith(".txt")) {
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    dropFilename.textContent = `✓ ${file.name}`;
  } else {
    showError("Only .txt files are supported.");
  }
});

// Redact button
btnRedact.addEventListener("click", async () => {
  clearError();
  const formData = new FormData();
  const activeTab = document.querySelector(".tab.active").dataset.tab;

  if (activeTab === "upload") {
    const file = fileInput.files[0];
    if (!file) { showError("Please select a .txt file to upload."); return; }
    formData.append("file", file);
  } else {
    const text = inputText.value.trim();
    if (!text) { showError("Please paste some text to redact."); return; }
    formData.append("text", text);
  }

  document.querySelectorAll('input[name="entity_types"]:checked').forEach(cb => {
    formData.append("entity_types", cb.value);
  });
  if ([...formData.getAll("entity_types")].length === 0) {
    showError("Please select at least one entity type to redact.");
    return;
  }

  btnRedact.classList.add("loading");
  btnRedact.querySelector(".btn-icon").textContent = "⟳";
  btnRedact.childNodes[1].textContent = " Processing…";

  try {
    const res  = await fetch("/redact", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok || data.error) { showError(data.error || "An unexpected error occurred."); return; }
    renderResults(data);
  } catch (err) {
    showError("Network error. Is the Flask server running?");
  } finally {
    btnRedact.classList.remove("loading");
    btnRedact.querySelector(".btn-icon").textContent = "◈";
    btnRedact.childNodes[1].textContent = " Run Redaction";
  }
});

function renderResults(data) {
  const colorMap = { NAME:"name", EMAIL:"email", PHONE:"phone", AADHAAR:"aadhaar", PAN:"pan" };
  const total = Object.values(data.summary).reduce((a,b) => a+b, 0);

  summaryGrid.innerHTML = "";
  for (const [label, count] of Object.entries(data.summary)) {
    const card = document.createElement("div");
    card.className = `summary-card card-${colorMap[label]}`;
    card.innerHTML = `<span class="count">${count}</span><span class="label">${label}</span>`;
    summaryGrid.appendChild(card);
  }
  const totalCard = document.createElement("div");
  totalCard.className = "summary-card card-total";
  totalCard.innerHTML = `<span class="count">${total}</span><span class="label">TOTAL</span>`;
  summaryGrid.appendChild(totalCard);

  outputHighlighted.innerHTML = data.highlighted_html;
  outputPlain.textContent = data.redacted_text;

  outputHighlighted.hidden = false;
  outputPlain.hidden = true;
  btnViewHighlight.classList.add("active");
  btnViewPlain.classList.remove("active");

  currentDownloadToken = data.download_token;
  outputPlaceholder.hidden = true;
  outputResults.hidden = false;

  if (window.innerWidth < 820) {
    outputResults.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// View toggle
btnViewHighlight.addEventListener("click", () => {
  outputHighlighted.hidden = false;
  outputPlain.hidden = true;
  btnViewHighlight.classList.add("active");
  btnViewPlain.classList.remove("active");
});
btnViewPlain.addEventListener("click", () => {
  outputHighlighted.hidden = true;
  outputPlain.hidden = false;
  btnViewPlain.classList.add("active");
  btnViewHighlight.classList.remove("active");
});

// Download
btnDownload.addEventListener("click", () => {
  if (currentDownloadToken) window.location.href = `/download/${currentDownloadToken}`;
});

// Session history
btnLoadHistory.addEventListener("click", async () => {
  if (!historyTableWrap.hidden) {
    historyTableWrap.hidden = true;
    btnLoadHistory.textContent = "Load History";
    return;
  }
  try {
    const res  = await fetch("/history");
    const rows = await res.json();
    historyTbody.innerHTML = "";
    if (rows.length === 0) {
      historyTbody.innerHTML = `<tr><td colspan="9" style="color:var(--text-muted);text-align:center;padding:20px">No sessions logged yet.</td></tr>`;
    } else {
      rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.id}</td>
          <td>${row.timestamp}</td>
          <td>${row.source}</td>
          <td>${row.counts.NAME ?? 0}</td>
          <td>${row.counts.EMAIL ?? 0}</td>
          <td>${row.counts.PHONE ?? 0}</td>
          <td>${row.counts.AADHAAR ?? 0}</td>
          <td>${row.counts.PAN ?? 0}</td>
          <td><strong>${row.total}</strong></td>
        `;
        historyTbody.appendChild(tr);
      });
    }
    historyTableWrap.hidden = false;
    btnLoadHistory.textContent = "Hide History";
  } catch (err) {
    console.error("History fetch error:", err);
  }
});

function showError(msg) { errorMsg.textContent = msg; errorMsg.hidden = false; }
function clearError()   { errorMsg.textContent = ""; errorMsg.hidden = true; }