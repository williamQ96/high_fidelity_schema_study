"use strict";

const state = { data: null, metric: "end_to_end_accuracy", blockers: [] };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pct(value, digits = 1) {
  return value == null ? "—" : `${(Number(value) * 100).toFixed(digits)}%`;
}

function humanStatus(value) {
  return String(value ?? "unknown").replaceAll("_", " ");
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("visible"), 2600);
}

function setView(view) {
  const target = $(`[data-section="${view}"]`) ? view : "overview";
  $$(".view").forEach((section) => section.classList.toggle("active", section.dataset.section === target));
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === target));
  if (location.hash !== `#${target}`) history.replaceState(null, "", `#${target}`);
  document.title = `${$(`#${target} h2`)?.textContent || "Research Console"} · High-Fidelity Schema Study`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function metricCard(label, value, note, tone) {
  return `<article class="metric-card" style="--tone:${tone}">
    <span class="metric-label">${escapeHtml(label)}</span>
    <strong>${escapeHtml(value)}</strong>
    <p>${escapeHtml(note)}</p>
  </article>`;
}

function renderOverview(data) {
  $("#research-title").textContent = data.headline.title;
  $("#research-subtitle").textContent = data.headline.subtitle;
  $("#current-result").textContent = data.headline.current_result;
  $("#paper-date").textContent = `Paper · ${data.artifact_snapshot.paper_date}`;
  $("#winner-status").textContent = data.headline.test_ready ? "Blind test released" : "No winner declared";
  $("#headline-metrics").innerHTML = [
    metricCard("NDP-50 corpus", data.ndp50.selected, "15 development · 10 validation · 25 sealed test", "var(--cyan)"),
    metricCard("Structural checks", `${data.readiness.checks_passed}/${data.readiness.checks_total}`, "Artifact and workflow bindings", "var(--green)"),
    metricCard("Release blockers", data.readiness.blockers.length, "Human evidence and external gates", "var(--red)"),
    metricCard("Project tests", data.headline.full_tests, "Recorded in the paper snapshot", "var(--blue)"),
  ].join("");

  $("#sidebar-state").textContent = data.headline.test_ready ? "Released" : "Pre-blind · blocked";
  $("#sidebar-state-note").textContent = data.headline.test_ready
    ? "Independent release authorization passed"
    : `${data.readiness.blockers.length} gates still require evidence`;
}

const variantDescriptions = {
  A: "Parser-owned schema and deterministic claims; zero semantic calls.",
  B: "At most one dataset-level response for unresolved semantic targets.",
  C: "Byte-identical B replay plus deterministic support and conflict checks.",
  D: "Historical per-field scheduling, fallback, and merge behavior.",
};

function renderVariants(data) {
  const labels = {
    end_to_end_accuracy: "accuracy",
    coverage: "coverage",
    selective_risk: "risk",
  };
  $("#variant-grid").innerHTML = data.methodology.variants.map((variant) => {
    const value = variant[state.metric];
    const status = variant.comparable ? "Comparable" : "Diagnostic only";
    return `<article class="variant-card" data-variant="${variant.id}">
      <div class="variant-header"><span class="variant-id">${variant.id}</span><span class="micro-label">${escapeHtml(status)}</span></div>
      <h4>${escapeHtml(variant.name)}</h4>
      <p>${escapeHtml(variantDescriptions[variant.id])}</p>
      <div class="variant-value"><strong>${pct(value)}</strong><span>${labels[state.metric]}</span></div>
    </article>`;
  }).join("");

  const comparisonNames = { A_vs_B: "A − B", B_vs_C: "B − C", C_vs_D: "C − D" };
  $("#comparison-strip").innerHTML = Object.entries(data.methodology.comparisons).map(([key, comparison]) =>
    `<div class="comparison-chip"><span>${comparisonNames[key] || escapeHtml(key)}</span><strong>${escapeHtml(humanStatus(comparison.status))}</strong></div>`
  ).join("");
}

