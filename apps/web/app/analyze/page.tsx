"use client";

import { upload } from "@vercel/blob/client";
import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowRight, Check, FileVideo, LoaderCircle, RotateCcw, ShieldCheck, Sparkles, UploadCloud, X } from "lucide-react";
import { apiError, type AnalysisResponse } from "@/lib/analysis";

const MAX_BYTES = 100 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["video/mp4", "video/quicktime", "video/webm"]);

function readDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    const url = URL.createObjectURL(file);
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      const value = video.duration;
      URL.revokeObjectURL(url);
      if (Number.isFinite(value) && value > 0) resolve(value);
      else reject(new Error("This video's duration could not be read."));
    };
    video.onerror = () => { URL.revokeObjectURL(url); reject(new Error("This video could not be read.")); };
    video.src = url;
  });
}

function formatTime(seconds: number | null): string {
  if (seconds === null) return "—";
  return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [outputLanguage, setOutputLanguage] = useState("English");
  const [caption, setCaption] = useState("");
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyPhase, setBusyPhase] = useState<"uploading" | "analyzing" | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const previewUrl = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setError(null);
    setAnalysis(null);
    setDurationSeconds(null);
    if (selected && !ALLOWED_TYPES.has(selected.type)) {
      setFile(null);
      setError("Use an MP4, MOV, or WebM file.");
      return;
    }
    if (selected && selected.size > MAX_BYTES) {
      setFile(null);
      setError("Choose a video no larger than 100 MB.");
      return;
    }
    if (!selected) { setFile(null); return; }
    try {
      const duration = await readDuration(selected);
      if (duration > 120) throw new Error("Choose a video no longer than two minutes.");
      setDurationSeconds(duration);
      setFile(selected);
    } catch (cause) {
      setFile(null);
      setError(cause instanceof Error ? cause.message : "This video could not be read.");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !durationSeconds || !consent || busy) return;
    setBusy(true); setError(null); setAnalysis(null);
    let temporaryBlobUrl: string | null = null;
    try {
      setBusyPhase("uploading");
      const safeName = file.name.replace(/[^a-zA-Z0-9._-]+/g, "-").slice(-100) || "video";
      const blob = await upload(`bridge/${crypto.randomUUID()}-${safeName}`, file, {
        access: "private",
        handleUploadUrl: "/api/upload",
        contentType: file.type,
        multipart: file.size > 5 * 1024 * 1024,
        clientPayload: JSON.stringify({ contentType: file.type, size: file.size, durationSeconds }),
        onUploadProgress: ({ percentage }) => setUploadProgress(Math.round(percentage)),
      });
      temporaryBlobUrl = blob.url;
      setBusyPhase("analyzing");
      setUploadProgress(null);
      setAnalysis({ id: "processing", upload_id: "private-blob", status: "processing", stage: "analyzing", result: null, error: null });
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blobUrl: blob.url, durationSeconds, outputLanguage, caption: caption || null, context: context || null }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      setAnalysis((await response.json()) as AnalysisResponse);
      temporaryBlobUrl = null;
    } catch (cause) {
      if (temporaryBlobUrl) {
        await fetch("/api/upload", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ blobUrl: temporaryBlobUrl }),
        }).catch(() => undefined);
      }
      setAnalysis(null);
      setError(cause instanceof Error ? cause.message : "Analysis could not be started.");
    } finally { setBusy(false); setBusyPhase(null); setUploadProgress(null); }
  }

  function reset() {
    setFile(null); setDurationSeconds(null); setAnalysis(null); setError(null); setUploadProgress(null); setConsent(false);
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
            <div className="file-preview">{previewUrl && <video src={previewUrl} controls preload="metadata" />}<div><FileVideo size={17} /><p><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(1)} MB{durationSeconds ? ` · ${formatTime(durationSeconds)}` : ""}</small></p><button type="button" aria-label="Remove video" onClick={reset}><X size={16} /></button></div></div>
          )}
          <input ref={inputRef} className="visually-hidden" type="file" accept="video/mp4,video/quicktime,video/webm,.mov" onChange={chooseFile} />
          <div className="field-grid">
            <label><span>Explain in</span><select value={outputLanguage} onChange={(event) => setOutputLanguage(event.target.value)}><option>English</option><option>Urdu</option><option>Hindi</option><option>Spanish</option></select></label>
            <label><span>Caption <small>optional</small></span><input maxLength={500} value={caption} onChange={(event) => setCaption(event.target.value)} placeholder="Paste the post caption" /></label>
          </div>
          <label className="context-field"><span>What context do you already have? <small>optional</small></span><textarea maxLength={1000} value={context} onChange={(event) => setContext(event.target.value)} placeholder="Creator, region, situation…" rows={3} /></label>
          <label className="consent-row"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span><strong>I agree to third-party AI processing.</strong> This clip is temporarily stored in private Vercel Blob storage, sent to Google Gemini, then deletion is requested from both services.</span></label>
          <button className="analyze-button" disabled={!file || !durationSeconds || !consent || busy} type="submit">{busy ? <><LoaderCircle className="spin" size={17} /> {busyPhase === "uploading" ? `Uploading ${uploadProgress ?? 0}%` : "Analyzing video"}</> : <>Analyze video <ArrowRight size={17} /></>}</button>
          <p className="retention-note"><ShieldCheck size={14} /> Uploads are private and deletion is requested after every analysis attempt. Do not upload sensitive media.</p>
        </form>
        <section className="result-panel" aria-live="polite">
          {!analysis && !error && <div className="result-empty"><span><Sparkles size={24} /></span><h2>Your context map appears here</h2><p>Transcript, literal meaning, cultural interpretation, timestamps, and evidence stay visibly separate.</p></div>}
          {error && <div className="result-error"><AlertCircle size={24} /><h2>Analysis stopped</h2><p>{error}</p><button type="button" onClick={() => setError(null)}>Try again</button></div>}
          {analysis?.status === "processing" && <div className="processing-state"><LoaderCircle className="spin" size={25} /><small>Live status</small><h2>Analyzing language and context</h2><p>No estimated percentage is shown because model processing time is not predictable.</p></div>}
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
