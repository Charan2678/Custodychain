/* ==========================================================================
   CustodyChain — Modern Calm Forensic Workspace Controller
   ========================================================================== */

const API_BASE = "http://localhost:8000";

const FORENSIC_SCENARIOS = [
  {
    prefix: "Case-2026-WhatsApp-ChatDB",
    title: "WhatsApp SQLite Chat DB",
    generate: (caseId, time) =>
      `CASE_REF: #2026-${caseId}-MOB\nEXHIBIT: WhatsApp SQLite Chat Database\nEXTRACTION_TIME: ${time}\n[14:00:01] Suspect: Meeting at warehouse confirmed.\n[14:01:23] Accomplice: Bring the encrypted drive.\nMD5_SOURCE: d41d8cd98f00b204e9800998ecf8427e`,
    tamperStep: 3,
    tamperLabel: "Step 3 — Export Tool (Silent CRLF)",
  },
  {
    prefix: "Case-2026-FinFraud-Ledger-TX",
    title: "Wire Transfer Settlement Ledger",
    generate: (caseId, time) =>
      `TRANSACTION_BATCH_AUDIT: TX-${caseId}-WIRE\nBATCH_TIMESTAMP: ${time}\nORIGIN_ROUTING: 021000021 (Chase Bank NY)\nBENEFICIARY_IBAN: GB29NWBK60161331926819\nTRANSFERRED_AMOUNT_USD: $3,750,000.00\nSETTLEMENT_STATUS: CLEARED_BY_FEDWIRE`,
    tamperStep: 2,
    tamperLabel: "Step 2 — Analyst Tool (Unauthorized Tag)",
  },
  {
    prefix: "Case-2026-CCTV-FrameCheck-North",
    title: "CCTV Surveillance Stream Checksum",
    generate: (caseId, time) =>
      `SURVEILLANCE_STREAM: CAM-04-NORTH-GATE\nFRAME_SYNC_TIME: ${time}\nKEYFRAME_HASH: 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d\nOFFICER_BADGE: SFPD-0892\nTAMPER_SEAL: PHYSICAL_ZIP_LOCK_TAG_${caseId}`,
    tamperStep: 4,
    tamperLabel: "Step 4 — Reviewer (Unlogged Redaction)",
  },
  {
    prefix: "Case-2026-NVMe-DiskImage-Raw",
    title: "Bitstream NVMe Physical Drive Image",
    generate: (caseId, time) =>
      `BITSTREAM_DISK_IMAGE: PHYSICAL_DRIVE_${caseId}\nIMAGING_TOOL: FTK_Imager_v4.7_HARDWARE_WRITE_BLOCKED\nTIME_ACQUIRED: ${time}\nPARTITION_TABLE: GPT / NTFS_VOLUME_GUID\nSECTOR_RANGE: LBA 0x00000000 - 0x7FFFFFFF`,
    tamperStep: 5,
    tamperLabel: "Step 5 — Archive (Storage Bit-Rot)",
  },
  {
    prefix: "Case-2026-HSM-Encrypted-Keystore",
    title: "Hardware Security Module Key Certificate",
    generate: (caseId, time) =>
      `VAULT_KEYSTORE: HSM-LUNA-PCIe-SLOT-${caseId}\nCERTIFICATE_ISSUER: Forensic Root Authority CA\nVALIDATED_AT: ${time}\nALGORITHM: RSA-4096 / SHA-256\nSTATUS: VALID_UNCOMPROMISED_CHAIN`,
    tamperStep: 0,
    tamperLabel: "None — Verified Chain Intact",
  },
];

let scenarioIndex = 0;
let currentEvidenceId = null;
let currentCaseId = 1;

// Element references
const runSampleBtn      = document.getElementById("runSampleBtn");
const newEvidenceBtn    = document.getElementById("newEvidenceBtn");
const openAuditBtn      = document.getElementById("openAuditBtn");
const closeAuditModalBtn= document.getElementById("closeAuditModalBtn");
const auditModal        = document.getElementById("auditModal");
const auditTableBody    = document.getElementById("auditTableBody");

