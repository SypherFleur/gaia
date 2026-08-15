const state = {
  status: null,
  identity: null,
  system: null,
  locations: null,
  activeLocationId: null,
  plants: [],
  selectedPlantId: null,
  lastMediaId: null,
  lastSeasonPlanId: null,
  lastConversationId: null,
};

const views = {
  chat: { title: "Chat", subtitle: "Ask GAIA with local context and visible provenance." },
  plants: { title: "Plants", subtitle: "Workspace records, observations, and plant-aware actions." },
  vision: { title: "Vision", subtitle: "Local image evidence with observations kept separate from hypotheses." },
  season: { title: "Season", subtitle: "Internal planning with optional calendar preview." },
  research: { title: "Research", subtitle: "Evidence search, contradictions, applicability, and citations." },
  movement: { title: "Movement", subtitle: "U.S. movement decision support with currentness and authority notes." },
  markets: { title: "Markets", subtitle: "Dated production and market context." },
  system: { title: "Settings", subtitle: "Runtime, provider, cost, and persistence status." },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

document.addEventListener("DOMContentLoaded", () => {
  bindNavigation();
  bindForms();
  refreshAll();
});

function bindNavigation() {
  $$(".nav-item").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view));
  });
  $("#refresh").addEventListener("click", refreshAll);
  $("#seed-demo").addEventListener("click", seedDemo);
  $("#device-location").addEventListener("click", useDeviceLocation);
  $("#manual-location").addEventListener("click", enterManualLocation);
  $("#ask-about-plant").addEventListener("click", () => {
    showView("chat");
    $("#chat-input").value = "What should I do for this plant today?";
    $("#chat-input").focus();
  });
}

function bindForms() {
  $("#plant-select").addEventListener("change", (event) => {
    state.selectedPlantId = event.target.value || null;
    renderSelectedPlant();
  });
  $("#location-select").addEventListener("change", setActiveLocationFromSelect);
  $("#chat-form").addEventListener("submit", submitChat);
  $("#plant-form").addEventListener("submit", submitPlant);
  $("#observation-form").addEventListener("submit", submitObservation);
  $("#vision-file").addEventListener("change", previewVisionFile);
  $("#vision-run").addEventListener("click", runVision);
  $("#season-form").addEventListener("submit", submitSeason);
  seedSeasonDateDefaults();
  $("#calendar-preview").addEventListener("click", previewCalendar);
  $("#research-form").addEventListener("submit", submitResearchSearch);
  $("#research-synthesize").addEventListener("click", synthesizeResearch);
  $("#movement-form").addEventListener("submit", submitMovement);
  $("#markets-form").addEventListener("submit", submitMarkets);
}

function showView(viewName) {
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === viewName));
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
  $("#view-title").textContent = views[viewName].title;
  $("#view-subtitle").textContent = views[viewName].subtitle;
}

async function refreshAll() {
  try {
    const [status, identity, system, locations, plants] = await Promise.all([
      api("/api/v1/status"),
      api("/api/v1/dev-identity"),
      api("/api/v1/system"),
      api("/api/v1/locations"),
      api("/api/v1/plants"),
    ]);
    state.status = status;
    state.identity = identity;
    state.system = system;
    state.locations = locations;
    state.activeLocationId = locations.active_location_id || identity.primary_location_id || null;
    state.plants = Array.isArray(plants) ? plants : [];
    if (!state.selectedPlantId && state.plants.length) state.selectedPlantId = state.plants[0].id;
    renderStatus();
    renderLocations();
    renderPlants();
    renderSelectedPlant();
    renderSystem();
  } catch (error) {
    toast(`Refresh failed: ${error.message}`);
  }
}

async function seedDemo() {
  try {
    const result = await api("/api/v1/seed/demo", { method: "POST", body: {} });
    toast(`Seeded ${result.plant_count} plant and ${result.guidance_plan_count} GuidancePlan.`);
    await refreshAll();
  } catch (error) {
    toast(`Seed failed: ${error.message}`);
  }
}

async function setActiveLocationFromSelect(event) {
  const locationId = event.target.value || null;
  if (!locationId) {
    state.activeLocationId = null;
    toast("No active location selected.");
    return;
  }
  try {
    const result = await api("/api/v1/locations/active", { method: "POST", body: { location_id: locationId } });
    state.activeLocationId = result.active_location?.id || locationId;
    toast(locationToast(result.active_location));
    await refreshAll();
  } catch (error) {
    toast(readableError(error));
  }
}

