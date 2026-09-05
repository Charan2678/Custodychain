/* ==========================================================================
   CustodyChain — Modern Calm Forensic Workspace Controller (Production Auth)
   ========================================================================== */

const API_BASE = "http://localhost:8000";

const FORENSIC_SCENARIOS = [
  {
    prefix: "Case-2026-WhatsApp-ChatDB",
    title: "WhatsApp SQLite Chat DB",
    generate: (caseId, time) =>
      `CASE_REF: #2026-${caseId}-MOB\nEXHIBIT: WhatsApp SQLite Chat Database\nEXTRACTION_TIME: ${time}\n[14:00:01] Suspect: Meeting at warehouse confirmed.\n[14:01:23] Accomplice: Bring the encrypted drive.\nMD5_SOURCE: d41d8cd98f00b204e9800998ecf8427e`,
    tamperStep: 0,
    tamperLabel: "Pure Verified Intact Chain",
  },
  {
    prefix: "Case-2026-FinFraud-Ledger-TX",
    title: "Wire Transfer Settlement Ledger",
    generate: (caseId, time) =>
      `TRANSACTION_BATCH_AUDIT: TX-${caseId}-WIRE\nBATCH_TIMESTAMP: ${time}\nORIGIN_ROUTING: 021000021 (Chase Bank NY)\nBENEFICIARY_IBAN: GB29NWBK60161331926819\nTRANSFERRED_AMOUNT_USD: $3,750,000.00\nSETTLEMENT_STATUS: CLEARED_BY_FEDWIRE`,
    tamperStep: 0,
    tamperLabel: "Pure Verified Intact Chain",
  },
  {
    prefix: "Case-2026-CCTV-FrameCheck-North",
    title: "CCTV Surveillance Stream Checksum",
    generate: (caseId, time) =>
      `SURVEILLANCE_STREAM: CAM-04-NORTH-GATE\nFRAME_SYNC_TIME: ${time}\nKEYFRAME_HASH: 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d\nOFFICER_BADGE: SFPD-0892\nTAMPER_SEAL: PHYSICAL_ZIP_LOCK_TAG_${caseId}`,
    tamperStep: 0,
    tamperLabel: "Pure Verified Intact Chain",
  },
  {
    prefix: "Case-2026-NVMe-DiskImage-Raw",
    title: "Bitstream NVMe Physical Drive Image",
    generate: (caseId, time) =>
      `BITSTREAM_DISK_IMAGE: PHYSICAL_DRIVE_${caseId}\nIMAGING_TOOL: FTK_Imager_v4.7_HARDWARE_WRITE_BLOCKED\nTIME_ACQUIRED: ${time}\nPARTITION_TABLE: GPT / NTFS_VOLUME_GUID\nSECTOR_RANGE: LBA 0x00000000 - 0x7FFFFFFF`,
    tamperStep: 0,
    tamperLabel: "Pure Verified Intact Chain",
  },
  {
    prefix: "Case-2026-HSM-Encrypted-Keystore",
    title: "Hardware Security Module Key Certificate",
    generate: (caseId, time) =>
      `VAULT_KEYSTORE: HSM-LUNA-PCIe-SLOT-${caseId}\nCERTIFICATE_ISSUER: Forensic Root Authority CA\nVALIDATED_AT: ${time}\nALGORITHM: RSA-4096 / SHA-256\nSTATUS: VALID_UNCOMPROMISED_CHAIN`,
    tamperStep: 0,
    tamperLabel: "Pure Verified Intact Chain",
  },
];

// Four-Tier Production RBAC Hierarchy Specification
const ROLE_HIERARCHY = {
  "SYSTEM_ADMIN": {
    level: 4,
    tier: "LEVEL 4",
    roleName: "System Admin",
    fullName: "Charan (Root Admin)",
    avatar: "A",
    tagline: "Full Root & Ledger Clearance",
    summary: "Complete administrative authority across custody chain, case registry, lab ingestion, independent verification, and immutable security audit logs.",
    email: "charan@custodychain.internal",
    canCase: true,
    canIngest: true,
    canVerify: true,
    canAudit: true,
    canSimulate: true,
    canReport: true,
    pills: [
      { text: "✓ Case Registry", allowed: true },
      { text: "✓ Evidence Intake", allowed: true },
      { text: "✓ Verification", allowed: true },
      { text: "✓ Audit Trail", allowed: true },
    ]
  },
  "EVIDENCE_OFFICER": {
    level: 3,
    tier: "LEVEL 3",
    roleName: "Evidence Officer",
    fullName: "Officer John Vance",
    avatar: "O",
    tagline: "Custody Intake & Case Registry",
    summary: "Authorized for official case registration and evidence intake. Strictly prohibited from inspecting internal audit trails or self-verifying intake.",
    email: "officer@custodychain.internal",
    canCase: true,
    canIngest: true,
    canVerify: false,
    canAudit: false,
    canSimulate: true,
    canReport: false,
    pills: [
      { text: "✓ Case Registry", allowed: true },
      { text: "✓ Evidence Intake", allowed: true },
      { text: "🔒 Verify (Locked)", allowed: false, reason: "Self-verification prohibited by court forensic standard" },
      { text: "🔒 Audit Trail (Locked)", allowed: false, reason: "Audit trail restricted to Auditors and Admins" },
    ]
  },
  "FORENSIC_ANALYST": {
    level: 2,
    tier: "LEVEL 2",
    roleName: "Forensic Analyst",
    fullName: "Dr. Elena Rostova",
    avatar: "F",
    tagline: "Laboratory Analysis & Verification",
    summary: "Authorized for forensic laboratory analysis, cryptographic recomputations, Ed25519 signature validation, and court report generation. Prohibited from registering legal cases.",
    email: "analyst@custodychain.internal",
    canCase: false,
    canIngest: true,
    canVerify: true,
    canAudit: false,
    canSimulate: true,
    canReport: true,
    pills: [
      { text: "🔒 Case Registry (Locked)", allowed: false, reason: "Case creation restricted to Evidence Officers and Admins" },
      { text: "✓ Lab Ingestion", allowed: true },
      { text: "✓ Verification", allowed: true },
      { text: "🔒 Audit Trail (Locked)", allowed: false, reason: "Audit trail restricted to Auditors and Admins" },
    ]
  },
  "AUDITOR": {
    level: 1,
    tier: "LEVEL 1",
    roleName: "Independent Auditor",
    fullName: "Sarah Chen (Auditor)",
    avatar: "I",
    tagline: "Regulatory Oversight (Read-Only)",
    summary: "Strict read-only regulatory oversight. Authorized to inspect immutable audit trails, verify cryptographic hash links, and validate certificates. Evidence creation strictly forbidden.",
    email: "auditor@custodychain.internal",
    canCase: false,
    canIngest: false,
    canVerify: true,
    canAudit: true,
    canSimulate: false,
    canReport: true,
    pills: [
      { text: "🔒 Case Registry (Locked)", allowed: false, reason: "Case creation restricted to Evidence Officers and Admins" },
      { text: "🔒 Ingestion (Forbidden)", allowed: false, reason: "Auditor must remain independent; cannot contaminate evidence chain" },
      { text: "✓ Verification", allowed: true },
      { text: "✓ Audit Trail", allowed: true },
    ]
  },
};

