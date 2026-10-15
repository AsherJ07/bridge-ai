"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowRight, Check, FileVideo, LoaderCircle, RotateCcw, ShieldCheck, Sparkles, UploadCloud, X } from "lucide-react";
import { API_BASE_URL, apiError, type AnalysisResponse, type AnalysisStage } from "@/lib/analysis";

const MAX_BYTES = 100 * 1024 * 1024;
const terminalStatuses = new Set(["completed", "failed"]);
const stageLabels: Record<AnalysisStage, string> = {
  queued: "Queued",
  validating: "Validating media",
  uploading_to_model: "Sending securely to Gemini",
  waiting_for_model_file: "Preparing video",
  analyzing: "Analyzing language and context",
  validating_result: "Checking evidence links",
  completed: "Analysis complete",
  failed: "Analysis failed",
};

interface UploadBody { id: string; filename: string; size_bytes: number; duration_seconds: number }

function uploadVideo(file: File, onProgress: (value: number) => void): Promise<UploadBody> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/api/v1/uploads`);
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(JSON.parse(request.responseText) as UploadBody);
        return;
      }
      try {
        const body = JSON.parse(request.responseText) as { detail?: string };
        reject(new Error(body.detail ?? `Upload failed (${request.status})`));
      } catch { reject(new Error(`Upload failed (${request.status})`)); }
    });
    request.addEventListener("error", () => reject(new Error("Could not reach the Bridge API.")));
    const data = new FormData();
    data.append("file", file);
    request.send(data);
  });
}

function formatTime(seconds: number | null): string {
  if (seconds === null) return "—";
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [outputLanguage, setOutputLanguage] = useState("English");
  const [caption, setCaption] = useState("");
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrl = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);
  useEffect(() => {
    if (!analysis || terminalStatuses.has(analysis.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/analyses/${analysis.id}`, { cache: "no-store" });
        if (!response.ok) throw new Error(await apiError(response));
        setAnalysis((await response.json()) as AnalysisResponse);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Could not read analysis status.");
      }
    }, 1400);
    return () => window.clearTimeout(timer);
  }, [analysis]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError(null);
    setAnalysis(null);
    if (selected && selected.size > MAX_BYTES) {
      setFile(null);
      setError("Choose a video no larger than 100 MB.");
      return;
    }
    setFile(selected);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !consent || busy) return;
    setBusy(true); setError(null); setAnalysis(null);
    try {
      const uploaded = await uploadVideo(file, setUploadProgress);
      const response = await fetch(`${API_BASE_URL}/api/v1/analyses`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ upload_id: uploaded.id, output_language: outputLanguage, caption: caption || null, context: context || null }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      setAnalysis((await response.json()) as AnalysisResponse);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Analysis could not be started.");
    } finally { setBusy(false); setUploadProgress(null); }
  }

  function reset() {
    setFile(null); setAnalysis(null); setError(null); setUploadProgress(null); setConsent(false);
    if (inputRef.current) inputRef.current.value = "";
  }

  const result = analysis?.result?.content;
  return (
    <main className="analyze-page">
      <section className="analyze-intro">
        <p className="kicker"><i /> Video analysis</p>
        <h1>What are they <em>really</em> saying?</h1>
        <p>Upload one short clip. Bridge keeps literal meaning, cultural context, and uncertainty distinct.</p>
      </section>
      <div className="analyze-layout">
        <form className="upload-panel" onSubmit={submit}>
          <div className="panel-heading"><div><span>01</span><h2>Add a clip</h2></div><small>MP4 · MOV · WebM<br />100 MB · 2 min max</small></div>
          {!file ? (
            <button className="drop-zone" type="button" onClick={() => inputRef.current?.click()}><span><UploadCloud size={25} /></span><strong>Choose a video</strong><small>One clip at a time</small></button>
          ) : (
            <div className="file-preview">{previewUrl && <video src={previewUrl} controls preload="metadata" />}<div><FileVideo size={17} /><p><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(1)} MB</small></p><button type="button" aria-label="Remove video" onClick={reset}><X size={16} /></button></div></div>
          )}
          <input ref={inputRef} className="visually-hidden" type="file" accept="video/mp4,video/quicktime,video/webm,.mov" onChange={chooseFile} />
          <div className="field-grid">
            <label><span>Explain in</span><select value={outputLanguage} onChange={(event) => setOutputLanguage(event.target.value)}><option>English</option><option>Urdu</option><option>Hindi</option><option>Spanish</option></select></label>
            <label><span>Caption <small>optional</small></span><input maxLength={500} value={caption} onChange={(event) => setCaption(event.target.value)} placeholder="Paste the post caption" /></label>
          </div>
          <label className="context-field"><span>What context do you already have? <small>optional</small></span><textarea maxLength={1000} value={context} onChange={(event) => setContext(event.target.value)} placeholder="Creator, region, situation…" rows={3} /></label>
          <label className="consent-row"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span><strong>I agree to third-party AI processing.</strong> This clip is sent to Google Gemini; Bridge requests deletion from Gemini after the analysis.</span></label>
          <button className="analyze-button" disabled={!file || !consent || busy} type="submit">{busy ? <><LoaderCircle className="spin" size={17} /> Uploading {uploadProgress ?? 0}%</> : <>Analyze video <ArrowRight size={17} /></>}</button>
          <p className="retention-note"><ShieldCheck size={14} /> Local uploads are private and expire after one hour while the API is running. Stale files are purged on later uploads. Do not upload sensitive media.</p>
        </form>
        <section className="result-panel" aria-live="polite">
          {!analysis && !error && <div className="result-empty"><span><Sparkles size={24} /></span><h2>Your context map appears here</h2><p>Transcript, literal meaning, cultural interpretation, timestamps, and evidence stay visibly separate.</p></div>}
          {error && <div className="result-error"><AlertCircle size={24} /><h2>Couldn&apos;t start analysis</h2><p>{error}</p><button type="button" onClick={() => setError(null)}>Try again</button></div>}
          {analysis && !terminalStatuses.has(analysis.status) && <div className="processing-state"><LoaderCircle className="spin" size={25} /><small>Live status</small><h2>{stageLabels[analysis.stage]}</h2><p>No estimated percentage is shown because model processing time is not predictable.</p></div>}
          {analysis?.status === "failed" && <div className="result-error"><AlertCircle size={24} /><small>{analysis.error?.code}</small><h2>Analysis stopped</h2><p>{analysis.error?.message}</p>{analysis.error?.retryable && <button type="button" onClick={() => setAnalysis(null)}>Retry</button>}</div>}
          {analysis?.status === "completed" && result && <div className="analysis-result">
            <div className="result-title"><span><Check size={16} /></span><div><small>{result.detected_languages.join(" · ") || "Language not identified"}</small><h2>{result.overview}</h2></div><button type="button" onClick={reset} title="Analyze another video"><RotateCcw size={16} /></button></div>
            <div className="result-section"><h3>Transcript</h3>{result.transcript.map((segment) => <article className="transcript-row" key={segment.id}><time>{formatTime(segment.start_seconds)}</time><div><p>{segment.spoken_text}</p>{segment.translated_text && <small>{segment.translated_text}</small>}</div></article>)}</div>
            <div className="result-section"><h3>Context, with evidence</h3>{result.interpretations.map((item) => <article className="interpretation-card" key={item.id}><div><span className={`support-pill ${item.support_status}`}>{item.support_status}</span><small>{item.evidence_ids.length} evidence link{item.evidence_ids.length === 1 ? "" : "s"}</small></div><h4>{item.claim}</h4>{item.literal_translation && <p className="literal">Literal: {item.literal_translation}</p>}<p>{item.cultural_context}</p>{item.caveat && <p className="caveat">Limit: {item.caveat}</p>}<ul>{item.evidence_ids.map((id) => { const evidence = result.evidence.find((entry) => entry.id === id); return evidence ? <li key={id}><time>{formatTime(evidence.start_seconds)}</time><span>{evidence.excerpt || evidence.description}</span></li> : null; })}</ul></article>)}</div>
            {(result.ambiguities.length > 0 || result.tone_and_humor.length > 0) && <div className="result-section result-notes"><h3>Nuance & limits</h3>{[...result.tone_and_humor, ...result.ambiguities].map((note) => <p key={note}>{note}</p>)}</div>}
            <footer>Model: {analysis.result?.model_id} · Prompt: {analysis.result?.prompt_version} · {analysis.result?.usage.total_tokens.toLocaleString()} tokens</footer>
          </div>}
        </section>
      </div>
    </main>
  );
}
