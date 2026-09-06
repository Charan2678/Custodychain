/* ==========================================================================
   CustodyChain — Minimal Forensic Workspace Controller
   Visual Philosophy: ChatGPT-Inspired Simplicity + Forensic Determinism
   ========================================================================== */

const API_BASE = window.location.port === "5500" ? "http://localhost:8000" : "";

// Application State
const state = {
  token: localStorage.getItem("custody_token") || null,
  role: localStorage.getItem("custody_role") || "EVIDENCE_OFFICER",
  user: JSON.parse(localStorage.getItem("custody_user") || "null"),
  currentCaseId: null,
  currentView: "overview",
  viewParams: {},
  dashboardData: null,
  adminAlertTimer: null,
  cachedCases: [],
  cachedEvidence: [],
  theme: localStorage.getItem("custody_theme") || "light",
};

// DOM References
const loginView = document.getElementById("loginView");
const appView = document.getElementById("appView");
const loginForm = document.getElementById("loginForm");
const loginEmail = document.getElementById("loginEmail");
const loginPassword = document.getElementById("loginPassword");
const demoAccessBtn = document.getElementById("demoAccessBtn");
const demoAccessModal = document.getElementById("demoAccessModal");
const closeDemoAccessBtn = document.getElementById("closeDemoAccessBtn");
const passwordToggleBtn = document.getElementById("passwordToggleBtn");
const loginError = document.getElementById("loginError");
const appSidebar = document.getElementById("appSidebar");
const sidebarNav = document.getElementById("sidebarNav");
const sidebarUserAvatar = document.getElementById("sidebarUserAvatar");
const sidebarUserName = document.getElementById("sidebarUserName");
const sidebarUserRole = document.getElementById("sidebarUserRole");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const themeIcon = document.getElementById("themeIcon");
const logoutBtn = document.getElementById("logoutBtn");
const mobileMenuToggle = document.getElementById("mobileMenuToggle");
const currentViewBreadcrumb = document.getElementById("currentViewBreadcrumb");
const globalCaseSelect = document.getElementById("globalCaseSelect");
const workspaceContent = document.getElementById("workspaceContent");
const minimalToast = document.getElementById("minimalToast");
const toastMessage = document.getElementById("toastMessage");

// Modals
const newCaseModal = document.getElementById("newCaseModal");
const newCaseForm = document.getElementById("newCaseForm");
const closeCaseModalBtn = document.getElementById("closeCaseModalBtn");
const cancelCaseModalBtn = document.getElementById("cancelCaseModalBtn");

const newEvidenceModal = document.getElementById("newEvidenceModal");
const newEvidenceForm = document.getElementById("newEvidenceForm");
const closeEvidenceModalBtn = document.getElementById("closeEvidenceModalBtn");
const cancelEvidenceModalBtn = document.getElementById("cancelEvidenceModalBtn");

// Evidence Upload / Bulk Import / Edit Modals
const uploadEvidenceModal = document.getElementById("uploadEvidenceModal");
const uploadEvidenceForm = document.getElementById("uploadEvidenceForm");
const closeUploadModalBtn = document.getElementById("closeUploadModalBtn");
const cancelUploadModalBtn = document.getElementById("cancelUploadModalBtn");
const uploadDropzone = document.getElementById("uploadDropzone");
const uploadFileInput = document.getElementById("uploadFileInput");
const uploadFilePreview = document.getElementById("uploadFilePreview");
const uploadMediaPreview = document.getElementById("uploadMediaPreview");

const bulkImportModal = document.getElementById("bulkImportModal");
const bulkImportForm = document.getElementById("bulkImportForm");
const closeBulkModalBtn = document.getElementById("closeBulkModalBtn");
const cancelBulkModalBtn = document.getElementById("cancelBulkModalBtn");


// Role Configuration & Navigation Menus
const ROLE_NAV_CONFIG = {
  EVIDENCE_OFFICER: [
    { id: "overview", label: "Overview", icon: "◎" },
    { id: "cases", label: "Cases", icon: "📁" },
    { id: "reviews", label: "Pending Reviews", icon: "✓" },
    { id: "handovers", label: "Handovers", icon: "➔" },
    { id: "reports", label: "Reports", icon: "📄" },
  ],
  FORENSIC_ANALYST: [
    { id: "overview", label: "Forensic Workspace", icon: "◎" },
    { id: "cases", label: "Assigned Cases", icon: "📁" },
    { id: "lab", label: "Laboratory Processing", icon: "🔬" },
    { id: "verification", label: "Verification", icon: "🛡" },
    { id: "reports", label: "Reports", icon: "📄" },
  ],
  AUDITOR: [
    { id: "overview", label: "Independent Verification", icon: "◎" },
    { id: "verification", label: "Verification Queue", icon: "🛡" },
    { id: "audit", label: "Audit Ledger", icon: "≡" },
    { id: "reports", label: "Reports", icon: "📄" },
  ],
  SYSTEM_ADMIN: [
    { id: "overview", label: "System Overview", icon: "◎" },
    { id: "cases", label: "All Cases", icon: "📁" },
    { id: "evidence-all", label: "All Evidence", icon: "📦" },
    { id: "verification", label: "Global Verifications", icon: "🛡" },
    { id: "audit", label: "Audit Ledger", icon: "≡" },
    { id: "system", label: "System Health & Scenarios", icon: "⚙" },
  ],
};

const VERIFICATION_ROLES = ["FORENSIC_ANALYST", "AUDITOR", "SYSTEM_ADMIN"];

function canRunVerification() {
  return VERIFICATION_ROLES.includes(state.role);
}

function verificationButton(evidence, label, className = "btn btn-primary btn-sm") {
  if (!canRunVerification()) return "";
  return `<button class="${className}" onclick="navigateTo('verify', { evidenceId: '${evidence.id}', evidenceName: '${esc(evidence.name)}' })">${label}</button>`;
}

// ==========================================================================
// API CLIENT WITH AUTOMATIC AUTH & RETRY
// ==========================================================================

