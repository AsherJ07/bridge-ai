import "server-only";

import { del, get } from "@vercel/blob";
import { z } from "zod";

const MAX_BYTES = 100 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["video/mp4", "video/quicktime", "video/webm"]);
const GEMINI_BASE = "https://generativelanguage.googleapis.com";

export class PublicAnalysisError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export const analyzeRequestSchema = z.object({
  blobUrl: z.string().url(),
  durationSeconds: z.number().positive().max(120),
  outputLanguage: z.enum(["English", "Urdu", "Hindi", "Spanish"]),
  caption: z.string().max(500).nullable().optional(),
  context: z.string().max(1000).nullable().optional(),
});

const transcriptSchema = z.object({
  id: z.string().min(1),
  start_seconds: z.number().nonnegative(),
  end_seconds: z.number().nonnegative(),
  spoken_text: z.string(),
  translated_text: z.string().nullable(),
});
const evidenceSchema = z.object({
  id: z.string().min(1),
  kind: z.enum(["transcript", "visual", "audio", "user_context"]),
  start_seconds: z.number().nonnegative().nullable(),
  end_seconds: z.number().nonnegative().nullable(),
  excerpt: z.string().nullable(),
  description: z.string(),
});
const interpretationSchema = z.object({
  id: z.string().min(1),
  claim: z.string(),
  literal_translation: z.string().nullable(),
  cultural_context: z.string(),
  support_status: z.enum(["supported", "partial", "uncertain"]),
  evidence_ids: z.array(z.string()),
  caveat: z.string().nullable(),
});
const contentSchema = z.object({
  overview: z.string(),
  detected_languages: z.array(z.string()),
  transcript: z.array(transcriptSchema),
  evidence: z.array(evidenceSchema),
  interpretations: z.array(interpretationSchema),
  tone_and_humor: z.array(z.string()),
  ambiguities: z.array(z.string()),
});

const responseJsonSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    overview: { type: "string" },
    detected_languages: { type: "array", items: { type: "string" } },
    transcript: { type: "array", items: { type: "object", additionalProperties: false, properties: {
      id: { type: "string" }, start_seconds: { type: "number" }, end_seconds: { type: "number" },
      spoken_text: { type: "string" }, translated_text: { type: ["string", "null"] },
    }, required: ["id", "start_seconds", "end_seconds", "spoken_text", "translated_text"] } },
    evidence: { type: "array", items: { type: "object", additionalProperties: false, properties: {
      id: { type: "string" }, kind: { type: "string", enum: ["transcript", "visual", "audio", "user_context"] },
      start_seconds: { type: ["number", "null"] }, end_seconds: { type: ["number", "null"] },
      excerpt: { type: ["string", "null"] }, description: { type: "string" },
    }, required: ["id", "kind", "start_seconds", "end_seconds", "excerpt", "description"] } },
    interpretations: { type: "array", items: { type: "object", additionalProperties: false, properties: {
      id: { type: "string" }, claim: { type: "string" }, literal_translation: { type: ["string", "null"] },
      cultural_context: { type: "string" }, support_status: { type: "string", enum: ["supported", "partial", "uncertain"] },
      evidence_ids: { type: "array", items: { type: "string" } }, caveat: { type: ["string", "null"] },
    }, required: ["id", "claim", "literal_translation", "cultural_context", "support_status", "evidence_ids", "caveat"] } },
    tone_and_humor: { type: "array", items: { type: "string" } },
    ambiguities: { type: "array", items: { type: "string" } },
  },
  required: ["overview", "detected_languages", "transcript", "evidence", "interpretations", "tone_and_humor", "ambiguities"],
} as const;

interface GeminiFile { name?: string; uri?: string; state?: string }

function providerMimeType(contentType: string): string {
  return contentType === "video/quicktime" ? "video/mov" : contentType;
}

function sanitizeProviderMessage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  return value.replace(/AIza[\w-]+/g, "[redacted]").replace(/https?:\/\/\S+/g, "provider endpoint").slice(0, 280);
}