const scenarioDrawer    = document.getElementById("scenarioDrawer");
const toggleSimulatorBtn= document.getElementById("toggleSimulatorBtn");
const closeDrawerBtn    = document.getElementById("closeDrawerBtn");
const runCustomBtn      = document.getElementById("runCustomBtn");

const verifyBtn         = document.getElementById("verifyBtn");
const verifyBtnText     = document.getElementById("verifyBtnText");
const downloadPdfBtn    = document.getElementById("downloadPdfBtn");

const exhibitNavList    = document.getElementById("exhibitNavList");
const sidebarExhibitCount = document.getElementById("sidebarExhibitCount");

const headerCaseNumber  = document.getElementById("headerCaseNumber");
const headerExhibitId   = document.getElementById("headerExhibitId");
const headerExhibitTitle= document.getElementById("headerExhibitTitle");
const metaTimestamp     = document.getElementById("metaTimestamp");
const metaCustodian     = document.getElementById("metaCustodian");
const metaHash          = document.getElementById("metaHash");

const verdictBanner     = document.getElementById("verdictBanner");
const verdictStatusBadge= document.getElementById("verdictStatusBadge");
const verdictTitle      = document.getElementById("verdictTitle");
const verdictExplanation= document.getElementById("verdictExplanation");
const timelineCards     = document.getElementById("timelineCards");

const userMenuBtn       = document.getElementById("userMenuBtn");
const roleDropdown      = document.getElementById("roleDropdown");
const navUserRole       = document.getElementById("navUserRole");
const globalSearch      = document.getElementById("globalSearch");


// ---- Init & Event Listeners ----
document.addEventListener("DOMContentLoaded", () => {
  loadExhibitList();
  loadCases();
  setupRoleMenu();
  setupSearch();
});

// User Role Dropdown Menu
function setupRoleMenu() {
  userMenuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    roleDropdown.classList.toggle("hidden");
  });

  document.addEventListener("click", () => {
    roleDropdown.classList.add("hidden");
  });

  document.querySelectorAll(".role-option").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const role = e.target.getAttribute("data-role");
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/switch-role`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role }),
        });
        if (res.ok) {
          const data = await res.json();
          navUserRole.textContent = formatRole(role);
          document.querySelectorAll(".role-option").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
        }
      } catch (err) {
        console.error("Role switch error:", err);
      }
    });
  });
}

function formatRole(role) {
  return role.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
}

// Global search keyboard shortcut
function setupSearch() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== globalSearch && document.activeElement.tagName !== "TEXTAREA" && document.activeElement.tagName !== "INPUT") {
      e.preventDefault();
      globalSearch.focus();
    }
  });

  globalSearch.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    document.querySelectorAll(".exhibit-nav-item").forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(q) ? "flex" : "none";
    });
  });
}

// Scenario Drawer Toggle
toggleSimulatorBtn.addEventListener("click", () => {
  scenarioDrawer.classList.toggle("hidden");
});
closeDrawerBtn.addEventListener("click", () => {
  scenarioDrawer.classList.add("hidden");
});
newEvidenceBtn.addEventListener("click", () => {
  scenarioDrawer.classList.remove("hidden");
  document.getElementById("evidenceName").focus();
});

// Audit Trail Modal
openAuditBtn.addEventListener("click", loadAuditTrail);
closeAuditModalBtn.addEventListener("click", () => auditModal.classList.add("hidden"));
auditModal.addEventListener("click", (e) => {
  if (e.target === auditModal) auditModal.classList.add("hidden");
});

async function loadAuditTrail() {
  auditModal.classList.remove("hidden");
  auditTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-dim);">Loading records...</td></tr>`;
  try {
    const res = await fetch(`${API_BASE}/api/v1/audit?limit=50`);
    if (!res.ok) throw new Error("Failed to load audit trail");
    const records = await res.json();
    if (records.length === 0) {
      auditTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-dim);">No audit events recorded yet.</td></tr>`;
      return;
    }
    auditTableBody.innerHTML = records.map(r => `
      <tr>
        <td class="font-mono">${formatDate(r.timestamp)}</td>
        <td><strong>${esc(r.user_name)}</strong></td>
        <td><span class="font-mono">${esc(r.action)}</span></td>
        <td>${esc(r.resource_type)} #${esc(r.resource_id)}</td>
        <td>${esc(r.details || '—')}</td>
      </tr>
    `).join("");
  } catch (err) {
    auditTableBody.innerHTML = `<tr><td colspan="5" style="color:var(--altered-text);">${esc(err.message)}</td></tr>`;
  }
}

