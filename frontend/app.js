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
  banner.innerHTML = isIntact
    ? "Chain intact — evidence verified end to end. This artifact reflects the original exactly."
    : `${data.final_verdict.replaceAll("_", " ")} — evidence in Archive no longer matches the original artifact collected. Later analysis based on this exhibit cannot be trusted.`;
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
      const row = document.createElement("div");
      row.className = "history-row";
      row.innerHTML = `
        <span class="history-name">#${item.evidence_id} — ${escHtml(item.name)}</span>
        <span class="history-meta">
          <span>${new Date(item.created_at).toLocaleTimeString()}</span>
          <span class="history-badge ${isIntact ? "ok" : "broken"}">
            ${isIntact ? "Intact" : "Broken"}
          </span>
        </span>
      `;
      row.addEventListener("click", async () => {
        try {
          const verifyRes = await fetch(`${API_BASE}/evidence/${item.evidence_id}/verify`);
          if (verifyRes.ok) {
            const verifyData = await verifyRes.json();
            renderResults(verifyData, { name: item.name });
            resultsSection.scrollIntoView({ behavior: "smooth" });
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