async function providerError(response: Response, step: string): Promise<never> {
  let detail: string | null = null;
  try {
    const body = await response.json() as { error?: { message?: unknown; status?: unknown } };
    detail = sanitizeProviderMessage(body.error?.message);
  } catch {
    // Provider errors are still categorized by HTTP status when no JSON body exists.
  }
  if (response.status === 429) throw new PublicAnalysisError(429, "GEMINI_RATE_LIMITED", "Gemini quota is exhausted or rate-limited. Check this key's active limits in Google AI Studio.");
  if (response.status === 401 || response.status === 403) throw new PublicAnalysisError(502, "GEMINI_ACCESS_DENIED", "Google rejected the configured API key or its access to this model.");
  if (response.status === 404) throw new PublicAnalysisError(502, "GEMINI_MODEL_NOT_FOUND", `The configured Gemini model is not available to this API project${detail ? `: ${detail}` : "."}`);
  if (response.status === 503) throw new PublicAnalysisError(503, "GEMINI_PROVIDER_BUSY", "Gemini is temporarily at capacity. Try again shortly.");
  if (response.status === 400) throw new PublicAnalysisError(502, "GEMINI_INVALID_REQUEST", `Gemini rejected the ${step} request${detail ? `: ${detail}` : "."}`);
  throw new PublicAnalysisError(502, "GEMINI_PROVIDER_ERROR", `Gemini failed during ${step}${detail ? `: ${detail}` : "."}`);
}