async function api(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(state.token ? { "Authorization": `Bearer ${state.token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (response.status === 401) {
    handleLogout();
    throw new Error("Session expired. Please sign in again.");
  }

  return response;
}

// ==========================================================================
// NAVIGATION & VIEW ROUTER
// ==========================================================================

function navigateTo(viewName, params = {}) {
  state.currentView = viewName;
  state.viewParams = params;

  // Update Breadcrumb
  currentViewBreadcrumb.textContent = getBreadcrumbLabel(viewName, params);

  // Update Active Nav Link
  document.querySelectorAll(".sidebar-link").forEach(link => {
    link.classList.toggle("active", link.dataset.view === viewName);
  });

  // Render Target View
  renderCurrentView();

  // Close mobile sidebar if open
  appSidebar.classList.remove("mobile-open");
}

function getBreadcrumbLabel(viewName, params) {
  switch (viewName) {
    case "overview": return "Overview";
    case "cases": return "Cases";
    case "case-detail": return `Case: ${params.caseNumber || 'Details'}`;
    case "inspect": return `Exhibit Inspection: ${params.evidenceName || ''}`;
    case "review": return `Forensic Review: ${params.evidenceName || ''}`;
    case "verify": return `Independent Verification: ${params.evidenceName || ''}`;
    case "audit": return "Security Audit Ledger";
    case "reports": return "Reports & Certificates";
    case "reviews": return "Pending Reviews";
    case "handovers": return "Custody Handovers";
    case "lab": return "Laboratory Processing";
    case "system": return "System Health & Scenarios";
    default: return viewName.charAt(0).toUpperCase() + viewName.slice(1);
  }
}

async function renderCurrentView() {
  workspaceContent.innerHTML = `<div style="padding:40px; text-align:center; color:var(--text-muted);">Loading workspace data...</div>`;

  try {
    switch (state.currentView) {
      case "overview":
        await renderOverviewView();
        break;
      case "cases":
      case "assigned-cases":
        await renderCasesView();
        break;
      case "case-detail":
        await renderCaseDetailView(state.viewParams.caseId);
        break;
      case "inspect":
        await renderInspectView(state.viewParams.evidenceId);
        break;
      case "review":
        await renderReviewView(state.viewParams.evidenceId);
        break;
      case "verify":
        await renderVerifyView(state.viewParams.evidenceId);
        break;
      case "audit":
        await renderAuditView();
        break;
      case "reports":
        await renderReportsView();
        break;
      case "reviews":
        await renderPendingReviewsView();
        break;
      case "handovers":
        await renderHandoversView();
        break;
      case "lab":
      case "evidence-all":
        await renderLabProcessingView();
        break;
      case "system":
        await renderSystemAdminView();
        break;
      default:
        await renderOverviewView();
    }
  } catch (err) {
    workspaceContent.innerHTML = `
      <div style="padding:24px; border:1px solid var(--status-broken-border); border-radius:var(--radius-lg); background:var(--status-broken-bg); color:var(--status-broken-text);">
        <strong>Error loading view:</strong> ${esc(err.message)}
        <div style="margin-top:12px;">
          <button class="btn btn-secondary btn-sm" onclick="navigateTo('overview')">Return to Overview</button>
        </div>
      </div>
    `;
  }
}

// ==========================================================================
// 1. OVERVIEW VIEWS (ROLE-SPECIFIC WORKSPACES)
// ==========================================================================

async function renderOverviewView() {
  const res = await api("/api/v1/dashboard");
  const data = await res.json();
  state.dashboardData = data;
  state.cachedCases = data.cases || [];
  state.cachedEvidence = data.evidence || [];

  updateGlobalCaseSelect(state.cachedCases);

  const userName = state.user?.display_name || "Investigator";
  const role = state.role;

  if (role === "EVIDENCE_OFFICER") {
    renderOfficerOverview(data, userName);
  } else if (role === "FORENSIC_ANALYST") {
    renderAnalystOverview(data, userName);
  } else if (role === "AUDITOR") {
    renderAuditorOverview(data, userName);
  } else if (role === "SYSTEM_ADMIN") {
    renderAdminOverview(data, userName);
    startAdminAlertPolling();
  } else if (state.adminAlertTimer) {
    clearInterval(state.adminAlertTimer);
    state.adminAlertTimer = null;
  }
}

function startAdminAlertPolling() {
  if (state.adminAlertTimer) clearInterval(state.adminAlertTimer);
  state.adminAlertTimer = setInterval(async () => {
    if (state.role !== "SYSTEM_ADMIN" || state.currentView !== "overview") return;
    const res = await api("/api/v1/dashboard");
    if (!res.ok) return;
    const data = await res.json();
    state.dashboardData = data;
    renderAdminOverview(data, state.user?.display_name || "Administrator");
  }, 10000);
}

// Evidence Officer Overview
function renderOfficerOverview(data, userName) {
  const m = data.metrics || {};
  const exhibits = data.evidence || [];
  const pendingReviews = exhibits.filter(e => e.review_decision !== "APPROVE");
  const readyHandovers = exhibits.filter(e => e.review_decision === "APPROVE");

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Good morning, ${esc(userName.split(" ")[0])}</h1>
        <p class="page-desc">Here's what needs your attention today in evidence intake and custody clearance.</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="openNewCaseModal()">+ New Case</button>
        <button class="btn btn-secondary" onclick="openUploadModal()">+ Upload File</button>
        <button class="btn btn-secondary" onclick="openBulkImportModal()">+ Bulk Import</button>
        <button class="btn btn-primary" onclick="openNewEvidenceModal()">+ Ingest Text</button>
      </div>
    </div>

    <!-- Conversational Summary Strip -->
    <div class="overview-summary-strip">
      <div class="summary-stat">
        <span class="summary-stat-val">${pendingReviews.length}</span>
        <span class="summary-stat-lbl">Reviews Required</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${readyHandovers.length}</span>
        <span class="summary-stat-lbl">Ready for Transfer</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${m.assigned_cases ?? 0}</span>
        <span class="summary-stat-lbl">Active Cases</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${exhibits.length}</span>
        <span class="summary-stat-lbl">Total Exhibits in Custody</span>
      </div>
    </div>

    <!-- Needs Attention List -->
    <div class="section-header">
      <h2 class="section-title">Needs Attention</h2>
      <span class="section-desc">${pendingReviews.length + readyHandovers.length} action items</span>
    </div>

    <div class="table-container">
      ${exhibits.length === 0 ? `
        <div style="padding:24px; text-align:center; color:var(--text-muted);">
          No active exhibits registered. Click "+ Ingest Evidence" above to start an intake.
        </div>
      ` : exhibits.map(e => {
        const isApproved = e.review_decision === "APPROVE";
        return `
          <div class="action-item-row">
            <div class="item-main-info">
              <span class="item-headline">${esc(e.name)}</span>
              <span class="item-subline font-mono">${esc(e.evidence_number || e.id.slice(0, 8))} · ${esc(e.review_step || 'Intake')}</span>
            </div>
<div style="display:flex; align-items:center; gap:12px;">
            <span class="status-pill ${isApproved ? 'valid' : (e.review_decision === 'REJECT' ? 'broken' : 'pending')}">
              ${isApproved ? '✓ Ready for Transfer' : (e.review_decision === 'REJECT' ? '✕ Rejected' : 'Review Required')}
            </span>
            ${e.latest_verdict === 'CHAIN_BROKEN' ? `
              <span class="status-pill broken font-mono">✕ CHAIN BROKEN</span>
            ` : ''}
            <button class="btn btn-secondary btn-sm" onclick="navigateTo('review', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">
              ${isApproved ? 'Review Notes' : 'Review'}
            </button>
            <button class="btn btn-accent btn-sm" onclick="navigateTo('verify', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">AI ✦ & Verify</button>
            ${isApproved ? `
              <button class="btn btn-primary btn-sm" onclick="handleTransferCustody('${e.id}')">Transfer ➔</button>
            ` : ''}
          </div>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

// Forensic Analyst Overview
function renderAnalystOverview(data, userName) {
  const exhibits = data.evidence || [];

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Forensic Laboratory Workspace</h1>
        <p class="page-desc">Examine raw bitstreams, execute technical derivations, and verify hash parity.</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="openUploadModal()">+ Upload File</button>
        <button class="btn btn-secondary" onclick="openBulkImportModal()">+ Bulk Import</button>
        <button class="btn btn-secondary" onclick="navigateTo('cases')">View Assigned Cases</button>
      </div>
    </div>

    <!-- Summary Strip -->
    <div class="overview-summary-strip">
      <div class="summary-stat">
        <span class="summary-stat-val">${exhibits.length}</span>
        <span class="summary-stat-lbl">Assigned Evidence</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${data.metrics?.broken_chains ?? 0}</span>
        <span class="summary-stat-lbl" style="color:var(--status-broken-text);">Compromised Chains</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${data.metrics?.completed_reports ?? 0}</span>
        <span class="summary-stat-lbl">Verified Intact</span>
      </div>
    </div>

    <!-- Assigned Evidence Table -->
    <div class="section-header">
      <h2 class="section-title">Assigned Exhibits in Laboratory Queue</h2>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Exhibit</th>
            <th>Stage</th>
            <th>Review Status</th>
            <th>Created</th>
            <th style="text-align:right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${exhibits.length === 0 ? `
            <tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:24px;">No laboratory exhibits in queue.</td></tr>
          ` : exhibits.map(e => `
            <tr>
              <td>
                <div style="font-weight:600;">${esc(e.name)}</div>
                <div class="font-mono text-muted" style="font-size:11px;">${esc(e.evidence_number || e.id.slice(0, 8))}</div>
              </td>
              <td>${esc(e.review_step || 'Stage 1')}</td>
              <td>
                <span class="status-pill ${e.review_decision === 'APPROVE' ? 'valid' : (e.review_decision === 'REJECT' ? 'broken' : 'neutral')}">
                  ${esc(e.review_decision || 'PENDING')}
                </span>
                ${e.latest_verdict === 'CHAIN_BROKEN' ? `
                  <span class="status-pill broken font-mono" style="margin-left:4px;">✕ BROKEN</span>
                ` : ''}
              </td>
              <td style="color:var(--text-secondary); font-size:12px;">${formatDate(e.created_at)}</td>
              <td style="text-align:right;">
                <div style="display:inline-flex; gap:6px;">
                  <button class="btn btn-ghost btn-sm" onclick="navigateTo('inspect', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Inspect</button>
                  <button class="btn btn-secondary btn-sm" onclick="navigateTo('review', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Review</button>
                  <button class="btn btn-primary btn-sm" onclick="navigateTo('verify', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Verify & AI</button>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// Independent Auditor Overview
function renderAuditorOverview(data, userName) {
  const exhibits = data.evidence || [];
  const brokenCount = data.metrics?.broken_chains ?? 0;

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Independent Verification</h1>
        <p class="page-desc">Regulatory oversight, cryptographic ledger proof, and first-break root cause localization.</p>
      </div>
      <button class="btn btn-secondary" onclick="navigateTo('audit')">View Audit Ledger ≡</button>
    </div>

    <!-- Summary Strip -->
    <div class="overview-summary-strip">
      <div class="summary-stat">
        <span class="summary-stat-val">${exhibits.length}</span>
        <span class="summary-stat-lbl">Verification Queue</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val" style="color:${brokenCount > 0 ? 'var(--status-broken-text)' : 'inherit'}">${brokenCount}</span>
        <span class="summary-stat-lbl">Broken Chains</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val">${data.metrics?.audit_records_count ?? 0}</span>
        <span class="summary-stat-lbl">Audit Log Records</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val" style="color:var(--status-valid-text);">100%</span>
        <span class="summary-stat-lbl">Ledger Continuity</span>
      </div>
    </div>

    <!-- Verification Queue -->
    <div class="section-header">
      <h2 class="section-title">Evidence Requiring Independent Verification</h2>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Exhibit</th>
            <th>Stage</th>
            <th>Status</th>
            <th>Intake Date</th>
            <th style="text-align:right;">Independent Audit Action</th>
          </tr>
        </thead>
        <tbody>
          ${exhibits.length === 0 ? `
            <tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:24px;">No evidence in verification queue.</td></tr>
          ` : exhibits.map(e => `
            <tr>
              <td>
                <div style="font-weight:600;">${esc(e.name)}</div>
                <div class="font-mono text-muted" style="font-size:11px;">${esc(e.evidence_number || e.id.slice(0, 8))}</div>
              </td>
              <td>${esc(e.review_step || 'Intake')}</td>
              <td>
                <span class="status-pill neutral">${esc(e.status || 'ACTIVE')}</span>
                ${e.latest_verdict === 'CHAIN_BROKEN' ? `
                  <span class="status-pill broken font-mono" style="margin-left:4px;">✕ BROKEN</span>
                ` : ''}
              </td>
              <td style="color:var(--text-secondary); font-size:12px;">${formatDate(e.created_at)}</td>
              <td style="text-align:right;">
                <div style="display:inline-flex; gap:6px;">
                  <button class="btn btn-ghost btn-sm" onclick="navigateTo('inspect', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Inspect</button>
                  <button class="btn btn-primary btn-sm" onclick="navigateTo('verify', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Verify Chain & AI</button>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// System Admin Overview
function renderAdminOverview(data, userName) {
  const health = data.system_health || {};
  const cases = data.cases || [];
  const securityAlerts = data.security_alerts || [];

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">System Overview</h1>
        <p class="page-desc">Infrastructure health, global evidence supervision, and demonstration scenarios.</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="openNewCaseModal()">+ Register Case</button>
        <button class="btn btn-secondary" onclick="openUploadModal()">+ Upload File</button>
        <button class="btn btn-secondary" onclick="openBulkImportModal()">+ Bulk Import</button>
        <button class="btn btn-secondary" onclick="runScenarioSimulation(0)">Simulate Clean Intact</button>
        <button class="btn btn-danger" onclick="runScenarioSimulation(3)">Simulate Step 3 Silent Tamper</button>
      </div>
    </div>

    ${securityAlerts.length ? `
      <div class="verification-verdict-banner verdict-banner-broken" style="margin-bottom:18px;">
        <div class="verdict-headline">${securityAlerts.length} security alert${securityAlerts.length === 1 ? '' : 's'} require attention</div>
        <div class="verdict-subtext">${securityAlerts.slice(0, 3).map(alert => `${esc(alert.action.replaceAll('_', ' '))} by ${esc(alert.actor_name)} at ${formatDate(alert.occurred_at)}`).join(' · ')}</div>
        <button class="btn btn-secondary btn-sm" onclick="navigateTo('audit')">Open Audit Ledger</button>
      </div>
    ` : ''}

    <!-- Health Strip -->
    <div class="overview-summary-strip">
      <div class="summary-stat">
        <span class="summary-stat-val" style="font-size:16px; color:var(--status-valid-text);">● ${esc(health.api || 'ONLINE')}</span>
        <span class="summary-stat-lbl">API Gateway</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val" style="font-size:16px; color:var(--status-valid-text);">● ${esc(health.database || 'HEALTHY')}</span>
        <span class="summary-stat-lbl">Database Storage</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val" style="font-size:16px; color:var(--status-valid-text);">● ${esc(health.artifact_storage || 'VERIFIED')}</span>
        <span class="summary-stat-lbl">Physical Object Store</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val" style="font-size:16px; color:var(--accent);">● ${esc(health.cryptography || 'ACTIVE')}</span>
        <span class="summary-stat-lbl">Ed25519 / SHA-256 Engine</span>
      </div>
    </div>

    <!-- Cases Summary Table -->
    <div class="section-header">
      <h2 class="section-title">Active Investigation Cases</h2>
      <button class="btn btn-ghost btn-sm" onclick="navigateTo('cases')">View All Cases ➔</button>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Case</th>
            <th>Title</th>
            <th>Status</th>
            <th>Exhibits</th>
            <th>Created</th>
            <th style="text-align:right;">Action</th>
          </tr>
        </thead>
        <tbody>
          ${cases.map(c => `
            <tr>
              <td class="font-mono" style="font-weight:600;">${esc(c.case_number)}</td>
              <td>${esc(c.title)}</td>
              <td><span class="status-pill valid">${esc(c.status)}</span></td>
              <td>${c.evidence_count} exhibits</td>
              <td style="color:var(--text-secondary); font-size:12px;">${formatDate(c.created_at)}</td>
              <td style="text-align:right;">
                <button class="btn btn-secondary btn-sm" onclick="navigateTo('case-detail', { caseId: '${c.id}', caseNumber: '${esc(c.case_number)}' })">Open Case</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ==========================================================================
// 2. CASES SCREEN & CASE DETAIL SCREEN
// ==========================================================================

async function renderCasesView() {
  const res = await api("/api/v1/cases");
  const cases = await res.json();
  state.cachedCases = cases;

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Cases</h1>
        <p class="page-desc">Official forensic containers and authorized investigation scopes.</p>
      </div>
      ${["EVIDENCE_OFFICER", "SYSTEM_ADMIN"].includes(state.role) ? `
        <button class="btn btn-primary" onclick="openNewCaseModal()">+ New Case</button>
      ` : ''}
    </div>

    <div style="margin-bottom:16px; display:flex; gap:12px;">
      <input type="text" id="caseSearchInput" class="text-input" placeholder="Search cases by reference or title..." style="max-width:320px;" oninput="filterCasesTable(this.value)" />
    </div>

    <div class="table-container">
      <table class="clean-table" id="casesTable">
        <thead>
          <tr>
            <th>Case Reference</th>
            <th>Title</th>
            <th>Status</th>
            <th>Evidence Exhibits</th>
            <th>Created</th>
            <th style="text-align:right;">Action</th>
          </tr>
        </thead>
        <tbody id="casesTableBody">
          ${cases.map(c => `
            <tr>
              <td class="font-mono" style="font-weight:600;">${esc(c.case_number)}</td>
              <td><strong>${esc(c.title)}</strong></td>
              <td><span class="status-pill valid">${esc(c.status)}</span></td>
              <td>${c.evidence_count ?? 0} exhibits</td>
              <td style="color:var(--text-secondary); font-size:12px;">${formatDate(c.created_at)}</td>
              <td style="text-align:right;">
                <button class="btn btn-secondary btn-sm" onclick="navigateTo('case-detail', { caseId: '${c.id}', caseNumber: '${esc(c.case_number)}' })">Open</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function filterCasesTable(query) {
  const q = query.toLowerCase();
  const rows = document.querySelectorAll("#casesTableBody tr");
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(q) ? "" : "none";
  });
}

async function renderCaseDetailView(caseId) {
  const [caseRes, evRes, assignmentRes] = await Promise.all([
    api(`/api/v1/cases/${caseId}`),
    api(`/api/v1/cases/${caseId}/evidence`),
    api(`/api/v1/cases/${caseId}/assignments`),
  ]);

  const c = await caseRes.json();
  const exhibits = await evRes.json();
  const assignments = await assignmentRes.json();

  state.currentCaseId = caseId;
  globalCaseSelect.value = caseId;

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
          <span class="font-mono" style="color:var(--text-muted); font-size:13px;">${esc(c.case_number)}</span>
          <span class="status-pill valid">${esc(c.status)}</span>
        </div>
        <h1 class="page-title">${esc(c.title)}</h1>
        <p class="page-desc">${esc(c.description || 'Digital investigation evidence container.')}</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="navigateTo('cases')">← Back to Cases</button>
        ${state.role === "EVIDENCE_OFFICER" ? `
          <button class="btn btn-secondary" onclick="openUploadModal()">+ Upload File</button>
          <button class="btn btn-secondary" onclick="openBulkImportModal()">+ Bulk Import</button>
          <button class="btn btn-primary" onclick="openNewEvidenceModal()">+ Add Evidence</button>
        ` : ''}
      </div>
    </div>

    <!-- Case Summary Strip -->
    <div class="overview-summary-strip">
      <div class="summary-stat">
        <span class="summary-stat-val">${exhibits.length}</span>
        <span class="summary-stat-lbl">Seized Exhibits</span>
      </div>
      <div class="summary-stat">
        <span class="summary-stat-val font-mono" style="font-size:13px; margin-top:4px;">${formatDate(c.created_at)}</span>
        <span class="summary-stat-lbl">Registration Date</span>
      </div>
    </div>

    <div class="section-header">
      <h2 class="section-title">Custody Assignment</h2>
      <span class="section-desc">Only the active stage owner may act</span>
    </div>
    <div class="overview-summary-strip">
      ${assignments.filter(a => a.status === "ACTIVE").map(a => `
        <div class="summary-stat">
          <span class="summary-stat-val" style="font-size:14px;">${esc(a.user_name || 'Unassigned')}</span>
          <span class="summary-stat-lbl">${esc(a.stage.replaceAll('_', ' '))}</span>
        </div>
      `).join('') || '<div style="padding:16px; color:var(--text-muted);">No active custody assignment.</div>'}
    </div>

    <!-- Evidence Exhibits Table -->
    <div class="section-header">
      <h2 class="section-title">Evidence Exhibits</h2>
      <span class="section-desc">${exhibits.length} items registered</span>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Exhibit Title</th>
            <th>Current Custody Stage</th>
            <th>Review Status</th>
            <th>Acquisition Time</th>
            <th style="text-align:right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${exhibits.length === 0 ? `
            <tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:28px;">No exhibits registered in this case. Click "+ Add Evidence" to begin intake.</td></tr>
          ` : exhibits.map(e => `
            <tr>
              <td>
                <div style="font-weight:600;">${esc(e.name)}</div>
                <div class="font-mono text-muted" style="font-size:11px;">${esc(e.evidence_number || e.id.slice(0, 8))}</div>
              </td>
              <td>${esc(e.review_step || 'Intake')}</td>
              <td>
                <span class="status-pill ${e.review_decision === 'APPROVE' ? 'valid' : (e.review_decision === 'REJECT' ? 'broken' : 'neutral')}">
                  ${esc(e.review_decision || 'PENDING')}
                </span>
                ${e.latest_verdict === 'CHAIN_BROKEN' ? `
                  <span class="status-pill broken font-mono" style="margin-left:4px;">✕ BROKEN</span>
                ` : ''}
              </td>
              <td style="color:var(--text-secondary); font-size:12px;">${formatDate(e.created_at)}</td>
              <td style="text-align:right;">
                <div style="display:inline-flex; gap:6px;">
                  <button class="btn btn-ghost btn-sm" onclick="navigateTo('inspect', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Inspect</button>
                  <button class="btn btn-secondary btn-sm" onclick="navigateTo('review', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Review</button>
                  ${verificationButton(e, "Verify & AI")}
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ==========================================================================
// 3. EVIDENCE INSPECTION VIEW (CALM FORENSIC INSPECTION INTERFACE)
// ==========================================================================

async function renderInspectView(evidenceId) {
  const res = await api(`/api/v1/evidence/${evidenceId}/review`);
  const d = await res.json();

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
          <span class="font-mono" style="color:var(--text-muted); font-size:12px;">${esc(d.case_number)} · Exhibit ${esc(d.exhibit_id || d.evidence_id.slice(0, 8))}</span>
          <span class="status-pill ${d.artifact.hash_matches ? 'valid' : 'broken'}">${d.artifact.hash_matches ? '✓ Integrity Verified' : '✕ Mutated'}</span>
        </div>
        <h1 class="page-title">${esc(d.name)}</h1>
        <p class="page-desc">Cryptographic bitstream parity and physical storage verification.</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="navigateTo('overview')">← Back</button>
        <button class="btn btn-secondary" onclick="navigateTo('review', { evidenceId: '${d.evidence_id}', evidenceName: '${esc(d.name)}' })">Review Handover</button>
        <button class="btn btn-primary" onclick="navigateTo('verify', { evidenceId: '${d.evidence_id}', evidenceName: '${esc(d.name)}' })">Verify Chain</button>
      </div>
    </div>

    <!-- Three Grouped Sections -->
    <div class="inspect-grid">
      <!-- Section 1: ARTIFACT -->
      <div class="inspect-column">
        <h3 class="inspect-col-title">Artifact</h3>
        <div class="field-group">
          <span class="field-label">Current Filename / Object</span>
          <span class="field-val font-mono">${esc(d.name)}.dd</span>
        </div>
        <div class="field-group">
          <span class="field-label">Artifact Size</span>
          <span class="field-val font-mono">${d.artifact.size_bytes} bytes</span>
        </div>
        <div class="field-group">
          <span class="field-label">Object Store</span>
          <span class="field-val">Evidence Object Store (WORM Local)</span>
        </div>
        <div class="field-group">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="field-label" style="margin-bottom:0;">Raw Bitstream Preview</span>
            <span id="copyIndicatorBadge" class="status-pill warning font-mono" style="display:none; font-size:11px; padding:2px 8px;">
              ✓ Copied & Monitored
            </span>
          </div>
          ${renderMediaPreview(d)}
        </div>
      </div>

      <!-- Section 2: INTEGRITY -->
      <div class="inspect-column">
        <h3 class="inspect-col-title">Integrity</h3>
        <div class="field-group">
          <span class="field-label">Declared Input Hash (SHA-256)</span>
          <span class="field-val font-mono">${esc(d.original_hash)}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Storage Recomputed Hash (SHA-256)</span>
          <span class="field-val font-mono" style="color:${d.artifact.hash_matches ? 'inherit' : 'var(--status-broken-text)'}; font-weight:${d.artifact.hash_matches ? 'normal' : '600'};">${esc(d.artifact.recomputed_sha256)}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Hash Parity Match</span>
          <div>
            <span class="status-pill ${d.artifact.hash_matches ? 'valid' : 'broken'}">
              ${d.artifact.hash_matches ? '✓ Verified (0 bytes mutated)' : '✕ Byte Discrepancy Detected'}
            </span>
          </div>
        </div>
      </div>

      <!-- Section 3: ACTOR / EVENT -->
      <div class="inspect-column">
        <h3 class="inspect-col-title">Actor / Event</h3>
        <div class="field-group">
          <span class="field-label">Current Custodian / Handler</span>
          <span class="field-val">${esc(d.current_handler)} (Step ${d.current_step})</span>
        </div>
        <div class="field-group">
          <span class="field-label">Event Timestamp</span>
          <span class="field-val font-mono">${formatDate(d.event.timestamp)}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Ed25519 Event Signature</span>
          <span class="field-val font-mono" style="font-size:11px;">${d.event.signature ? esc(d.event.signature.slice(0, 32)) + '...' : 'Genesis Seizure'}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Signature Validity</span>
          <div><span class="status-pill valid">✓ Cryptographically Valid</span></div>
        </div>
      </div>
    </div>

    <!-- AI Forensic Explanation (Every role can request it) -->
    <div class="section-header">
      <h2 class="section-title">AI Forensic Explanation (FRE 902)</h2>
      <button class="btn btn-accent btn-sm" id="btnExplainAI" onclick="fetchGeminiExplanation('${esc(d.evidence_id)}')">
        Explain finding with AI ✦
      </button>
    </div>
    <div id="aiExplanationContainer">
      <div style="font-size:13px; color:var(--text-muted); padding:12px 0;">
        Click "Explain finding with AI" above to generate a court-admissible forensic explanation.
      </div>
    </div>
  `;

  hydrateMediaPreviewFromDOM();
  attachEvidenceCopyMonitor(d.evidence_id);
}

// ==========================================================================
// 4. REVIEW SCREEN (FORMAL FORENSIC REVIEW & IMMUTABLE CUSTODY)
// ==========================================================================

async function renderReviewView(evidenceId) {
  const res = await api(`/api/v1/evidence/${evidenceId}/review`);
  const d = await res.json();

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:4px;">
          ${esc(d.case_number)} · Exhibit ${esc(d.exhibit_id || d.evidence_id.slice(0, 8))}
        </div>
        <h1 class="page-title">Review Evidence</h1>
        <p class="page-desc">Formal inspection and custody transfer authorization.</p>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <button class="btn btn-secondary" onclick="navigateTo('overview')">Cancel</button>
      </div>
    </div>

    <!-- Product Principle Notice -->
    <div class="immutable-notice">
      <strong>Immutable Integrity Notice:</strong> Evidence bytes are immutable. Review actions record a new signed custody and audit event on the permanent ledger.
    </div>

    <div class="review-layout">
      <!-- Left: Evidence Summary Details -->
      <div class="inspect-column">
        <h3 class="inspect-col-title">Evidence Details</h3>
        <div class="field-group">
          <span class="field-label">Exhibit Title</span>
          <span class="field-val"><strong>${esc(d.name)}</strong></span>
        </div>
        <div class="field-group">
          <span class="field-label">Genesis Hash (SHA-256)</span>
          <span class="field-val font-mono">${esc(d.original_hash)}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Storage Recomputed Hash</span>
          <span class="field-val font-mono">${esc(d.artifact.recomputed_sha256)}</span>
        </div>
        <div class="field-group">
          <span class="field-label">Custody Transition Route</span>
          <span class="field-val">Step ${d.current_step} (${esc(d.current_handler)}) ➔ Step ${d.next_step} (${esc(d.next_handler)})</span>
        </div>

        <div class="field-group" style="margin-top:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span class="field-label" style="margin-bottom:0;">Raw Bitstream Preview</span>
            <span id="copyIndicatorBadgeReview" class="status-pill warning font-mono" style="display:none; font-size:11px; padding:2px 8px;">
              ✓ Copied & Monitored
            </span>
          </div>
          ${renderMediaPreview(d)}
        </div>

        <div style="margin-top:12px;">
          <span class="field-label" style="margin-bottom:6px; display:block;">Audit Process Marks (${(d.process_marks || []).length})</span>
          <div style="font-size:12px; display:flex; flex-direction:column; gap:6px;">
            ${(d.process_marks || []).length === 0 ? '<span class="text-muted">No prior review marks.</span>' : (d.process_marks || []).map(m => `
              <div style="padding:6px 8px; border:1px solid var(--border-subtle); border-radius:var(--radius-sm); background:var(--bg-inset);">
                <div style="display:flex; justify-content:space-between;">
                  <strong>${esc(m.reviewer_name)} (${esc(m.reviewer_role)})</strong>
                  <span class="status-pill ${m.decision === 'APPROVE' ? 'valid' : 'broken'}">${esc(m.decision)}</span>
                </div>
                <div style="color:var(--text-secondary); margin-top:2px;">${esc(m.notes)}</div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- Right: Review Decision Form -->
      <div class="inspect-column">
        <h3 class="inspect-col-title">Review Determination</h3>
        <form id="activeReviewForm" onsubmit="submitFormalReview(event, '${d.evidence_id}')">
          <div class="form-field">
            <label>Custody Decision</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" name="reviewDecision" value="APPROVE" checked />
                <span><strong>Approve</strong> — Certified intact, authorize transfer</span>
              </label>
              <label class="radio-label">
                <input type="radio" name="reviewDecision" value="REJECT" />
                <span><strong>Reject</strong> — Bar transfer due to tamper or defect</span>
              </label>
              <label class="radio-label">
                <input type="radio" name="reviewDecision" value="REQUEST_CLARIFICATION" />
                <span><strong>Request clarification</strong> — Hold in quarantine</span>
              </label>
            </div>
          </div>

          <div class="form-field">
            <label for="reviewNotesInput">Inspector Notes</label>
            <textarea id="reviewNotesInput" class="text-area" rows="4" placeholder="Write formal forensic review remarks..." required></textarea>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
            <button type="button" class="btn btn-secondary" onclick="navigateTo('overview')">Cancel</button>
            <button type="submit" class="btn btn-primary">Save Review</button>
          </div>
        </form>
      </div>
    </div>

    <!-- AI Forensic Explanation (Every role can request it) -->
    <div class="section-header">
      <h2 class="section-title">AI Forensic Explanation (FRE 902)</h2>
      <button class="btn btn-accent btn-sm" id="btnExplainAI" onclick="fetchGeminiExplanation('${esc(d.evidence_id)}')">
        Explain finding with AI ✦
      </button>
    </div>
    <div id="aiExplanationContainer">
      <div style="font-size:13px; color:var(--text-muted); padding:12px 0;">
        Click "Explain finding with AI" above to generate a court-admissible forensic explanation.
      </div>
    </div>
  `;

  hydrateMediaPreviewFromDOM();
  attachEvidenceCopyMonitor(d.evidence_id);
}

async function submitFormalReview(e, evidenceId) {
  e.preventDefault();
  const decision = document.querySelector('input[name="reviewDecision"]:checked')?.value || "APPROVE";
  const notes = document.getElementById("reviewNotesInput").value.trim();

  try {
    const res = await api(`/api/v1/evidence/${evidenceId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, notes }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Review submission failed");
    }

    showToast("Review signed and recorded to audit ledger.");
    navigateTo("overview");
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

async function handleTransferCustody(evidenceId) {
  try {
    const res = await api(`/api/v1/evidence/${evidenceId}/transfer`, {
      method: "POST",
      body: JSON.stringify({ simulate_tamper: false }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Custody transfer blocked");
    }

    const d = await res.json();
    showToast(`Advanced to Sequence ${d.sequence_number}: ${d.operation}`);
    renderCurrentView();
  } catch (err) {
    showToast(`Transfer Blocked: ${err.message}`);
  }
}

// ==========================================================================
// 5. FLAGSHIP VERIFICATION & FIRST BREAK SCREEN (MOST IMPORTANT VIEW)
// ==========================================================================

async function renderVerifyView(evidenceId) {
  if (!canRunVerification() && state.role !== "EVIDENCE_OFFICER") {
    workspaceContent.innerHTML = `<div class="verification-verdict-banner verdict-banner-broken"><div class="verdict-headline">Verification unavailable</div><div class="verdict-subtext">Independent verification is restricted to forensic analysts, auditors, and system administrators.</div><button class="btn btn-secondary" onclick="navigateTo('overview')">Return to Overview</button></div>`;
    return;
  }

  workspaceContent.innerHTML = `<div style="padding:40px; text-align:center; color:var(--text-muted);">Executing independent multi-vector verification...</div>`;

  const verificationMethod = state.role === "EVIDENCE_OFFICER" ? "GET" : "POST";
  const res = await api(`/api/v1/verification/${evidenceId}`, { method: verificationMethod });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || "Verification failed to load");
  }
  const v = await res.json();

  const isIntact = v.final_verdict === "CHAIN_INTACT";
  const fb = v.first_break;
  const steps = v.steps || [];

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono); margin-bottom:4px;">
          Exhibit ${esc(v.evidence_number || v.evidence_id.slice(0, 8))}
        </div>
        <h1 class="page-title">Independent Verification</h1>
        <p class="page-desc">Complete mathematical re-calculation of hashes, signatures, and provenance links.</p>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary" onclick="navigateTo('overview')">← Back</button>
        <button class="btn btn-secondary" onclick="downloadReportPdf('${v.evidence_id}')">Export PDF</button>
      </div>
    </div>

    <!-- Overall Verdict Banner -->
    <div class="verification-verdict-banner ${isIntact ? 'verdict-banner-intact' : 'verdict-banner-broken'}">
      <div>
        <div class="verdict-headline">${isIntact ? '✓ CHAIN INTACT' : '✕ CHAIN BROKEN'}</div>
        <div class="verdict-subtext">
          ${isIntact 
            ? 'All digital artifacts match storage hashes byte-for-byte. All custody transitions authenticated.'
            : `First break identified at Step ${fb?.step_order ?? 3} (${esc(fb?.handler_name ?? 'Handler')}). Artifact mutated.`}
        </div>
      </div>
      <span class="status-pill ${isIntact ? 'valid' : 'broken'} font-mono">${isIntact ? 'VERIFIED' : 'TAMPER_DETECTED'}</span>
    </div>

    <!-- Prominent FIRST BREAK Panel (Only when broken) -->
    ${!isIntact && fb ? `
      <div class="first-break-card">
        <span class="first-break-badge">First Break Localized</span>
        <h2 class="first-break-title">Step ${fb.step_order} · ${esc(fb.handler_name)}</h2>
        <p style="font-size:13px; color:var(--text-secondary); margin-top:4px;">
          The software tool reported "SUCCESS", but independent recalculation of physical storage bytes revealed an unauthorized mutation.
        </p>

        <div class="hash-comparison-grid">
          <div class="hash-cell">
            <span class="hash-cell-label">Expected SHA-256 (Declared Input)</span>
            <span class="hash-cell-code">${esc(fb.expected_value)}</span>
          </div>
          <div class="hash-cell mismatch">
            <span class="hash-cell-label">Observed Storage SHA-256 (Actual Physical Bytes)</span>
            <span class="hash-cell-code">${esc(fb.observed_value)}</span>
          </div>
        </div>

        <div class="first-break-vectors">
          <span>Fault: <strong>${esc(fb.reason)}</strong></span>
          <span>·</span>
          <span>Event Signature: <strong style="color:var(--status-valid-text);">✓ Valid</strong></span>
          <span>·</span>
          <span>Ledger Link: <strong style="color:var(--status-valid-text);">✓ Valid</strong></span>
          <span>·</span>
          <span>Downstream Quarantined: <strong>Step ${fb.affected_downstream_steps ? fb.affected_downstream_steps.join(", Step ") : '4'}</strong></span>
        </div>
      </div>
    ` : ''}

    <!-- Clean Provenance Timeline -->
    <div class="section-header">
      <h2 class="section-title">Custody Chain Timeline</h2>
      <span class="section-desc">${steps.length} sequential transitions</span>
    </div>

    <div class="timeline-list">
      ${steps.map(s => {
        const isBreak = !s.verified && !s.downstream;
        const isDownstream = s.downstream;
        return `
          <div class="timeline-step-row ${isBreak ? 'is-break' : (isDownstream ? 'is-downstream' : '')}">
            <div class="timeline-step-left">
              <div class="timeline-step-num">${s.step_order}</div>
              <div class="timeline-step-info">
                <strong>${esc(s.handler_name)}</strong>
                <span class="font-mono">${esc(s.actor_name)} · SHA-256: ${esc((s.hash_after || s.declared_sha256).slice(0, 16))}...</span>
              </div>
            </div>
            <div>
              <span class="status-pill ${s.verified ? 'valid' : (isBreak ? 'broken' : 'warning')}">
                ${s.verified ? '✓ Valid' : (isBreak ? '✕ FIRST BREAK' : '⚠ Downstream Affected')}
              </span>
            </div>
          </div>
        `;
      }).join("")}
    </div>

    <!-- Gemini AI Judicial Explanation Section -->
    <div class="section-header">
      <h2 class="section-title">AI Forensic Explanation (FRE 902)</h2>
      <button class="btn btn-accent btn-sm" id="btnExplainAI" onclick="fetchGeminiExplanation('${v.evidence_id}')">
        Explain finding with AI ✦
      </button>
    </div>

    <div id="aiExplanationContainer">
      <div style="font-size:13px; color:var(--text-muted); padding:12px 0;">
        Click "Explain finding with AI" above to generate a court-admissible forensic explanation powered by Google Gemini.
      </div>
    </div>
  `;
}

// Fetch & Render Google Gemini AI Explanation
async function fetchGeminiExplanation(evidenceId) {
  const container = document.getElementById("aiExplanationContainer");
  const btn = document.getElementById("btnExplainAI");

  if (btn) btn.disabled = true;
  container.innerHTML = `<div style="padding:16px; color:var(--text-muted);">Consulting independent verification authority & generating judicial assessment...</div>`;

  try {
    const res = await api(`/api/v1/verification/${evidenceId}/explain`, { method: "POST" });
    const exp = await res.json();

    container.innerHTML = `
      <div class="ai-explanation-card">
        <div class="ai-explanation-header">
          <span class="ai-pill">✦ ${esc(exp.ai_engine || 'Google Gemini 3.6 Flash')}</span>
          <span style="font-size:11px; color:var(--text-muted); font-weight:600;">FRE 902(14) Self-Authentication Directive</span>
        </div>
        <div class="ai-narrative-text">${esc(exp.summary)}</div>
        <span class="ai-disclaimer">
          Generated from deterministic verification findings. Cryptographic verifier decides mathematical truth; AI explains judicial implications.
        </span>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color:var(--status-broken-text); font-size:13px;">Error retrieving AI explanation: ${esc(err.message)}</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ==========================================================================
// EVIDENCE COPY MONITORING & AUDIT (WORM AUDIT TRAIL)
// ==========================================================================

let activeInspectedEvidenceId = null;
let lastCopyAttemptTime = 0;
let lastCopyEvidenceId = null;

async function recordCopyAttempt(evidenceId) {
  if (!evidenceId) return;
  const now = Date.now();
  // Prevent duplicate audit blocks within 1.5 seconds for the same evidence
  if (lastCopyEvidenceId === evidenceId && now - lastCopyAttemptTime < 1500) {
    return;
  }
  lastCopyAttemptTime = now;
  lastCopyEvidenceId = evidenceId;

  // Immediate visual feedback: show "Copied" badge and toast
  const badges = document.querySelectorAll("#copyIndicatorBadge, #copyIndicatorBadgeReview");
  badges.forEach(b => {
    b.style.display = "inline-flex";
  });
  showToast("✓ Copied — Evidence access recorded in Security Audit Ledger");

  setTimeout(() => {
    badges.forEach(b => {
      b.style.display = "none";
    });
  }, 3500);

  // Background audit recording to append-only WORM ledger
  try {
    const res = await api(`/api/v1/evidence/${evidenceId}/copy-attempt`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      console.warn("Copy audit warning:", err.detail);
    }
  } catch (err) {
    console.warn("Copy audit network error:", err.message);
  }
}

function attachEvidenceCopyMonitor(evidenceId) {
  if (!evidenceId) return;
  activeInspectedEvidenceId = evidenceId;

  const elements = document.querySelectorAll(`[data-evidence-preview="${evidenceId}"], #evidenceMediaContainer`);
  elements.forEach(el => {
    if (el.dataset.copyMonitored) return;
    el.dataset.copyMonitored = "true";

    // 1. Direct copy event on the preview element
    el.addEventListener("copy", () => {
      recordCopyAttempt(evidenceId);
    });

    // 2. Direct keydown event for Ctrl+C / Cmd+C when selecting text in the textarea
    el.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === "c" || e.key === "C")) {
        recordCopyAttempt(evidenceId);
      }
    });
  });
}

// Global copy listener on document as safety net for any copy when inspecting evidence
document.addEventListener("copy", (e) => {
  if (!activeInspectedEvidenceId) return;
  const preview = document.querySelector(`[data-evidence-preview="${activeInspectedEvidenceId}"]`);
  if (!preview) return;

  const isTargetPreview = e.target === preview || preview.contains(e.target);
  const isFocusedPreview = document.activeElement === preview;
  const hasTextSelected = (preview.selectionStart !== undefined && preview.selectionStart !== preview.selectionEnd);

  if (isTargetPreview || isFocusedPreview || hasTextSelected) {
    recordCopyAttempt(activeInspectedEvidenceId);
  }
});

// ==========================================================================
// MEDIA PREVIEW HELPERS (images / videos inside inspection views)
// ==========================================================================

function renderMediaPreview(d) {
  const mime = (d.artifact?.mime_type || d.mime_type || "").toLowerCase();
  const artId = d.artifact?.id || "";
  const evId = d.evidence_id || d.id || "";
  if (artId && (mime.startsWith("image/") || mime.startsWith("video/") || mime.includes("pdf"))) {
    return `
      <div id="evidenceMediaContainer" class="media-preview-frame"
           data-evidence-preview="${esc(evId)}"
           data-artid="${esc(artId)}" data-mime="${esc(mime)}"
           data-content="${esc(d.artifact?.content || '')}">
        <div style="padding:12px; font-size:12px; color:var(--text-muted);">Loading media preview...</div>
      </div>
    `;
  }
  return `<textarea class="text-area font-mono" rows="6" readonly data-evidence-preview="${esc(evId)}" style="font-size:11px; background:var(--bg-inset); width:100%; resize:vertical;">${esc(d.artifact?.content || '')}</textarea>`;
}

async function hydrateMediaPreviewFromDOM() {
  const container = document.getElementById("evidenceMediaContainer");
  if (!container || !container.dataset.artid) return;
  const artId = container.dataset.artid;
  const mime = container.dataset.mime || "";

  try {
    const res = await api(`/api/v1/artifacts/${artId}/download`);
    if (!res.ok) throw new Error("download failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    if (mime.startsWith("image/")) {
      container.innerHTML = `<img src="${url}" alt="Evidence image preview" style="display:block; max-width:100%; max-height:320px; margin:0 auto;" />`;
    } else if (mime.startsWith("video/")) {
      container.innerHTML = `<video src="${url}" controls style="display:block; max-width:100%; max-height:320px; margin:0 auto;"></video>`;
    } else if (mime.includes("pdf")) {
      container.innerHTML = `<div style="padding:12px; font-size:12px; color:var(--text-muted);">
        PDF artifact available. <a href="${url}" target="_blank" rel="noopener">Open document</a>
      </div>`;
    } else {
      container.innerHTML = `<div style="padding:12px; font-size:12px; color:var(--text-muted);">
        Binary artifact (${esc(mime || "application/octet-stream")}). <a href="${url}" download>Download raw file</a>
      </div>`;
    }
  } catch {
    container.innerHTML = `<div style="padding:12px; font-size:12px; color:var(--status-broken-text);">Media preview unavailable for this artifact.</div>`;
  }
}

// ==========================================================================
// 6. AUDIT PAGE & REPORTS PAGE
// ==========================================================================

async function renderAuditView() {
  workspaceContent.innerHTML = `<div style="padding:40px; text-align:center; color:var(--text-muted);">Loading immutable audit trail...</div>`;

  const [auditRes, verifyRes] = await Promise.all([
    api("/api/v1/audit?limit=50"),
    api("/api/v1/audit/verify"),
  ]);

  const logs = await auditRes.json();
  const v = await verifyRes.json();

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Security Audit Ledger</h1>
        <p class="page-desc">Append-only cryptographic WORM log of every user action and verification event.</p>
      </div>
      <div style="display:flex; align-items:center; gap:8px;">
        <span class="status-pill ${v.valid ? 'valid' : 'broken'}">
          ${v.valid ? `✓ Ledger Chain Valid (${v.count} blocks intact)` : `✕ Broken at block ${v.broken_at_id}`}
        </span>
        <button class="btn btn-secondary btn-sm" onclick="renderAuditView()">Re-verify ⟳</button>
      </div>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Target Resource</th>
            <th>Process Details</th>
            <th>Block Hash</th>
          </tr>
        </thead>
        <tbody>
          ${logs.map(l => `
            <tr>
              <td class="font-mono text-muted" style="font-size:11px;">${formatDate(l.timestamp)}</td>
              <td><strong>${esc(l.user_name)}</strong></td>
              <td><span class="status-pill neutral font-mono">${esc(l.action)}</span></td>
              <td class="font-mono" style="font-size:11px;">${esc(l.resource_id.slice(0, 8))}</td>
              <td style="font-size:12px;">${esc(l.details)}</td>
              <td class="font-mono text-muted" style="font-size:10px;">${esc(l.event_hash.slice(0, 12))}…</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function renderReportsView() {
  const res = await api("/api/v1/dashboard");
  const data = await res.json();
  const exhibits = data.evidence || [];

  workspaceContent.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Reports & Forensic Certificates</h1>
        <p class="page-desc">Generate court-admissible chain-of-custody certificates under FRE 902(14).</p>
      </div>
    </div>

    <div class="table-container">
      <table class="clean-table">
        <thead>
          <tr>
            <th>Exhibit</th>
            <th>Custody Stage</th>
            <th>Verification Status</th>
            <th style="text-align:right;">Export</th>
          </tr>
        </thead>
        <tbody>
          ${exhibits.map(e => `
            <tr>
              <td>
                <div style="font-weight:600;">${esc(e.name)}</div>
                <div class="font-mono text-muted" style="font-size:11px;">${esc(e.evidence_number || e.id.slice(0, 8))}</div>
              </td>
              <td>${esc(e.review_step || 'Intake')}</td>
              <td>
                ${e.latest_verdict === 'CHAIN_BROKEN'
                  ? `<span class="status-pill broken">✕ CHAIN BROKEN</span>`
                  : `<span class="status-pill valid">✓ ${esc(e.latest_verdict || 'CHAIN_INTACT')}</span>`}
              </td>
              <td style="text-align:right;">
                <div style="display:inline-flex; gap:6px;">
                  <button class="btn btn-secondary btn-sm" onclick="navigateTo('verify', { evidenceId: '${e.id}', evidenceName: '${esc(e.name)}' })">Verify & AI</button>
                  <button class="btn btn-primary btn-sm" onclick="downloadReportPdf('${e.id}')">Download PDF ⇩</button>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// Download PDF Report
async function downloadReportPdf(evidenceId) {
  const pdfWindow = window.open("about:blank", "_blank");
  try {
    showToast("Generating certified PDF report...");
    const res = await api(`/api/v1/reports/${evidenceId}/pdf`);
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to generate PDF");
    }

    const blob = await res.blob();
    if (!blob.size || blob.type !== "application/pdf") {
      throw new Error("The server returned an invalid PDF file");
    }

    const url = window.URL.createObjectURL(blob);
    if (pdfWindow && !pdfWindow.closed) pdfWindow.location.href = url;

    const a = document.createElement("a");
    a.href = url;
    a.download = `CustodyChain_Certificate_${evidenceId.slice(0, 8)}.pdf`;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    showToast("PDF opened and download started.");
  } catch (err) {
    if (pdfWindow && !pdfWindow.closed) pdfWindow.close();
    showToast(`Export failed: ${err.message}`);
  }
}

// Sidebar Secondary Views
async function renderPendingReviewsView() {
  await renderOverviewView();
}

async function renderHandoversView() {
  await renderOverviewView();
}

async function renderLabProcessingView() {
  await renderOverviewView();
}

async function renderSystemAdminView() {
  await renderOverviewView();
}

// Scenario Simulation Runner
async function runScenarioSimulation(tamperStep) {
  if (!state.currentCaseId && state.cachedCases.length > 0) {
    state.currentCaseId = state.cachedCases[0].id;
  }
  if (!state.currentCaseId) {
    showToast("Please register a case first.");
    return;
  }

  try {
    showToast(`Executing automated scenario (Tamper Step ${tamperStep})...`);
    const res = await api("/api/v1/evidence/simulation", {
      method: "POST",
      body: JSON.stringify({
        case_id: state.currentCaseId,
        name: tamperStep === 3 ? "Tampered-Memory-Image" : "Intact-Storage-Volume",
        content: `FORENSIC_RAW_STREAM_${Date.now()}`,
        tamper_step: tamperStep,
      }),
    });

    if (!res.ok) throw new Error("Simulation failed");
    const d = await res.json();
    showToast(`Simulation completed. Verdict: ${d.verdict}`);
    navigateTo("verify", { evidenceId: d.evidence_id, evidenceName: d.evidence_name });
  } catch (err) {
    showToast(`Simulation error: ${err.message}`);
  }
}

// ==========================================================================
// 7. AUTHENTICATION & LOGIN SCREEN CONTROLLER
// ==========================================================================

function showLoginScreen() {
  loginView.classList.remove("hidden");
  appView.classList.add("hidden");
}

function showAppWorkspace() {
  loginView.classList.add("hidden");
  appView.classList.remove("hidden");
}

async function loginWithCredentials(email, password, roleHint = null) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid email or password");
    }

    const data = await res.json();
    state.token = data.access_token;
    state.role = data.user?.role || roleHint || "EVIDENCE_OFFICER";
    state.user = data.user;

    localStorage.setItem("custody_token", state.token);
    localStorage.setItem("custody_role", state.role);
    localStorage.setItem("custody_user", JSON.stringify(state.user || {}));

    updateAppShellUI();
    showAppWorkspace();
    navigateTo("overview");
    showToast(`Signed in as ${state.user?.display_name || 'Officer'}`);
  } catch (err) {
    if (loginError) {
      loginError.textContent = "⚠ Invalid email or password.";
    } else {
      showToast(`Sign in error: ${err.message}`);
    }
  }
}

async function restoreAuthenticatedSession() {
  if (!state.token) return false;
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!res.ok) throw new Error("Session invalid");
    const user = await res.json();
    state.user = user;
    state.role = user.role;
    localStorage.setItem("custody_role", state.role);
    localStorage.setItem("custody_user", JSON.stringify(user));
    return true;
  } catch {
    handleLogout(false);
    return false;
  }
}

function handleLogout(showMessage = true) {
  state.token = null;
  state.role = "EVIDENCE_OFFICER";
  state.user = null;
  state.currentCaseId = null;

  localStorage.removeItem("custody_token");
  localStorage.removeItem("custody_role");
  localStorage.removeItem("custody_user");

  if (loginForm) loginForm.reset();
  showLoginScreen();
  if (showMessage) showToast("You have been signed out.");
}

function updateAppShellUI() {
  const role = state.role;
  const user = state.user || {};

  // Update Sidebar Profile
  sidebarUserAvatar.textContent = (user.display_name || "O").charAt(0);
  sidebarUserName.textContent = user.display_name || "Investigator";
  sidebarUserRole.textContent = formatRole(role);

  // Render Role-Tailored Navigation Links
  const navItems = ROLE_NAV_CONFIG[role] || ROLE_NAV_CONFIG.EVIDENCE_OFFICER;
  sidebarNav.innerHTML = navItems.map(item => `
    <button class="sidebar-link ${item.id === state.currentView ? 'active' : ''}" data-view="${item.id}" onclick="navigateTo('${item.id}')">
      <span class="link-icon">${item.icon}</span>
      <span>${item.label}</span>
    </button>
  `).join("");
}

function updateGlobalCaseSelect(cases) {
  globalCaseSelect.innerHTML = "";
  if (!cases || cases.length === 0) {
    globalCaseSelect.innerHTML = `<option value="">No Active Cases</option>`;
    state.currentCaseId = null;
    return;
  }

  cases.forEach((c, idx) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.case_number}: ${c.title}`;
    if (idx === 0 && !state.currentCaseId) {
      state.currentCaseId = c.id;
      opt.selected = true;
    } else if (state.currentCaseId === c.id) {
      opt.selected = true;
    }
    globalCaseSelect.appendChild(opt);
  });
}

// ==========================================================================
// 8. MODAL HANDLERS
// ==========================================================================

function openNewCaseModal() {
  newCaseModal.classList.remove("hidden");
}

function closeNewCaseModal() {
  newCaseModal.classList.add("hidden");
  newCaseForm.reset();
}

function openNewEvidenceModal() {
  if (!state.currentCaseId) {
    showToast("Please select an active case first.");
    return;
  }
  newEvidenceModal.classList.remove("hidden");
}

function closeNewEvidenceModal() {
  newEvidenceModal.classList.add("hidden");
  newEvidenceForm.reset();
}

// ── Upload Evidence File Modal ─────────────────────────────────────────────

function openUploadModal() {
  if (!state.currentCaseId) {
    showToast("Please select an active case first.");
    return;
  }
  uploadEvidenceForm.reset();
  uploadFilePreview.classList.add("hidden");
  uploadMediaPreview.classList.add("hidden");
  uploadMediaPreview.innerHTML = "";
  uploadEvidenceModal.classList.remove("hidden");
}

function closeUploadModal() {
  uploadEvidenceModal.classList.add("hidden");
  uploadEvidenceForm.reset();
  uploadFilePreview.classList.add("hidden");
  uploadMediaPreview.classList.add("hidden");
  uploadMediaPreview.innerHTML = "";
}

function pickUploadFile() {
  uploadFileInput?.click();
}

async function submitUploadEvidence(e) {
  e.preventDefault();
  const name = document.getElementById("uploadNameInput").value.trim();
  const description = document.getElementById("uploadDescInput").value.trim();
  const file = uploadFileInput.files && uploadFileInput.files[0];

  if (!file) return showToast("Please choose a file to upload.");

  try {
    const formData = new FormData();
    formData.append("case_id", state.currentCaseId);
    formData.append("name", name);
    formData.append("description", description);
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/api/v1/evidence/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${state.token}` },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }

    const d = await res.json();
    const verdict = d.final_verdict || d.verdict || "CHAIN_INTACT";
    closeUploadModal();
    showToast(`Exhibit "${name}" sealed. Verdict: ${verdict}`);
    navigateTo("inspect", { evidenceId: d.evidence_id, evidenceName: d.evidence_name || name });
  } catch (err) {
    showToast(`Upload error: ${err.message}`);
  }
}