function renderMethodology(data) {
  $("#research-question").textContent = data.methodology.research_question;
  $("#method-pipeline").innerHTML = data.methodology.pipeline.map((step, index) =>
    `<div class="pipeline-step"><span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(step)}</strong></div>`
  ).join("");
  renderVariants(data);
  $("#inference-design").innerHTML = [
    ["Co-primary contrasts", data.methodology.co_primary_contrasts.join(" · ")],
    ["Primary test", data.methodology.primary_test],
    ["Multiplicity", data.methodology.multiplicity],
    ["Fail-closed rule", data.methodology.claim_boundary],
  ].map(([term, value]) => `<div class="definition-row"><strong>${escapeHtml(term)}</strong><span>${escapeHtml(value)}</span></div>`).join("");
}

function renderNdp50(data) {
  const splits = [
    ["Development", data.ndp50.splits.development, "var(--blue)"],
    ["Validation", data.ndp50.splits.validation, "var(--cyan)"],
    ["Sealed test", data.ndp50.splits.sealed_test, "var(--surface-3)"],
  ];
  let cursor = 0;
  const gradients = splits.map(([, count, color]) => {
    const start = cursor;
    cursor += (count / data.ndp50.selected) * 100;
    return `${color} ${start}% ${cursor}%`;
  });
  $("#split-ring").style.background = `conic-gradient(${gradients.join(",")})`;
  $("#split-ring strong").textContent = data.ndp50.selected;
  $("#split-legend").innerHTML = splits.map(([label, count, color]) =>
    `<div class="legend-row"><i class="legend-dot" style="--color:${color}"></i><span>${label}</span><strong>${count}</strong></div>`
  ).join("");
  $("#selection-status").textContent = humanStatus(data.ndp50.selection_status);
  $("#reserve-count").textContent = `${data.ndp50.reserves} deterministic reserves`;

  const strata = Object.entries(data.ndp50.strata);
  const max = Math.max(...strata.map(([, value]) => value));
  $("#strata-bars").innerHTML = strata.map(([label, value]) =>
    `<div class="bar-row"><label title="${escapeHtml(humanStatus(label))}">${escapeHtml(humanStatus(label))}</label><div class="bar-track"><div class="bar-fill" style="--width:${(value / max) * 100}%"></div></div><strong>${value}</strong></div>`
  ).join("");

  const executionCard = (run) => `<article class="panel execution-card">
    <div class="execution-card-header"><div><p class="panel-kicker">STRUCTURAL RUN</p><h3>${escapeHtml(run.role)}</h3></div><span class="micro-label">NOT SEMANTIC ACCURACY</span></div>
    <div class="execution-metrics">
      <div><strong>${run.successful_datasets}/${run.datasets}</strong><span>datasets extracted</span></div>
      <div><strong>${pct(run.dataset_end_to_end_rate)}</strong><span>dataset end-to-end</span></div>
      <div><strong>${pct(run.extraction_success_given_acquisition)}</strong><span>given acquisition</span></div>
    </div>
    <p>${escapeHtml(run.claim_boundary)}</p>
  </article>`;
  $("#execution-grid").innerHTML = executionCard(data.ndp50.development_execution) + executionCard(data.ndp50.validation_execution);
}