// Quick Sample Demo Runner (Cycles Scenarios)
runSampleBtn.addEventListener("click", () => {
  const scenario = FORENSIC_SCENARIOS[scenarioIndex];
  scenarioIndex = (scenarioIndex + 1) % FORENSIC_SCENARIOS.length;
  const randId = Math.floor(Math.random() * 9000 + 1000);
  const time = new Date().toLocaleTimeString();

  const name = `${scenario.prefix}-#${randId}`;
  const content = scenario.generate(randId, time);
  const simulateTamper = scenario.tamperStep !== 0;

  // Sync drawer fields
  document.getElementById("evidenceName").value = name;
  document.getElementById("evidenceContent").value = content;
  document.getElementById("tamperStepSelect").value = String(scenario.tamperStep);
  document.getElementById("tamperToggle").checked = simulateTamper;

  ingestAndVerify({
    name,
    content,
    simulate_tamper: simulateTamper,
    tamper_step: scenario.tamperStep,
  });
});

// Manual Drawer Run
runCustomBtn.addEventListener("click", () => {
  const name = document.getElementById("evidenceName").value.trim() || `Exhibit-${Date.now()}`;
  const content = document.getElementById("evidenceContent").value.trim();
  const simulateTamper = document.getElementById("tamperToggle").checked;
  const tamperStep = parseInt(document.getElementById("tamperStepSelect").value, 10);

  if (!content) {
    alert("Please enter digital artifact content to ingest.");
    return;
  }

  ingestAndVerify({
    name,
    content,
    simulate_tamper: simulateTamper,
    tamper_step: tamperStep,
  });
  scenarioDrawer.classList.add("hidden");
});