let currentActiveRole = "SYSTEM_ADMIN";
let scenarioIndex = 0;
let currentEvidenceId = null;
let currentCaseId = 1;
let currentVerificationData = null;
let allExhibits = [];
let showAllExhibits = false;
const SIDEBAR_PREVIEW_LIMIT = 5;

// DOM Elements
const newCaseBtn          = document.getElementById("newCaseBtn");
const newCaseBtnLabel     = document.getElementById("newCaseBtnLabel");
const runSampleBtn        = document.getElementById("runSampleBtn");
const runSampleBtnLabel   = document.getElementById("runSampleBtnLabel");
const newEvidenceBtn      = document.getElementById("newEvidenceBtn");
const newEvidenceBtnLabel = document.getElementById("newEvidenceBtnLabel");
const openAuditBtn        = document.getElementById("openAuditBtn");
const openAuditBtnLabel   = document.getElementById("openAuditBtnLabel");

const closeAuditModalBtn  = document.getElementById("closeAuditModalBtn");
const auditModal          = document.getElementById("auditModal");
const auditTableBody      = document.getElementById("auditTableBody");
const verifyAuditLedgerBtn= document.getElementById("verifyAuditLedgerBtn");
const auditVerifyStatus   = document.getElementById("auditVerifyStatus");

const newCaseModal        = document.getElementById("newCaseModal");
const closeNewCaseModalBtn= document.getElementById("closeNewCaseModalBtn");
const cancelNewCaseBtn    = document.getElementById("cancelNewCaseBtn");
const newCaseForm         = document.getElementById("newCaseForm");

const scenarioModal       = document.getElementById("scenarioModal");
const toggleSimulatorBtn  = document.getElementById("toggleSimulatorBtn");
const closeDrawerBtn      = document.getElementById("closeDrawerBtn");
const cancelModalBtn      = document.getElementById("cancelModalBtn");
const runCustomBtn        = document.getElementById("runCustomBtn");

const howVerifiedBtn      = document.getElementById("howVerifiedBtn");
const howVerifiedModal    = document.getElementById("howVerifiedModal");
const closeHowVerifiedBtn = document.getElementById("closeHowVerifiedBtn");

const verifyBtn           = document.getElementById("verifyBtn");
const verifyBtnText       = document.getElementById("verifyBtnText");
const explainBtn          = document.getElementById("explainBtn");
const downloadPdfBtn      = document.getElementById("downloadPdfBtn");

const exhibitNavList      = document.getElementById("exhibitNavList");
const sidebarExhibitCount = document.getElementById("sidebarExhibitCount");
const sidebarExpandWrap   = document.getElementById("sidebarExpandWrap");
const toggleAllExhibitsBtn= document.getElementById("toggleAllExhibitsBtn");
const sidebarSearch       = document.getElementById("sidebarSearch");
const globalSearch        = document.getElementById("globalSearch");

const caseSelect          = document.getElementById("caseSelect");
const headerCaseNumber    = document.getElementById("headerCaseNumber");
const headerExhibitId     = document.getElementById("headerExhibitId");
const headerExhibitTitle  = document.getElementById("headerExhibitTitle");
const headerStatusTag     = document.getElementById("headerStatusTag");

const toggleDetailsBtn    = document.getElementById("toggleDetailsBtn");
const detailsChevron      = document.getElementById("detailsChevron");
const detailsContent      = document.getElementById("detailsContent");
const detailsPreview      = document.getElementById("detailsPreview");
const metaTimestamp       = document.getElementById("metaTimestamp");
const metaCustodian       = document.getElementById("metaCustodian");
const metaHash            = document.getElementById("metaHash");

const verdictBanner       = document.getElementById("verdictBanner");
const verdictTitle        = document.getElementById("verdictTitle");
const verdictBreakPoint   = document.getElementById("verdictBreakPoint");
const verdictExplanation  = document.getElementById("verdictExplanation");
const verdictExplainBtn   = document.getElementById("verdictExplainBtn");

const explanationCard     = document.getElementById("explanationCard");
const explanationTitle    = document.getElementById("explanationTitle");
const explanationBody     = document.getElementById("explanationBody");
const closeExplanationBtn = document.getElementById("closeExplanationBtn");

const timelineCards       = document.getElementById("timelineCards");