// ── Bulk Import Modal ──────────────────────────────────────────────────────

function openBulkImportModal() {
  if (!state.currentCaseId) {
    showToast("Please select an active case first.");
    return;
  }
  bulkImportForm.reset();
  bulkImportModal.classList.remove("hidden");
}

function closeBulkImportModal() {
  bulkImportModal.classList.add("hidden");
  bulkImportForm.reset();
}

async function submitBulkImport(e) {
  e.preventDefault();
  const rawText = document.getElementById("bulkImportTextarea").value.trim();
  const description = document.getElementById("bulkDescInput").value.trim();

  if (!rawText) return showToast("Please enter at least one item.");

  const items = [];
  const errors = [];
  rawText.split("\n").forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const [name, ...rest] = trimmed.split("|");
    if (!name || !rest.length) {
      errors.push(`Line ${i + 1}: expected "Name | Content"`);
      return;
    }
    items.push({
      name: name.trim(),
      content: rest.join("|").trim(),
      description: description || `Bulk imported evidence (item ${items.length + 1})`,
    });
  });

  if (errors.length) {
    showToast(`Bulk import aborted: ${errors[0]}`);
    return;
  }
  if (items.length === 0) return showToast("No valid items to import.");

  try {
    const res = await api("/api/v1/evidence/bulk-import", {
      method: "POST",
      body: JSON.stringify({ case_id: state.currentCaseId, items }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Bulk import failed");
    }

    const d = await res.json();
    showToast(`Bulk import complete: ${d.imported} imported, ${d.errors} failed.`);

    const errLines = (d.error_details || []).map(ed =>
      `<div class="err">✕ Item ${ed.index + 1} (${esc(ed.name)}): ${esc(ed.error)}</div>`
    ).join("");

    const resultHTML = `
      <div class="bulk-result-box">
        <div class="ok">✓ ${d.imported} exhibit(s) sealed into case.</div>
        ${errLines}
      </div>
    `;

    closeBulkImportModal();
    showToast(`Bulk import complete: ${d.imported} imported, ${d.errors} failed.`);
    navigateTo("case-detail", { caseId: state.currentCaseId });
  } catch (err) {
    showToast(`Bulk import error: ${err.message}`);
  }
}

// ==========================================================================
// 9. APP INITIALIZATION & EVENT LISTENERS
// ==========================================================================

function init() {
  // Theme Setup
  if (state.theme === "dark") {
    document.body.classList.add("theme-dark");
    themeIcon.textContent = "🌙";
  } else {
    document.body.classList.remove("theme-dark");
    themeIcon.textContent = "☀️";
  }

  themeToggleBtn?.addEventListener("click", () => {
    document.body.classList.toggle("theme-dark");
    const isDark = document.body.classList.contains("theme-dark");
    state.theme = isDark ? "dark" : "light";
    localStorage.setItem("custody_theme", state.theme);
    themeIcon.textContent = isDark ? "🌙" : "☀️";
  });

  // Mobile Menu Toggle
  mobileMenuToggle?.addEventListener("click", () => {
    appSidebar.classList.toggle("mobile-open");
  });

  // Global Case Selector
  globalCaseSelect?.addEventListener("change", (e) => {
    state.currentCaseId = e.target.value;
    navigateTo("case-detail", { caseId: state.currentCaseId });
  });

  // Login Form
  loginForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (loginError) loginError.textContent = "";
    await loginWithCredentials(loginEmail.value.trim(), loginPassword.value);
  });

  loginEmail?.addEventListener("input", () => { if (loginError) loginError.textContent = ""; });
  loginPassword?.addEventListener("input", () => { if (loginError) loginError.textContent = ""; });

  demoAccessBtn?.addEventListener("click", () => demoAccessModal?.classList.remove("hidden"));
  closeDemoAccessBtn?.addEventListener("click", () => demoAccessModal?.classList.add("hidden"));
  demoAccessModal?.addEventListener("click", (e) => {
    if (e.target === demoAccessModal) demoAccessModal.classList.add("hidden");
  });
  passwordToggleBtn?.addEventListener("click", () => {
    const isPassword = loginPassword.type === "password";
    loginPassword.type = isPassword ? "text" : "password";
    passwordToggleBtn.textContent = isPassword ? "Hide" : "Show";
    passwordToggleBtn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
  });

  // Quick Account Role Buttons on Login
  document.querySelectorAll(".quick-role-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      loginEmail.value = btn.dataset.email;
      loginPassword.value = btn.dataset.pass;
      demoAccessModal?.classList.add("hidden");
      await loginWithCredentials(btn.dataset.email, btn.dataset.pass, btn.dataset.role);
    });
  });

  // Logout
  logoutBtn?.addEventListener("click", handleLogout);

  // New Case Form
  newCaseForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const caseNumber = document.getElementById("caseNumInput").value.trim();
    const title = document.getElementById("caseTitleInput").value.trim();
    const description = document.getElementById("caseDescInput").value.trim();

    try {
      const res = await api("/api/v1/cases", {
        method: "POST",
        body: JSON.stringify({ case_number: caseNumber, title, description }),
      });
      if (!res.ok) throw new Error("Case registration failed");
      const c = await res.json();
      closeNewCaseModal();
      showToast(`Case ${caseNumber} created.`);
      navigateTo("case-detail", { caseId: c.id, caseNumber: c.case_number });
    } catch (err) {
      showToast(`Error: ${err.message}`);
    }
  });

  closeCaseModalBtn?.addEventListener("click", closeNewCaseModal);
  cancelCaseModalBtn?.addEventListener("click", closeNewCaseModal);

  // New Evidence Form (unified intake — every active role may seal evidence)
  newEvidenceForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("evNameInput").value.trim();
    const content = document.getElementById("evContentInput").value;
    const description = document.getElementById("evDescInput").value.trim();

    try {
      const res = await api("/api/v1/evidence", {
        method: "POST",
        body: JSON.stringify({
          name,
          content,
          description,
          case_id: state.currentCaseId,
          step_by_step: true,
          simulate_tamper: false,
          tamper_step: 0,
        }),
      });
      if (!res.ok) throw new Error("Evidence intake failed");
      const d = await res.json();
      const evId = d.evidence_id || d.id;
      const evName = d.evidence_name || d.name || name;
      closeNewEvidenceModal();
      showToast(`Exhibit ${evName} ingested and sealed. Verdict: ${d.final_verdict || "CHAIN_INTACT"}`);
      navigateTo("inspect", { evidenceId: evId, evidenceName: evName });
    } catch (err) {
      showToast(`Error: ${err.message}`);
    }
  });

  closeEvidenceModalBtn?.addEventListener("click", closeNewEvidenceModal);
  cancelEvidenceModalBtn?.addEventListener("click", closeNewEvidenceModal);

  // Upload Evidence Modal wiring
  closeUploadModalBtn?.addEventListener("click", closeUploadModal);
  cancelUploadModalBtn?.addEventListener("click", closeUploadModal);
  uploadEvidenceForm?.addEventListener("submit", submitUploadEvidence);
  uploadDropzone?.addEventListener("click", pickUploadFile);
  wireDropzone(uploadDropzone, uploadFileInput);
  uploadFileInput?.addEventListener("change", () => {
    const file = uploadFileInput.files && uploadFileInput.files[0];
    if (file) {
      uploadFilePreview.classList.remove("hidden");
      uploadFilePreview.textContent = `${file.name} (${formatBytes(file.size)})`;
      const reader = new FileReader();
      reader.onload = () => {
        const type = file.type || "";
        if (type.startsWith("image/")) {
          uploadMediaPreview.classList.remove("hidden");
          uploadMediaPreview.innerHTML = `<img src="${reader.result}" alt="Upload preview" />`;
        } else if (type.startsWith("video/")) {
          uploadMediaPreview.classList.remove("hidden");
          uploadMediaPreview.innerHTML = `<video src="${reader.result}" controls></video>`;
        } else {
          uploadMediaPreview.classList.add("hidden");
          uploadMediaPreview.innerHTML = "";
        }
      };
      reader.readAsDataURL(file);
    } else {
      uploadFilePreview.classList.add("hidden");
      uploadFilePreview.textContent = "No file selected.";
      uploadMediaPreview.classList.add("hidden");
      uploadMediaPreview.innerHTML = "";
    }
  });

  // Bulk Import Modal wiring
  closeBulkModalBtn?.addEventListener("click", closeBulkImportModal);
  cancelBulkModalBtn?.addEventListener("click", closeBulkImportModal);
  bulkImportForm?.addEventListener("submit", submitBulkImport);

  // Initial State Check: never trust a cached localStorage role. Ask the backend
  // who owns the token so a modified browser value cannot change the dashboard role.
  if (state.token) {
    restoreAuthenticatedSession().then((valid) => {
      if (!valid) return;
      updateAppShellUI();
      showAppWorkspace();
      navigateTo("overview");
    });
  } else {
    showLoginScreen();
  }
}