async function useDeviceLocation() {
  if (!navigator.geolocation) return toast("Browser geolocation is unavailable.");
  $("#device-location").disabled = true;
  try {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 12000, maximumAge: 600000 });
    });
    const { latitude, longitude, accuracy } = position.coords;
    const result = await api("/api/v1/locations/active", {
      method: "POST",
      body: {
        source_kind: "device",
        label: "Device location",
        latitude,
        longitude,
        accuracy_m: accuracy,
      },
    });
    state.activeLocationId = result.active_location?.id || null;
    toast(locationToast(result.active_location));
    await refreshAll();
  } catch (error) {
    toast(error.message || "Location permission was not granted.");
  } finally {
    $("#device-location").disabled = false;
  }
}

async function enterManualLocation() {
  const coordinateText = window.prompt("Enter latitude and longitude, separated by a comma.");
  if (!coordinateText) return;
  const [latitudeText, longitudeText] = coordinateText.split(",").map((item) => item.trim());
  const latitude = Number(latitudeText);
  const longitude = Number(longitudeText);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return toast("Enter coordinates like 29.7604, -95.3698.");
  }
  const label = window.prompt("Name this location.", "Manual location") || "Manual location";
  try {
    const result = await api("/api/v1/locations/active", {
      method: "POST",
      body: {
        source_kind: "manual",
        label,
        latitude,
        longitude,
      },
    });
    state.activeLocationId = result.active_location?.id || null;
    toast(locationToast(result.active_location));
    await refreshAll();
  } catch (error) {
    toast(readableError(error));
  }
}

async function submitChat(event) {
  event.preventDefault();
  const text = $("#chat-input").value.trim();
  if (!text) return;
  appendMessage("user", text);
  const imageFile = $("#chat-image").files[0];
  if (imageFile) await uploadAndAnalyzeImage(imageFile, "chat");
  const assistant = appendMessage("assistant", "");
  $("#chat-route").textContent = "routing";
  $("#chat-model-runs").textContent = "0";
  $("#chat-source-count").textContent = "0";
  $("#guidance-card").textContent = "Waiting for GAIA...";
  try {
    await streamChat(text, assistant);
    $("#chat-input").value = "";
    $("#chat-image").value = "";
  } catch (error) {
    assistant.textContent = readableError(error);
    $("#chat-route").textContent = "error";
  }
}

async function streamChat(message, node) {
  const response = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      location_id: activeLocationId(),
      user_plant_id: state.selectedPlantId,
      conversation_id: state.lastConversationId,
    }),
  });
  if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) handleStreamEvent(part, node);
  }
  if (buffer.trim()) handleStreamEvent(buffer, node);
}

function handleStreamEvent(raw, node) {
  const dataLine = raw.split("\n").find((line) => line.startsWith("data: "));
  if (!dataLine) return;
  const event = JSON.parse(dataLine.slice(6));
  if (event.event === "route") {
    $("#chat-route").textContent = event.route;
    $("#chat-model-runs").textContent = String(event.model_run_count);
  }
  if (event.event === "token") {
    node.textContent += event.text;
  }
  if (event.event === "final") {
    const result = event.data;
    state.lastConversationId = result.conversation_id;
    $("#chat-route").textContent = result.route;
    $("#chat-model-runs").textContent = String(result.model_run_count);
    const sourceIds = result.source_record_ids || result.context_bundle?.source_record_ids || [];
    $("#chat-source-count").textContent = String(sourceIds.length);
    renderGuidance(result);
    renderSourceChips(sourceIds);
    refreshAll();
  }
}

async function submitPlant(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  try {
    const result = await api("/api/v1/plants", {
      method: "POST",
      body: {
        taxon: data.get("taxon"),
        nickname: data.get("nickname"),
        cultivar: data.get("cultivar"),
        location_id: activeLocationId(),
        lifecycle_stage: "vegetative",
      },
    });
    state.selectedPlantId = result.plant?.id;
    toast("Plant created.");
    await refreshAll();
  } catch (error) {
    toast(readableError(error));
  }
}

async function submitObservation(event) {
  event.preventDefault();
  if (!state.selectedPlantId) return toast("Select a plant first.");
  const data = new FormData(event.currentTarget);
  try {
    await api(`/api/v1/plants/${state.selectedPlantId}/observations`, {
      method: "POST",
      body: { text: data.get("text"), observed_facts: [{ label: data.get("text"), source: "manual alpha" }] },
    });
    toast("Observation added.");
    await renderSelectedPlant();
  } catch (error) {
    toast(readableError(error));
  }
}

