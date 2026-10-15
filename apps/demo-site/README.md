# Bridge production demo

This dependency-free Worker powers the owner-private Bridge demo at <https://bridge-beyond-translation.asherjavaid07.chatgpt.site>.

It serves the responsive interface and handles the critical video-analysis journey server-side: validates MP4/MOV/WebM uploads, uploads accepted media to the Gemini Files API, requests schema-constrained analysis, validates evidence references, deletes the provider file, and returns the result. It intentionally shows no benchmark metrics until verified labels exist.

The runtime requires `GEMINI_API_KEY` as a secret and `GEMINI_MODEL` as a non-secret environment variable. Never put credentials in source control.

## Build and validate

Pass these argument arrays as `commands`:

```json
[
  ["node", "scripts/test-worker.mjs"],
  ["bash", "scripts/build.sh"],
  ["node", "scripts/validate-artifact.mjs"]
]
```

The deterministic build copies only `worker/index.js` and `.openai/hosting.json` and produces:

```text
dist/
├── .openai/
│   └── hosting.json
└── server/
    └── index.js
```

`dist/server/index.js` is an ES module with a default export containing `fetch(request, env, ctx)`. Edit `worker/index.js`, not the generated file under `dist/`.

The deployment is intentionally owner-private. A successful deployment verifies packaging and publication, while a complete inference smoke test still requires a licensed test video and an authenticated owner session.
