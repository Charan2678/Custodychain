/* ================================================================
   CustodyChain — app.js
   Handles: form input, API calls, timeline rendering, expandable rows
   ================================================================ */

const API_BASE = "http://localhost:8000";

// ---- Sample evidence (pre-loaded for quick demo) ----
const SAMPLE_EVIDENCE = {
  name: "Case-2026-0912-Exhibit-A",
  content: "CASE_FILE_2026_0912\nSuspect device seized at 14:02.\nHash chain begins here.",
};

// ---- Element refs ----
const runBtn      = document.getElementById("runDemoBtn");
const sampleBtn   = document.getElementById("runSampleBtn");
const btnText     = document.getElementById("btnText");
const btnIcon     = document.getElementById("btnIcon");
const banner      = document.getElementById("verdictBanner");
const resultsSection = document.getElementById("resultsSection");
const timeline    = document.getElementById("timeline");
const tamperToggle = document.getElementById("tamperToggle");
const toggleDesc   = document.getElementById("toggleDescription");

// ---- Tamper toggle hint ----
function updateToggleDesc() {
  if (tamperToggle.checked) {
    toggleDesc.textContent = "On — Export Tool will silently alter content and still report success";
    toggleDesc.style.color = "var(--danger)";
  } else {
    toggleDesc.textContent = "Off — Export Tool passes evidence through unchanged (expect Chain Intact)";
    toggleDesc.style.color = "var(--success)";
  }
}
tamperToggle.addEventListener("change", updateToggleDesc);
updateToggleDesc();

// ---- Quick sample demo ----
sampleBtn.addEventListener("click", () => {
  runVerification(SAMPLE_EVIDENCE.name, SAMPLE_EVIDENCE.content, tamperToggle.checked);
});

// ---- Manual form ----
runBtn.addEventListener("click", () => {
  const name           = document.getElementById("evidenceName").value.trim() || "Untitled-Evidence";
  const content        = document.getElementById("evidenceContent").value.trim();
  const simulateTamper = tamperToggle.checked;

  if (!content) {
    const ta = document.getElementById("evidenceContent");
    ta.style.borderColor = "var(--danger)";
    ta.style.boxShadow   = "0 0 0 3px rgba(248,113,113,0.15)";
    setTimeout(() => { ta.style.borderColor = ""; ta.style.boxShadow = ""; }, 1500);
    ta.focus();
    return;
  }
  runVerification(name, content, simulateTamper);
});