async function runVision() {
  const file = $("#vision-file").files[0] || $("#chat-image").files[0];
  if (!file) return toast("Choose an image.");
  await uploadAndAnalyzeImage(file, "vision");
}

async function uploadAndAnalyzeImage(file, origin) {
  if (!state.selectedPlantId) return toast("Select a plant first.");
  const imageBase64 = await fileToBase64(file);
  $("#vision-status").textContent = "uploading";
  const media = await api("/api/v1/vision/media", {
    method: "POST",
    body: {
      image_base64: imageBase64,
      content_type: file.type || "image/jpeg",
      user_plant_id: state.selectedPlantId,
    },
  });
  state.lastMediaId = media.id;
  $("#vision-status").textContent = "analyzing";
  const analysis = await api("/api/v1/vision/analyze", {
    method: "POST",
    body: {
      media_attachment_id: media.id,
      user_plant_id: state.selectedPlantId,
      location_id: activeLocationId(),
    },
  });
  renderVision(analysis);
  if (origin === "chat") appendMessage("assistant", `Image analysis status: ${analysis.provider_status}`);
  await renderSelectedPlant();
}

function seedSeasonDateDefaults() {
  const startInput = document.querySelector("#season-form input[name='start']");
  const endInput = document.querySelector("#season-form input[name='end']");
  if (!startInput || !endInput) return;
  const today = new Date();
  const end = new Date(today);
  end.setDate(end.getDate() + 90);
  const iso = (value) => value.toISOString().slice(0, 10);
  if (!startInput.value) startInput.value = iso(today);
  if (!endInput.value) endInput.value = iso(end);
}

async function submitSeason(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  try {
    const result = await api("/api/v1/season/plan", {
      method: "POST",
      body: {
        crop_names: String(data.get("crops")).split(",").map((item) => item.trim()).filter(Boolean),
        objective: data.get("goal"),
        start_date: data.get("start") || null,
        end_date: data.get("end") || null,
        location_id: activeLocationId(),
        include_mercator: true,
      },
    });
    state.lastSeasonPlanId = result.season_plan.id;
    renderSeason(result);
    toast("Season Plan created.");
    await refreshAll();
  } catch (error) {
    toast(readableError(error));
  }
}

async function previewCalendar() {
  if (!state.lastSeasonPlanId) {
    const plans = state.system?.persistence?.season_plan_count ? await api("/api/v1/season/plans") : { season_plans: [] };
    state.lastSeasonPlanId = plans.season_plans?.[0]?.id;
  }
  if (!state.lastSeasonPlanId) return toast("Create a Season Plan first.");
  try {
    const preview = await api("/api/v1/calendar/preview", { method: "POST", body: { season_plan_id: state.lastSeasonPlanId } });
    $("#season-output").textContent = JSON.stringify(preview, null, 2);
    $("#calendar-state").textContent = "Preview ready - external writes: 0";
  } catch (error) {
    $("#calendar-state").textContent = "Google Calendar - Not connected";
    toast(readableError(error));
  }
}

async function submitResearchSearch(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  try {
    const result = await api("/api/v1/research/search", { method: "POST", body: { query: data.get("query"), limit: 5 } });
    renderResearchSearch(result);
  } catch (error) {
    toast(readableError(error));
  }
}

async function synthesizeResearch() {
  const query = $("#research-form input[name='query']").value;
  try {
    const result = await api("/api/v1/research/synthesize", { method: "POST", body: { question: query, use_model: false } });
    renderResearchSynthesis(result);
  } catch (error) {
    toast(readableError(error));
  }
}

async function submitMovement(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  try {
    const result = await api("/api/v1/movement/check", {
      method: "POST",
      body: {
        species: data.get("species"),
        origin_alias: data.get("origin"),
        destination_alias: data.get("destination"),
        plant_part: data.get("plantPart"),
        live_plant: data.get("livePlant") === "on",
        soil_attached: data.get("soilAttached") === "on",
        purpose: data.get("purpose"),
      },
    });
    renderMovement(result);
  } catch (error) {
    toast(readableError(error));
  }
}

async function submitMarkets(event) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  try {
    const result = await api("/api/v1/markets/context", { method: "POST", body: { commodity: data.get("commodity"), location_id: activeLocationId() } });
    renderMarkets(result);
  } catch (error) {
    toast(readableError(error));
  }
}

