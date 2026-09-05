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
    tamperLabel: "Step 3 — Export Tool (Silent CRLF Alteration)",
  },
  {
    prefix: "Case-2026-FinFraud-Ledger-TX",
    title: "Wire Transfer Settlement Ledger",
    generate: (caseId, time) =>
      `TRANSACTION_BATCH_AUDIT: TX-${caseId}-WIRE\nBATCH_TIMESTAMP: ${time}\nORIGIN_ROUTING: 021000021 (Chase Bank NY)\nBENEFICIARY_IBAN: GB29NWBK60161331926819\nTRANSFERRED_AMOUNT_USD: $3,750,000.00\nSETTLEMENT_STATUS: CLEARED_BY_FEDWIRE`,
    tamperStep: 2,
    tamperLabel: "Step 2 — Analyst Tool (Unauthorized Metadata Tag)",
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
    tamperLabel: "None — Pure Verified Intact Chain",
  },
];

let scenarioIndex = 0;
let currentEvidenceId = null;
let currentCaseId = 1;
let currentVerificationData = null;
let allExhibits = [];
let showAllExhibits = false;
const SIDEBAR_PREVIEW_LIMIT = 5;

// DOM Elements
const runSampleBtn       = document.getElementById("runSampleBtn");
const newEvidenceBtn     = document.getElementById("newEvidenceBtn");
const openAuditBtn       = document.getElementById("openAuditBtn");
const closeAuditModalBtn = document.getElementById("closeAuditModalBtn");
const auditModal         = document.getElementById("auditModal");
const auditTableBody     = document.getElementById("auditTableBody");

const scenarioModal      = document.getElementById("scenarioModal");
const toggleSimulatorBtn = document.getElementById("toggleSimulatorBtn");
const closeDrawerBtn     = document.getElementById("closeDrawerBtn");
const cancelModalBtn     = document.getElementById("cancelModalBtn");
const runCustomBtn       = document.getElementById("runCustomBtn");

const howVerifiedBtn     = document.getElementById("howVerifiedBtn");
const howVerifiedModal   = document.getElementById("howVerifiedModal");
const closeHowVerifiedBtn= document.getElementById("closeHowVerifiedBtn");

const verifyBtn          = document.getElementById("verifyBtn");
const verifyBtnText      = document.getElementById("verifyBtnText");
const explainBtn         = document.getElementById("explainBtn");
const downloadPdfBtn     = document.getElementById("downloadPdfBtn");

const exhibitNavList     = document.getElementById("exhibitNavList");
const sidebarExhibitCount= document.getElementById("sidebarExhibitCount");
const sidebarExpandWrap  = document.getElementById("sidebarExpandWrap");
const toggleAllExhibitsBtn = document.getElementById("toggleAllExhibitsBtn");
const sidebarSearch      = document.getElementById("sidebarSearch");
const globalSearch       = document.getElementById("globalSearch");

const headerCaseNumber   = document.getElementById("headerCaseNumber");
const headerExhibitId    = document.getElementById("headerExhibitId");
const headerExhibitTitle = document.getElementById("headerExhibitTitle");
const headerStatusTag    = document.getElementById("headerStatusTag");

const toggleDetailsBtn   = document.getElementById("toggleDetailsBtn");
const detailsChevron     = document.getElementById("detailsChevron");
const detailsContent     = document.getElementById("detailsContent");
const detailsPreview     = document.getElementById("detailsPreview");
const metaTimestamp      = document.getElementById("metaTimestamp");
const metaCustodian      = document.getElementById("metaCustodian");
const metaHash           = document.getElementById("metaHash");

const verdictBanner      = document.getElementById("verdictBanner");
const verdictTitle       = document.getElementById("verdictTitle");
const verdictBreakPoint  = document.getElementById("verdictBreakPoint");
const verdictExplanation = document.getElementById("verdictExplanation");
const verdictExplainBtn  = document.getElementById("verdictExplainBtn");

const explanationCard    = document.getElementById("explanationCard");
const explanationTitle   = document.getElementById("explanationTitle");
const explanationBody    = document.getElementById("explanationBody");
const closeExplanationBtn= document.getElementById("closeExplanationBtn");

