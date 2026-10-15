import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    status: "ok",
    configured: Boolean(process.env.GEMINI_API_KEY && (process.env.BLOB_READ_WRITE_TOKEN || process.env.BLOB_STORE_ID)),
    model: process.env.GEMINI_MODEL || "gemini-3.8-flash",
    fallback_models: (process.env.GEMINI_FALLBACK_MODELS || "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite").split(","),
  });
}