async function generateWithFallback(key: string, mimeType: string, fileUri: string, prompt: string): Promise<{ response: Response; model: string }> {
  const primary = process.env.GEMINI_MODEL || "gemini-3.8-flash";
  const fallbacks = (process.env.GEMINI_FALLBACK_MODELS || "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite")
    .split(",")
    .map((model) => model.trim())
    .filter(Boolean);
  const models = [...new Set([primary, ...fallbacks])];
  let lastResponse: Response | undefined;
  for (const model of models) {
    let response: Response;
    try {
      response = await providerFetch(`${GEMINI_BASE}/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
        method: "POST",
        headers: { "x-goog-api-key": key, "content-type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ file_data: { mime_type: mimeType, file_uri: fileUri } }, { text: prompt }] }],
          generationConfig: {
            responseMimeType: "application/json",
            responseJsonSchema,
          },
        }),
      }, model === primary && models.length > 1 ? 45_000 : 220_000);
    } catch (error) {
      if (model !== models.at(-1) && error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError")) continue;
      throw new PublicAnalysisError(504, "GEMINI_TIMEOUT", "Gemini took too long to complete this analysis. Try a shorter clip.");
    }
    if (response.ok) return { response, model };
    lastResponse = response;
    if (![429, 503].includes(response.status) || model === models.at(-1)) await providerError(response, "analysis");
  }
  if (lastResponse) await providerError(lastResponse, "analysis");
  throw new PublicAnalysisError(502, "GEMINI_PROVIDER_ERROR", "Gemini could not complete the analysis.");
}

async function providerFetch(url: string, init: RequestInit, timeout = 30_000): Promise<Response> {
  return fetch(url, { ...init, signal: AbortSignal.timeout(timeout) });
}

function validateMagic(bytes: Uint8Array): void {
  const isIso = bytes.length >= 12 && String.fromCharCode(...bytes.slice(4, 8)) === "ftyp";
  const isWebm = bytes.length >= 4 && bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3;
  if (!isIso && !isWebm) throw new PublicAnalysisError(415, "INVALID_MEDIA", "The uploaded content is not recognized as MP4, MOV, or WebM.");
}

async function replayableStream(stream: ReadableStream<Uint8Array>): Promise<ReadableStream<Uint8Array>> {
  const reader = stream.getReader();
  const captured: Uint8Array[] = [];
  let capturedBytes = 0;
  while (capturedBytes < 12) {
    const next = await reader.read();
    if (next.done) break;
    captured.push(next.value);
    capturedBytes += next.value.byteLength;
  }
  const prefix = new Uint8Array(capturedBytes);
  let offset = 0;
  for (const chunk of captured) { prefix.set(chunk, offset); offset += chunk.byteLength; }
  validateMagic(prefix);
  let index = 0;
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      if (index < captured.length) { controller.enqueue(captured[index++]); return; }
      const next = await reader.read();
      if (next.done) controller.close(); else controller.enqueue(next.value);
    },
    cancel(reason) { return reader.cancel(reason); },
  });
}

async function uploadToGemini(stream: ReadableStream<Uint8Array>, size: number, mimeType: string, key: string): Promise<GeminiFile> {
  const start = await providerFetch(`${GEMINI_BASE}/upload/v1beta/files`, {
    method: "POST",
    headers: {
      "x-goog-api-key": key,
      "content-type": "application/json",
      "x-goog-upload-protocol": "resumable",
      "x-goog-upload-command": "start",
      "x-goog-upload-header-content-length": String(size),
      "x-goog-upload-header-content-type": mimeType,
    },
    body: JSON.stringify({ file: { display_name: `bridge-${crypto.randomUUID()}` } }),
  });
  if (!start.ok) await providerError(start, "upload initialization");
  const uploadUrl = start.headers.get("x-goog-upload-url");
  if (!uploadUrl) throw new PublicAnalysisError(502, "GEMINI_UPLOAD_FAILED", "Gemini did not return an upload session.");

  const uploaded = await providerFetch(uploadUrl, {
    method: "POST",
    headers: {
      "content-length": String(size),
      "x-goog-upload-offset": "0",
      "x-goog-upload-command": "upload, finalize",
    },
    body: stream,
    // Node's fetch requires duplex when streaming a request body.
    duplex: "half",
  } as RequestInit & { duplex: "half" }, 180_000);
  if (!uploaded.ok) await providerError(uploaded, "video upload");
  const body = await uploaded.json() as { file?: GeminiFile };
  if (!body.file?.name || !body.file.uri) throw new PublicAnalysisError(502, "GEMINI_UPLOAD_FAILED", "Gemini returned incomplete file metadata.");
  return body.file;
}

async function waitForFile(file: GeminiFile, key: string): Promise<GeminiFile> {
  const deadline = Date.now() + 120_000;
  while (!file.state || file.state === "PROCESSING") {
    if (Date.now() >= deadline) throw new PublicAnalysisError(504, "GEMINI_FILE_TIMEOUT", "Gemini took too long to prepare this video.");
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    const response = await providerFetch(`${GEMINI_BASE}/v1beta/${file.name}`, { headers: { "x-goog-api-key": key } });
    if (!response.ok) await providerError(response, "file processing");
    file = await response.json() as GeminiFile;
  }
  if (file.state !== "ACTIVE" || !file.uri) throw new PublicAnalysisError(422, "GEMINI_FILE_REJECTED", "Gemini could not prepare this video.");
  return file;
}

function enforceRelationships(content: z.infer<typeof contentSchema>): void {
  const evidenceById = new Map(content.evidence.map((item) => [item.id, item]));
  for (const claim of content.interpretations) {
    if (claim.evidence_ids.some((id) => !evidenceById.has(id))) throw new Error("unknown evidence reference");
    if (claim.evidence_ids.length === 0 && claim.support_status !== "uncertain") throw new Error("unsupported positive claim");
    const onlyUserContext = claim.evidence_ids.length > 0
      && claim.evidence_ids.every((id) => evidenceById.get(id)?.kind === "user_context");
    if (onlyUserContext && claim.support_status !== "uncertain") {
      claim.support_status = "uncertain";
      claim.caveat = "This claim is based only on unverified user-provided context, so Bridge cannot treat it as supported evidence.";
    }
    if (claim.support_status === "uncertain" && !claim.caveat?.trim()) throw new Error("uncertain claim without caveat");
  }
}

export async function analyzeBlob(input: z.infer<typeof analyzeRequestSchema>) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new PublicAnalysisError(503, "AI_NOT_CONFIGURED", "Live analysis is not configured.");
  const blobUrl = new URL(input.blobUrl);
  if (!blobUrl.hostname.endsWith(".private.blob.vercel-storage.com") || !blobUrl.pathname.startsWith("/bridge/")) {
    throw new PublicAnalysisError(400, "INVALID_UPLOAD", "Use a video uploaded through this Bridge deployment.");
  }

  let remote: GeminiFile | undefined;
  try {
    const blob = await get(input.blobUrl, { access: "private" });
    if (!blob || blob.statusCode !== 200 || !blob.stream) throw new PublicAnalysisError(404, "UPLOAD_NOT_FOUND", "The temporary upload is no longer available.");
    const size = blob.blob.size;
    const contentType = blob.blob.contentType || "";
    if (!size || size > MAX_BYTES) throw new PublicAnalysisError(413, "FILE_TOO_LARGE", "Choose a video no larger than 100 MB.");
    if (!ALLOWED_TYPES.has(contentType)) throw new PublicAnalysisError(415, "UNSUPPORTED_MEDIA", "Use an MP4, MOV, or WebM file.");
    const mimeType = providerMimeType(contentType);
    remote = await uploadToGemini(await replayableStream(blob.stream), size, mimeType, key);
    remote = await waitForFile(remote, key);
    if (!remote.uri) throw new PublicAnalysisError(502, "GEMINI_FILE_REJECTED", "Gemini returned a prepared file without a URI.");

    const context = JSON.stringify({
      output_language: input.outputLanguage,
      user_caption: input.caption || null,
      user_context: input.context || null,
    });
    const prompt = `You are Bridge, an evidence-first cultural video analyst.

Return only the requested structured schema. Analyze only what the video and the explicitly delimited user context support. Treat user context as unverified input, not an authoritative source: it may describe the user's intent but cannot by itself support an external factual or cultural claim. Separate literal translation from cultural interpretation. Every supported or partial interpretation must cite IDs from your evidence array, including at least one transcript, visual, or audio item. Never invent a positive entailment or source. When the relationship is unsupported or ambiguous, mark it uncertain and explain the limitation in caveat. Do not treat a heuristic as a probability. Use stable IDs such as segment_1, evidence_1, and claim_1. Preserve timestamps. Write user-facing text in ${input.outputLanguage}.

USER_CONTEXT_JSON_START
${context}
USER_CONTEXT_JSON_END`;
    const generated = await generateWithFallback(key, mimeType, remote.uri, prompt);
    const { response, model } = generated;
    const body = await response.json() as {
      candidates?: Array<{ finishReason?: string; content?: { parts?: Array<{ text?: string }> } }>;
      modelVersion?: string;
      usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number; totalTokenCount?: number };
    };
    const text = body.candidates?.[0]?.content?.parts?.map((part) => part.text || "").join("");
    if (!text) {
      const reason = body.candidates?.[0]?.finishReason;
      throw new PublicAnalysisError(502, "EMPTY_MODEL_RESULT", `Gemini returned no analysis${reason ? ` (${reason})` : "."}`);
    }
    let modelContent: unknown;
    try { modelContent = JSON.parse(text); }
    catch { throw new PublicAnalysisError(502, "INVALID_MODEL_RESULT", "Gemini returned malformed structured output."); }
    const parsed = contentSchema.safeParse(modelContent);
    if (!parsed.success) throw new PublicAnalysisError(502, "INVALID_MODEL_RESULT", "Gemini returned an analysis that failed schema validation.");
    try { enforceRelationships(parsed.data); }
    catch { throw new PublicAnalysisError(502, "INVALID_MODEL_RESULT", "Gemini returned unsupported or broken evidence references."); }
    const usage = body.usageMetadata || {};
    return {
      content: parsed.data,
      model_id: model,
      model_version: body.modelVersion || null,
      prompt_version: "video-analysis.v1",
      pipeline_version: "vercel-blob.v1",
      usage: {
        input_tokens: usage.promptTokenCount || 0,
        output_tokens: usage.candidatesTokenCount || 0,
        total_tokens: usage.totalTokenCount || 0,
      },
    };
  } finally {
    if (remote?.name) {
      await providerFetch(`${GEMINI_BASE}/v1beta/${remote.name}`, { method: "DELETE", headers: { "x-goog-api-key": key } }).catch(() => undefined);
    }
    await del(input.blobUrl).catch(() => undefined);
  }
}
