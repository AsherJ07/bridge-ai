import { del } from "@vercel/blob";
import { handleUpload, type HandleUploadBody } from "@vercel/blob/client";
import { NextResponse } from "next/server";

const MAX_BYTES = 100 * 1024 * 1024;
const ALLOWED_TYPES = ["video/mp4", "video/quicktime", "video/webm"];

function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try { return new URL(origin).host === request.headers.get("host"); }
  catch { return false; }
}

export async function POST(request: Request) {
  if (!sameOrigin(request)) return NextResponse.json({ code: "CROSS_SITE_REQUEST", message: "Cross-site uploads are not allowed." }, { status: 403 });
  try {
    const body = await request.json() as HandleUploadBody;
    const response = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        if (!pathname.startsWith("bridge/")) throw new Error("Invalid upload path.");
        const metadata = JSON.parse(clientPayload || "{}") as { contentType?: string; size?: number; durationSeconds?: number };
        if (!metadata.contentType || !ALLOWED_TYPES.includes(metadata.contentType)) throw new Error("Use an MP4, MOV, or WebM file.");
        if (!metadata.size || metadata.size > MAX_BYTES) throw new Error("Choose a video no larger than 100 MB.");
        if (!metadata.durationSeconds || metadata.durationSeconds > 120) throw new Error("Choose a video no longer than two minutes.");
        return {
          allowedContentTypes: ALLOWED_TYPES,
          maximumSizeInBytes: MAX_BYTES,
          addRandomSuffix: true,
          tokenPayload: clientPayload,
        };
      },
    });
    return NextResponse.json(response);
  } catch (error) {
    return NextResponse.json({ code: "UPLOAD_TOKEN_FAILED", message: error instanceof Error ? error.message : "The upload could not be authorized." }, { status: 400 });
  }
}

export async function DELETE(request: Request) {
  if (!sameOrigin(request)) return NextResponse.json({ code: "CROSS_SITE_REQUEST", message: "Cross-site cleanup requests are not allowed." }, { status: 403 });
  try {
    const body = await request.json() as { blobUrl?: unknown };
    if (typeof body.blobUrl !== "string") throw new Error("A temporary upload URL is required.");
    const blobUrl = new URL(body.blobUrl);
    if (!blobUrl.hostname.endsWith(".private.blob.vercel-storage.com") || !blobUrl.pathname.startsWith("/bridge/")) {
      throw new Error("Only Bridge temporary uploads can be removed.");
    }
    await del(blobUrl.href);
    return NextResponse.json({ deleted: true });
  } catch (error) {
    return NextResponse.json({ code: "UPLOAD_CLEANUP_FAILED", message: error instanceof Error ? error.message : "The temporary upload could not be removed." }, { status: 400 });
  }
}
