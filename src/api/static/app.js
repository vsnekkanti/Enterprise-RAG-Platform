const DEMO_TOKENS = {
  user_a: "e7e0ac4358145a17fe33582f906e237bab13f388fcbc564de60b757fb6371f6a",
  user_b: "142f2a2e5e1d3066fe8bb2cb63160992fb15b71e64309e59ce555a2f5a720db5",
};

function currentToken() {
  const select = document.getElementById("user-select");
  if (select.value === "custom") {
    return document.getElementById("custom-token").value.trim();
  }
  return DEMO_TOKENS[select.value];
}

function authHeaders(extra) {
  return Object.assign({ Authorization: `Bearer ${currentToken()}` }, extra || {});
}

function initUserSelector() {
  const select = document.getElementById("user-select");
  const customInput = document.getElementById("custom-token");
  select.addEventListener("change", () => {
    customInput.classList.toggle("hidden", select.value !== "custom");
  });
}

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

async function pollHealth() {
  const dot = document.getElementById("health-dot");
  try {
    const res = await fetch("/health");
    dot.className = "brand-dot " + (res.ok ? "ok" : "down");
  } catch {
    dot.className = "brand-dot down";
  }
}

function appendMessage(role, text) {
  const messages = document.getElementById("messages");
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el;
}

function appendSources(el, sources) {
  if (!sources || sources.length === 0) return;
  const wrap = document.createElement("div");
  wrap.className = "sources";
  sources.forEach((s) => {
    const badge = document.createElement("span");
    badge.className = "source-badge";
    badge.textContent = `${s.source} #${s.chunk_id}`;
    wrap.appendChild(badge);
  });
  el.appendChild(wrap);
}

async function sendChat(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;

  appendMessage("user", question);
  input.value = "";
  const sendBtn = document.getElementById("chat-send");
  sendBtn.disabled = true;
  const pending = appendMessage("assistant pending", "Thinking…");

  const limit = parseInt(document.getElementById("opt-limit").value, 10) || 8;
  const maxTokensRaw = document.getElementById("opt-max-tokens").value;
  const body = { query: question, limit };
  if (maxTokensRaw) body.max_tokens = parseInt(maxTokensRaw, 10);

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    const data = await res.json();
    pending.remove();
    if (!res.ok) {
      appendMessage("error", data.detail || `Error ${res.status}`);
      return;
    }
    const el = appendMessage("assistant", data.answer + (data.cached ? "  (cached)" : ""));
    appendSources(el, data.sources);
  } catch (err) {
    pending.remove();
    appendMessage("error", `Request failed: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

function initDropzone() {
  const zone = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const label = document.getElementById("dropzone-label");

  input.addEventListener("change", () => {
    if (input.files[0]) label.textContent = input.files[0].name;
  });
  ["dragenter", "dragover"].forEach((evt) =>
    zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.add("dragover"); })
  );
  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => { e.preventDefault(); zone.classList.remove("dragover"); })
  );
  zone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files[0]) {
      input.files = e.dataTransfer.files;
      label.textContent = e.dataTransfer.files[0].name;
    }
  });
}

function setUploadStatus(text, cls) {
  const status = document.getElementById("upload-status");
  status.textContent = text;
  status.className = `upload-status ${cls}`;
}

async function handleUpload(event) {
  event.preventDefault();
  const fileInput = document.getElementById("file-input");
  const aclGroup = document.getElementById("acl-group").value.trim();
  if (!fileInput.files[0]) return;

  const submitBtn = document.getElementById("upload-submit");
  submitBtn.disabled = true;
  setUploadStatus("Uploading and ingesting… this can take a minute for large PDFs.", "");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("acl_group", aclGroup);

  try {
    const res = await fetch("/ingest/upload", {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      setUploadStatus(data.detail || `Error ${res.status}`, "error");
      return;
    }
    setUploadStatus(
      `✓ Ingested "${data.filename}" into "${data.acl_group}" (${data.chunks_ingested} chunks).`,
      "ok"
    );
    event.target.reset();
    document.getElementById("dropzone-label").textContent = "Drop a PDF here, or click to choose a file";
  } catch (err) {
    setUploadStatus(`Upload failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initUserSelector();
  initTabs();
  initDropzone();
  const chatForm = document.getElementById("chat-form");
  chatForm.addEventListener("submit", sendChat);
  document.getElementById("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      chatForm.requestSubmit();
    }
  });
  document.getElementById("upload-form").addEventListener("submit", handleUpload);
  pollHealth();
  setInterval(pollHealth, 15000);
});
