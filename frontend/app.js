/* ================================================================
   CustodyChain — app.js
   Handles: form input, API calls, timeline rendering, expandable rows
   ================================================================ */

const API_BASE = "http://localhost:8000";

const FORENSIC_SCENARIOS = [
  {
    prefix: "Case-2026-WhatsApp-ChatDB",
    title: "WhatsApp SQLite Chat DB",
    generate: (caseId, time) =>
      `CASE_REF: #2026-${caseId}-MOB\nEXHIBIT: WhatsApp SQLite Chat Database\nEXTRACTION_TIME: ${time}\n[14:00:01] Suspect: Meeting at warehouse confirmed.\n[14:01:23] Accomplice: Bring the encrypted drive.\nMD5_SOURCE: d41d8cd98f00b204e9800998ecf8427e`,
    tamperStep: 2,
    tamperLabel: "Step 2 — Analyst Tool",
  },
  {
    prefix: "Case-2026-FinFraud-Ledger-TX",
    title: "Wire Transfer Settlement Ledger",
    generate: (caseId, time) =>
      `TRANSACTION_BATCH_AUDIT: TX-${caseId}-WIRE\nBATCH_TIMESTAMP: ${time}\nORIGIN_ROUTING: 021000021 (Chase Bank NY)\nBENEFICIARY_IBAN: GB29NWBK60161331926819\nTRANSFERRED_AMOUNT_USD: $3,750,000.00\nSETTLEMENT_STATUS: CLEARED_BY_FEDWIRE`,
    tamperStep: 3,
    tamperLabel: "Step 3 — Export Tool",
  },
  {
    prefix: "Case-2026-CCTV-FrameCheck-North",
    title: "CCTV Surveillance Checksum",
    generate: (caseId, time) =>
      `SURVEILLANCE_STREAM: CAM-04-NORTH-GATE\nFRAME_SYNC_TIME: ${time}\nKEYFRAME_HASH: 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d\nOFFICER_BADGE: SFPD-0892\nTAMPER_SEAL: PHYSICAL_ZIP_LOCK_TAG_${caseId}`,
    tamperStep: 4,
    tamperLabel: "Step 4 — Reviewer",
  },
  {
    prefix: "Case-2026-NVMe-DiskImage-Raw",
    title: "Bitstream NVMe Physical Drive Image",
    generate: (caseId, time) =>
      `BITSTREAM_DISK_IMAGE: PHYSICAL_DRIVE_${caseId}\nIMAGING_TOOL: FTK_Imager_v4.7_HARDWARE_WRITE_BLOCKED\nTIME_ACQUIRED: ${time}\nPARTITION_TABLE: GPT / NTFS_VOLUME_GUID\nSECTOR_RANGE: LBA 0x00000000 - 0x7FFFFFFF`,
    tamperStep: 5,
    tamperLabel: "Step 5 — Archive",
  },
  {
    prefix: "Case-2026-HSM-Encrypted-Keystore",
    title: "Hardware Security Module Key Certificate",
    generate: (caseId, time) =>
      `VAULT_KEYSTORE: HSM-LUNA-PCIe-SLOT-${caseId}\nCERTIFICATE_ISSUER: Forensic Root Authority CA\nVALIDATED_AT: ${time}\nALGORITHM: RSA-4096 / SHA-256\nSTATUS: VALID_UNCOMPROMISED_CHAIN`,
    tamperStep: 0,
    tamperLabel: "None — Chain Intact",
  },
];

let currentScenarioIndex = 0;

function getNextScenario() {
  const scenario = FORENSIC_SCENARIOS[currentScenarioIndex];
  currentScenarioIndex = (currentScenarioIndex + 1) % FORENSIC_SCENARIOS.length;
  const caseId = Math.floor(Math.random() * 9000 + 1000);
  const time = new Date().toLocaleTimeString();

  return {
    name: `${scenario.prefix}-#${caseId}`,
    content: scenario.generate(caseId, time),
    tamperStep: scenario.tamperStep,
    tamperLabel: scenario.tamperLabel,
  };
}

// ---- Element refs ----
const runBtn          = document.getElementById("runDemoBtn");
const sampleBtn       = document.getElementById("runSampleBtn");
const btnText         = document.getElementById("btnText");
const btnIcon         = document.getElementById("btnIcon");
const banner          = document.getElementById("verdictBanner");
const resultsSection  = document.getElementById("resultsSection");
const timeline        = document.getElementById("timeline");
const tamperToggle    = document.getElementById("tamperToggle");
const toggleDesc      = document.getElementById("toggleDescription");
const tamperStepSelect = document.getElementById("tamperStepSelect");
const metaTamperValue = document.getElementById("metaTamperValue");