// Re-Verify Active Evidence Button
verifyBtn.addEventListener("click", async () => {
  if (!currentEvidenceId) return;
  verifyBtn.disabled = true;
  verifyBtnText.textContent = "Verifying…";
  try {
    const res = await fetch(`${API_BASE}/api/v1/verification/${currentEvidenceId}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      renderVerificationResults(data);
      loadExhibitList();
    }
  } catch (err) {
    console.error("Verification error:", err);
  } finally {
    verifyBtn.disabled = false;
    verifyBtnText.textContent = "Verify Integrity";
  }
});

// Download Court Certificate PDF
downloadPdfBtn.addEventListener("click", () => {
  if (!currentEvidenceId) return;
  window.open(`${API_BASE}/api/v1/reports/${currentEvidenceId}/pdf`, "_blank");
});

// Core Ingestion & Authoritative Verification Flow
async function ingestAndVerify(payload) {
  setGlobalLoading(true);
  try {
    // 1. Ingest Evidence
    const createRes = await fetch(`${API_BASE}/api/v1/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: payload.name,
        content: payload.content,
        case_id: currentCaseId,
        simulate_tamper: payload.simulate_tamper,
        tamper_step: payload.tamper_step,
      }),
    });

    if (!createRes.ok) {
      const err = await createRes.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${createRes.status}`);
    }

    const created = await createRes.json();
    currentEvidenceId = created.evidence_id;

    // 2. Query Authoritative Backend Verification Engine
    const verifyRes = await fetch(`${API_BASE}/api/v1/verification/${currentEvidenceId}`, { method: "POST" });
    if (!verifyRes.ok) throw new Error("Failed to verify evidence");
    const verifyData = await verifyRes.json();

    // 3. Render Results
    renderVerificationResults(verifyData);
    loadExhibitList();

  } catch (err) {
    alert("Error executing custody pipeline: " + err.message);
  } finally {
    setGlobalLoading(false);
  }
}

// Render Authoritative Results to Canvas
function renderVerificationResults(data) {
  currentEvidenceId = data.evidence_id;

  // Header
  headerExhibitId.textContent = data.exhibit_id || `EX-${data.evidence_id}`;
  headerExhibitTitle.textContent = data.evidence_name;
  metaTimestamp.textContent = `Acquired: ${new Date().toLocaleTimeString()}`;
  metaHash.textContent = `Original SHA-256: ${trunc(data.original_hash, 16)}`;

  // Authoritative Verdict Banner
  const isIntact = data.final_verdict === "CHAIN_INTACT";
  verdictBanner.className = `verdict-banner-card ${isIntact ? "verified" : "altered"}`;
  verdictBanner.classList.remove("hidden");

  verdictStatusBadge.textContent = isIntact ? "VERIFIED" : "ALTERED";

  if (isIntact) {
    verdictTitle.textContent = "Chain Intact · All 5 Handlers Verified";
    verdictExplanation.textContent =
      "Authoritative independent recomputation confirmed: physical storage artifacts match baseline SHA-256, Ed25519 digital signatures are authentic, and event hash continuity is intact.";
  } else {
    verdictTitle.textContent = `Integrity Compromise Localized · ${formatVerdict(data.final_verdict)}`;
    verdictExplanation.textContent =
      "Unauthorized mutation detected. The stored artifact hash no longer matches the expected state. Downstream findings are forensically tainted.";
  }

  // Render Handler Progression Cards
  timelineCards.innerHTML = "";
  let breakEncountered = false;

  data.steps.forEach((step) => {
    let statusClass = "verified";
    let statusLabel = "Verified";

    if (!step.verified) {
      statusClass = "altered";
      statusLabel = "Altered";
      breakEncountered = true;
    } else if (step.downstream_of_break || breakEncountered) {
      statusClass = "downstream";
      statusLabel = "Downstream";
    }

    const card = document.createElement("div");
    card.className = `handler-card ${statusClass === "altered" ? "altered" : ""}`;

    const seqNum = String(step.step_order).padStart(2, "0");
    const sigValid = step.signature_valid !== false;

    card.innerHTML = `
      <div class="handler-card-main">
        <div class="handler-left">
          <span class="step-number">${seqNum}</span>
          <div class="handler-identity">
            <span class="handler-name">${esc(step.handler_name)}</span>
            <span class="handler-action">${esc(step.action || 'Standard forensic custody handling')}</span>
          </div>
        </div>
        <div class="handler-right">
          <span class="declared-pill">Declared: <strong>${esc(step.declared_status)}</strong></span>
          <span class="verification-tag ${statusClass}">${statusLabel}</span>
          <span class="expand-indicator">▾</span>
        </div>
      </div>
      <div class="handler-card-details">
        <div class="proofs-grid">
          <div class="proof-item">
            <span class="proof-label">Input SHA-256</span>
            <span class="proof-value">${esc(step.hash_before)}</span>
          </div>
          <div class="proof-item">
            <span class="proof-label">Self-Declared Hash</span>
            <span class="proof-value">${esc(step.hash_after)}</span>
          </div>
          <div class="proof-item">
            <span class="proof-label">Storage Recomputed Hash</span>
            <span class="proof-value ${step.verified ? 'match' : 'mismatch'}">${esc(step.actual_hash)}</span>
          </div>
        </div>
        <div class="crypto-audit-row">
          <div class="sig-status ${sigValid ? 'valid' : 'invalid'}">
            <span>Ed25519 Signature:</span>
            <strong>${sigValid ? 'Valid Authenticated' : 'Signature Invalid / Forged'}</strong>
            <span class="font-mono" style="opacity:0.7">(${esc(step.signature_preview || 'Ed25519')})</span>
          </div>
          <div class="ledger-chain-status">
            <span>Ledger Link:</span>
            <strong style="color:var(--verified-text)">Continuous</strong>
          </div>
        </div>
      </div>
    `;

    // Toggle progressive disclosure
    card.querySelector(".handler-card-main").addEventListener("click", () => {
      card.classList.toggle("expanded");
    });

    timelineCards.appendChild(card);
  });
}

// Load Exhibits for Sidebar
async function loadExhibitList() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/evidence`);
    if (!res.ok) return;
    const exhibits = await res.json();

    sidebarExhibitCount.textContent = `${exhibits.length} exhibits`;
    exhibitNavList.innerHTML = "";

    if (exhibits.length === 0) {
      exhibitNavList.innerHTML = `<div class="empty-notice" style="padding:16px 8px;font-size:11px;color:var(--text-dim);text-align:center;">No exhibits yet. Run Quick Demo.</div>`;
      return;
    }

    exhibits.forEach((item) => {
      const isVerified = item.status === "VERIFIED" || item.latest_verdict === "CHAIN_INTACT";
      const navItem = document.createElement("div");
      navItem.className = `exhibit-nav-item ${currentEvidenceId === item.id ? "active" : ""}`;
      navItem.innerHTML = `
        <div class="nav-item-top">
          <span class="nav-item-name" title="${esc(item.name)}">${esc(item.name)}</span>
          <span class="nav-item-badge ${isVerified ? 'verified' : 'altered'}">
            ${isVerified ? 'Verified' : 'Altered'}
          </span>
        </div>
        <div class="nav-item-sub">
          <span>${esc(item.exhibit_id || '#' + item.id)}</span>
          <span>${formatDate(item.created_at)}</span>
        </div>
      `;

      navItem.addEventListener("click", async () => {
        document.querySelectorAll(".exhibit-nav-item").forEach(i => i.classList.remove("active"));
        navItem.classList.add("active");
        try {
          const verifyRes = await fetch(`${API_BASE}/api/v1/verification/${item.id}`, { method: "POST" });
          if (verifyRes.ok) {
            const data = await verifyRes.json();
            renderVerificationResults(data);
          }
        } catch (e) {
          console.error("Error loading exhibit:", e);
        }
      });

      exhibitNavList.appendChild(navItem);
    });

    // If no evidence is currently selected, auto-select the latest one
    if (!currentEvidenceId && exhibits.length > 0) {
      const latest = exhibits[0];
      const verifyRes = await fetch(`${API_BASE}/api/v1/verification/${latest.id}`, { method: "POST" });
      if (verifyRes.ok) {
        const data = await verifyRes.json();
        renderVerificationResults(data);
      }
    }

  } catch (err) {
    console.warn("Failed to load exhibits:", err);
  }
}