const timelineCards      = document.getElementById("timelineCards");

const userMenuBtn        = document.getElementById("userMenuBtn");
const roleDropdown       = document.getElementById("roleDropdown");
const navUserRole        = document.getElementById("navUserRole");

const themeToggleBtn     = document.getElementById("themeToggleBtn");
const themeIcon          = document.getElementById("themeIcon");
const themeLabel         = document.getElementById("themeLabel");
const toggleSidebarBtn   = document.getElementById("toggleSidebarBtn");
const workspaceSidebar   = document.querySelector(".workspace-sidebar");


// ---- Initialization ----
document.addEventListener("DOMContentLoaded", () => {
  loadExhibitList();
  loadCases();
  setupRoleMenu();
  setupSearch();
  setupModals();
  setupDetailsToggle();
  setupTheme();
  setupSidebarToggle();
});

// Setup Modals & Dialogs
function setupModals() {
  // Scenario / Ingestion Modal
  toggleSimulatorBtn.addEventListener("click", () => scenarioModal.classList.remove("hidden"));
  newEvidenceBtn.addEventListener("click", () => {
    scenarioModal.classList.remove("hidden");
    document.getElementById("evidenceName").focus();
  });
  closeDrawerBtn.addEventListener("click", () => scenarioModal.classList.add("hidden"));
  cancelModalBtn.addEventListener("click", () => scenarioModal.classList.add("hidden"));
  scenarioModal.addEventListener("click", (e) => {
    if (e.target === scenarioModal) scenarioModal.classList.add("hidden");
  });

  // "How Was This Verified?" Modal
  howVerifiedBtn.addEventListener("click", () => howVerifiedModal.classList.remove("hidden"));
  closeHowVerifiedBtn.addEventListener("click", () => howVerifiedModal.classList.add("hidden"));
  howVerifiedModal.addEventListener("click", (e) => {
    if (e.target === howVerifiedModal) howVerifiedModal.classList.add("hidden");
  });

  // Audit Modal
  openAuditBtn.addEventListener("click", loadAuditTrail);
  closeAuditModalBtn.addEventListener("click", () => auditModal.classList.add("hidden"));
  auditModal.addEventListener("click", (e) => {
    if (e.target === auditModal) auditModal.classList.add("hidden");
  });

  // Conversational Explanation Card
  explainBtn.addEventListener("click", () => {
    if (!currentVerificationData) return;
    renderExplanation(currentVerificationData);
    explanationCard.classList.remove("hidden");
    explanationCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
  verdictExplainBtn.addEventListener("click", () => {
    if (!currentVerificationData) return;
    renderExplanation(currentVerificationData);
    explanationCard.classList.remove("hidden");
    explanationCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
  closeExplanationBtn.addEventListener("click", () => {
    explanationCard.classList.add("hidden");
  });
}

// Sidebar Collapse / Expand Toggle
function setupSidebarToggle() {
  if (!toggleSidebarBtn || !workspaceSidebar) return;
  toggleSidebarBtn.addEventListener("click", () => {
    const isCollapsed = workspaceSidebar.classList.toggle("collapsed");
    toggleSidebarBtn.title = isCollapsed ? "Expand Evidence Sidebar" : "Collapse Evidence Sidebar";
  });
}

// Light / Dark Theme Controller
function setupTheme() {
  if (!themeToggleBtn) return;
  
  const savedTheme = localStorage.getItem("custodychain_theme");
  if (savedTheme === "light") {
    applyTheme("light");
  } else {
    applyTheme("dark");
  }

  themeToggleBtn.addEventListener("click", () => {
    const isCurrentlyLight = document.body.classList.contains("theme-light");
    const nextTheme = isCurrentlyLight ? "dark" : "light";
    applyTheme(nextTheme);
    localStorage.setItem("custodychain_theme", nextTheme);
  });
}

function applyTheme(theme) {
  if (theme === "light") {
    document.body.classList.add("theme-light");
    if (themeIcon) themeIcon.textContent = "☀️";
    if (themeLabel) themeLabel.textContent = "Light Theme";
  } else {
    document.body.classList.remove("theme-light");
    if (themeIcon) themeIcon.textContent = "🌙";
    if (themeLabel) themeLabel.textContent = "Dark Theme";
  }
}

// Collapsible Evidence Details (Level 3)
function setupDetailsToggle() {
  toggleDetailsBtn.addEventListener("click", () => {
    const isHidden = detailsContent.classList.contains("hidden");
    if (isHidden) {
      detailsContent.classList.remove("hidden");
      detailsChevron.textContent = "▾";
    } else {
      detailsContent.classList.add("hidden");
      detailsChevron.textContent = "▸";
    }
  });
}

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

// Global & Sidebar Search
function setupSearch() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== globalSearch && document.activeElement !== sidebarSearch &&
        document.activeElement.tagName !== "TEXTAREA" && document.activeElement.tagName !== "INPUT") {
      e.preventDefault();
      globalSearch.focus();
    }
  });

  const filterSidebar = (query) => {
    const q = query.toLowerCase().trim();
    document.querySelectorAll(".exhibit-nav-item").forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(q) ? "flex" : "none";
    });
  };

  globalSearch.addEventListener("input", (e) => {
    sidebarSearch.value = e.target.value;
    filterSidebar(e.target.value);
  });

  sidebarSearch.addEventListener("input", (e) => {
    globalSearch.value = e.target.value;
    filterSidebar(e.target.value);
  });
}