// ---- Tamper toggle hint ----
function updateToggleDesc() {
  const step = parseInt(tamperStepSelect ? tamperStepSelect.value : "3", 10);
  if (!tamperToggle.checked || step === 0) {
    toggleDesc.textContent = "Off — all handlers pass evidence honestly (expect Chain Intact)";
    toggleDesc.style.color = "var(--success)";
    if (metaTamperValue) {
      metaTamperValue.textContent = "None — Clean Pipeline";
      metaTamperValue.className = "meta-value accent";
    }
  } else {
    const stepNames = { 2: "Step 2 — Analyst Tool", 3: "Step 3 — Export Tool", 4: "Step 4 — Reviewer", 5: "Step 5 — Archive" };
    const label = stepNames[step] || `Step ${step}`;
    toggleDesc.textContent = `On — ${label} will silently alter content and still report success`;
    toggleDesc.style.color = "var(--danger)";
    if (metaTamperValue) {
      metaTamperValue.textContent = label;
      metaTamperValue.className = "meta-value danger";
    }
  }
}

tamperToggle.addEventListener("change", updateToggleDesc);
if (tamperStepSelect) {
  tamperStepSelect.addEventListener("change", updateToggleDesc);
}
updateToggleDesc();

// ---- Quick sample demo (cycles across different scenarios & tamper points) ----
sampleBtn.addEventListener("click", () => {
  const sample = getNextScenario();
  document.getElementById("evidenceName").value = sample.name;
  document.getElementById("evidenceContent").value = sample.content;

  if (tamperStepSelect) {
    tamperStepSelect.value = String(sample.tamperStep);
  }
  tamperToggle.checked = sample.tamperStep !== 0;
  updateToggleDesc();

  runVerification(sample.name, sample.content, tamperToggle.checked, sample.tamperStep);
});

// ---- Manual form ----
runBtn.addEventListener("click", () => {
  const name           = document.getElementById("evidenceName").value.trim() || "Untitled-Evidence";
  const content        = document.getElementById("evidenceContent").value.trim();
  const simulateTamper = tamperToggle.checked;
  const tamperStep     = parseInt(tamperStepSelect ? tamperStepSelect.value : "3", 10);

  if (!content) {
    const ta = document.getElementById("evidenceContent");
    ta.style.borderColor = "var(--danger)";
    ta.style.boxShadow   = "0 0 0 3px rgba(248,113,113,0.15)";
    setTimeout(() => { ta.style.borderColor = ""; ta.style.boxShadow = ""; }, 1500);
    ta.focus();
    return;
  }
  runVerification(name, content, simulateTamper, tamperStep);
});