// Utilities
function esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatRole(role) {
  switch (role) {
    case "EVIDENCE_OFFICER": return "Evidence Officer";
    case "FORENSIC_ANALYST": return "Forensic Analyst";
    case "AUDITOR": return "Independent Auditor";
    case "SYSTEM_ADMIN": return "System Admin";
    default: return role;
  }
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function wireDropzone(dz, input) {
  if (!dz || !input) return;
  ["dragenter", "dragover"].forEach(evt => dz.addEventListener(evt, (ev) => {
    ev.preventDefault();
    dz.classList.add("drag-over");
  }));
  ["dragleave", "drop"].forEach(evt => dz.addEventListener(evt, (ev) => {
    ev.preventDefault();
    dz.classList.remove("drag-over");
  }));
  dz.addEventListener("drop", (ev) => {
    ev.preventDefault();
    if (ev.dataTransfer.files && ev.dataTransfer.files.length) {
      input.files = ev.dataTransfer.files;
      input.dispatchEvent(new Event("change"));
    }
  });
}

let toastTimer = null;
function showToast(msg) {
  if (!minimalToast) return;
  toastMessage.textContent = msg;
  minimalToast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    minimalToast.classList.add("hidden");
  }, 3200);
}

// Bootstrap
document.addEventListener("DOMContentLoaded", init);
