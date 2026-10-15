export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AnalysisStage = "queued" | "validating" | "uploading_to_model" | "waiting_for_model_file" | "analyzing" | "validating_result" | "completed" | "failed";

export interface AnalysisResponse {
  id: string;
  upload_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: AnalysisStage;
  result: null | {
    model_id: string;
    model_version: string | null;
    prompt_version: string;
    usage: { input_tokens: number; output_tokens: number; total_tokens: number };
    content: {
      overview: string;
      detected_languages: string[];
      transcript: Array<{ id: string; start_seconds: number; end_seconds: number; spoken_text: string; translated_text: string | null }>;
      evidence: Array<{ id: string; kind: string; start_seconds: number | null; end_seconds: number | null; excerpt: string | null; description: string }>;
      interpretations: Array<{ id: string; claim: string; literal_translation: string | null; cultural_context: string; support_status: "supported" | "partial" | "uncertain"; evidence_ids: string[]; caveat: string | null }>;
      tone_and_humor: string[];
      ambiguities: string[];
    };
  };
  error: null | { code: string; message: string; retryable: boolean };
}

export async function apiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | Array<{ msg: string }> };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join("; ");
  } catch {
    // Use a stable fallback when the API does not return JSON.
  }
  return `Request failed (${response.status})`;
}