// Custody Handover Card Elements
const custodyHandoverCard   = document.getElementById("custodyHandoverCard");
const handoverTitle         = document.getElementById("handoverTitle");
const handoverSubtitle      = document.getElementById("handoverSubtitle");
const handoverStatusBadge   = document.getElementById("handoverStatusBadge");
const handoverCurrentActor  = document.getElementById("handoverCurrentActor");
const handoverCurrentRole   = document.getElementById("handoverCurrentRole");
const handoverNextActor     = document.getElementById("handoverNextActor");
const handoverNextRole      = document.getElementById("handoverNextRole");
const handoverTamperToggle  = document.getElementById("handoverTamperToggle");
const advanceCustodyBtn     = document.getElementById("advanceCustodyBtn");
const advanceCustodyBtnText = document.getElementById("advanceCustodyBtnText");
const handoverHint          = document.getElementById("handoverHint");

const userMenuBtn         = document.getElementById("userMenuBtn");
const roleDropdown        = document.getElementById("roleDropdown");
const navUserAvatar       = document.getElementById("navUserAvatar");
const navClearanceTag     = document.getElementById("navClearanceTag");
const navUserName         = document.getElementById("navUserName");
const navUserRole         = document.getElementById("navUserRole");

const roleClearanceCard   = document.getElementById("roleClearanceCard");
const clearanceLevelTag   = document.getElementById("clearanceLevelTag");
const clearanceTitle      = document.getElementById("clearanceTitle");
const clearanceSummary    = document.getElementById("clearanceSummary");
const clearanceMatrix     = document.getElementById("clearanceMatrix");

const securityToast       = document.getElementById("securityToast");
const toastTitle          = document.getElementById("toastTitle");
const toastMsg            = document.getElementById("toastMsg");

const themeToggleBtn      = document.getElementById("themeToggleBtn");
const themeIcon           = document.getElementById("themeIcon");
const themeLabel          = document.getElementById("themeLabel");
const toggleSidebarBtn    = document.getElementById("toggleSidebarBtn");
const workspaceSidebar    = document.querySelector(".workspace-sidebar");


// ==========================================================================
// Centralized Production API Helper with Bearer Authentication
// ==========================================================================
async function apiFetch(url, options = {}) {
  let token = localStorage.getItem("access_token");
  if (!token) {
    token = await authenticateUser("charan@custodychain.internal", "evidence123");
  }

  const headers = {
    ...(options.headers || {}),
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    token = await authenticateUser("charan@custodychain.internal", "evidence123");
    if (token) {
      const retryHeaders = {
        ...(options.headers || {}),
        "Authorization": `Bearer ${token}`,
      };
      return fetch(url, { ...options, headers: retryHeaders });
    }
  }
  return response;
}

async function authenticateUser(email, password) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("current_user", JSON.stringify(data.user));
      updateUserDisplay(data.user);
      return data.access_token;
    }
  } catch (err) {
    console.error("Authentication error:", err);
  }
  return null;
}

function updateUserDisplay(user) {
  if (!user || !user.role) return;
  applyRoleHierarchy(user.role);
}

// Global Security Notification Toast
function showSecurityToast(title, message) {
  if (!securityToast) return;
  if (toastTitle) toastTitle.textContent = title;
  if (toastMsg) toastMsg.textContent = message;
  securityToast.classList.remove("hidden");
  clearTimeout(window._toastTimeout);
  window._toastTimeout = setTimeout(() => {
    securityToast.classList.add("hidden");
  }, 4200);
}