function renderStatus() {
  $("#identity-label").textContent = state.identity?.label || "Development Identity";
  $("#sidebar-spend").textContent = `$${Number(state.system?.cost?.total_development_cash_spent || 0).toFixed(2)}`;
  $("#sidebar-db").textContent = state.status?.database || "SQLite";
  $("#sidebar-model").textContent = state.status?.text_model || "unknown";
}

function renderLocations() {
  const select = $("#location-select");
  const locations = state.locations?.locations || [];
  const active = state.locations?.active_location;
  select.innerHTML = `<option value="">Saved locations</option>`;
  for (const location of locations) {
    const option = document.createElement("option");
    option.value = location.id;
    option.textContent = `${locationLabel(location)} - ${locationKindLabel(location.source_kind)}`;
    option.selected = location.id === state.activeLocationId;
    select.appendChild(option);
  }
  select.classList.toggle("hidden", locations.length === 0);
  select.title = active
    ? `${active.source_kind}: ${active.admin2 || active.label}`
    : "No active location. Use browser location, enter a location, or select a saved real location.";

  if (!active) {
    $("#location-primary").textContent = "Location required";
    $("#location-secondary").textContent = "Use current location or enter location manually.";
    $("#location-accuracy").textContent = "";
    return;
  }
  $("#location-primary").textContent = locationLabel(active);
  $("#location-secondary").textContent = locationKindLabel(active.source_kind);
  $("#location-accuracy").textContent = active.accuracy_m ? `Accuracy: ~${formatMeters(active.accuracy_m)} m` : "";
}

function renderPlants() {
  $("#plant-count").textContent = String(state.plants.length);
  const select = $("#plant-select");
  select.innerHTML = "";
  for (const plant of state.plants) {
    const option = document.createElement("option");
    option.value = plant.id;
    option.textContent = plant.nickname;
    option.selected = plant.id === state.selectedPlantId;
    select.appendChild(option);
  }
  $("#plant-list").innerHTML = state.plants.map((plant) => plantCard(plant)).join("") || `<div class="empty">No plants.</div>`;
  $$(".plant-card").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedPlantId = button.dataset.id;
      renderPlants();
      renderSelectedPlant();
    });
  });
}

async function renderSelectedPlant() {
  const plantId = state.selectedPlantId;
  if (!plantId) {
    $("#plant-detail").innerHTML = `<div class="empty">No plant selected.</div>`;
    $("#observation-list").innerHTML = "";
    return;
  }
  try {
    const detail = await api(`/api/v1/plants/${plantId}`);
    const observations = await api(`/api/v1/plants/${plantId}/observations`);
    $("#plant-detail").innerHTML = plantDetail(detail);
    $("#observation-list").innerHTML = observations.map((item) => timelineItem(item.observed_at, item.text)).join("") || `<div class="empty">No observations.</div>`;
  } catch (error) {
    $("#plant-detail").innerHTML = `<div class="empty">${readableError(error)}</div>`;
  }
}

function renderGuidance(result) {
  if (result.route === "environment" && result.structured_response?.type === "environment_report") {
    $("#guidance-card").innerHTML = environmentCard(result.structured_response);
    return;
  }
  if (result.guidance_plan_id) {
    $("#guidance-card").innerHTML = `<strong>Saved GuidancePlan</strong><span>${result.guidance_plan_id}</span><p>${escapeHtml(result.content)}</p>`;
  } else {
    $("#guidance-card").textContent = result.validation_error || result.content || "No GuidancePlan persisted.";
  }
}

async function renderSourceChips(sourceIds) {
  const box = $("#chat-sources");
  if (!sourceIds.length) {
    box.innerHTML = "";
    return;
  }
  try {
    const payload = await api(`/api/v1/source-records?ids=${encodeURIComponent(sourceIds.join(","))}`);
    box.innerHTML = payload.source_records.map((source) => `<span>${escapeHtml(source.provider)}: ${escapeHtml(source.title || source.authority || "source")}</span>`).join("");
  } catch {
    box.innerHTML = sourceIds.map((id) => `<span>${escapeHtml(id)}</span>`).join("");
  }
}

function renderVision(result) {
  const analysis = result.visual_analysis || {};
  $("#vision-status").textContent = `${analysis.status || result.provider_status || "unknown"} - ${analysis.provider || "provider"}`;
  $("#vision-observations").innerHTML = (analysis.visual_observations || []).map((item) => `<li>${escapeHtml(item.label)} <span>${escapeHtml(item.description || "")}</span></li>`).join("");
  $("#vision-hypotheses").innerHTML = (analysis.visual_hypotheses || []).map((item) => `<li>${escapeHtml(item.label)} <span>${escapeHtml(item.status || "hypothesis")}</span></li>`).join("");
  $("#vision-output").textContent = JSON.stringify(result, null, 2);
}