// Quick Sample Demo Scenario (Cycles Real Forensic Examples)
runSampleBtn.addEventListener("click", () => {
  const scenario = FORENSIC_SCENARIOS[scenarioIndex];
  scenarioIndex = (scenarioIndex + 1) % FORENSIC_SCENARIOS.length;
  const randId = Math.floor(Math.random() * 9000 + 1000);
  const time = new Date().toLocaleTimeString();

  const name = `${scenario.prefix}-#${randId}`;
  const content = scenario.generate(randId, time);
  const simulateTamper = scenario.tamperStep !== 0;

  // Pre-fill modal form for transparency
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

// Manual Scenario Modal Ingestion
runCustomBtn.addEventListener("click", () => {
  const name = document.getElementById("evidenceName").value.trim() || `Exhibit-${Date.now()}`;
  const content = document.getElementById("evidenceContent").value.trim();
  const simulateTamper = document.getElementById("tamperToggle").checked;
  const tamperStep = parseInt(document.getElementById("tamperStepSelect").value, 10);

  if (!content) {
    alert("Please enter digital artifact content to ingest.");
    return;
  }

  scenarioModal.classList.add("hidden");
  ingestAndVerify({
    name,
    content,
    simulate_tamper: simulateTamper,
    tamper_step: tamperStep,
  });
});

// Re-Verify Active Evidence
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
    verifyBtnText.textContent = "Verify";
  }
});

// Export PDF Report
downloadPdfBtn.addEventListener("click", () => {
  if (!currentEvidenceId) return;
  window.open(`${API_BASE}/api/v1/reports/${currentEvidenceId}/pdf`, "_blank");
});

// Core Pipeline Execution
async function ingestAndVerify(payload) {
  setGlobalLoading(true);
  try {
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

    // Independent Multi-Vector Verification
    const verifyRes = await fetch(`${API_BASE}/api/v1/verification/${currentEvidenceId}`, { method: "POST" });
    if (!verifyRes.ok) throw new Error("Failed to verify evidence");
    const verifyData = await verifyRes.json();

    renderVerificationResults(verifyData);
    loadExhibitList();

  } catch (err) {
    alert("Error running custody pipeline: " + err.message);
  } finally {
    setGlobalLoading(false);
  }
}