// ---- Shared verification runner ----
async function runVerification(name, content, simulateTamper, tamperStep = 3) {
  setLoading(true);
  clearResults();

  try {
    // Step 1: Create evidence and run it through the full pipeline
    const createRes = await fetch(`${API_BASE}/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        content,
        simulate_tamper: simulateTamper,
        tamper_step: simulateTamper ? tamperStep : 0,
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

    // Render
    renderResults(verifyData, { name });
    loadHistory();

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
  const titleText = isIntact
    ? "Chain Intact — Integrity Verified"
    : formatVerdict(data.final_verdict);

  const subtitleText = isIntact
    ? "All handlers verified independently end-to-end. Evidence in Archive matches original acquisition byte-for-byte."
    : "Evidence in Archive no longer matches the original artifact collected. Unauthorized modification detected; subsequent forensic findings cannot be trusted.";

  banner.innerHTML = `
    <div class="verdict-header">
      <span class="verdict-icon-badge ${isIntact ? "ok" : "broken"}">${isIntact ? "✓" : "✕"}</span>
      <div class="verdict-text-block">
        <h3 class="verdict-headline">${escHtml(titleText)}</h3>
        <p class="verdict-subtext">${escHtml(subtitleText)}</p>
      </div>
    </div>
  `;
  banner.className = "verdict-banner " + (isIntact ? "ok" : "broken");

  // Timeline
  timeline.innerHTML = "";
  let brokenSeen = false;

  data.steps.forEach((step, index) => {
    let rowClass = "ok";
    let iconChar = "✓";
    let tag = "";

    if (!step.verified) {
      rowClass = "broken";
      iconChar = "✕";
      brokenSeen = true;
      tag = '<span class="step-tag broken">Tamper detected</span>';
    } else if (brokenSeen) {
      rowClass = "downstream";
      iconChar = "⚠";
      tag = '<span class="step-tag downstream">Downstream of break</span>';
    }

    const hashMismatch = !step.verified && step.handler_name !== "Collector";
    const detail = buildDetail(step, hashMismatch, rowClass);

    const row = document.createElement("div");
    row.className = "step-row " + rowClass;
    row.style.animationDelay = `${index * 60}ms`;
    row.innerHTML = `
      <div class="step-main">
        <span class="step-icon ${rowClass}">${iconChar}</span>
        <div class="step-name">
          <span class="step-title">${escHtml(step.step_order + ". " + step.handler_name)}</span>
          ${tag}
        </div>
        <div class="step-meta-right">
          <span class="step-status">Declared: <strong>${escHtml(step.declared_status)}</strong></span>
          <span class="step-hash" title="Actual SHA-256">${truncHash(step.actual_hash)}</span>
          <span class="step-expand">▾</span>
        </div>
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

  // Smoothly reveal results ensuring the banner is at the top of view
  banner.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---- Build expandable hash detail ----
function buildDetail(step, hashMismatch, rowClass) {
  const actualClass = hashMismatch ? "hash-value mismatch" : "hash-value match";

  let verdictMsg = "";
  if (step.handler_name === "Collector") {
    verdictMsg = `<div class="detail-verdict ok">✓ Trusted origin — baseline acquisition hash for the entire custody chain.</div>`;
  } else if (rowClass === "broken") {
    verdictMsg = `<div class="detail-verdict fail">✕ Breach Point — unauthorized content alteration detected. Output hash does not match previous handler output.</div>`;
  } else if (rowClass === "downstream") {
    verdictMsg = `<div class="detail-verdict warn">⚠ Downstream of break — this handler did not tamper with evidence, but inherited already-compromised artifact data.</div>`;
  } else if (step.verified) {
    verdictMsg = `<div class="detail-verdict ok">✓ Verified — recomputed hash matches previous stage output exactly. No tampering detected.</div>`;
  }

  return `
    <div class="hash-fields-grid">
      <div class="hash-field">
        <span class="hash-label">Input Hash (Previous Output)</span>
        <span class="hash-value">${escHtml(step.hash_before)}</span>
      </div>
      <div class="hash-field">
        <span class="hash-label">Self-Reported Declared Hash</span>
        <span class="hash-value">${escHtml(step.hash_after)}</span>
      </div>
      <div class="hash-field">
        <span class="hash-label">Independent Verifier Recomputed Hash</span>
        <span class="${actualClass}">${escHtml(step.actual_hash)}</span>
      </div>
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

// ---- History loader ----
async function loadHistory() {
  try {
    const res = await fetch(`${API_BASE}/history`);
    if (!res.ok) return;
    const items = await res.json();

    const countEl = document.getElementById("historyCount");
    if (countEl) countEl.textContent = `${items.length} total`;

    const list = document.getElementById("historyList");
    if (!list) return;
    list.innerHTML = "";

    if (items.length === 0) {
      list.innerHTML = '<div class="history-empty">No runs yet — click Run sample demo or Run verification to begin.</div>';
      return;
    }

    items.forEach((item) => {
      const isIntact = item.final_verdict === "CHAIN_INTACT";
      const verdictLabel = isIntact
        ? "Verified Intact"
        : item.final_verdict.replace("CHAIN_BROKEN_AT_", "").replace(/_/g, " ");

      const row = document.createElement("div");
      row.className = "history-row";
      row.innerHTML = `
        <div class="history-row-main">
          <div class="history-row-header">
            <span class="history-id">#${item.evidence_id}</span>
            <span class="history-name" title="${escHtml(item.name)}">${escHtml(item.name)}</span>
            <span class="history-badge ${isIntact ? "ok" : "broken"}">
              ${isIntact ? "INTACT" : "BROKEN"}
            </span>
          </div>
          <div class="history-row-sub">
            <span class="history-time">${new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            <span class="history-verdict-summary ${isIntact ? "ok" : "broken"}">${escHtml(verdictLabel)}</span>
          </div>
        </div>
      `;
      row.addEventListener("click", async () => {
        try {
          const verifyRes = await fetch(`${API_BASE}/evidence/${item.evidence_id}/verify`);
          if (verifyRes.ok) {
            const verifyData = await verifyRes.json();
            renderResults(verifyData, { name: item.name });
          }
        } catch (e) {
          console.error("Error loading historical verification:", e);
        }
      });
      list.appendChild(row);
    });
  } catch (err) {
    console.warn("Failed to load history:", err);
  }
}

// Initial load
loadHistory();