// Active Role & Permission Hierarchy Enforcement
function applyRoleHierarchy(roleKey) {
  const meta = ROLE_HIERARCHY[roleKey] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
  currentActiveRole = roleKey;

  // 1. Top Navbar Updates
  if (navUserAvatar) navUserAvatar.textContent = meta.avatar;
  if (navClearanceTag) navClearanceTag.textContent = meta.tier;
  if (navUserName) navUserName.textContent = meta.fullName;
  if (navUserRole) navUserRole.textContent = `${meta.roleName} · ${meta.tagline}`;

  // 2. Role Dropdown Active Indicator
  document.querySelectorAll(".role-option").forEach(btn => {
    const r = btn.getAttribute("data-role");
    if (r === roleKey) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // 3. Sidebar Role Clearance Card
  if (clearanceLevelTag) clearanceLevelTag.textContent = meta.tier;
  if (clearanceTitle) clearanceTitle.textContent = meta.roleName;
  if (clearanceSummary) clearanceSummary.textContent = meta.summary;
  if (clearanceMatrix) {
    clearanceMatrix.innerHTML = meta.pills.map(p => `
      <span class="perm-pill ${p.allowed ? 'allowed' : 'locked'}" title="${esc(p.reason || (p.allowed ? 'Clearance active' : 'Restricted for role'))}">
        ${esc(p.text)}
      </span>
    `).join("");
  }

  // 4. Action Buttons Control & Honest Hierarchy Locks

  // New Case Button
  if (newCaseBtn) {
    if (meta.canCase) {
      newCaseBtn.classList.remove("btn-locked");
      newCaseBtn.title = "Register new legal case (Level 3/4 Clearance)";
      if (newCaseBtnLabel) newCaseBtnLabel.textContent = "New Case";
    } else {
      newCaseBtn.classList.add("btn-locked");
      newCaseBtn.title = `🔒 Restricted: Case registration requires Evidence Officer or Admin clearance (Current: ${meta.roleName})`;
      if (newCaseBtnLabel) newCaseBtnLabel.textContent = "🔒 New Case";
    }
  }

  // Quick Ingestion Button
  if (runSampleBtn) {
    if (meta.canIngest) {
      runSampleBtn.classList.remove("btn-locked");
      runSampleBtn.title = "Cycle through real-world forensic exhibits";
      if (runSampleBtnLabel) runSampleBtnLabel.textContent = "Quick Ingestion";
    } else {
      runSampleBtn.classList.add("btn-locked");
      runSampleBtn.title = "🔒 Restricted: Auditor has read-only oversight; cannot ingest evidence.";
      if (runSampleBtnLabel) runSampleBtnLabel.textContent = "🔒 Ingestion (Read-Only)";
    }
  }

  // Simulation / Ingestion Button
  if (newEvidenceBtn) {
    if (meta.canIngest) {
      newEvidenceBtn.classList.remove("btn-locked");
      newEvidenceBtn.title = "Ingest new exhibit artifact or simulate tamper";
      if (newEvidenceBtnLabel) newEvidenceBtnLabel.textContent = "Simulation / Ingestion";
    } else {
      newEvidenceBtn.classList.add("btn-locked");
      newEvidenceBtn.title = "🔒 Restricted: Auditor cannot ingest or modify evidence.";
      if (newEvidenceBtnLabel) newEvidenceBtnLabel.textContent = "🔒 Ingestion (Read-Only)";
    }
  }

  // Audit Trail Button
  if (openAuditBtn) {
    if (meta.canAudit) {
      openAuditBtn.classList.remove("btn-locked");
      openAuditBtn.title = "Inspect immutable security audit ledger";
      if (openAuditBtnLabel) openAuditBtnLabel.textContent = roleKey === "AUDITOR" ? "Audit Trail ★" : "Audit Trail";
    } else {
      openAuditBtn.classList.add("btn-locked");
      openAuditBtn.title = `🔒 Restricted: Audit trail inspection is restricted to Auditor and Admin (Current: ${meta.roleName})`;
      if (openAuditBtnLabel) openAuditBtnLabel.textContent = "🔒 Audit Trail (Auditor Only)";
    }
  }

  // Scenario Button in Canvas Header
  if (toggleSimulatorBtn) {
    if (meta.canSimulate) {
      toggleSimulatorBtn.classList.remove("action-locked");
      toggleSimulatorBtn.title = "Configure simulated tamper scenario";
    } else {
      toggleSimulatorBtn.classList.add("action-locked");
      toggleSimulatorBtn.title = "🔒 Restricted: Auditor cannot inject simulated tamper scenarios.";
    }
  }

  // Verify Button
  if (verifyBtn) {
    if (meta.canVerify) {
      verifyBtn.classList.remove("action-locked");
      verifyBtn.title = "Execute independent multi-vector verification";
      if (verifyBtnText) verifyBtnText.textContent = "Verify";
    } else {
      verifyBtn.classList.add("action-locked");
      verifyBtn.title = "🔒 Restricted: Evidence Officers cannot self-verify evidence intake.";
      if (verifyBtnText) verifyBtnText.textContent = "🔒 Verify (Analyst Only)";
    }
  }

  // Report Button
  if (downloadPdfBtn) {
    if (meta.canReport) {
      downloadPdfBtn.classList.remove("action-locked");
      downloadPdfBtn.title = "Export Court-Admissible Chain-of-Custody Certificate";
    } else {
      downloadPdfBtn.classList.add("action-locked");
      downloadPdfBtn.title = "🔒 Restricted: Report generation restricted to Forensic Analysts, Auditors, and Admins.";
    }
  }

  // 5. Update custody handover card according to newly active role
  if (currentVerificationData && typeof updateCustodyHandoverCard === "function") {
    updateCustodyHandoverCard(currentVerificationData);
  }
}

// ---- Initialization ----
document.addEventListener("DOMContentLoaded", async () => {
  // 1. Initial Authentication & Hierarchy Setup
  const savedUser = localStorage.getItem("current_user");
  let userObj = null;
  if (savedUser) {
    try {
      userObj = JSON.parse(savedUser);
    } catch {}
  }
  
  if (userObj && userObj.role) {
    applyRoleHierarchy(userObj.role);
  } else {
    await authenticateUser("charan@custodychain.internal", "evidence123");
    applyRoleHierarchy("SYSTEM_ADMIN");
  }

  // 2. Load Workspace Data
  await loadCases();
  await loadExhibitList();

  // 3. Setup UI Listeners
  setupRoleMenu();
  setupSearch();
  setupModals();
  setupDetailsToggle();
  setupTheme();
  setupSidebarToggle();
  setupCaseSelector();
});

// Case Selector Synchronization
function setupCaseSelector() {
  if (!caseSelect) return;
  caseSelect.addEventListener("change", (e) => {
    currentCaseId = Number(e.target.value);
    const opt = caseSelect.options[caseSelect.selectedIndex];
    if (opt && headerCaseNumber) {
      const match = opt.textContent.match(/\(([^)]+)\)/);
      headerCaseNumber.textContent = match ? match[1] : `CASE-${currentCaseId}`;
    }
  });
}

// Setup Modals & Dialogs
function setupModals() {
  // New Case Modal & Submission
  if (newCaseBtn) {
    newCaseBtn.addEventListener("click", () => {
      const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
      if (!meta.canCase) {
        showSecurityToast("Permission Denied (Level 3 Required)", `${meta.roleName} lacks case creation clearance. Only Evidence Officers and Admins may register cases.`);
        return;
      }
      if (newCaseModal) {
        newCaseModal.classList.remove("hidden");
        const numInput = document.getElementById("newCaseNumber");
        if (numInput) {
          numInput.value = `CASE-${new Date().getFullYear()}-${Math.floor(Math.random() * 9000 + 1000)}`;
          numInput.focus();
        }
      }
    });
  }

  if (closeNewCaseModalBtn) closeNewCaseModalBtn.addEventListener("click", () => newCaseModal.classList.add("hidden"));
  if (cancelNewCaseBtn) cancelNewCaseBtn.addEventListener("click", () => newCaseModal.classList.add("hidden"));
  if (newCaseModal) {
    newCaseModal.addEventListener("click", (e) => {
      if (e.target === newCaseModal) newCaseModal.classList.add("hidden");
    });
  }

  if (newCaseForm) {
    newCaseForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const caseNum = document.getElementById("newCaseNumber").value.trim();
      const title = document.getElementById("newCaseTitle").value.trim();
      const desc = document.getElementById("newCaseDesc").value.trim();
      const submitBtn = document.getElementById("submitNewCaseBtn");
      submitBtn.disabled = true;
      submitBtn.textContent = "Registering...";

      try {
        const res = await apiFetch(`${API_BASE}/api/v1/cases`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ case_number: caseNum, title: title, description: desc }),
        });

        if (res.ok) {
          const newCase = await res.json();
          newCaseModal.classList.add("hidden");
          newCaseForm.reset();
          await loadCases();
          if (caseSelect) {
            caseSelect.value = String(newCase.id);
            currentCaseId = newCase.id;
            headerCaseNumber.textContent = newCase.case_number;
          }
          showSecurityToast("Case Registered", `Official case ${caseNum} registered into forensic ledger.`);
        } else {
          const errData = await res.json().catch(() => ({ detail: "Failed to register case" }));
          showSecurityToast("Registration Failed", errData.detail || "Unable to register case.");
        }
      } catch (err) {
        showSecurityToast("Network Error", err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Register Case";
      }
    });
  }

  // Scenario / Ingestion Modal
  toggleSimulatorBtn.addEventListener("click", () => {
    const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
    if (!meta.canSimulate) {
      showSecurityToast("Action Restricted", `${meta.roleName} cannot inject simulated tamper scenarios.`);
      return;
    }
    scenarioModal.classList.remove("hidden");
  });

  newEvidenceBtn.addEventListener("click", () => {
    const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
    if (!meta.canIngest) {
      showSecurityToast("Action Restricted (Read-Only)", `${meta.roleName} is an independent oversight role and cannot ingest evidence.`);
      return;
    }
    scenarioModal.classList.remove("hidden");
    const evNameInput = document.getElementById("evidenceName");
    if (evNameInput) evNameInput.focus();
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

  // Audit Modal & Ledger Verification
  openAuditBtn.addEventListener("click", () => {
    const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
    if (!meta.canAudit) {
      showSecurityToast("Permission Denied (403 Forbidden)", `System Audit Trail is restricted to Auditor and Admin. Current role (${meta.roleName}) lacks VIEW_AUDIT clearance.`);
      return;
    }
    loadAuditTrail();
  });

  closeAuditModalBtn.addEventListener("click", () => auditModal.classList.add("hidden"));
  auditModal.addEventListener("click", (e) => {
    if (e.target === auditModal) auditModal.classList.add("hidden");
  });

  if (verifyAuditLedgerBtn) {
    verifyAuditLedgerBtn.addEventListener("click", async () => {
      verifyAuditLedgerBtn.disabled = true;
      verifyAuditLedgerBtn.textContent = "Checking Hashes...";
      try {
        const res = await apiFetch(`${API_BASE}/api/v1/audit/verify`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "VALID" || data.status === "INTACT") {
            auditVerifyStatus.className = "audit-verify-banner intact";
            auditVerifyStatus.textContent = `✓ Audit Ledger Intact: ${data.events_checked} records cryptographically verified via unbroken SHA-256 hash continuity.`;
            auditVerifyStatus.classList.remove("hidden");
          } else {
            auditVerifyStatus.className = "audit-verify-banner failed";
            auditVerifyStatus.textContent = `✕ Break Detected: Record #${data.broken_event_id || 'N/A'} hash mismatch.`;
            auditVerifyStatus.classList.remove("hidden");
          }
        } else {
          auditVerifyStatus.className = "audit-verify-banner failed";
          auditVerifyStatus.textContent = `Access Denied: 403 Forbidden.`;
          auditVerifyStatus.classList.remove("hidden");
        }
      } catch (err) {
        auditVerifyStatus.className = "audit-verify-banner failed";
        auditVerifyStatus.textContent = `Verification Error: ${err.message}`;
        auditVerifyStatus.classList.remove("hidden");
      } finally {
        verifyAuditLedgerBtn.disabled = false;
        verifyAuditLedgerBtn.textContent = "Verify Ledger Continuity";
      }
    });
  }

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

  // Interactive Custody Handover Advancement Button
  if (advanceCustodyBtn) {
    advanceCustodyBtn.addEventListener("click", async () => {
      if (!currentEvidenceId) return;

      advanceCustodyBtn.disabled = true;
      advanceCustodyBtnText.textContent = "Transferring & Signing…";

      const simulateTamper = handoverTamperToggle ? handoverTamperToggle.checked : false;

      try {
        const res = await apiFetch(`${API_BASE}/api/v1/evidence/${currentEvidenceId}/transfer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ simulate_tamper: simulateTamper }),
        });

        if (res.ok) {
          const updatedData = await res.json();
          if (handoverTamperToggle) handoverTamperToggle.checked = false;
          renderVerificationResults(updatedData);
          loadExhibitList();

          const latestStep = updatedData.steps ? updatedData.steps[updatedData.steps.length - 1] : null;
          showSecurityToast("Custody Transferred", `Step ${latestStep?.step_order || ''} (${latestStep?.handler_name || 'Handover'}) executed & cryptographically signed.`);
        } else {
          const err = await res.json().catch(() => ({ detail: "Handover failed" }));
          showSecurityToast("Transfer Prohibited (403)", err.detail || "Clearance lacked for this handover.");
          if (currentVerificationData) updateCustodyHandoverCard(currentVerificationData);
        }
      } catch (err) {
        showSecurityToast("Network Error", err.message);
        if (currentVerificationData) updateCustodyHandoverCard(currentVerificationData);
      }
    });
  }
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

// Production RBAC Persona Switching via Real Login Authentication
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
      const roleKey = btn.getAttribute("data-role");
      const meta = ROLE_HIERARCHY[roleKey];
      if (!meta) return;

      // Authenticate as this role via real JWT endpoint
      const token = await authenticateUser(meta.email, "evidence123");
      if (token) {
        applyRoleHierarchy(roleKey);
        roleDropdown.classList.add("hidden");
        showSecurityToast(`Switched to ${meta.roleName}`, `Clearance: ${meta.tier}. Permissions updated across workspace.`);
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

// Quick Sample Ingestion (Step-by-Step Initial Intake)
runSampleBtn.addEventListener("click", () => {
  const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
  if (!meta.canIngest) {
    showSecurityToast("Action Restricted (Read-Only)", `${meta.roleName} is an independent oversight role and cannot ingest digital exhibits.`);
    return;
  }

  const scenario = FORENSIC_SCENARIOS[scenarioIndex];
  scenarioIndex = (scenarioIndex + 1) % FORENSIC_SCENARIOS.length;
  const randId = Math.floor(Math.random() * 9000 + 1000);
  const time = new Date().toLocaleTimeString();

  const name = `${scenario.prefix}-#${randId}`;
  const content = scenario.generate(randId, time);

  document.getElementById("evidenceName").value = name;
  document.getElementById("evidenceContent").value = content;
  document.getElementById("tamperStepSelect").value = "0";
  document.getElementById("tamperToggle").checked = false;

  // Registered at Step 1 (Collector) intact by Evidence Officer, awaiting handover
  ingestAndVerify({
    name,
    content,
    step_by_step: true,
    simulate_tamper: false,
    tamper_step: 0,
  });
});

// Manual Scenario Modal Ingestion
runCustomBtn.addEventListener("click", () => {
  const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
  if (!meta.canIngest) {
    showSecurityToast("Action Restricted (Read-Only)", `${meta.roleName} is an independent oversight role and cannot ingest digital exhibits.`);
    return;
  }

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
    step_by_step: !simulateTamper, // Step-by-step for clean exhibits; direct pipeline execution for tamper tests
    simulate_tamper: simulateTamper,
    tamper_step: tamperStep,
  });
});

// Re-Verify Active Evidence
verifyBtn.addEventListener("click", async () => {
  const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
  if (!meta.canVerify) {
    showSecurityToast("Forensic Safeguard Active", `${meta.roleName} cannot self-verify evidence intake. Independent verification must be run by a Forensic Analyst or Auditor.`);
    return;
  }

  if (!currentEvidenceId) return;
  verifyBtn.disabled = true;
  verifyBtnText.textContent = "Verifying…";
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/verification/${currentEvidenceId}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      renderVerificationResults(data);
      loadExhibitList();
    } else if (res.status === 403) {
      showSecurityToast("Permission Denied (403)", "Your active role lacks permission to verify evidence.");
    }
  } catch (err) {
    console.error("Verification error:", err);
  } finally {
    verifyBtn.disabled = false;
    verifyBtnText.textContent = "Verify";
  }
});