function renderSeason(result) {
  const plan = result.season_plan || {};
  state.lastSeasonPlanId = plan.id || state.lastSeasonPlanId;
  $("#season-timeline").innerHTML = (result.actions || []).map((action) => timelineItem(action.preferred_at || action.earliest_at || "scheduled", action.title)).join("");
  $("#season-output").textContent = JSON.stringify(result, null, 2);
  $("#calendar-state").textContent = "Google Calendar - Not connected";
}

function renderResearchSearch(result) {
  const providerStatuses = result.provider_statuses || [];
  const works = result.works || [];
  $("#research-quality").innerHTML = providerStatuses.map((item) => `<span>${escapeHtml(item)}</span>`).join("");
  $("#research-results").innerHTML = works.map((work) => sourceCard(work.title, `${work.journal || "unknown journal"} ${work.publication_year || ""}`, work.study_type || "unknown")).join("");
  $("#research-output").textContent = JSON.stringify(result, null, 2);
}

function renderResearchSynthesis(result) {
  $("#research-quality").innerHTML = `<span>${escapeHtml(result.evidence_quality || "unknown")}</span><span>${escapeHtml(result.model_confidence || "not_model_generated")}</span>`;
  $("#research-results").innerHTML = [
    ...((result.supporting_claims || []).map((claim) => sourceCard(claim.statement, "supporting", claim.evidence_quality))),
    ...((result.contradictory_claims || []).map((claim) => sourceCard(claim.statement, "contradictory", claim.evidence_quality))),
  ].join("");
  $("#research-output").textContent = JSON.stringify(result, null, 2);
}

function renderMovement(result) {
  $("#movement-status").textContent = result.status || "UNRESOLVED";
  $("#movement-status").dataset.status = result.status || "UNRESOLVED";
  $("#movement-rules").innerHTML = (result.applicable_rules || []).map((rule) => sourceCard(rule.rule_id, rule.authority, rule.jurisdiction_pack)).join("") || `<div class="empty">No applicable rules.</div>`;
  $("#movement-output").textContent = JSON.stringify(result, null, 2);
}

function renderMarkets(result) {
  const dates = result.data_dates || {};
  $("#market-metrics").innerHTML = [
    metric("Commodity", result.commodity?.canonical_name || "unknown"),
    metric("Production", (dates.production || []).join(", ") || "unavailable"),
    metric("Markets", (dates.markets || []).join(", ") || "unavailable"),
    metric("Freshness", result.freshness?.markets || "unavailable"),
  ].join("");
  $("#markets-output").textContent = JSON.stringify(result, null, 2);
}

function renderSystem() {
  const status = state.system || {};
  const active = state.locations?.active_location;
  const automaticPaidUsage = status.cost?.automatic_paid_usage_enabled ? "ON" : "OFF";
  $("#system-list").innerHTML = [
    metricRow("UI", status.ui_url),
    metricRow("API", status.api_url),
    metricRow("Database", status.database),
    metricRow("Text model", status.text_model),
    metricRow("Vision model", status.vision_model),
    metricRow("Automatic paid usage", automaticPaidUsage),
    metricRow("Spend", `$${Number(status.cost?.total_development_cash_spent || 0).toFixed(2)}`),
    metricRow("Reserve", `$${Number(status.cost?.reserve_remaining || 20).toFixed(2)}`),
    metricRow("Telemetry", status.telemetry),
    metricRow("Active location", active ? `${active.label} (${active.source_kind})` : "none"),
    metricRow("Git", status.git_commit),
  ].join("");
  $("#provider-list").innerHTML = (status.providers || []).map((provider) => sourceCard(provider.provider_id, provider.enabled ? provider.mode : "disabled", provider.billing_class)).join("");
  $("#persistence-list").innerHTML = Object.entries(status.persistence || {}).map(([key, value]) => metricRow(key, value)).join("");
}

function appendMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.textContent = text;
  $("#messages").appendChild(node);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return node;
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: { ...(options.headers || {}) } };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) throw new Error(payload.message || payload.status || `HTTP ${response.status}`);
  return payload;
}

