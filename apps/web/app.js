const form = document.querySelector(".composer");
const input = form.querySelector("input");
const messages = document.querySelector(".messages");
const route = document.querySelector("#route");
const modelRuns = document.querySelector("#model-runs");
const sources = document.querySelector("#sources");
const providers = document.querySelector("#providers");
const plantList = document.querySelector("#plant-list");
const plantForm = document.querySelector("#plant-form");
const selectedPlantName = document.querySelector("#selected-plant-name");
const detailName = document.querySelector("#detail-name");
const detailSpecies = document.querySelector("#detail-species");
const detailStage = document.querySelector("#detail-stage");
const detailProfile = document.querySelector("#detail-profile");
const observations = document.querySelector("#observations");
const germplasmForm = document.querySelector("#germplasm-form");
const germplasm = document.querySelector("#germplasm");
const visionDemo = document.querySelector("#vision-demo");
const visionStatus = document.querySelector("#vision-status");
const visionProvider = document.querySelector("#vision-provider");
const visionOutput = document.querySelector("#vision-output");
const evidenceDemo = document.querySelector("#evidence-demo");
const evidenceOutput = document.querySelector("#evidence-output");

const plants = [
  {
    id: "plant-demo-tomato",
    nickname: "Patio tomato",
    species: "Solanum lycopersicum",
    cultivar: "Cherokee Purple",
    lifecycle_stage: "vegetative",
    location: "Austin garden",
    profile: "taxonomy source-backed; cultivation traits mostly unknown",
    source_count: 3,
    observations: ["Three lower leaves have yellow margins."],
    vision: {
      status: "AVAILABLE",
      provider: "fixture-vision-local",
      observations: ["visible yellowing", "brown circular lesions"],
      hypotheses: [
        {
          label: "early blight",
          status: "hypothesis",
          confidence: 0.46,
          required_next_evidence: ["underside of affected leaf", "close-up of lesion margins"],
        },
      ],
      safety_note: "Vision output is visual evidence, not a confirmed diagnosis.",
    },
    evidence: {
      question: "What does research say about calcium sprays for blossom-end rot?",
      evidence_quality: "mixed",
      source_cards: [
        {
          title: "Blossom-end rot of tomato: calcium transport, water stress, and management",
          authors: "Doe J",
          journal: "Horticultural Reviews",
          year: 2019,
          doi: "10.1000/ber-review",
          study_type: "review",
          relevance: "species partial; intervention partial",
          why_used: "Review evidence reports inconsistent foliar calcium spray benefit.",
          retrieved_through: "Europe PMC",
          category: "Peer-reviewed",
        },
        {
          title: "Greenhouse calcium sprays in tomato under controlled humidity",
          authors: "Green G",
          journal: "Protected Horticulture",
          year: 2018,
          doi: null,
          study_type: "controlled experiment",
          relevance: "greenhouse growing-system mismatch",
          why_used: "Shows context limits for applying controlled greenhouse results outdoors.",
          retrieved_through: "Europe PMC",
          category: "Experimental",
        },
      ],
    },
  },
];

let selectedPlant = plants[0];

const demoResponses = [
  {
    match: "county",
    route: "geography",
    model_run_count: 0,
    content: "Your selected location resolves to Travis County, Texas, United States.",
    sources: 4,
    providers: { atlas: { geography: "AVAILABLE", watershed: "AVAILABLE", hardiness: "AVAILABLE" } },
  },
  {
    match: "environment",
    route: "environment",
    model_run_count: 0,
    content: "For Travis County, GAIA has environmental context. Temperature context: 18.3 C (FORECAST). Soil context: Austin urban land complex.",
    sources: 8,
    providers: { terra: { nws: "AVAILABLE", nasa_power: "AVAILABLE", soil: "AVAILABLE", water: "AVAILABLE" } },
  },
  {
    match: "image",
    route: "vision",
    model_run_count: 0,
    content: "The image route stores visible observations separately from cautious hypotheses. It does not persist a confirmed diagnosis.",
    sources: 1,
    providers: { vision: { "fixture-vision-local": "AVAILABLE" } },
  },
  {
    match: "tomato",
    route: "reasoning",
    model_run_count: 1,
    content: "Tomato planting considerations: Wait for a warm, stable window before planting tomatoes.\nAction: Check nighttime lows before transplanting\nConfidence: medium",
    sources: 8,
    providers: { model: { provider_id: "ollama-local", model: "llama3.1:latest" } },
  },
];

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  appendMessage("user", text);
  const response = selectDemoResponse(text);
  route.textContent = "routing";
  const assistant = appendMessage("assistant", "");
  await streamText(assistant, response.content);
  route.textContent = response.route;
  modelRuns.textContent = String(response.model_run_count);
  sources.textContent = String(response.sources);
  providers.textContent = JSON.stringify(response.providers, null, 2);
});

plantForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(plantForm);
  const plant = {
    id: `plant-${Date.now()}`,
    nickname: data.get("nickname"),
    species: data.get("taxon"),
    cultivar: data.get("cultivar"),
    lifecycle_stage: "unknown",
    location: "Austin garden",
    profile: "pending taxonomy confirmation",
    source_count: 0,
    observations: [],
    vision: null,
  };
  plants.unshift(plant);
  selectPlant(plant);
  renderPlants();
});

germplasmForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = new FormData(germplasmForm).get("query");
  germplasm.textContent = JSON.stringify(
    {
      query,
      accessions: [
        {
          accession_number: "TVu-12345",
          taxon: "Vigna unguiculata",
          institute: "IITA Genetic Resources Center fixture",
          origin: "Nigeria",
          traits: query.toLowerCase().includes("heat") ? ["heat tolerance"] : [],
          caveat: "Availability, legal movement, cost, import eligibility, and suitability are not verified.",
        },
      ],
    },
    null,
    2,
  );
});

visionDemo.addEventListener("click", () => {
  const fallback = {
    status: "UNAVAILABLE",
    provider: "fixture-vision-local",
    observations: [],
    hypotheses: [],
    safety_note: "No image evidence has been attached for this plant.",
  };
  const analysis = selectedPlant.vision || fallback;
  visionStatus.textContent = analysis.status;
  visionProvider.textContent = analysis.provider;
  visionOutput.textContent = JSON.stringify(analysis, null, 2);
  providers.textContent = JSON.stringify({ vision: { [analysis.provider]: analysis.status } }, null, 2);
  modelRuns.textContent = "0";
});

evidenceDemo.addEventListener("click", () => {
  const evidence = selectedPlant.evidence || {
    question: "No research evidence loaded.",
    evidence_quality: "insufficient",
    source_cards: [],
  };
  evidenceOutput.textContent = JSON.stringify(evidence, null, 2);
  providers.textContent = JSON.stringify({ scholar: { "europe-pmc": "AVAILABLE" } }, null, 2);
});

function selectDemoResponse(text) {
  const lower = text.toLowerCase();
  return demoResponses.find((item) => lower.includes(item.match)) || demoResponses[3];
}

function appendMessage(role, text) {
  const node = document.createElement("article");
  node.className = `message ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

async function streamText(node, text) {
  node.textContent = "";
  for (let index = 0; index < text.length; index += 16) {
    node.textContent += text.slice(index, index + 16);
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}

function renderPlants() {
  plantList.innerHTML = "";
  for (const plant of plants) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "plant-card";
    button.innerHTML = `<strong>${plant.nickname}</strong><span>${plant.species}${plant.cultivar ? ` - ${plant.cultivar}` : ""}</span>`;
    button.addEventListener("click", () => selectPlant(plant));
    plantList.appendChild(button);
  }
}

function selectPlant(plant) {
  selectedPlant = plant;
  selectedPlantName.textContent = plant.nickname;
  detailName.textContent = plant.nickname;
  detailSpecies.textContent = `${plant.species}${plant.cultivar ? ` - ${plant.cultivar}` : ""}`;
  detailStage.textContent = plant.lifecycle_stage;
  detailProfile.textContent = plant.profile;
  sources.textContent = String(plant.source_count);
  observations.innerHTML = "";
  for (const observation of plant.observations) {
    const item = document.createElement("li");
    item.textContent = observation;
    observations.appendChild(item);
  }
  visionStatus.textContent = plant.vision?.status || "idle";
  visionProvider.textContent = plant.vision?.provider || "none";
  visionOutput.textContent = JSON.stringify(plant.vision || {}, null, 2);
  evidenceOutput.textContent = JSON.stringify(plant.evidence || {}, null, 2);
}

renderPlants();
selectPlant(selectedPlant);
