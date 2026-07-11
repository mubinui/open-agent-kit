"""Flash deployment endpoints — deployable chatbot pages served by the app itself.

Deployments are static single-file chat frontends generated from a workflow.
They are written under ``data/deployments/<id>/`` and served same-origin at
``/d/<id>/`` by this application — no extra processes or ports required.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/deployments", tags=["deployments"])

# Public router (no /api prefix) that serves the deployed chatbot pages
pages_router = APIRouter(tags=["deployments"])

DATA_DIR = Path("data")
CONFIG_PATH = DATA_DIR / "deployments.json"
DEPLOYMENTS_DIR = DATA_DIR / "deployments"
DeploymentStatus = Literal["active", "error"]

MARKDOWN_STYLE = """
        .md-content p { margin: 0 0 8px; }
        .md-content p:last-child { margin-bottom: 0; }
        .md-content ul, .md-content ol { margin: 8px 0; padding-left: 20px; }
        .md-content li { margin: 3px 0; }
        .md-content code { background: rgba(255,255,255,.1); border-radius: 4px; padding: 2px 4px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: .92em; }
        .md-content pre { background: #0b1220; color: #f8fafc; border-radius: 8px; padding: 12px; overflow: auto; white-space: pre; }
        .md-content pre code { background: transparent; padding: 0; color: inherit; }
        .md-content blockquote { margin: 8px 0; border-left: 3px solid #64748b; padding-left: 10px; color: #cbd5e1; }
        .md-content a { color: #93c5fd; text-decoration: underline; }
        .md-content table { border-collapse: collapse; width: 100%; margin: 8px 0; }
        .md-content th, .md-content td { border: 1px solid rgba(148,163,184,.45); padding: 6px 8px; text-align: left; }
"""

MARKDOWN_SCRIPT = r"""
        function escapeHtml(value) {
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }
        function inlineMarkdown(value) {
            let html = escapeHtml(value);
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
            html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
            return html;
        }
        function renderMarkdown(markdown) {
            const lines = String(markdown || '').split(/\r?\n/);
            const blocks = [];
            let list = null;
            let code = [];
            let inCode = false;
            function closeList() {
                if (!list) return;
                blocks.push('<' + list.type + '>' + list.items.map(item => '<li>' + inlineMarkdown(item) + '</li>').join('') + '</' + list.type + '>');
                list = null;
            }
            function closeCode() {
                if (!inCode) return;
                blocks.push('<pre><code>' + escapeHtml(code.join('\n')) + '</code></pre>');
                code = [];
                inCode = false;
            }
            for (const line of lines) {
                if (line.trim().startsWith('```')) {
                    if (inCode) closeCode(); else { closeList(); inCode = true; code = []; }
                    continue;
                }
                if (inCode) { code.push(line); continue; }
                if (!line.trim()) { closeList(); continue; }
                const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
                const unordered = line.match(/^\s*[-*]\s+(.+)$/);
                if (ordered || unordered) {
                    const type = ordered ? 'ol' : 'ul';
                    if (!list || list.type !== type) { closeList(); list = { type, items: [] }; }
                    list.items.push((ordered || unordered)[1]);
                    continue;
                }
                closeList();
                if (line.startsWith('### ')) blocks.push('<h3>' + inlineMarkdown(line.slice(4)) + '</h3>');
                else if (line.startsWith('## ')) blocks.push('<h2>' + inlineMarkdown(line.slice(3)) + '</h2>');
                else if (line.startsWith('# ')) blocks.push('<h1>' + inlineMarkdown(line.slice(2)) + '</h1>');
                else if (line.startsWith('> ')) blocks.push('<blockquote>' + inlineMarkdown(line.slice(2)) + '</blockquote>');
                else blocks.push('<p>' + inlineMarkdown(line) + '</p>');
            }
            closeCode();
            closeList();
            return blocks.join('');
        }
"""


class DeploymentCreateRequest(BaseModel):
    workflow_id: str
    name: str
    # Empty api_url means same-origin (the app that serves the page)
    api_url: str = ""
    trigger_id: str | None = None
    title: str = "AI Chatbot"
    theme: str = "midnight"
    greeting: str = "Hi, how can I help?"
    provider_id: str = "openrouter"
    model_id: str = "openai/gpt-oss-20b"
    auth_mode: str = "public"
    frontend_html: str | None = None
    frontend_source: str = "default"


class DeploymentResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    api_url: str = ""
    trigger_id: str | None = None
    title: str
    theme: str
    greeting: str
    provider_id: str
    model_id: str
    auth_mode: str
    status: DeploymentStatus
    url: str
    path: str
    created_at: str
    updated_at: str
    error: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "chatbot"


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"version": "1.0", "deployments": []}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _delete_deployment_path(path_value: str | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    # Only ever delete inside the deployments directory
    try:
        path.resolve().relative_to(DEPLOYMENTS_DIR.resolve())
    except ValueError:
        return
    if path.exists():
        shutil.rmtree(path)


def _ensure_deployed_markdown_support(html: str) -> str:
    if "function renderMarkdown" in html:
        return html
    if "</style>" in html:
        html = html.replace("</style>", f"{MARKDOWN_STYLE}\n  </style>", 1)
    elif "</head>" in html:
        html = html.replace("</head>", f"<style>{MARKDOWN_STYLE}</style></head>", 1)
    script = f"<script>\n{MARKDOWN_SCRIPT}\n</script>"
    if "</body>" in html:
        return html.replace("</body>", f"{script}</body>", 1)
    return f"{html}{script}"


def _chatbot_html(body: DeploymentCreateRequest) -> str:
    settings = json.dumps(body.model_dump(exclude={"frontend_html"}))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{body.title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #101820; color: #e6edf3; }}
    main {{ min-height: 100vh; display: grid; grid-template-columns: minmax(280px, 420px) 1fr; }}
    aside {{ padding: 32px; background: #0f1720; border-right: 1px solid #263241; display: flex; flex-direction: column; justify-content: space-between; }}
    h1 {{ font-size: 34px; margin: 0 0 14px; line-height: 1; letter-spacing: 0; }}
    p {{ color: #9fb0c2; line-height: 1.6; }}
    .status {{ display: inline-flex; align-items: center; gap: 8px; color: #74d99f; font-size: 13px; margin-top: 24px; }}
    .dot {{ width: 8px; height: 8px; background: #22c55e; border-radius: 50%; }}
    section {{ display: flex; align-items: center; justify-content: center; padding: 28px; }}
    .chat {{ width: min(780px, 100%); height: min(760px, calc(100vh - 56px)); border: 1px solid #263241; background: #121d29; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 24px 70px rgba(0,0,0,.28); }}
    .messages {{ flex: 1; padding: 22px; overflow: auto; display: flex; flex-direction: column; gap: 14px; }}
    .msg {{ max-width: 82%; padding: 12px 14px; border-radius: 8px; white-space: pre-wrap; line-height: 1.45; font-size: 14px; }}
    .user {{ align-self: flex-end; background: #2f6fed; color: white; }}
    .assistant {{ align-self: flex-start; background: #1b2a3a; border: 1px solid #314257; }}
{MARKDOWN_STYLE}
    form {{ display: flex; gap: 10px; padding: 16px; border-top: 1px solid #263241; background: #0f1720; }}
    input {{ flex: 1; background: #111c28; border: 1px solid #34465c; color: white; border-radius: 6px; padding: 12px; font-size: 14px; }}
    button {{ border: 0; background: #2f6fed; color: white; border-radius: 6px; padding: 0 18px; font-weight: 700; cursor: pointer; }}
    button:disabled {{ opacity: .55; cursor: wait; }}
    @media (max-width: 820px) {{ main {{ grid-template-columns: 1fr; }} aside {{ display: none; }} section {{ padding: 12px; }} .chat {{ height: calc(100vh - 24px); }} }}
  </style>
</head>
<body>
  <main>
    <aside>
      <div>
        <h1>{body.title}</h1>
        <p>{body.greeting}</p>
        <div class="status"><span class="dot"></span> Live on workflow <strong>{body.workflow_id}</strong></div>
      </div>
      <p>Provider: {body.provider_id}<br/>Model: {body.model_id}</p>
    </aside>
    <section>
      <div class="chat">
        <div id="messages" class="messages"></div>
        <form id="form">
          <input id="input" autocomplete="off" placeholder="Ask anything..." />
          <button id="send" type="submit">Send</button>
        </form>
      </div>
    </section>
  </main>
  <script>
    const cfg = {settings};
    // Empty api_url = same origin: the app serving this page also serves the API
    const apiBase = cfg.api_url || '';
    const messages = document.getElementById('messages');
    const input = document.getElementById('input');
    const send = document.getElementById('send');
    let sessionId = null;
{MARKDOWN_SCRIPT}
    function add(role, text) {{
      const div = document.createElement('div');
      div.className = 'msg ' + role;
            if (role === 'assistant') {{
                div.classList.add('md-content');
                div.innerHTML = renderMarkdown(text);
            }} else {{
                div.textContent = text;
            }}
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
    }}
    async function ensureSession() {{
      if (sessionId) return sessionId;
      const res = await fetch(apiBase + '/api/v1/sessions', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ workflow_id: cfg.workflow_id, user_id: 'flash-user', metadata: {{ deployment: cfg.name }} }})
      }});
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      sessionId = data.session_id;
      return sessionId;
    }}
    add('assistant', cfg.greeting);
    document.getElementById('form').addEventListener('submit', async (event) => {{
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      add('user', text);
      send.disabled = true;
      try {{
        const sid = await ensureSession();
        const res = await fetch(apiBase + '/api/v1/sessions/' + sid + '/messages', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ message: text, max_turns: 10, metadata: {{ provider_id: cfg.provider_id, model_id: cfg.model_id }} }})
        }});
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        add('assistant', data.response || 'No response');
      }} catch (error) {{
        add('assistant', 'Error: ' + error.message);
      }} finally {{
        send.disabled = false;
        input.focus();
      }}
    }});
  </script>
</body>
</html>
"""


def _write_deployment(deployment_id: str, body: DeploymentCreateRequest) -> Path:
    path = DEPLOYMENTS_DIR / deployment_id
    path.mkdir(parents=True, exist_ok=True)
    html = body.frontend_html or _chatbot_html(body)
    runtime_config = json.dumps(body.model_dump(exclude={"frontend_html"}))
    if "__CHATBOT_CONFIG__" in html:
        html = html.replace("__CHATBOT_CONFIG__", runtime_config)
    elif body.frontend_html:
        html = html.replace("</body>", f"<script>window.CHATBOT_CONFIG = {runtime_config};</script></body>")
    html = _ensure_deployed_markdown_support(html)
    (path / "index.html").write_text(html, encoding="utf-8")
    (path / "deployment.json").write_text(json.dumps(body.model_dump(exclude={"frontend_html"}), indent=2), encoding="utf-8")
    return path


@router.get("", response_model=list[DeploymentResponse])
async def list_deployments() -> list[DeploymentResponse]:
    config = _load_config()
    return [DeploymentResponse(**deployment) for deployment in config.get("deployments", [])]


@router.post("/preview")
async def preview_deployment(body: DeploymentCreateRequest) -> dict[str, Any]:
    deployment_id = _slug(body.name)
    return {
        "url": f"/d/{deployment_id}/",
        "path": str(DEPLOYMENTS_DIR / deployment_id),
        "warnings": [],
    }


@router.post("/flash", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def flash_deploy(body: DeploymentCreateRequest) -> DeploymentResponse:
    config = _load_config()
    deployment_id = _slug(body.name)
    now = _now()
    record: dict[str, Any] = {
        **body.model_dump(exclude={"frontend_html"}),
        "id": deployment_id,
        "status": "active",
        "url": f"/d/{deployment_id}/",
        "path": str(DEPLOYMENTS_DIR / deployment_id),
        "created_at": now,
        "updated_at": now,
        "error": None,
    }

    try:
        _write_deployment(deployment_id, body)
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)

    config["deployments"] = [
        deployment for deployment in config.get("deployments", []) if deployment["id"] != deployment_id
    ]
    config.setdefault("deployments", []).append(record)
    _save_config(config)
    return DeploymentResponse(**record)


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(deployment_id: str) -> None:
    config = _load_config()
    deployments = config.get("deployments", [])
    record = next((deployment for deployment in deployments if deployment["id"] == deployment_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")

    config["deployments"] = [
        deployment for deployment in deployments if deployment["id"] != deployment_id
    ]
    _save_config(config)
    _delete_deployment_path(record.get("path"))


@pages_router.get("/d/{deployment_id}/", include_in_schema=False)
@pages_router.get("/d/{deployment_id}", include_in_schema=False)
async def serve_deployment_page(deployment_id: str) -> FileResponse:
    """Serve a deployed chatbot page same-origin."""
    index = DEPLOYMENTS_DIR / deployment_id / "index.html"
    try:
        index.resolve().relative_to(DEPLOYMENTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not index.exists():
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deployment_id}")
    return FileResponse(index, media_type="text/html")
