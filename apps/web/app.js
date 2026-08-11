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

function selectDemoResponse(text) {
  const lower = text.toLowerCase();
  return demoResponses.find((item) => lower.includes(item.match)) || demoResponses[2];
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
    button.innerHTML = `<strong>${plant.nickname}</strong><span>${plant.species}${plant.cultivar ? ` · ${plant.cultivar}` : ""}</span>`;
    button.addEventListener("click", () => selectPlant(plant));
    plantList.appendChild(button);
  }
}

function selectPlant(plant) {
  selectedPlant = plant;
  selectedPlantName.textContent = plant.nickname;
  detailName.textContent = plant.nickname;
  detailSpecies.textContent = `${plant.species}${plant.cultivar ? ` · ${plant.cultivar}` : ""}`;
  detailStage.textContent = plant.lifecycle_stage;
  detailProfile.textContent = plant.profile;
  sources.textContent = String(plant.source_count);
  observations.innerHTML = "";
  for (const observation of plant.observations) {
    const item = document.createElement("li");
    item.textContent = observation;
    observations.appendChild(item);
  }
}

renderPlants();
selectPlant(selectedPlant);