function renderEvidence(data) {
  const evidence = data.development_evidence;
  $("#development-summary").innerHTML = [
    [evidence.case_count, "development cases"],
    [evidence.semantic_opportunity_cases, "semantic opportunity cases"],
    [Object.values(evidence.pairwise_status).filter((value) => value === "not_comparable").length, "non-comparable contrasts"],
  ].map(([value, label]) => `<div><strong>${value}</strong><span>${escapeHtml(label)}</span></div>`).join("");

  const metrics = [
    ["Accuracy", "end_to_end_accuracy"],
    ["Coverage", "coverage"],
    ["Risk", "selective_risk"],
    ["Calls", "model_calls"],
  ];
  let chart = `<div class="chart-label"></div>${evidence.variants.map((v) => `<div class="chart-cell chart-head">${v.id}</div>`).join("")}`;
  metrics.forEach(([label, key]) => {
    chart += `<div class="chart-label">${label}</div>`;
    evidence.variants.forEach((variant) => {
      const value = variant[key];
      const normalized = key === "model_calls" ? Math.min(value / 6, 1) : Number(value || 0);
      const display = key === "model_calls" ? String(value) : pct(value);
      chart += `<div class="chart-cell"><div class="mini-track"><div class="mini-fill" style="--width:${normalized * 100}%"></div></div><span>${display}</span></div>`;
    });
  });
  $("#development-chart").innerHTML = chart;
  $("#development-interpretation").textContent = evidence.interpretation;

  const qualification = data.qualification;
  $("#qualification-model").textContent = `${qualification.model} · ${qualification.quantization}`;
  $("#qualification-status").textContent = humanStatus(qualification.assessment);
  $("#qualification-status").className = `status-pill ${qualification.eligible ? "good" : "blocked"}`;
  $("#qualification-facts").innerHTML = [
    [qualification.case_count, "datasets"],
    [qualification.target_count, "semantic targets"],
    [qualification.context_length.toLocaleString(), "context length"],
    [qualification.identity_binding_complete ? "Complete" : "Pending", "blind identity binding"],
  ].map(([value, label]) => `<div class="qualification-fact"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join("");

  const maxCalls = Math.max(qualification.dataset_calls, qualification.legacy_calls);
  const maxLatency = Math.max(qualification.dataset_mean_latency_seconds, qualification.legacy_mean_latency_seconds);
  const costRows = [
    ["Dataset reasoner", qualification.dataset_calls, maxCalls, "calls", "dataset"],
    ["Legacy pipeline", qualification.legacy_calls, maxCalls, "calls", "legacy"],
    ["Dataset latency", qualification.dataset_mean_latency_seconds, maxLatency, "s / attempt", "dataset"],
    ["Legacy latency", qualification.legacy_mean_latency_seconds, maxLatency, "s / dataset", "legacy"],
  ];
  $("#qualification-cost-chart").innerHTML = costRows.map(([label, value, max, unit, cls]) =>
    `<div class="cost-row"><label>${label}</label><div class="bar-track"><div class="bar-fill ${cls}" style="--width:${(value / max) * 100}%"></div></div><strong>${value} ${unit}</strong></div>`
  ).join("");
  $("#identity-warning").innerHTML = `<strong>Identity binding remains incomplete</strong><ul>${qualification.remaining_identity_blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  $("#qualification-boundary").textContent = qualification.interpretation_boundary;
}

function renderReadiness(data) {
  const readiness = data.readiness;
  const progress = readiness.checks_total ? (readiness.checks_passed / readiness.checks_total) * 100 : 0;
  $("#readiness-ring").style.setProperty("--progress", `${progress}%`);
  $("#readiness-ring strong").textContent = `${readiness.checks_passed}/${readiness.checks_total}`;
  $("#readiness-count").textContent = `${readiness.checks_passed} structural checks passed`;
  $("#blocker-count").textContent = readiness.blockers.length;
  $("#test-ready-chip").textContent = data.headline.test_ready ? "TEST_READY = TRUE" : "TEST_READY = FALSE";
  $("#test-ready-chip").className = `status-pill ${data.headline.test_ready ? "good" : "blocked"}`;

  $("#gate-matrix").innerHTML = [
    `<div class="gate-cell header">Gate family</div><div class="gate-cell header">Workflow ready</div><div class="gate-cell header">Evidence complete</div>`,
    ...readiness.gate_groups.map((group) => `
      <div class="gate-cell">${escapeHtml(group.label)}</div>
      <div class="gate-cell gate-state"><i class="state-dot ${group.workflow_ready ? "pass" : ""}"></i>${group.workflow_ready ? "Ready" : "Pending"}</div>
      <div class="gate-cell gate-state"><i class="state-dot ${group.evidence_complete ? "pass" : ""}"></i>${group.evidence_complete ? "Complete" : "Pending"}</div>`),
  ].join("");
  state.blockers = readiness.blockers;
  renderBlockers("");
}

function renderBlockers(query) {
  const normalized = query.trim().toLowerCase();
  const filtered = state.blockers.filter((item) => item.toLowerCase().includes(normalized));
  $("#blocker-list").innerHTML = filtered.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#blocker-empty").hidden = filtered.length !== 0;
}

function renderHumanWorkflow(data) {
  const workflow = data.human_workflow;
  $("#roster-status").textContent = humanStatus(workflow.roster_status);
  $("#packet-count").textContent = `${workflow.packet_count} isolated assignment packets`;
  const roleDetails = [
    "Freeze the corpus-specific vocabulary without cross-reviewer anchoring.",
    "Approve license, transfer, attribution, and redistribution boundaries.",
    "Create independent, calibrated, prediction-blind reference labels.",
    "Review the F01–F16 response contract as a project collaborator.",
    "Verify the immutable public package before sealed-test release.",
  ];
  $("#role-graph").innerHTML = workflow.roles.map((role, index) =>
    `<article class="role-card"><span>ROLE ${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(role)}</strong><p>${escapeHtml(roleDetails[index])}</p></article>`
  ).join("");
  const feedback = $("#feedback-status");
  feedback.className = `status-callout ${workflow.feedback_signoff_complete ? "complete" : ""}`;
  feedback.textContent = workflow.feedback_signoff_complete
    ? "F01–F16 collaborator sign-off is complete and bound to the response materials."
    : "Packet acceptance is recorded, but the completed F01–F16 review payload and validator receipt remain pending.";
  $("#information-boundary").textContent = workflow.information_boundary;
}

function renderSources(data) {
  $("#source-list").innerHTML = data.sources.map((source) => `<li>${escapeHtml(source)}</li>`).join("");
}

function renderAll(data) {
  state.data = data;
  renderOverview(data);
  renderMethodology(data);
  renderNdp50(data);
  renderEvidence(data);
  renderReadiness(data);
  renderHumanWorkflow(data);
  renderSources(data);
  const timestamp = new Date(data.generated_at);
  $("#artifact-status").textContent = `Live artifact view · ${timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  $(".topbar-status").className = "topbar-status loaded";
}

async function loadDashboard({ announce = false } = {}) {
  const refresh = $("#refresh-data");
  refresh.classList.add("is-loading");
  refresh.disabled = true;
  try {
    const response = await fetch("/api/research-status", { cache: "no-store" });
    if (!response.ok) throw new Error(`Research API returned ${response.status}`);
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Research status unavailable");
    renderAll(payload);
    if (announce) showToast("Research artifacts refreshed.");
  } catch (error) {
    $(".topbar-status").className = "topbar-status error";
    $("#artifact-status").textContent = "Live artifact API unavailable";
    $("#current-result").textContent = "Start the full demo server to load the current research state.";
    showToast(`${error.message}. Run the Python demo server.`);
  } finally {
    refresh.classList.remove("is-loading");
    refresh.disabled = false;
  }
}

function setupInteractions() {
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $$(".segment").forEach((button) => button.addEventListener("click", () => {
    state.metric = button.dataset.metric;
    $$(".segment").forEach((item) => item.classList.toggle("active", item === button));
    if (state.data) renderVariants(state.data);
  }));
  $("#refresh-data").addEventListener("click", () => loadDashboard({ announce: true }));
  $("#blocker-filter").addEventListener("input", (event) => renderBlockers(event.target.value));

  const dialog = $("#sources-dialog");
  $("#open-sources").addEventListener("click", () => dialog.showModal());
  $("#close-sources").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  window.addEventListener("hashchange", () => setView(location.hash.slice(1)));
}

setupInteractions();
setView(location.hash.slice(1) || "overview");
loadDashboard();
