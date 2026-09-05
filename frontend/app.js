/* ================================================================
   CustodyChain — app.js
   Handles: Run Demo, API calls, timeline rendering, expandable rows
   ================================================================ */

const API_BASE = "http://localhost:8000";

const SAMPLE_CONTENT =
  "CASE_FILE_2026_0912\nSuspect device seized at 14:02.\nHash chain begins here.";

// ---- Element refs ----
const runBtn      = document.getElementById("runDemoBtn");
const runBtnText  = document.getElementById("runBtnText");
const banner      = document.getElementById("verdictBanner");
const verdictIcon = document.getElementById("verdictIcon");
const verdictTitle= document.getElementById("verdictTitle");
const verdictSub  = document.getElementById("verdictSub");
const verdictPulse= document.getElementById("verdictPulse");
const timeline    = document.getElementById("timeline");
const timelineSec = document.getElementById("timelineSection");
const evidenceMeta= document.getElementById("evidenceMeta");
const metaId      = document.getElementById("metaId");
const metaName    = document.getElementById("metaName");
const metaTime    = document.getElementById("metaTime");
const legend      = document.getElementById("legend");

// ---- Run Demo ----
runBtn.addEventListener("click", runDemo);

async function runDemo() {
  setLoading(true);
  clearResults();

  try {
    // Step 1: Create evidence & run it through the pipeline
    const createRes = await fetch(`${API_BASE}/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Case-2026-0912-Exhibit-A",
        content: SAMPLE_CONTENT,
      }),
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

    // Render everything
    renderMeta(verifyData, evidenceId);
    renderVerdict(verifyData);
    renderTimeline(verifyData.steps);

  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
}

// ---- Loading state ----
function setLoading(loading) {
  runBtn.disabled = loading;
  if (loading) {
    runBtnText.textContent = "Running…";
    const icon = runBtn.querySelector(".run-btn-icon");
    icon.innerHTML = '<span class="spinner"></span>';
  } else {
    runBtnText.textContent = "Run Demo";
    const icon = runBtn.querySelector(".run-btn-icon");
    icon.textContent = "▶";
  }
}

// ---- Clear previous results ----
function clearResults() {
  banner.className = "verdict-banner hidden";
  timelineSec.classList.add("hidden");
  evidenceMeta.classList.add("hidden");
  legend.classList.add("hidden");
  timeline.innerHTML = "";
}

// ---- Render evidence meta strip ----
function renderMeta(data, evidenceId) {
  metaId.textContent = `#${evidenceId}`;
  metaName.textContent = data.evidence_name || "Case-2026-0912-Exhibit-A";
  metaTime.textContent = new Date().toLocaleTimeString();
  evidenceMeta.classList.remove("hidden");
}

// ---- Render verdict banner ----
function renderVerdict(data) {
  const isIntact = data.final_verdict === "CHAIN_INTACT";

  banner.className = `verdict-banner ${isIntact ? "intact" : "broken"}`;

  verdictIcon.textContent = isIntact ? "🔒" : "⚠️";
  verdictTitle.textContent = isIntact
    ? "Chain Intact — Evidence Verified End to End"
    : formatVerdict(data.final_verdict);

  verdictSub.textContent = isIntact
    ? "All handlers preserved the evidence exactly. No tampering detected."
    : "An unauthorized modification was detected. The verifier identified the break point.";
}

function formatVerdict(raw) {
  // "CHAIN_BROKEN_AT_STEP_3_EXPORT_TOOL" → "Chain Broken at Step 3 — Export Tool"
  return raw
    .replace("CHAIN_BROKEN_AT_STEP_", "Chain Broken at Step ")
    .replace(/_/g, " ")
    .replace(/(\d+) (.+)/, "$1 — $2");
}

// ---- Render timeline ----
function renderTimeline(steps) {
  timeline.innerHTML = "";

  steps.forEach((step, index) => {
    const row = buildStepRow(step);
    row.style.animationDelay = `${index * 80}ms`;
    timeline.appendChild(row);
  });

  timelineSec.classList.remove("hidden");
  legend.classList.remove("hidden");
}

// ---- Build a single step row ----
function buildStepRow(step) {
  const isVerified   = step.verified;
  const isDownstream = step.downstream_of_break;
  const isBreakPoint = !isVerified && !isDownstream;

  // Row class
  let rowClass = "step-row ";
  if (isVerified)       rowClass += "verified";
  else if (isBreakPoint) rowClass += "broken-step";
  else                  rowClass += "downstream";

  // Status icon
  const icon = isVerified ? "✅" : (isBreakPoint ? "❌" : "⚠️");

  // Badge (only for break point and downstream)
  const badge = isBreakPoint
    ? '<span class="tamper-badge">Tamper Detected</span>'
    : isDownstream
      ? '<span class="downstream-badge">Downstream of Break</span>'
      : "";

  // Hash preview (first 8 + … + last 4 chars)
  const hashPreview = truncateHash(step.actual_hash);

  // Determine if actual hash mismatches expected (non-verified non-origin steps)
  const hashMismatch = !isVerified && step.handler_name !== "Collector";

  // Build expandable hash detail
  const detailHtml = buildDetailHtml(step, hashMismatch, isDownstream);

  const row = document.createElement("div");
  row.className = rowClass;
  row.innerHTML = `
    <div class="step-main" role="button" tabindex="0" aria-expanded="false"
         aria-label="Step ${step.step_order}: ${step.handler_name}">
      <span class="step-number">${step.step_order}</span>
      <span class="step-status-icon">${icon}</span>
      <div class="step-info">
        <div class="step-name">
          ${escapeHtml(step.handler_name)}
          ${badge}
        </div>
        <div class="step-declared">
          Declared: <span class="declared-val">${escapeHtml(step.declared_status)}</span>
        </div>
      </div>
      <span class="step-hash-preview mono">${hashPreview}</span>
      <span class="step-expand-icon">▾</span>
    </div>
    ${detailHtml}
  `;

  // Expand/collapse on click or Enter
  const mainEl = row.querySelector(".step-main");
  mainEl.addEventListener("click", () => toggleExpand(row, mainEl));
  mainEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggleExpand(row, mainEl);
    }
  });

  return row;
}

