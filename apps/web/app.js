/* GAIA ontology workbench.
 *
 * Design rules this file follows:
 *  - The ontology is the navigation. Objects are selected, then acted on.
 *  - Nothing is rendered as fact without its provenance reachable in one click.
 *  - Absent data renders as an explicit "unavailable", never as a blank or a
 *    plausible-looking default. GAIA's whole value is that it does not guess.
 */

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const state = {
  pillar: "planning",
  system: null,
  identity: null,
  locations: { locations: [], active_location: null, active_location_id: null },
  plants: [],
  seasonPlans: [],
  selection: null, // { type, id, data }
  sourceCache: new Map(),
  objectTypes: [],
  lastResearch: null,
  lastMovement: null,
  lastMarket: null,
  lastVision: null,
  lastEnvironment: null,
  modelRuns: 0,
};

/* ---------------- ontology definition ----------------
 * Types mirror packages/domain. Each knows how to list and label itself so the
 * explorer and inspector stay generic. */

const ONTOLOGY = [
  { id: "location", glyph: "◎", name: "Location", pillar: "identify",
    list: () => state.locations.locations || [],
    label: (o) => o.label || "Location",
    sub: (o) => [o.admin2, o.admin1].filter(Boolean).join(", ") || o.id.slice(0, 8) },
  { id: "plant", glyph: "❧", name: "Plant", pillar: "identify",
    list: () => state.plants,
    label: (o) => o.nickname || o.cultivar || "Plant",
    sub: (o) => o.lifecycle_stage || "unknown stage" },
  { id: "season_plan", glyph: "▤", name: "Season plan", pillar: "planning",
    list: () => state.seasonPlans,
    label: (o) => o.name || "Season plan",
    sub: (o) => `${o.start_date || "?"} → ${o.end_date || "?"}` },
  { id: "research_work", glyph: "❡", name: "Research work", pillar: "evidence",
    list: () => (state.lastResearch && state.lastResearch.works) || [],
    label: (o) => o.title || "Untitled work",
    sub: (o) => [o.publication_year, o.journal].filter(Boolean).join(" · ") || o.provider_id || "" },
  { id: "source_record", glyph: "⛓", name: "Source record", pillar: "evidence",
    list: () => Array.from(state.sourceCache.values()),
    label: (o) => o.title || o.authority || o.provider || "Source",
    sub: (o) => o.provider || "" },
];

const PILLAR_TYPES = {
  planning: ["season_plan", "location", "plant"],
  evidence: ["research_work", "source_record"],
  identify: ["plant", "location"],
};

/* ---------------- boot ---------------- */

document.addEventListener("DOMContentLoaded", () => {
  bindShell();
  renderPillar();
  refreshAll();
});

function bindShell() {
  $$(".pillar").forEach((button) => {
    button.addEventListener("click", () => {
      state.pillar = button.dataset.pillar;
      $$(".pillar").forEach((other) => other.classList.toggle("active", other === button));
      renderObjectTypes();
      renderPillar();
    });
  });
  $("#agent-form").addEventListener("submit", submitAgent);
  $("#btn-seed").addEventListener("click", seedDemo);
  $("#btn-system").addEventListener("click", showSystem);
  $("#btn-geolocate").addEventListener("click", useDeviceLocation);
  $("#btn-manual-location").addEventListener("click", enterLocation);
  $("#location-select").addEventListener("change", activateSelectedLocation);
}