function previewVisionFile() {
  const file = $("#vision-file").files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    $("#image-preview").innerHTML = `<img src="${reader.result}" alt="Selected plant" />`;
  };
  reader.readAsDataURL(file);
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function plantCard(plant) {
  const active = plant.id === state.selectedPlantId ? " active" : "";
  return `<button class="plant-card${active}" data-id="${plant.id}" type="button"><strong>${escapeHtml(plant.nickname)}</strong><span>${escapeHtml(plant.cultivar || plant.lifecycle_stage || "plant")}</span></button>`;
}

function plantDetail(detail) {
  const plant = detail.plant || {};
  const entity = detail.plant_entity || {};
  const profile = detail.plant_profile || {};
  return `
    <dl class="metric-list">
      ${metricRow("Nickname", plant.nickname)}
      ${metricRow("Scientific name", entity.scientific_name)}
      ${metricRow("Cultivar", plant.cultivar || "unknown")}
      ${metricRow("Stage", plant.lifecycle_stage || "unknown")}
      ${metricRow("Status", plant.status)}
      ${metricRow("Profile completeness", profile.completeness ?? "unknown")}
    </dl>
  `;
}

function timelineItem(date, text) {
  return `<div class="timeline-item"><strong>${escapeHtml(date || "undated")}</strong><span>${escapeHtml(text || "")}</span></div>`;
}

function sourceCard(title, meta, badge) {
  return `<article class="source-card"><strong>${escapeHtml(title || "Untitled")}</strong><span>${escapeHtml(meta || "")}</span><em>${escapeHtml(badge || "")}</em></article>`;
}

function environmentCard(report) {
  const location = report.location?.label || "Current location";
  return `
    <article class="environment-card">
      <strong>${escapeHtml(location)}</strong>
      <div class="metric-grid">
        ${metric("Temperature", measurementValue(report.temperature))}
        ${metric("Rain chance", measurementValue(report.precipitation_probability))}
        ${metric("Wind", windValue(report.wind))}
        ${metric("Daylight", daylightValue(report.photoperiod))}
      </div>
      <dl class="metric-list">
        ${metricRow("Humidity", measurementValue(report.humidity))}
        ${metricRow("Soil moisture", contextValue(report.soil_moisture_context))}
        ${metricRow("Solar radiation", measurementValue(report.solar_radiation))}
        ${metricRow("Water context", contextValue(report.water_context))}
      </dl>
    </article>
  `;
}

function metric(label, value) {
  return `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function metricRow(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? "unknown")}</dd></div>`;
}

function activeLocationId() {
  return state.activeLocationId || null;
}

function locationLabel(location) {
  const county = location?.admin2 || location?.label || "Location";
  const state = stateName(location?.admin1);
  return state ? `${county}, ${state}` : county;
}

function stateName(code) {
  return {
    CA: "California",
    FL: "Florida",
    GA: "Georgia",
    TX: "Texas",
  }[String(code || "").toUpperCase()] || "";
}

function locationKindLabel(sourceKind) {
  if (sourceKind === "device") return "Device location";
  if (sourceKind === "manual") return "Manual location";
  if (sourceKind === "demo_fixture") return "Demo fixture location";
  return "Saved location";
}

function formatMeters(value) {
  const meters = Number(value);
  if (!Number.isFinite(meters)) return "";
  return String(Math.round(meters));
}

function locationToast(location) {
  if (!location) return "No active location selected.";
  return `${locationKindLabel(location.source_kind)} active: ${locationLabel(location)}.`;
}

function measurementValue(measurement) {
  if (!measurement || measurement.status !== "available") return "unavailable";
  return `${measurement.value}${measurement.unit ? ` ${measurement.unit}` : ""}`;
}

function windValue(wind) {
  if (!wind || wind.status !== "available") return "unavailable";
  if (wind.direction && wind.speed) return `${wind.direction} at ${wind.speed}`;
  return wind.speed || wind.direction || "unavailable";
}

function daylightValue(measurement) {
  const value = measurementValue(measurement);
  return value === "unavailable" ? value : `${value} daylight`;
}

function contextValue(context) {
  if (!context || context.status !== "available") return "unavailable";
  return context.map_unit || context.summary || context.semantic_note || "available";
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 3200);
}

function readableError(error) {
  const text = String(error.message || error);
  if (text.includes("provider")) return `Provider unavailable: ${text}`;
  if (text.includes("denied")) return `Policy denied the request: ${text}`;
  if (text.includes("calendar")) return `Calendar disconnected: ${text}`;
  if (text.includes("image")) return `Invalid image: ${text}`;
  return text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