// Export Evidence Integrity PDF Report with Bearer Authorization
downloadPdfBtn.addEventListener("click", async () => {
  const meta = ROLE_HIERARCHY[currentActiveRole] || ROLE_HIERARCHY["SYSTEM_ADMIN"];
  if (!meta.canReport) {
    showSecurityToast("Action Restricted", `${meta.roleName} is not authorized to generate forensic integrity reports.`);
    return;
  }

  if (!currentEvidenceId) return;
  downloadPdfBtn.disabled = true;
  downloadPdfBtn.textContent = "Exporting…";
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/reports/${currentEvidenceId}/pdf`);
    if (!res.ok) {
      if (res.status === 403) {
        showSecurityToast("Access Denied (403)", "Your active role cannot generate forensic reports.");
      } else {
        alert("Failed to generate report.");
      }
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CustodyChain_EvidenceIntegrity_EX-${currentEvidenceId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("PDF download error:", err);
  } finally {
    downloadPdfBtn.disabled = false;
    downloadPdfBtn.innerHTML = `<span class="btn-symbol">⇩</span><span>Report</span>`;
  }
});

// Core Ingestion & Authoritative Verification Flow
async function ingestAndVerify(payload) {
  if (!currentCaseId) {
    alert("Please select an active investigation case before ingesting evidence.");
    return;
  }

  setGlobalLoading(true);
  try {
    const createRes = await apiFetch(`${API_BASE}/api/v1/evidence`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: payload.name,
        content: payload.content,
        case_id: currentCaseId,
        step_by_step: payload.step_by_step !== undefined ? payload.step_by_step : true,
        simulate_tamper: payload.simulate_tamper || false,
        tamper_step: payload.tamper_step || 0,
      }),
    });

    if (!createRes.ok) {
      if (createRes.status === 403) {
        throw new Error("Access Denied: Your current role (e.g. Auditor) is not authorized to ingest evidence.");
      }
      const err = await createRes.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${createRes.status}`);
    }

    const createdData = await createRes.json();
    currentEvidenceId = createdData.evidence_id;

    // Direct render from authoritative backend verification response
    renderVerificationResults(createdData);
    loadExhibitList();

    const isStep1 = createdData.steps && createdData.steps.length === 1;
    if (isStep1) {
      showSecurityToast("Evidence Ingested (Step 1)", `Exhibit registered intact at Step 1 (Collector) by ${ROLE_HIERARCHY[currentActiveRole]?.fullName || 'Officer'}. Awaiting handover.`);
    } else {
      showSecurityToast("Pipeline Executed", `Exhibit ${createdData.exhibit_id || '#' + createdData.evidence_id} processed across custody chain.`);
    }

  } catch (err) {
    showSecurityToast("Ingestion Error", err.message);
  } finally {
    setGlobalLoading(false);
  }
}