// Load Cases for Case Selector
async function loadCases() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/cases`);
    if (!res.ok) return;
    const cases = await res.json();
    const caseSelect = document.getElementById("caseSelect");
    if (!caseSelect || cases.length === 0) return;

    caseSelect.innerHTML = cases.map(c => `
      <option value="${c.id}">Case: ${esc(c.title)} (${esc(c.case_number)})</option>
    `).join("");

    headerCaseNumber.textContent = cases[0].case_number;
    currentCaseId = cases[0].id;
  } catch (err) {
    console.warn("Failed to load cases:", err);
  }
}

// Utility Helpers
function setGlobalLoading(isLoading) {
  runSampleBtn.disabled = isLoading;
  runCustomBtn.disabled = isLoading;
  if (isLoading) {
    runSampleBtn.innerHTML = `<span class="btn-symbol">⏳</span><span>Processing…</span>`;
  } else {
    runSampleBtn.innerHTML = `<span class="btn-symbol">▶</span><span>Quick Demo Scenario</span>`;
  }
}

function formatVerdict(v) {
  return v
    .replace("CHAIN_BROKEN_AT_STEP_", "Step ")
    .replace("SIGNATURE_INVALID_AT_STEP_", "Invalid Signature at Step ")
    .replace("LEDGER_BROKEN_AT_STEP_", "Ledger Broken at Step ")
    .replace(/_/g, " ");
}

function formatDate(isoStr) {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return String(isoStr);
  }
}

function trunc(str, len = 12) {
  if (!str) return "—";
  if (str.length <= len) return str;
  return `${str.slice(0, len)}…`;
}

function esc(str) {
  if (typeof str !== "string") return String(str ?? "");
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