// ---- Shared verification runner ----
async function runVerification(name, content, simulateTamper) {
  setLoading(true);
  clearResults();

  try {
    // Step 1: Create evidence and run it through the full pipeline
    const createRes = await fetch(`${API_BASE}/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, content, simulate_tamper: simulateTamper }),
    });

    if (!createRes.ok) {
      const err = await createRes.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${createRes.status}`);
    }

    const created = await createRes.json();
    const evidenceId = created.evidence_id;

    // Step 2: Run the Verifier
    const verifyRes = await fetch(`${API_BASE}/evidence/${evidenceId}/verify`);

    if (!verifyRes.ok) {
      const err = await verifyRes.json().catch(() => ({}));
      throw new Error(err.detail || `Verifier error: ${verifyRes.status}`);
    }

    const verifyData = await verifyRes.json();

    // Render
    renderResults(verifyData, { name });

  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

// ---- Loading state ----
function setLoading(loading) {
  runBtn.disabled    = loading;
  sampleBtn.disabled = loading;
  if (loading) {
    btnText.textContent = "Running…";
    btnIcon.innerHTML = '<span class="spinner"></span>';
  } else {
    btnText.textContent = "Run verification";
    btnIcon.textContent = "▶";
  }
}

// ---- Clear previous results ----
function clearResults() {
  banner.className = "verdict-banner hidden";
  resultsSection.classList.add("hidden");
  timeline.innerHTML = "";
}

// ---- Render results (verdict + timeline) ----
function renderResults(data, meta) {
  // Meta strip
  document.getElementById("resultEvidenceId").textContent   = "#" + data.evidence_id;
  document.getElementById("resultEvidenceName").textContent = meta.name;
  document.getElementById("resultCheckedAt").textContent    = new Date().toLocaleTimeString();

  // Verdict banner
  const isIntact = data.final_verdict === "CHAIN_INTACT";
  banner.textContent = isIntact
    ? "✓  Chain intact — evidence verified end to end"
    : "✕  " + formatVerdict(data.final_verdict);
  banner.className = "verdict-banner " + (isIntact ? "ok" : "broken");

  // Timeline
  timeline.innerHTML = "";
  let brokenSeen = false;

  data.steps.forEach((step, index) => {
    let rowClass = "ok";
    let tag = "";

    if (!step.verified) {
      rowClass = "broken";
      brokenSeen = true;
      tag = '<span class="step-tag broken">Tamper detected</span>';
    } else if (brokenSeen) {
      rowClass = "downstream";
      tag = '<span class="step-tag downstream">Downstream of break</span>';
    }

    const hashMismatch = !step.verified && step.handler_name !== "Collector";
    const detail = buildDetail(step, hashMismatch, rowClass);

    const row = document.createElement("div");
    row.className = "step-row " + rowClass;
    row.style.animationDelay = `${index * 60}ms`;
    row.innerHTML = `
      <div class="step-main">
        <span class="step-icon ${rowClass}">${step.verified ? "✓" : "✕"}</span>
        <span class="step-name">
          ${escHtml(step.step_order + ". " + step.handler_name)}
          ${tag}
        </span>
        <span class="step-status">Declared: <strong>${escHtml(step.declared_status)}</strong></span>
        <span class="step-hash">${truncHash(step.actual_hash)}</span>
        <span class="step-expand">▾</span>
      </div>
      <div class="step-detail">${detail}</div>
    `;

    // Expand on click
    row.querySelector(".step-main").addEventListener("click", () => {
      row.classList.toggle("expanded");
    });

    timeline.appendChild(row);
  });

  resultsSection.classList.remove("hidden");
}

// ---- Build expandable hash detail ----
function buildDetail(step, hashMismatch, rowClass) {
  const afterClass  = hashMismatch ? "hash-value mismatch" : "hash-value match";
  const actualClass = hashMismatch ? "hash-value mismatch" : "hash-value match";

  let verdictMsg = "";
  if (step.handler_name === "Collector") {
    verdictMsg = `<div class="detail-verdict ok">✓ Trusted origin — this is the baseline hash for the chain.</div>`;
  } else if (step.verified) {
    verdictMsg = `<div class="detail-verdict ok">✓ Verified — actual hash matches previous step. Evidence unchanged.</div>`;
  } else if (rowClass === "downstream") {
    verdictMsg = `<div class="detail-verdict warn">⚠ Downstream of break — chain already compromised upstream.</div>`;
  } else {
    verdictMsg = `<div class="detail-verdict fail">✕ Tamper detected — actual hash does not match input. This step silently altered the evidence despite declaring "success".</div>`;
  }

  return `
    <div class="hash-field">
      <div class="hash-label">Hash before (declared by handler)</div>
      <div class="hash-value">${escHtml(step.hash_before)}</div>
    </div>
    <div class="hash-field">
      <div class="hash-label">Hash after (declared by handler)</div>
      <div class="${afterClass}">${escHtml(step.hash_after)}</div>
    </div>
    <div class="hash-field">
      <div class="hash-label">Actual hash (independently recomputed by Verifier)</div>
      <div class="${actualClass}">${escHtml(step.actual_hash)}</div>
    </div>
    ${verdictMsg}
  `;
}

// ---- Error display ----
function showError(message) {
  banner.className = "verdict-banner broken";
  banner.textContent = "✕  Error: " + message;
}

// ---- Helpers ----
function formatVerdict(raw) {
  // "CHAIN_BROKEN_AT_STEP_3_EXPORT_TOOL" → "Chain broken at step 3 — Export Tool"
  return raw
    .replace("CHAIN_BROKEN_AT_STEP_", "Chain broken at step ")
    .replace(/_/g, " ")
    .replace(/(\d+) (.+)/, (_, n, rest) => `${n} — ${rest}`);
}

function truncHash(hash) {
  if (!hash || hash.length < 12) return hash || "—";
  return `${hash.slice(0, 10)}…${hash.slice(-4)}`;
}

function escHtml(str) {
  if (typeof str !== "string") return String(str ?? "");
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
