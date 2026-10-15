import { readFile } from "node:fs/promises";
import { basename } from "node:path";

import { upload } from "@vercel/blob/client";

const [videoPath, baseUrl = "http://127.0.0.1:3100", durationValue = "60"] = process.argv.slice(2);
if (!videoPath) throw new Error("Usage: node scripts/smoke-analysis.mjs <video-path> [base-url] [duration-seconds]");

const durationSeconds = Number(durationValue);
const bytes = await readFile(videoPath);
const file = new File([bytes], basename(videoPath), { type: "video/mp4" });
const blob = await upload(`bridge/smoke/${crypto.randomUUID()}-${file.name}`, file, {
  access: "private",
  handleUploadUrl: `${baseUrl}/api/upload`,
  contentType: file.type,
  multipart: true,
  clientPayload: JSON.stringify({ contentType: file.type, size: file.size, durationSeconds }),
});
if (process.env.BRIDGE_UPLOAD_ONLY === "1") {
  console.log(JSON.stringify({ blobUrl: blob.url }));
  process.exit(0);
}
const response = await fetch(`${baseUrl}/api/analyze`, {
  method: "POST",
  headers: {
    "content-type": "application/json",
    origin: baseUrl,
    "x-forwarded-for": "203.0.113.77",
  },
  body: JSON.stringify({
    blobUrl: blob.url,
    durationSeconds,
    outputLanguage: "English",
    caption: null,
    context: "Licensed Big Buck Bunny connectivity smoke test.",
  }),
});
const body = await response.json();
console.log(JSON.stringify({
  status: response.status,
  code: body.code ?? null,
  message: body.message ?? null,
  analysisStatus: body.status ?? null,
  model: body.result?.model_id ?? null,
  transcriptSegments: body.result?.content?.transcript?.length ?? null,
  evidenceItems: body.result?.content?.evidence?.length ?? null,
  interpretations: body.result?.content?.interpretations?.length ?? null,
  totalTokens: body.result?.usage?.total_tokens ?? null,
}, null, 2));

if (!response.ok) process.exitCode = 1;