function toggleExpand(row, mainEl) {
  const expanded = row.classList.toggle("expanded");
  mainEl.setAttribute("aria-expanded", String(expanded));
}

// ---- Build expandable detail HTML ----
function buildDetailHtml(step, hashMismatch, isDownstream) {
  const hashBeforeClass = "hash-row-value";
  const hashAfterClass  = hashMismatch ? "hash-row-value mismatch" : "hash-row-value match";
  const actualHashClass = hashMismatch ? "hash-row-value mismatch" : "hash-row-value match";

  let verdictMsg = "";
  if (step.handler_name === "Collector") {
    verdictMsg = `<div class="detail-verdict ok">✅ Trusted origin — this is the baseline hash for the chain.</div>`;
  } else if (step.verified) {
    verdictMsg = `<div class="detail-verdict ok">✅ Verified — actual hash matches previous step. Evidence unchanged.</div>`;
  } else if (isDownstream) {
    verdictMsg = `<div class="detail-verdict warn">⚠️ Downstream of break — cannot establish integrity. Chain already compromised upstream.</div>`;
  } else {
    verdictMsg = `<div class="detail-verdict fail">❌ TAMPER DETECTED — actual hash does not match previous step's output. This step silently altered the evidence despite declaring "success".</div>`;
  }

  return `
    <div class="step-detail">
      <div class="hash-row">
        <div class="hash-row-label">Hash Before (declared by handler)</div>
        <div class="${hashBeforeClass}">${escapeHtml(step.hash_before)}</div>
      </div>
      <div class="hash-row">
        <div class="hash-row-label">Hash After (declared by handler)</div>
        <div class="${hashAfterClass}">${escapeHtml(step.hash_after)}</div>
      </div>
      <div class="hash-row">
        <div class="hash-row-label">Actual Hash (independently recomputed by Verifier)</div>
        <div class="${actualHashClass}">${escapeHtml(step.actual_hash)}</div>
      </div>
      ${verdictMsg}
    </div>
  `;
}

// ---- Error display ----
function showError(message) {
  banner.className = "verdict-banner broken";
  verdictIcon.textContent = "🚨";
  verdictTitle.textContent = "Connection Error";
  verdictSub.textContent = message;
  verdictPulse.style.display = "none";
}

// ---- Helpers ----
function truncateHash(hash) {
  if (!hash || hash.length < 12) return hash || "—";
  return `${hash.slice(0, 8)}…${hash.slice(-4)}`;
}

function escapeHtml(str) {
  if (typeof str !== "string") return String(str ?? "");
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