// Render Results with 3-Level Progressive Disclosure
function renderVerificationResults(data) {
  currentEvidenceId = data.evidence_id;
  currentVerificationData = data;

  const isIntact = data.final_verdict === "CHAIN_INTACT";
  // Derive first broken step if not explicitly keyed in response
  let firstBreak = data.first_break;
  if (!firstBreak && data.steps) {
    firstBreak = data.steps.find(s => !s.verified);
    if (firstBreak && !firstBreak.reason) {
      if (firstBreak.signature_valid === false) {
        firstBreak.reason = "SIGNATURE_INVALID";
      } else if (firstBreak.ledger_link_valid === false) {
        firstBreak.reason = "LEDGER_LINK_BROKEN";
      } else {
        firstBreak.reason = "STORAGE_HASH_MISMATCH";
      }
    }
  }

  // Level 1: What is happening?
  headerExhibitTitle.textContent = data.evidence_name;
  headerExhibitId.textContent = data.exhibit_id || `EX-${data.evidence_id}`;
  
  if (isIntact) {
    headerStatusTag.className = "status-summary-tag verified";
    headerStatusTag.textContent = "Chain intact";
  } else {
    headerStatusTag.className = "status-summary-tag broken";
    headerStatusTag.textContent = `Broken at ${firstBreak?.handler_name || 'pipeline'}`;
  }

  // Level 3 Details Accordion Preview & Values
  const acquiredStr = new Date().toLocaleTimeString();
  metaTimestamp.textContent = acquiredStr;
  metaHash.textContent = data.original_hash;
  detailsPreview.textContent = `Acquired: ${acquiredStr} · Hash: ${trunc(data.original_hash, 16)}`;

  // Level 1: Quiet Verdict Summary Banner
  verdictBanner.className = `verdict-banner-card ${isIntact ? "verified" : "broken"}`;
  verdictBanner.classList.remove("hidden");

  if (isIntact) {
    verdictTitle.textContent = "Chain intact";
    verdictBreakPoint.textContent = "· All 5 handlers verified";
    verdictExplanation.textContent =
      "All custody handoffs independently recomputed. Artifact storage states match baseline hashes, and all digital signatures are authentic.";
  } else {
    verdictTitle.textContent = "Chain broken";
    verdictBreakPoint.textContent = `· First verifiable break: ${firstBreak?.handler_name || 'Step'} (Step ${firstBreak?.step_order || '?'})`;
    verdictExplanation.textContent =
      "The exported artifact differs from the verified input. Downstream findings are forensically tainted.";
  }

  // Update conversational explanation block if currently open
  if (!explanationCard.classList.contains("hidden")) {
    renderExplanation(data);
  }

  // Level 2 & 3: Timeline Cards with Progressive Disclosure
  renderTimelineCards(data);
}

// Render Conversational Explanation ("Why is this broken / intact?")
function renderExplanation(data) {
  const isIntact = data.final_verdict === "CHAIN_INTACT";
  let firstBreak = data.first_break;
  if (!firstBreak && data.steps) {
    firstBreak = data.steps.find(s => !s.verified);
    if (firstBreak && !firstBreak.reason) {
      if (firstBreak.signature_valid === false) {
        firstBreak.reason = "SIGNATURE_INVALID";
      } else if (firstBreak.ledger_link_valid === false) {
        firstBreak.reason = "LEDGER_LINK_BROKEN";
      } else {
        firstBreak.reason = "STORAGE_HASH_MISMATCH";
      }
    }
  }

  if (isIntact) {
    explanationTitle.textContent = "Integrity Analysis: Chain Intact";
    explanationBody.innerHTML = `
      <p><strong>Independent verification confirmed custody integrity.</strong></p>
      <p>Every digital artifact retrieved from physical storage matched its declared SHA-256 hash. All 5 handler transitions were authenticated with valid Ed25519 digital signatures, and previous-event ledger linkage remained continuous without omission.</p>
    `;
  } else {
    explanationTitle.textContent = `Why is this broken? (Break at Step ${firstBreak?.step_order}: ${esc(firstBreak?.handler_name)})`;

    let breakExplanation = "";
    if (firstBreak?.reason === "STORAGE_HASH_MISMATCH") {
      breakExplanation = `The first verifiable mismatch occurred during the <strong>${esc(firstBreak.handler_name)}</strong> transition (Step ${firstBreak.step_order}). The physical artifact hash stored on disk (<span class="hash-tag">${trunc(firstBreak.actual_hash, 16)}</span>) differs from the expected input hash (<span class="hash-tag">${trunc(firstBreak.hash_before, 16)}</span>).`;
    } else if (firstBreak?.reason === "SIGNATURE_INVALID") {
      breakExplanation = `The Ed25519 digital signature for <strong>${esc(firstBreak.handler_name)}</strong> failed cryptographic validation against the registered public key, indicating the record was either forged or altered in transit.`;
    } else if (firstBreak?.reason === "LEDGER_LINK_BROKEN") {
      breakExplanation = `The cryptographic previous-event hash chain was severed at <strong>${esc(firstBreak.handler_name)}</strong>. The event link did not match the hash of the preceding custody record.`;
    } else {
      breakExplanation = `An unauthorized mutation was localized at <strong>${esc(firstBreak?.handler_name || 'Step')}</strong>.`;
    }

    const downstreamSteps = data.steps.filter(s => s.downstream_of_break || s.step_order > (firstBreak?.step_order ?? 99));
    const downstreamNames = downstreamSteps.map(s => esc(s.handler_name)).join(", ") || "subsequent steps";

    explanationBody.innerHTML = `
      <p>${breakExplanation}</p>
      <p>Because the chain of custody was broken at this transition, all downstream handlers (<strong>${downstreamNames}</strong>) operated on tainted artifacts and cannot be admitted as authentic evidence.</p>
    `;
  }
}

