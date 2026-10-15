import assert from "node:assert/strict";

import worker from "../worker/index.js";

const env = { GEMINI_API_KEY: "test-only", GEMINI_MODEL: "gemini-test" };

async function request(path, init = {}, runtimeEnv = env) {
  return worker.fetch(new Request(`https://bridge.test${path}`, init), runtimeEnv);
}

function formRequest(file, duration = "30", ip = "203.0.113.1") {
  const body = new FormData();
  if (file) body.set("video", file);
  body.set("duration_seconds", duration);
  body.set("output_language", "English");
  return {
    method: "POST",
    headers: { "cf-connecting-ip": ip, "sec-fetch-site": "same-origin" },
    body,
  };
}

const health = await request("/api/health", {}, {});
assert.equal(health.status, 200);
assert.deepEqual(await health.json(), {
  status: "ok",
  configured: false,
  model: "gemini-3.8-flash",
});

const home = await request("/");
assert.equal(home.status, 200);
assert.match(home.headers.get("content-security-policy"), /default-src 'self'/);
assert.match(await home.text(), /No evaluation results yet/);

const missing = await request("/api/analyze", formRequest(null, "30", "203.0.113.2"));
assert.equal(missing.status, 400);
assert.equal((await missing.json()).code, "VIDEO_REQUIRED");

const textFile = new File(["not a video"], "clip.txt", { type: "text/plain" });
const unsupported = await request("/api/analyze", formRequest(textFile, "30", "203.0.113.3"));
assert.equal(unsupported.status, 415);
assert.equal((await unsupported.json()).code, "UNSUPPORTED_MEDIA");

const fakeMp4 = new File([new Uint8Array([0, 0, 0, 20, 0x66, 0x74, 0x79, 0x70, 0, 0, 0, 0])], "clip.mp4", { type: "video/mp4" });
const duration = await request("/api/analyze", formRequest(fakeMp4, "121", "203.0.113.4"));
assert.equal(duration.status, 422);
assert.equal((await duration.json()).code, "INVALID_DURATION");

const crossSite = await request("/api/analyze", {
  ...formRequest(fakeMp4, "30", "203.0.113.5"),
  headers: { "cf-connecting-ip": "203.0.113.5", "sec-fetch-site": "cross-site" },
});
assert.equal(crossSite.status, 403);
assert.equal((await crossSite.json()).code, "CROSS_SITE_REQUEST");

const unconfigured = await request("/api/analyze", formRequest(fakeMp4, "30", "203.0.113.6"), {});
assert.equal(unconfigured.status, 503);
assert.equal((await unconfigured.json()).code, "AI_NOT_CONFIGURED");

console.log("Worker contracts passed");