// Handover Progression Sequence Definitions
const HANDOVER_STAGES = [
  {
    step: 1,
    title: "Stage 1: Evidence Intake & Scene Seizure",
    subtitle: "Exhibit registered in forensic ledger. Ready for handover to Forensic Laboratory.",
    currentActor: "Officer John Vance",
    currentRole: "Evidence Officer",
    nextActor: "Dr. Elena Rostova",
    nextRole: "Forensic Analyst",
    actionName: "Pass Custody to Dr. Elena Rostova",
    allowedRoles: ["EVIDENCE_OFFICER", "SYSTEM_ADMIN"],
    roleRequirementText: "Requires Evidence Officer or System Admin clearance to authorize transfer.",
  },
  {
    step: 2,
    title: "Stage 2: Laboratory Ingestion",
    subtitle: "Exhibit in forensic laboratory custody. Ready for analysis & format export.",
    currentActor: "Dr. Elena Rostova",
    currentRole: "Forensic Analyst",
    nextActor: "Forensic Laboratory (Export Tool)",
    nextRole: "Forensic Analyst",
    actionName: "Execute Laboratory Analysis & Export",
    allowedRoles: ["FORENSIC_ANALYST", "SYSTEM_ADMIN"],
    roleRequirementText: "Requires Forensic Analyst or System Admin clearance to run lab analysis.",
  },
  {
    step: 3,
    title: "Stage 3: Export Processing Completed",
    subtitle: "Lab processing finalized. Ready for handover to Legal Review Division.",
    currentActor: "Dr. Elena Rostova",
    currentRole: "Forensic Analyst",
    nextActor: "Legal Review Division",
    nextRole: "Legal Reviewer",
    actionName: "Submit to Legal Review",
    allowedRoles: ["FORENSIC_ANALYST", "SYSTEM_ADMIN"],
    roleRequirementText: "Requires Forensic Analyst or System Admin clearance to submit for legal review.",
  },
  {
    step: 4,
    title: "Stage 4: Legal Review Finalized",
    subtitle: "Legal chain verified. Ready for long-term sealing in Forensic Archive Vault.",
    currentActor: "Legal Review Division",
    currentRole: "Legal Review",
    nextActor: "Forensic Archive Vault",
    nextRole: "Archive Vault",
    actionName: "Seal into Archive Vault",
    allowedRoles: ["FORENSIC_ANALYST", "SYSTEM_ADMIN"],
    roleRequirementText: "Requires Forensic Analyst or System Admin clearance to seal into vault.",
  },
];