// Render Simplified Custody Cards
function renderTimelineCards(data) {
  timelineCards.innerHTML = "";
  let breakEncountered = false;

  data.steps.forEach((step) => {
    let statusClass = "verified";
    let statusLabel = "Verified";

    if (!step.verified) {
      statusClass = "broken";
      statusLabel = "Broken";
      breakEncountered = true;
    } else if (step.downstream_of_break || breakEncountered) {
      statusClass = "downstream";
      statusLabel = "Downstream";
    }

    const card = document.createElement("div");
    card.className = `handler-card ${statusClass}`;

    const seqNum = String(step.step_order).padStart(2, "0");
    const sigValid = step.signature_valid !== false;
    const timeStr = formatDate(step.timestamp);
    const shortHash = trunc(step.actual_hash || step.hash_after || step.hash_before, 14);

    // Initial View (Level 2) + Expandable Details + Expandable Level 3 Proofs
    card.innerHTML = `
      <div class="handler-card-main">
        <div class="handler-left">
          <span class="step-number">${seqNum}</span>
          <span class="handler-name">${esc(step.handler_name)}</span>
        </div>
        <div class="handler-right">
          <span class="handler-time">${timeStr}</span>
          <span class="verification-tag ${statusClass}">${statusLabel}</span>
          <span class="expand-chevron">▾</span>
        </div>
      </div>

      <div class="handler-card-details">
        <div class="step-summary-row">
          <div class="step-summary-meta">
            <span>Handler: <strong>${esc(step.handler_name)}</strong></span>
            <span>Hash: <span class="font-mono">${esc(shortHash)}</span></span>
            <span>Signature: <strong style="color:${sigValid ? 'var(--verified-text)' : 'var(--broken-text)'}">${sigValid ? 'Valid' : 'Invalid'}</strong></span>
          </div>
          <button class="btn-toggle-proofs" type="button">View technical details</button>
        </div>

        <div class="technical-proofs-block">
          <div class="proofs-grid">
            <div class="proof-item">
              <span class="proof-label">Input SHA-256</span>
              <span class="proof-value">${esc(step.hash_before || '—')}</span>
            </div>
            <div class="proof-item">
              <span class="proof-label">Declared Hash</span>
              <span class="proof-value">${esc(step.hash_after || '—')}</span>
            </div>
            <div class="proof-item">
              <span class="proof-label">Storage Recomputed Hash</span>
              <span class="proof-value ${step.verified ? 'match' : 'mismatch'}">${esc(step.actual_hash || '—')}</span>
            </div>
          </div>
          <div class="crypto-audit-row">
            <div class="sig-status ${sigValid ? 'valid' : 'invalid'}">
              <span>Ed25519: <strong>${sigValid ? 'Valid Authenticated' : 'Signature Invalid / Forged'}</strong></span>
              <span class="font-mono" style="opacity:0.6">(${esc(step.signature_preview || 'Ed25519')})</span>
            </div>
            <div class="ledger-chain-status">
              <span>Ledger Link: <strong style="color:var(--verified-text)">Continuous</strong></span>
            </div>
          </div>
        </div>
      </div>
    `;

    // Click handler main row to toggle Level 2 details
    const mainRow = card.querySelector(".handler-card-main");
    mainRow.addEventListener("click", () => {
      card.classList.toggle("expanded");
    });

    // Click button to toggle Level 3 technical proofs
    const proofsBtn = card.querySelector(".btn-toggle-proofs");
    const proofsBlock = card.querySelector(".technical-proofs-block");
    proofsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = proofsBlock.classList.toggle("open");
      proofsBtn.textContent = isOpen ? "Hide technical details" : "View technical details";
    });

    timelineCards.appendChild(card);
  });
}

