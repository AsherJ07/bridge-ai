const key = process.env.GEMINI_API_KEY;
if (!key) throw new Error("GEMINI_API_KEY is required.");

const response = await fetch("https://generativelanguage.googleapis.com/v1beta/models?pageSize=100", {
  headers: { "x-goog-api-key": key },
});
const body = await response.json();
console.log(JSON.stringify({
  status: response.status,
  models: (body.models || [])
    .filter((model) => (model.supportedGenerationMethods || []).includes("generateContent"))
    .map((model) => model.name),
}, null, 2));

if (!response.ok) process.exitCode = 1;