async function refreshAll() {
  try {
    const [system, identity, locations, plants, plans] = await Promise.all([
      api("/api/v1/system"),
      api("/api/v1/dev-identity"),
      api("/api/v1/locations"),
      api("/api/v1/plants"),
      api("/api/v1/season/plans").catch(() => ({ season_plans: [] })),
    ]);
    state.system = system;
    state.identity = identity;
    state.locations = locations;
    state.plants = plants || [];
    state.seasonPlans = (plans && plans.season_plans) || [];
    renderTopbar();
    renderLocationSelect();
    renderObjectTypes();
    renderPillar();
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* ---------------- topbar ---------------- */

function renderTopbar() {
  const system = state.system || {};
  const active = state.locations.active_location;
  $("#stat-location").textContent = active
    ? [active.admin2, active.admin1].filter(Boolean).join(", ") || active.label
    : "none";

  const providers = system.providers || [];
  const live = providers.filter((p) => p.mode === "live").length;
  const enabled = providers.filter((p) => p.enabled).length;
  $("#stat-providers").textContent = `${live} live / ${enabled} on`;

  const cost = system.cost || {};
  $("#stat-spend").textContent = `$${Number(cost.total_development_cash_spent || 0).toFixed(2)}`;
  $("#stat-modelruns").textContent = String(state.modelRuns);

  const mode = $("#stat-mode");
  const paid = cost.automatic_paid_usage_enabled;
  mode.textContent = paid ? "paid enabled" : "$0 automatic";
  mode.className = `badge ${paid ? "bad" : "ok"}`;
}

/* ---------------- ontology explorer ---------------- */

function renderObjectTypes() {
  const container = $("#object-types");
  const relevant = PILLAR_TYPES[state.pillar] || [];
  container.innerHTML = "";
  ONTOLOGY.filter((type) => relevant.includes(type.id)).forEach((type) => {
    const items = type.list();
    const button = document.createElement("button");
    button.className = "object-type" + (state.selection && state.selection.type === type.id ? " active" : "");
    button.innerHTML = `<span class="glyph">${type.glyph}</span><span class="name">${type.name}</span><span class="count">${items.length}</span>`;
    button.addEventListener("click", () => {
      renderObjectList(type);
    });
    container.appendChild(button);
  });
}

function renderObjectList(type) {
  const items = type.list();
  const panel = panelElement(`${type.name} — ${items.length}`);
  const body = panel.querySelector(".panel-body");
  body.classList.add("tight");
  if (!items.length) {
    body.innerHTML = `<div class="empty-state">No ${type.name.toLowerCase()} objects yet.</div>`;
  } else {
    const list = document.createElement("div");
    list.className = "obj-list";
    items.forEach((item) => {
      const row = document.createElement("button");
      row.className = "obj-row";
      row.innerHTML = `<span class="primary">${escapeHtml(type.label(item))}</span><span class="secondary">${escapeHtml(type.sub(item) || "")}</span>`;
      row.addEventListener("click", () => select(type.id, item));
      list.appendChild(row);
    });
    body.appendChild(list);
  }
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  canvas.appendChild(panel);
}

/* ---------------- pillars ---------------- */

function renderPillar() {
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  if (state.pillar === "planning") renderPlanning(canvas);
  else if (state.pillar === "evidence") renderEvidence(canvas);
  else renderIdentify(canvas);
}

/* --- Pillar 1: Planning --- */

function renderPlanning(canvas) {
  const form = panelElement("Generate season plan");
  form.querySelector(".panel-body").innerHTML = `
    <div class="row">
      <div class="field"><label>Crops</label><input id="plan-crops" value="tomato" /></div>
      <div class="field"><label>Objective</label><input id="plan-goal" value="Plan the coming season" /></div>
    </div>
    <div class="row" style="margin-top:8px">
      <div class="field"><label>Start (blank = today)</label><input id="plan-start" type="date" /></div>
      <div class="field"><label>End (blank = horizon)</label><input id="plan-end" type="date" /></div>
      <button class="btn primary" id="plan-run">Build plan</button>
    </div>
    <p class="muted" style="margin:8px 0 0;font-size:11px">
      Dates are derived from today when left blank. Calendar writes require an explicit preview and commit.
    </p>`;
  canvas.appendChild(form);
  $("#plan-run").addEventListener("click", buildSeasonPlan);

  const plansPanel = panelElement(`Season plans — ${state.seasonPlans.length}`);
  const body = plansPanel.querySelector(".panel-body");
  body.classList.add("tight");
  if (!state.seasonPlans.length) {
    body.innerHTML = `<div class="empty-state">No season plans yet.<div class="hint">Build one above, or ask the agent to plan a season.</div></div>`;
  } else {
    body.appendChild(objectTable(
      ["Plan", "Window", "Status", "Confidence"],
      state.seasonPlans.map((plan) => ({
        object: plan,
        type: "season_plan",
        cells: [
          { text: plan.name || "Season plan", className: "text" },
          { text: `${plan.start_date || "?"} → ${plan.end_date || "?"}` },
          { html: `<span class="badge ${plan.status === "draft" ? "warn" : "ok"}">${escapeHtml(plan.status || "unknown")}</span>` },
          { text: plan.confidence == null ? "—" : String(plan.confidence) },
        ],
      }))
    ));
  }
  canvas.appendChild(plansPanel);
}

async function buildSeasonPlan() {
  const crops = String($("#plan-crops").value || "").split(",").map((s) => s.trim()).filter(Boolean);
  try {
    const result = await api("/api/v1/season/plan", {
      method: "POST",
      body: {
        crop_names: crops,
        objective: $("#plan-goal").value,
        start_date: $("#plan-start").value || null,
        end_date: $("#plan-end").value || null,
        location_id: state.locations.active_location_id,
        include_mercator: true,
      },
    });
    toast(`Plan created with ${(result.actions || []).length} actions.`);
    await refreshAll();
    if (result.season_plan) select("season_plan", result.season_plan, { actions: result.actions });
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* --- Pillar 2: Evidence --- */

function renderEvidence(canvas) {
  const search = panelElement("Retrieve evidence");
  search.querySelector(".panel-body").innerHTML = `
    <div class="row">
      <div class="field" style="flex:3"><label>Question</label><input id="ev-query" value="tomato heat stress shading" /></div>
      <button class="btn" id="ev-search">Search</button>
      <button class="btn primary" id="ev-synth">Synthesize</button>
    </div>
    <p class="muted" style="margin:8px 0 0;font-size:11px">
      Search is retrieval only and runs no model. Synthesis validates every citation against retrieved works —
      an identifier the model invents, even inside prose, is rejected rather than stored.
    </p>`;
  canvas.appendChild(search);
  $("#ev-search").addEventListener("click", () => runResearch(false));
  $("#ev-synth").addEventListener("click", () => runResearch(true));

  const works = (state.lastResearch && state.lastResearch.works) || [];
  const resultsPanel = panelElement(`Retrieved works — ${works.length}`);
  const body = resultsPanel.querySelector(".panel-body");
  body.classList.add("tight");
  if (!works.length) {
    body.innerHTML = `<div class="empty-state">No retrieval yet.<div class="hint">Results carry publication identity and study type, and contradictions stay visible.</div></div>`;
  } else {
    body.appendChild(objectTable(
      ["Title", "Year", "Type", "Identity"],
      works.map((work) => ({
        object: work,
        type: "research_work",
        cells: [
          { text: work.title || "Untitled", className: "text" },
          { text: work.publication_year || "—" },
          { html: `<span class="badge muted">${escapeHtml(work.study_type || "unclassified")}</span>` },
          { text: work.doi || work.pmid || work.external_id || "—" },
        ],
      }))
    ));
  }
  canvas.appendChild(resultsPanel);

  if (state.lastResearch && state.lastResearch.synthesis) {
    const synthesis = state.lastResearch.synthesis;
    const panel = panelElement("Synthesis");
    panel.querySelector(".panel-body").innerHTML = `
      <div class="row" style="margin-bottom:8px">
        <span class="badge info">quality: ${escapeHtml(String(synthesis.evidence_quality || "unknown"))}</span>
        ${synthesis.uncertainty ? `<span class="badge warn">uncertainty: ${escapeHtml(String(synthesis.uncertainty.level || "unstated"))}</span>` : ""}
        <span class="badge muted">model runs: ${Number(synthesis.model_run_count || 0)}</span>
      </div>
      <div>${escapeHtml(String(synthesis.summary || "No summary returned."))}</div>
      <div style="margin-top:8px">${sourceChips(synthesis.source_record_ids || [])}</div>`;
    canvas.appendChild(panel);
  }
}

async function runResearch(synthesize) {
  const query = $("#ev-query").value;
  try {
    if (synthesize) {
      const result = await api("/api/v1/research/synthesize", {
        method: "POST",
        body: { question: query, location_id: state.locations.active_location_id, use_model: false },
      });
      state.lastResearch = state.lastResearch || {};
      state.lastResearch.synthesis = result;
      toast("Synthesis complete; citations validated.");
    } else {
      const result = await api("/api/v1/research/search", { method: "POST", body: { query, limit: 10 } });
      state.lastResearch = { works: result.works || result.results || [] };
      toast(`Retrieved ${(state.lastResearch.works || []).length} works.`);
    }
    renderObjectTypes();
    renderPillar();
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* --- Pillar 3: Identify & Forecast --- */

function renderIdentify(canvas) {
  const conditions = panelElement("Current conditions");
  const body = conditions.querySelector(".panel-body");
  if (!state.locations.active_location_id) {
    body.innerHTML = `<div class="empty-state">No active location.<div class="hint">Set one in the left rail to resolve geography, weather, soil, and water.</div></div>`;
  } else if (!state.lastEnvironment) {
    body.innerHTML = `<button class="btn primary" id="env-load">Resolve conditions</button>
      <p class="muted" style="margin:8px 0 0;font-size:11px">Deterministic path — no model run.</p>`;
  } else {
    body.appendChild(environmentReport(state.lastEnvironment));
  }
  canvas.appendChild(conditions);
  if ($("#env-load")) $("#env-load").addEventListener("click", loadEnvironment);

  const taxonomy = panelElement("Identify");
  taxonomy.querySelector(".panel-body").innerHTML = `
    <div class="row">
      <div class="field" style="flex:2"><label>Taxon or common name</label><input id="id-taxon" value="Solanum lycopersicum" /></div>
      <button class="btn" id="id-resolve">Resolve taxonomy</button>
    </div>
    <div class="row" style="margin-top:8px">
      <div class="field" style="flex:2"><label>Photo</label><input id="id-image" type="file" accept="image/*" /></div>
      <button class="btn" id="id-vision">Analyze image</button>
    </div>
    <p class="muted" style="margin:8px 0 0;font-size:11px">
      Vision output separates what is visible from what is hypothesized, and is never a confirmed diagnosis.
    </p>
    <div id="id-result" style="margin-top:10px"></div>`;
  canvas.appendChild(taxonomy);
  $("#id-resolve").addEventListener("click", resolveTaxon);
  $("#id-vision").addEventListener("click", analyzeImage);

  const movement = panelElement("Regulatory movement check");
  movement.querySelector(".panel-body").innerHTML = `
    <div class="row">
      <div class="field"><label>Origin</label><input id="mv-origin" value="tx-houston" /></div>
      <div class="field"><label>Destination</label><input id="mv-dest" value="fl-orlando" /></div>
      <div class="field"><label>Species</label><input id="mv-species" value="Citrus sinensis" /></div>
      <button class="btn" id="mv-run">Check</button>
    </div>
    <p class="muted" style="margin:8px 0 0;font-size:11px">
      Fail-closed: an unresolved rule returns UNRESOLVED, never an implied permission. Not legal advice.
    </p>
    <div id="mv-result" style="margin-top:10px"></div>`;
  canvas.appendChild(movement);
  $("#mv-run").addEventListener("click", checkMovement);
}

async function loadEnvironment() {
  try {
    state.lastEnvironment = await api("/api/v1/context/environment", {
      method: "POST",
      body: { location_id: state.locations.active_location_id },
    });
    renderPillar();
  } catch (error) {
    toast(readableError(error), true);
  }
}

function environmentReport(bundle) {
  const snapshot = bundle.environmental_snapshot || {};
  const wrapper = document.createElement("div");
  const measures = [
    ["Temperature", snapshot.temperature],
    ["Rain chance", snapshot.precipitation],
    ["Humidity", snapshot.humidity],
    ["Solar radiation", snapshot.solar_radiation],
    ["Photoperiod", snapshot.photoperiod],
  ];
  const list = document.createElement("dl");
  list.className = "kv";
  measures.forEach(([label, measure]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const value = document.createElement("dd");
    if (measure && measure.value != null) {
      value.textContent = `${measure.value}${measure.unit ? " " + measure.unit : ""}`;
    } else {
      value.textContent = "unavailable";
      value.className = "unset";
    }
    list.append(term, value);
  });
  wrapper.appendChild(list);

  const statuses = snapshot.provider_statuses || {};
  const badges = document.createElement("div");
  badges.style.marginTop = "10px";
  badges.innerHTML = Object.entries(statuses)
    .map(([provider, status]) => `<span class="badge ${status === "AVAILABLE" || status === "CACHE_HIT" ? "ok" : "warn"}">${escapeHtml(provider)}: ${escapeHtml(String(status))}</span> `)
    .join("");
  wrapper.appendChild(badges);
  wrapper.appendChild(chipRow(bundle.source_record_ids || []));
  return wrapper;
}

async function resolveTaxon() {
  try {
    const result = await api("/api/v1/research/search", { method: "POST", body: { query: $("#id-taxon").value, limit: 1 } });
    $("#id-result").innerHTML = `<pre class="raw">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
  } catch (error) {
    toast(readableError(error), true);
  }
}

async function analyzeImage() {
  const file = $("#id-image").files[0];
  if (!file) return toast("Choose an image first.", true);
  try {
    const base64 = await fileToBase64(file);
    const media = await api("/api/v1/vision/media", { method: "POST", body: { image_base64: base64, content_type: file.type || "image/jpeg" } });
    const analysis = await api("/api/v1/vision/analyze", {
      method: "POST",
      body: { media_attachment_id: media.id, location_id: state.locations.active_location_id },
    });
    state.lastVision = analysis;
    $("#id-result").innerHTML = visionHtml(analysis);
  } catch (error) {
    toast(readableError(error), true);
  }
}

function visionHtml(analysis) {
  const observations = analysis.visual_observations || [];
  const hypotheses = analysis.visual_hypotheses || [];
  return `
    <div class="badge ${analysis.provider_status === "AVAILABLE" ? "ok" : "warn"}">${escapeHtml(String(analysis.provider_status || analysis.status || "unknown"))}</div>
    <h3 style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-2);margin:10px 0 4px">Visible evidence</h3>
    ${observations.length ? `<ul style="margin:0;padding-left:18px">${observations.map((o) => `<li>${escapeHtml(o.label || "")} — ${escapeHtml(o.description || "")}</li>`).join("")}</ul>` : `<div class="muted">none reported</div>`}
    <h3 style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--text-2);margin:10px 0 4px">Hypotheses (not a diagnosis)</h3>
    ${hypotheses.length ? `<ul style="margin:0;padding-left:18px">${hypotheses.map((h) => `<li>${escapeHtml(h.label || "")} <span class="badge muted">${escapeHtml(String(h.status || "hypothesis"))}</span></li>`).join("")}</ul>` : `<div class="muted">none reported</div>`}`;
}

async function checkMovement() {
  try {
    const result = await api("/api/v1/movement/check", {
      method: "POST",
      body: {
        origin_alias: $("#mv-origin").value,
        destination_alias: $("#mv-dest").value,
        species: $("#mv-species").value,
        plant_part: "live plant",
        live_plant: true,
      },
    });
    state.lastMovement = result;
    const tone = result.status === "RESTRICTED" ? "bad" : result.status === "ALLOWED" ? "ok" : "warn";
    $("#mv-result").innerHTML = `
      <div class="badge ${tone}" style="font-size:12px">${escapeHtml(String(result.status))}</div>
      <div style="margin-top:8px">${(result.applicable_rules || []).map((rule) => `
        <div class="provenance">
          <div class="src"><span class="authority">${escapeHtml(rule.authority || rule.jurisdiction_pack || "rule")}</span></div>
          <div class="src"><span class="meta">${escapeHtml(rule.citation || rule.rule_id || "")}</span></div>
          <div>${escapeHtml(rule.requirement || rule.summary || "")}</div>
        </div>`).join("") || `<div class="muted">No matching rules.</div>`}</div>`;
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* ---------------- selection + inspector ---------------- */

function select(typeId, object, extra) {
  state.selection = { type: typeId, id: object.id, data: object, extra: extra || {} };
  renderObjectTypes();
  renderInspector();
  $$(".obj-row").forEach((row) => row.classList.remove("selected"));
}

function renderInspector() {
  const selection = state.selection;
  if (!selection) return;
  const type = ONTOLOGY.find((t) => t.id === selection.type);
  const object = selection.data;

  $("#insp-type").textContent = type ? type.name : selection.type;
  $("#insp-title").textContent = type ? type.label(object) : "Object";
  $("#insp-id").textContent = object.id || "";

  const body = $("#insp-body");
  body.innerHTML = "";

  body.appendChild(inspectorSection("Properties", propertyList(object)));

  const sourceIds = object.source_record_ids || [];
  if (sourceIds.length) {
    body.appendChild(inspectorSection("Provenance", chipRow(sourceIds)));
  } else {
    const none = document.createElement("div");
    none.className = "muted";
    none.style.fontSize = "11px";
    none.textContent = "No source records attached to this object.";
    body.appendChild(inspectorSection("Provenance", none));
  }

  if (selection.extra && selection.extra.actions) {
    body.appendChild(inspectorSection("Actions", actionTimeline(selection.extra.actions)));
  }

  const raw = document.createElement("pre");
  raw.className = "raw";
  raw.textContent = JSON.stringify(object, null, 2);
  body.appendChild(inspectorSection("Raw object", raw));
}

function propertyList(object) {
  const list = document.createElement("dl");
  list.className = "kv";
  Object.entries(object)
    .filter(([key, value]) => typeof value !== "object" || value === null)
    .slice(0, 24)
    .forEach(([key, value]) => {
      const term = document.createElement("dt");
      term.textContent = key.replace(/_/g, " ");
      const definition = document.createElement("dd");
      if (value === null || value === "" || value === undefined) {
        definition.textContent = "unset";
        definition.className = "unset";
      } else {
        definition.textContent = String(value);
      }
      list.append(term, definition);
    });
  return list;
}

function actionTimeline(actions) {
  const wrapper = document.createElement("div");
  wrapper.className = "timeline";
  actions.forEach((action) => {
    const item = document.createElement("div");
    item.className = "timeline-item";
    item.innerHTML = `<div class="when">${escapeHtml(String(action.preferred_at || "").slice(0, 16))}</div>
      <div class="what">${escapeHtml(action.title || action.action_type || "action")}</div>`;
    wrapper.appendChild(item);
  });
  return wrapper;
}

function inspectorSection(heading, node) {
  const section = document.createElement("div");
  section.className = "inspector-section";
  const title = document.createElement("h3");
  title.textContent = heading;
  section.append(title, node);
  return section;
}

/* ---------------- provenance ---------------- */

function chipRow(ids) {
  const wrapper = document.createElement("div");
  wrapper.innerHTML = sourceChips(ids);
  wrapper.querySelectorAll(".source-chip").forEach((chip) => {
    chip.addEventListener("click", () => openSource(chip.dataset.id));
  });
  return wrapper;
}

function sourceChips(ids) {
  if (!ids || !ids.length) return `<span class="muted" style="font-size:11px">No sources attached.</span>`;
  return ids.map((id) => `<span class="source-chip" data-id="${escapeHtml(id)}">${escapeHtml(String(id).slice(0, 8))}</span>`).join("");
}

async function openSource(id) {
  try {
    if (!state.sourceCache.has(id)) {
      const result = await api(`/api/v1/source-records?ids=${encodeURIComponent(id)}`);
      (result.source_records || []).forEach((record) => state.sourceCache.set(record.id, record));
    }
    const record = state.sourceCache.get(id);
    if (record) select("source_record", record);
    renderObjectTypes();
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* ---------------- agent ---------------- */

async function submitAgent(event) {
  event.preventDefault();
  const input = $("#agent-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  appendTurn("user", message);
  $("#agent-route").textContent = "working";
  $("#agent-route").className = "badge info";

  try {
    const result = await api("/api/v1/chat", {
      method: "POST",
      body: {
        message,
        location_id: state.locations.active_location_id,
        user_plant_id: state.selection && state.selection.type === "plant" ? state.selection.id : null,
      },
    });
    state.modelRuns += Number(result.model_run_count || 0);
    renderTopbar();
    appendTurn("gaia", result.content || "", result);
    $("#agent-route").textContent = result.route || "done";
    $("#agent-route").className = "badge " + (result.model_run_count ? "info" : "ok");
    await refreshAll();
  } catch (error) {
    appendTurn("gaia", readableError(error));
    $("#agent-route").textContent = "error";
    $("#agent-route").className = "badge bad";
  }
}

function appendTurn(who, text, result) {
  const log = $("#agent-log");
  const turn = document.createElement("div");
  turn.className = `turn ${who}`;
  const label = document.createElement("div");
  label.className = "who";
  label.textContent = who === "user" ? "You" : "GAIA";
  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text;
  turn.append(label, body);

  if (result) {
    const meta = document.createElement("div");
    meta.className = "route-line";
    meta.innerHTML = `<span class="badge ${result.model_run_count ? "info" : "ok"}">${escapeHtml(String(result.route || "route"))}</span>
      <span class="badge muted">model runs: ${Number(result.model_run_count || 0)}</span>`;
    turn.appendChild(meta);
    if ((result.source_record_ids || []).length) turn.appendChild(chipRow(result.source_record_ids));
  }

  log.appendChild(turn);
  log.scrollTop = log.scrollHeight;
}

/* ---------------- location ---------------- */

function renderLocationSelect() {
  const select = $("#location-select");
  const locations = state.locations.locations || [];
  select.innerHTML = locations.length
    ? locations.map((location) => `<option value="${escapeHtml(location.id)}"${location.id === state.locations.active_location_id ? " selected" : ""}>${escapeHtml(location.label || location.id)}</option>`).join("")
    : `<option value="">No location set</option>`;
}

async function activateSelectedLocation() {
  const id = $("#location-select").value;
  if (!id) return;
  const location = (state.locations.locations || []).find((item) => item.id === id);
  if (!location) return;
  await setActiveLocation({ source_kind: "saved", label: location.label, latitude: location.latitude, longitude: location.longitude });
}

function useDeviceLocation() {
  if (!navigator.geolocation) return toast("This browser has no geolocation.", true);
  navigator.geolocation.getCurrentPosition(
    (position) => setActiveLocation({
      source_kind: "device",
      label: "Device location",
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy_m: position.coords.accuracy,
    }),
    () => toast("Location permission denied.", true)
  );
}

function enterLocation() {
  const raw = window.prompt("Enter latitude, longitude (decimal degrees)");
  if (!raw) return;
  const [latitude, longitude] = raw.split(",").map((part) => Number(part.trim()));
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return toast("Could not read those coordinates.", true);
  setActiveLocation({ source_kind: "manual", label: "Manual location", latitude, longitude });
}

async function setActiveLocation(body) {
  try {
    await api("/api/v1/locations/active", { method: "POST", body });
    state.lastEnvironment = null;
    await refreshAll();
    toast("Active location set.");
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* ---------------- system ---------------- */

async function showSystem() {
  const system = state.system || (await api("/api/v1/system"));
  const canvas = $("#canvas");
  canvas.innerHTML = "";
  const panel = panelElement("Providers");
  const body = panel.querySelector(".panel-body");
  body.classList.add("tight");
  body.appendChild(objectTable(
    ["Provider", "Type", "Mode", "Billing", "Remote"],
    (system.providers || []).map((provider) => ({
      cells: [
        { text: provider.provider_id, className: "text" },
        { text: provider.provider_type },
        { html: `<span class="badge ${provider.mode === "live" ? "ok" : provider.mode === "disabled" ? "muted" : "info"}">${escapeHtml(String(provider.mode))}</span>` },
        { text: provider.billing_class },
        { text: provider.remote ? "yes" : "no" },
      ],
    }))
  ));
  canvas.appendChild(panel);

  const cost = panelElement("Cost posture");
  cost.querySelector(".panel-body").innerHTML = `<pre class="raw">${escapeHtml(JSON.stringify(system.cost || {}, null, 2))}</pre>`;
  canvas.appendChild(cost);
}

async function seedDemo() {
  try {
    await api("/api/v1/seed/demo", { method: "POST", body: {} });
    toast("Demo workspace seeded.");
    await refreshAll();
  } catch (error) {
    toast(readableError(error), true);
  }
}

/* ---------------- primitives ---------------- */

function panelElement(heading) {
  const panel = document.createElement("section");
  panel.className = "panel";
  panel.innerHTML = `<div class="panel-head"><h2>${escapeHtml(heading)}</h2><span class="spacer"></span></div><div class="panel-body"></div>`;
  return panel;
}

function objectTable(headers, rows) {
  const table = document.createElement("table");
  table.className = "data";
  table.innerHTML = `<thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>`;
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.cells.forEach((cell) => {
      const td = document.createElement("td");
      if (cell.html) td.innerHTML = cell.html;
      else td.textContent = cell.text == null ? "—" : String(cell.text);
      if (cell.className) td.className = cell.className;
      tr.appendChild(td);
    });
    if (row.object) {
      tr.style.cursor = "pointer";
      tr.addEventListener("click", () => select(row.type, row.object, row.extra));
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

async function api(path, options) {
  const settings = { method: (options && options.method) || "GET", headers: { "Content-Type": "application/json" } };
  if (options && options.body !== undefined) settings.body = JSON.stringify(options.body);
  const response = await fetch(path, settings);
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`Malformed response from ${path}`);
  }
  if (!response.ok) {
    const reference = payload.error_reference ? ` (ref ${payload.error_reference})` : "";
    throw new Error(`${payload.error || response.status}${reference}`);
  }
  return payload;
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function toast(message, isError) {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { element.className = "toast"; }, 4200);
}

function readableError(error) {
  return error && error.message ? error.message : String(error);
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