// Update Custody Handover Progression Card
function updateCustodyHandoverCard(data) {
  if (!custodyHandoverCard) return;

  custodyHandoverCard.classList.remove("hidden");
  custodyHandoverCard.classList.remove("awaiting", "completed", "broken-state");

  const steps = data.steps || [];
  const stepCount = steps.length;
  const isIntact = data.final_verdict === "CHAIN_INTACT";
  const firstBreak = data.first_break || (steps.find(s => !s.verified) || null);

  // Case 1: Tamper or Break detected
  if (!isIntact || firstBreak) {
    custodyHandoverCard.classList.add("broken-state");
    handoverTitle.textContent = `Custody Severed at ${firstBreak?.handler_name || 'Handler'} (Step ${firstBreak?.step_order || '?'})`;
    handoverSubtitle.textContent = "Integrity check failed. Digital artifact does not match cryptographic ledger.";
    handoverStatusBadge.className = "handover-status-badge broken";
    handoverStatusBadge.textContent = "Broken — Handover Halted";

    handoverCurrentActor.textContent = firstBreak?.handler_name || "Compromised Handler";
    handoverCurrentRole.textContent = "Broken Transition";
    handoverNextActor.textContent = "Quarantined";
    handoverNextRole.textContent = "Tainted Evidence";

    advanceCustodyBtn.disabled = true;
    advanceCustodyBtnText.textContent = "✕ Custody Transfers Barred";
    handoverHint.textContent = "Forensic protocol prohibits transferring or processing compromised exhibits.";
    if (handoverTamperToggle) handoverTamperToggle.disabled = true;
    return;
  }

  // Case 2: All 5 Handlers Completed (Lifecycle Archive Vault Complete)
  if (stepCount >= 5) {
    custodyHandoverCard.classList.add("completed");
    handoverTitle.textContent = "Chain of Custody Lifecycle Complete";
    handoverSubtitle.textContent = "Exhibit permanently sealed and archived in forensic vault. All 5 handler transitions verified.";
    handoverStatusBadge.className = "handover-status-badge complete";
    handoverStatusBadge.textContent = "Archived & Sealed (5 of 5)";

    handoverCurrentActor.textContent = "Forensic Archive Vault";
    handoverCurrentRole.textContent = "WORM Storage";
    handoverNextActor.textContent = "Court Admissible";
    handoverNextRole.textContent = "Verified Legal Ledger";

    advanceCustodyBtn.disabled = true;
    advanceCustodyBtnText.textContent = "✓ Lifecycle Sealed in Vault";
    handoverHint.textContent = "Cryptographic ledger continuity and Ed25519 signatures permanently immutable.";
    if (handoverTamperToggle) handoverTamperToggle.disabled = true;
    return;
  }

  // Case 3: Step-by-Step Handover Ready (Step 1 to 4)
  custodyHandoverCard.classList.add("awaiting");
  if (handoverTamperToggle) handoverTamperToggle.disabled = false;

  const currentStage = HANDOVER_STAGES[stepCount - 1] || HANDOVER_STAGES[0];

  handoverTitle.textContent = currentStage.title;
  handoverSubtitle.textContent = `${currentStage.subtitle} (Step ${stepCount} of 5 Completed)`;
  handoverStatusBadge.className = "handover-status-badge";
  handoverStatusBadge.textContent = `Awaiting Step ${stepCount + 1} Handover`;

  handoverCurrentActor.textContent = currentStage.currentActor;
  handoverCurrentRole.textContent = currentStage.currentRole;
  handoverNextActor.textContent = currentStage.nextActor;
  handoverNextRole.textContent = currentStage.nextRole;

  // Check Role Clearance for current transition
  const hasClearance = currentStage.allowedRoles.includes(currentActiveRole);

  if (hasClearance) {
    advanceCustodyBtn.disabled = false;
    advanceCustodyBtnText.textContent = currentStage.actionName;
    handoverHint.textContent = `Authorized as ${ROLE_HIERARCHY[currentActiveRole]?.roleName || currentActiveRole}. Click to cryptographically sign handover.`;
  } else {
    advanceCustodyBtn.disabled = true;
    if (currentActiveRole === "AUDITOR") {
      advanceCustodyBtnText.textContent = "🔒 Handover Prohibited (Read-Only)";
      handoverHint.textContent = "Auditors hold read-only compliance oversight and cannot sign custody handovers.";
    } else {
      const requiredRoleName = currentStage.allowedRoles[0] === "EVIDENCE_OFFICER" ? "Evidence Officer" : "Forensic Analyst";
      advanceCustodyBtnText.textContent = `🔒 Requires ${requiredRoleName}`;
      handoverHint.textContent = currentStage.roleRequirementText;
    }
  }
}