// Load Exhibits for Minimal Sidebar (Progressive Disclosure)
async function loadExhibitList() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/evidence`);
    if (!res.ok) return;
    allExhibits = await res.json();

    sidebarExhibitCount.textContent = `${allExhibits.length} items`;
    renderSidebarExhibits();

    // Auto-select latest exhibit if none active
    if (!currentEvidenceId && allExhibits.length > 0) {
      selectExhibit(allExhibits[0].id);
    }
  } catch (err) {
    console.warn("Failed to load exhibits:", err);
  }
}

function renderSidebarExhibits() {
  exhibitNavList.innerHTML = "";

  if (allExhibits.length === 0) {
    exhibitNavList.innerHTML = `<div style="padding:16px 8px;font-size:11px;color:var(--text-dim);text-align:center;">No exhibits yet. Run Quick Demo.</div>`;
    sidebarExpandWrap.classList.add("hidden");
    return;
  }

  const exhibitsToRender = showAllExhibits ? allExhibits : allExhibits.slice(0, SIDEBAR_PREVIEW_LIMIT);

  exhibitsToRender.forEach((item) => {
    const isVerified = item.status === "VERIFIED" || item.latest_verdict === "CHAIN_INTACT";
    const navItem = document.createElement("div");
    navItem.className = `exhibit-nav-item ${currentEvidenceId === item.id ? "active" : ""}`;
    navItem.innerHTML = `
      <div class="nav-item-left">
        <span class="nav-item-name" title="${esc(item.name)}">${esc(item.name)}</span>
        <span class="nav-item-id">${esc(item.exhibit_id || '#' + item.id)}</span>
      </div>
      <span class="nav-item-tag ${isVerified ? 'verified' : 'broken'}">
        ${isVerified ? 'Verified' : 'Broken'}
      </span>
    `;

    navItem.addEventListener("click", () => {
      document.querySelectorAll(".exhibit-nav-item").forEach(i => i.classList.remove("active"));
      navItem.classList.add("active");
      selectExhibit(item.id);
    });

    exhibitNavList.appendChild(navItem);
  });

  // Toggle "View all N evidence"
  if (allExhibits.length > SIDEBAR_PREVIEW_LIMIT) {
    sidebarExpandWrap.classList.remove("hidden");
    toggleAllExhibitsBtn.textContent = showAllExhibits
      ? "Show fewer evidence"
      : `View all ${allExhibits.length} evidence`;
  } else {
    sidebarExpandWrap.classList.add("hidden");
  }
}

toggleAllExhibitsBtn.addEventListener("click", () => {
  showAllExhibits = !showAllExhibits;
  renderSidebarExhibits();
});

async function selectExhibit(id) {
  try {
    const verifyRes = await fetch(`${API_BASE}/api/v1/verification/${id}`, { method: "POST" });
    if (verifyRes.ok) {
      const data = await verifyRes.json();
      renderVerificationResults(data);
    }
  } catch (e) {
    console.error("Error loading exhibit:", e);
  }
}

// Load Cases
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

// Load Immutable System Audit Trail
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
    auditTableBody.innerHTML = `<tr><td colspan="5" style="color:var(--broken-text);">${esc(err.message)}</td></tr>`;
  }
}

// Helpers
function setGlobalLoading(isLoading) {
  runSampleBtn.disabled = isLoading;
  runCustomBtn.disabled = isLoading;
  if (isLoading) {
    runSampleBtn.innerHTML = `<span class="btn-symbol">⏳</span><span>Processing…</span>`;
  } else {
    runSampleBtn.innerHTML = `<span class="btn-symbol">▶</span><span>Quick Demo Scenario</span>`;
  }
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
