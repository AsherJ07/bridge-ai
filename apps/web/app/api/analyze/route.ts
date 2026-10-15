import { NextResponse } from "next/server";
import { analyzeBlob, analyzeRequestSchema, PublicAnalysisError } from "@/lib/gemini-video";

export const maxDuration = 300;

const requestWindows = new Map<string, number[]>();

function rateLimit(request: Request): void {
  const key = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const now = Date.now();
  const recent = (requestWindows.get(key) || []).filter((time) => now - time < 10 * 60_000);
  if (recent.length >= 4) throw new PublicAnalysisError(429, "RATE_LIMITED", "Too many analyses. Try again in a few minutes.");
  recent.push(now);
  requestWindows.set(key, recent);
}

export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  let sameOrigin = true;
  if (origin) {
    try { sameOrigin = new URL(origin).host === request.headers.get("host"); }
    catch { sameOrigin = false; }
  }
  if (!sameOrigin) return NextResponse.json({ code: "CROSS_SITE_REQUEST", message: "Cross-site analysis requests are not allowed." }, { status: 403 });
  try {
    rateLimit(request);
    let body: unknown;
    try { body = await request.json(); }
    catch { throw new PublicAnalysisError(400, "INVALID_REQUEST", "The analysis request must be valid JSON."); }
    const parsed = analyzeRequestSchema.safeParse(body);
    if (!parsed.success) throw new PublicAnalysisError(400, "INVALID_REQUEST", "The analysis request is incomplete or invalid.");
    const result = await analyzeBlob(parsed.data);
    return NextResponse.json({
      id: crypto.randomUUID(),
      upload_id: "deleted-after-analysis",
      status: "completed",
      stage: "completed",
      result,
      error: null,
    });
  } catch (error) {
    if (error instanceof PublicAnalysisError) return NextResponse.json({ code: error.code, message: error.message }, { status: error.status });
    console.error("analysis_failed", error instanceof Error ? error.message : "unknown");
    return NextResponse.json({ code: "INTERNAL_ERROR", message: "The analysis failed unexpectedly." }, { status: 500 });
  }
}