// Render Results with 3-Level Progressive Disclosure
function renderVerificationResults(data) {
  currentEvidenceId = data.evidence_id;
  currentVerificationData = data;

  const isIntact = data.final_verdict === "CHAIN_INTACT";
  // Authoritative first_break object provided directly by backend
  const firstBreak = data.first_break || (data.steps ? data.steps.find(s => !s.verified) : null);
  const stepCount = data.steps ? data.steps.length : 0;

  // Level 1: What is happening?
  headerExhibitTitle.textContent = data.evidence_name;
  headerExhibitId.textContent = data.exhibit_id || `EX-${data.evidence_id}`;
  
  if (isIntact) {
    headerStatusTag.className = "status-summary-tag verified";
    headerStatusTag.textContent = stepCount < 5 ? `Intact (${stepCount} of 5)` : "Chain intact";
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
    verdictBreakPoint.textContent = `· ${stepCount} handler${stepCount === 1 ? '' : 's'} verified`;
    verdictExplanation.textContent =
      stepCount < 5
        ? `Evidence exhibit verified at Step ${stepCount}. Previous-event ledger continuous, Ed25519 signatures valid, and WORM storage hashes match.`
        : "All 5 custody handoffs independently recomputed. Artifact storage states match baseline hashes, and all digital signatures are authentic.";
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

  // Update Custody Handover Card
  updateCustodyHandoverCard(data);

  // Level 2 & 3: Timeline Cards with Progressive Disclosure
  renderTimelineCards(data);
}


// Render Conversational Explanation ("Why is this broken / intact?")
function renderExplanation(data) {
  const isIntact = data.final_verdict === "CHAIN_INTACT";
  const firstBreak = data.first_break || (data.steps ? data.steps.find(s => !s.verified) : null);

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
      breakExplanation = `The first verifiable mismatch occurred during the <strong>${esc(firstBreak.handler_name)}</strong> transition (Step ${firstBreak.step_order}). The physical artifact hash stored on disk (<span class="hash-tag">${trunc(firstBreak.actual_hash || 'mismatch', 16)}</span>) differs from the expected input hash (<span class="hash-tag">${trunc(firstBreak.hash_before || 'expected', 16)}</span>).`;
    } else if (firstBreak?.reason === "SIGNATURE_INVALID") {
      breakExplanation = `The Ed25519 digital signature for <strong>${esc(firstBreak.handler_name)}</strong> failed cryptographic validation against the registered public key, indicating the record was either forged or altered in transit.`;
    } else if (firstBreak?.reason === "LEDGER_LINK_BROKEN") {
      breakExplanation = `The cryptographic previous-event hash chain was severed at <strong>${esc(firstBreak.handler_name)}</strong>. The event link did not match the hash of the preceding custody record.`;
    } else if (firstBreak?.reason === "ARTIFACT_CHAIN_DISCONNECTED") {
      breakExplanation = `The physical artifact lineage was disconnected at <strong>${esc(firstBreak.handler_name)}</strong>. The input artifact ID did not chain to the preceding output artifact.`;
    } else {
      breakExplanation = `An unauthorized mutation was localized at <strong>${esc(firstBreak?.handler_name || 'Step')}</strong>.`;
    }

    const downstreamSteps = data.steps ? data.steps.filter(s => s.downstream_of_break || s.step_order > (firstBreak?.step_order ?? 99)) : [];
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
            <span>Signature: <strong style="color:${sigValid ? 'var(--verified-text)' : 'var(--broken-text)'}">${sigValid ? 'Valid Authenticated' : 'Invalid'}</strong></span>
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

    const mainRow = card.querySelector(".handler-card-main");
    mainRow.addEventListener("click", () => {
      card.classList.toggle("expanded");
    });

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
    const res = await apiFetch(`${API_BASE}/api/v1/evidence`);
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
    const verifyRes = await apiFetch(`${API_BASE}/api/v1/verification/${id}`, { method: "GET" });
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
    const res = await apiFetch(`${API_BASE}/api/v1/cases`);
    if (!res.ok) return;
    const cases = await res.json();
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

// Load Immutable System Audit Trail (Requires AUDITOR or SYSTEM_ADMIN)
async function loadAuditTrail() {
  auditModal.classList.remove("hidden");
  auditTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-dim);">Loading records...</td></tr>`;
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/audit?limit=50`);
    if (res.status === 403) {
      auditTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--broken-text);">Access Denied (403 Forbidden): Your active role does not have permission to view system audit logs. Switch to Auditor or System Admin.</td></tr>`;
      return;
    }
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
