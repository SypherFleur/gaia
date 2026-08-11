const form = document.querySelector(".composer");
const input = form.querySelector("input");
const messages = document.querySelector(".messages");
const route = document.querySelector("#route");
const modelRuns = document.querySelector("#model-runs");
const sources = document.querySelector("#sources");
const providers = document.querySelector("#providers");

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
