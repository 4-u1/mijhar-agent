// مِجهر agent UI. No framework, no build step. Every server string is rendered with textContent.
// Keys live in memory only (a page reload asks again); only the session id is kept in sessionStorage.
"use strict";

const I18N = {
  ar: {
    title: "مِجهر", subtitle: "وكيل تدقيق المستندات بقرار بشري موقّع", caseFile: "ملف القضية", close: "إغلاق",
    keyTitle: "ابدأ بمفتاح الوصول", keyHelp: "انسخ قيمة MIJHAR_DEMO_CLIENT_KEY من ملف backend/.env، أو شغّل «uv run mijhar agent» ليفتح الرابط بالمفاتيح تلقائياً. المفتاح يبقى في ذاكرة الصفحة فقط.",
    clientKey: "مفتاح العميل", connect: "اتصال", attach: "إرفاق ملف", sample: "مستند تجريبي…", send: "إرسال",
    placeholder: "اكتب طلبك… مثال: دقّق المستند", docs: "المستندات", noDocs: "لا يوجد مستند بعد", context: "سياق النموذج",
    tools: "الأدوات المسموحة", prefs: "تفضيلاتي (ذاكرة)", prefLang: "لغة الرد", auto: "تلقائي", prefDetail: "التفصيل",
    brief: "مختصر", detailed: "مفصّل", prefNote: "يقرأها الوكيل في بداية كل طلب، ولا يستطيع تعديلها.", newSession: "جلسة جديدة",
    approvalTitle: "طلب اعتماد بانتظار توقيعك", job: "المهمة", hash: "بصمة التقرير", riskOf: "من 100", reviewer: "معرّف المراجع",
    reviewerKey: "مفتاح المراجع", approve: "اعتماد ونشر الشهادة", revise: "طلب مراجعة", reject: "رفض",
    signNote: "يُوقَّع القرار على الخادم بمفتاحك، ويُربط بهذه البصمة بالذات، ويُستخدم مرة واحدة.",
    you: "أنت", agent: "الوكيل", harness: "النظام (ليس النموذج)", thinking: "الوكيل يقرر الخطوة التالية…", working: "ينفّذ الأداة…",
    llm: "نموذج لغوي", offline: "مخطط محلي (بدون نموذج)", mcp: "MCP", local: "محلي",
    chips: ["دقّق المستند", "اعتمد", "كم مدة الإبلاغ عن حوادث الذكاء الاصطناعي؟", "اشرح CLM-001"],
    blocked: "مُنعت: الأداة غير مسموحة", tokens: "رمز تقديري", trimmed: "نتائج مختصرة", turns: "الطلبات", modelCalls: "استدعاءات النموذج",
    toolCalls: "استدعاءات الأدوات", audits: "عمليات التدقيق", attachedOk: "أُرفق", decided: "تم تسجيل القرار",
    threats: "تهديدات محجوبة", noThreats: "لا تهديدات", empty: "أرفق مستنداً أو اختر مستنداً تجريبياً، ثم اطلب التدقيق. أو اسأل عن الأنظمة المرجعية.",
    errNet: "تعذر الاتصال بالخادم. تأكد أن «uv run mijhar serve» يعمل.", lang: "EN",
    status: { contradicted: "متناقض", verified: "مؤكَّد", unsubstantiated: "بلا سند", inconclusive: "غير حاسم" },
    toolNames: { load_skill: "تحميل مهارة", search_regulations: "بحث في الأنظمة", check_claim: "فحص ادعاء", audit_document: "تدقيق المستند",
      get_audit_report: "قراءة التقرير", request_publication: "طلب اعتماد بشري" },
    nodes: ["استلام", "حارس", "ادعاءات", "استرجاع", "تحقق", "تقييم", "بوابة", "كتابة"],
  },
  en: {
    title: "MIJHAR", subtitle: "Document audit agent with a signed human decision", caseFile: "Case file", close: "Close",
    keyTitle: "Start with an access key", keyHelp: "Copy MIJHAR_DEMO_CLIENT_KEY from backend/.env, or run “uv run mijhar agent” to open the link with keys filled in. The key stays in this page's memory only.",
    clientKey: "Client key", connect: "Connect", attach: "Attach file", sample: "Sample document…", send: "Send",
    placeholder: "Type a request… e.g. audit the document", docs: "Documents", noDocs: "No document yet", context: "Model context",
    tools: "Allowed tools", prefs: "My preferences (memory)", prefLang: "Reply language", auto: "Automatic", prefDetail: "Detail",
    brief: "Brief", detailed: "Detailed", prefNote: "The agent reads these at the start of every request and cannot change them.", newSession: "New session",
    approvalTitle: "Approval waiting for your signature", job: "Job", hash: "Report hash", riskOf: "of 100", reviewer: "Reviewer id",
    reviewerKey: "Reviewer key", approve: "Approve and publish", revise: "Request revision", reject: "Reject",
    signNote: "The decision is signed on the server with your key, bound to this exact hash, and usable once.",
    you: "You", agent: "Agent", harness: "System (not the model)", thinking: "The agent is choosing the next step…", working: "Running the tool…",
    llm: "Language model", offline: "Offline planner (no model)", mcp: "MCP", local: "local",
    chips: ["Audit the document", "Approve", "How fast must AI incidents be reported?", "Explain CLM-001"],
    blocked: "Blocked: tool not allowed", tokens: "est. tokens", trimmed: "results trimmed", turns: "Requests", modelCalls: "Model calls",
    toolCalls: "Tool calls", audits: "Audits", attachedOk: "Attached", decided: "Decision recorded",
    threats: "Threats redacted", noThreats: "No threats", empty: "Attach a document or pick a sample, then ask for an audit. Or ask about the reference regulations.",
    errNet: "Cannot reach the server. Check that “uv run mijhar serve” is running.", lang: "ع",
    status: { contradicted: "Contradicted", verified: "Verified", unsubstantiated: "Unsubstantiated", inconclusive: "Inconclusive" },
    toolNames: { load_skill: "Load skill", search_regulations: "Search regulations", check_claim: "Check claim", audit_document: "Audit document",
      get_audit_report: "Read report", request_publication: "Ask human approval" },
    nodes: ["ingest", "guard", "extract", "retrieve", "verify", "score", "gate", "commit"],
  },
};
const NODES = ["ingest", "guardrail", "extract", "retrieve", "verify", "score", "hitl_gate", "commit"];

const S = { lang: "ar", ck: "", rk: "", rid: "", sid: null, busy: false, caps: null, steps: null, thinking: null, stepEls: {} };
const $ = (id) => document.getElementById(id);
const t = (k) => I18N[S.lang][k] ?? k;
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

// ------------------------------------------------------------------ boot
function readFragment() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get("ck")) S.ck = h.get("ck");
  if (h.get("rk")) S.rk = h.get("rk");
  if (h.get("rid")) S.rid = h.get("rid");
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);   // keys leave the address bar at once
}
function applyLang() {
  document.documentElement.lang = S.lang;
  document.documentElement.dir = S.lang === "ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach((n) => { const v = I18N[S.lang][n.dataset.i18n]; if (typeof v === "string") n.textContent = v; });
  document.querySelectorAll("[data-i18n-ph]").forEach((n) => { n.placeholder = t(n.dataset.i18nPh); });
  $("lang").textContent = t("lang");
  document.title = S.lang === "ar" ? "مِجهر · وكيل التدقيق" : "MIJHAR · audit agent";
  renderChips(); renderCaps();
}
async function api(path, opts = {}) {
  const headers = Object.assign({ "Content-Type": "application/json", "X-API-Key": S.ck }, opts.headers || {});
  const r = await fetch("api" + path, Object.assign({}, opts, { headers }));
  if (!r.ok) { let d = r.statusText; try { d = (await r.json()).detail || d; } catch (_) {} const e = new Error(d); e.status = r.status; throw e; }
  return r;
}
async function boot() {
  readFragment();
  try { S.lang = localStorage.getItem("mijhar.lang") || "ar"; } catch (_) {}
  applyLang();
  try { S.caps = await (await fetch("api/capabilities")).json(); renderCaps(); } catch (_) { note(t("errNet"), "error"); }
  try { const s = await (await fetch("api/samples")).json(); for (const n of s.samples) { const o = el("option", null, n); o.value = n; $("sample").append(o); } } catch (_) {}
  if (!S.ck) { $("keyForm").hidden = false; $("ckInput").focus(); setComposer(false); return; }
  await start();
}
async function start() {
  $("keyForm").hidden = true;
  try {
    const prefs = await (await api("/memory")).json();
    $("prefLang").value = prefs.language; $("prefDetail").value = prefs.detail;
  } catch (e) { if (e.status === 401) { $("keyForm").hidden = false; note(e.message, "error"); return; } }
  let sid = null;
  try { sid = sessionStorage.getItem("mijhar.sid"); } catch (_) {}
  if (sid) {
    try { const v = await (await api(`/sessions/${sid}`)).json(); S.sid = sid; replay(v); setComposer(true); return; } catch (_) {}
  }
  await newSession();
}
async function newSession() {
  $("log").replaceChildren(); $("attached").replaceChildren(); S.steps = null;
  const r = await (await api("/sessions", { method: "POST", body: "{}" })).json();
  S.sid = r.session_id;
  try { sessionStorage.setItem("mijhar.sid", S.sid); } catch (_) {}
  renderDocs([]); renderUsage(null);
  $("log").append(el("p", "note", t("empty")));
  setComposer(true);
}

// ------------------------------------------------------------------ rendering
function renderCaps() {
  const c = S.caps; if (!c) return;
  const b = $("planner"); b.className = "badge " + c.planner;
  b.textContent = c.planner === "llm" ? `${t("llm")}: ${c.model}` : t("offline");
  b.title = c.reason || "";
  const ul = $("toolList"); ul.replaceChildren();
  for (const tool of c.tools) {
    const li = el("li"); li.append(el("span", null, I18N[S.lang].toolNames[tool.name] || tool.name));
    li.append(el("code", null, `${tool.level} · ${tool.transport === "mcp" && c.mcp ? "MCP" : t("local")}`)); ul.append(li);
  }
}
function renderChips() {
  const box = $("chips"); box.replaceChildren();
  for (const c of t("chips")) { const b = el("button", null, c); b.type = "button"; b.onclick = () => { $("msg").value = c; send(); }; box.append(b); }
}
function renderDocs(docs) {
  const ul = $("docs"); ul.replaceChildren();
  if (!docs.length) { ul.append(el("li", "muted", t("noDocs"))); return; }
  for (const d of docs) { const li = el("li"); li.append(el("span", null, d.name + " ")); li.append(el("code", null, `${d.doc_id} · ${d.chars.toLocaleString()}`)); ul.append(li); }
}
function renderUsage(u) {
  const dl = $("usage"); dl.replaceChildren(); if (!u) return;
  for (const [k, lab] of [["turns", "turns"], ["model_calls", "modelCalls"], ["tool_calls", "toolCalls"], ["audits", "audits"], ["tokens", "tokens"]]) {
    dl.append(el("dt", null, t(lab))); dl.append(el("dd", null, (u[k] ?? 0).toLocaleString()));
  }
}
function scrollEnd() { const l = $("log"); l.scrollTop = l.scrollHeight; }
function note(text, level = "info") { $("log").append(el("p", "note " + level, text)); scrollEnd(); }
function bubble(text, who) {
  const d = el("div", "msg " + (who === "user" ? "user" : "agent" + (who === "harness" ? " harness" : "")));
  if (who !== "user") d.append(el("span", "who", who === "harness" ? t("harness") : t("agent")));
  d.append(document.createTextNode(text)); $("log").append(d); scrollEnd(); return d;
}
function setThinking(on, label) {
  if (S.thinking) { S.thinking.remove(); S.thinking = null; }
  if (!on) return;
  S.thinking = el("div", "thinking"); S.thinking.append(el("span", "dot")); S.thinking.append(el("span", null, label || t("thinking")));
  $("log").append(S.thinking); scrollEnd();
}
function stepsBox() {
  if (!S.steps) { S.steps = el("div", "steps"); $("log").append(S.steps); }
  if (S.thinking) $("log").append(S.thinking);
  return S.steps;
}
function toolStep(ev) {
  const d = el("details", "step run"); const s = el("summary");
  s.append(el("span", "st"));
  const mid = el("div"); mid.append(el("span", "name", I18N[S.lang].toolNames[ev.name] || ev.name));
  const sum = el("span", "sum", argLine(ev.args)); mid.append(sum); s.append(mid);
  const tag = el("span", "tag " + (ev.transport === "mcp" && S.caps?.mcp ? "mcp" : ev.level === "gated" ? "gated" : ""),
    ev.transport === "mcp" && S.caps?.mcp ? "MCP" : ev.level);
  s.append(tag); d.append(s);
  if (ev.name === "audit_document") {   // inside <summary> so the live track is visible while the step is collapsed
    const tr = el("div", "track"); NODES.forEach((n, i) => { const x = el("span", n === "hitl_gate" ? "gate" : "", I18N[S.lang].nodes[i]); x.dataset.node = n; x.title = n; tr.append(x); });
    s.append(tr);
  }
  const pre = el("pre"); pre.textContent = JSON.stringify(ev.args, null, 2); d.append(pre);
  stepsBox().append(d); S.stepEls[ev.id] = { d, sum, pre }; scrollEnd();
}
function argLine(a) { return Object.entries(a || {}).map(([k, v]) => `${k}: ${String(v).slice(0, 60)}`).join(" · "); }
function toolProgress(ev) {
  const s = S.stepEls[ev.id]; if (!s) return;
  const x = s.d.querySelector(`.track [data-node="${ev.node}"]`); if (x) x.classList.add(ev.status === "ok" ? "on" : "fail");
}
function toolResult(ev) {
  const s = S.stepEls[ev.id]; if (!s) return;
  s.d.classList.remove("run"); s.d.classList.add(ev.status);
  s.sum.textContent = ev.summary + (ev.ms != null ? ` · ${ev.ms} ms` : "");
  s.pre.textContent = JSON.stringify(ev.result, null, 2);
  if (ev.name === "audit_document" && ev.status === "ok") { const g = s.d.querySelector('.track [data-node="hitl_gate"]'); if (g) g.classList.add("on"); }
}
function riskClass(n) { return n >= 60 ? "high" : n >= 25 ? "mid" : "low"; }
function approvalCard(a) {
  const node = $("tplApproval").content.firstElementChild.cloneNode(true);
  node.querySelectorAll("[data-i18n]").forEach((n) => { const v = I18N[S.lang][n.dataset.i18n]; if (typeof v === "string") n.textContent = v; });
  node.querySelector(".job").textContent = a.job_id;
  node.querySelector(".hash").textContent = a.report_sha256.slice(0, 12) + "…";
  node.querySelector(".hash").title = a.report_sha256;
  const r = node.querySelector(".risk"); r.classList.add(riskClass(a.risk_score)); node.querySelector(".risk-n").textContent = a.risk_score;
  const th = node.querySelector(".threats");
  if (a.threats.length) for (const x of a.threats) th.append(el("span", "threat", `${x.severity} · ${x.attack}`));
  else th.append(el("span", "small muted", t("noThreats")));
  const ol = node.querySelector(".claims");
  for (const c of a.claims) {
    const li = el("li"); li.append(el("span", "stamp " + c.status, I18N[S.lang].status[c.status] || c.status));
    const body = el("div"); body.append(el("span", null, `${c.id} · ${c.text}`));
    body.append(el("span", "ev", c.evidence.map((e) => `${e.id} ${e.stance} ${e.score}`).join(" · ") || "—"));
    li.append(body); ol.append(li);
  }
  const form = node.querySelector("form");
  form.rid.value = S.rid; form.rk.value = S.rk;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const decision = (e.submitter && e.submitter.value) || "approve";
    const err = form.querySelector(".sign-error"); err.textContent = "";
    form.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const r = await (await api(`/sessions/${S.sid}/decision`, { method: "POST", headers: { "X-Reviewer-Key": form.rk.value },
        body: JSON.stringify({ reviewer: form.rid.value.trim(), decision, report_sha256: a.report_sha256 }) })).json();
      S.rid = form.rid.value.trim(); S.rk = form.rk.value;
      node.classList.add("done");
      for (const ev of r.events) handle(ev, node);
    } catch (x) { err.textContent = x.message; form.querySelectorAll("button").forEach((b) => (b.disabled = false)); }
  });
  $("log").append(node); scrollEnd(); node.focus({ preventScroll: true });
  if (!S.rid) form.rid.focus({ preventScroll: true });
}

// ------------------------------------------------------------------ events
function handle(ev, card) {
  switch (ev.type) {
    case "user": bubble(ev.text, "user"); break;
    case "document": addDocChip(ev.doc); break;
    case "turn_start": S.steps = null; setThinking(true); break;
    case "model_call": setThinking(true, ev.tool_calls ? t("working") : t("thinking")); break;
    case "context": {
      const pct = Math.min(100, Math.round((ev.tokens / ev.limit) * 100));
      $("ctxBar").style.width = pct + "%";
      $("ctxText").textContent = `${ev.tokens.toLocaleString()} / ${ev.limit.toLocaleString()} ${t("tokens")}` + (ev.trimmed ? ` · ${ev.trimmed} ${t("trimmed")}` : "");
      break;
    }
    case "tool_call": toolStep(ev); break;
    case "tool_progress": toolProgress(ev); break;
    case "tool_result": toolResult(ev); break;
    case "blocked_tool": note(`${t("blocked")}: ${ev.name}`, "error"); break;
    case "assistant_text": bubble(ev.text, "agent"); break;
    case "notice": note(ev.text, ev.level === "error" ? "error" : ev.level === "warn" ? "warn" : "info"); break;
    case "approval_required": setThinking(false); approvalCard(ev); break;
    case "decision": {
      const ok = ev.status === "committed";
      const v = el("p", "verdict" + (ok ? "" : " neg"), `${t("decided")}: ${ev.decision} → ${ev.status}` + (ev.tx_hash ? ` · tx ${ev.tx_hash.slice(0, 16)}…` : ""));
      (card || $("log")).append(v); scrollEnd(); break;
    }
    case "final": setThinking(false); bubble(ev.text, ev.author === "harness" ? "harness" : "agent"); break;
    case "error": setThinking(false); note(ev.message, "error"); break;
    case "done": setThinking(false); renderUsage(ev.usage); if (ev.planner && S.caps && ev.planner !== S.caps.planner) { S.caps.planner = ev.planner; renderCaps(); } break;
  }
}
function addDocChip(d) { $("attached").append(el("span", "doc-chip", `${t("attachedOk")}: ${d.name}`)); refreshDocs(); }
async function refreshDocs() { try { const v = await (await api(`/sessions/${S.sid}`)).json(); renderDocs(v.docs); } catch (_) {} }
function replay(v) {
  $("log").replaceChildren(); renderDocs(v.docs); renderUsage(v.usage);
  let pendingShown = false;
  for (const ev of v.events) {
    if (ev.type === "approval_required") { if (v.pending && v.pending.job_id === ev.job_id && !pendingShown) { approvalCard(v.pending); pendingShown = true; } continue; }
    if (ev.type === "document") continue;
    handle(ev);
  }
  setThinking(false);
  if (!v.events.length) $("log").append(el("p", "note", t("empty")));
}

// ------------------------------------------------------------------ actions
function setComposer(on) { S.busy = !on; $("send").disabled = !on; $("msg").disabled = !on; }
async function send() {
  const text = $("msg").value.trim(); if (!text || S.busy || !S.sid) return;
  $("msg").value = ""; autosize(); setComposer(false); $("attached").replaceChildren();
  bubble(text, "user");
  try {
    const r = await api(`/sessions/${S.sid}/messages`, { method: "POST", headers: { Accept: "text/event-stream" }, body: JSON.stringify({ text }) });
    const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
    for (;;) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i; while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (line) { try { handle(JSON.parse(line.slice(6))); } catch (err) { console.error("event", err); } }
      }
    }
  } catch (e) { setThinking(false); note(e.message || t("errNet"), "error"); }
  setComposer(true); $("msg").focus();
}
async function attachText(name, text) {
  try { const d = await (await api(`/sessions/${S.sid}/documents`, { method: "POST", body: JSON.stringify({ filename: name, text }) })).json(); addDocChip(d); }
  catch (e) { note(e.message, "error"); }
}
function autosize() { const m = $("msg"); m.style.height = "auto"; m.style.height = Math.min(m.scrollHeight, window.innerHeight * 0.4) + "px"; }
function toggleCase(open) { $("case").classList.toggle("open", open); $("caseBtn").setAttribute("aria-expanded", String(open)); if (open) $("caseClose").focus(); }

document.addEventListener("DOMContentLoaded", () => {
  $("keyForm").addEventListener("submit", (e) => { e.preventDefault(); S.ck = $("ckInput").value.trim(); $("ckInput").value = ""; start(); });
  $("composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  $("msg").addEventListener("input", autosize);
  $("msg").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
  $("file").addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    if (f.size > 400000) { note("> 400 KB", "error"); return; }
    const rd = new FileReader(); rd.onload = () => attachText(f.name, String(rd.result)); rd.readAsText(f); e.target.value = "";
  });
  $("sample").addEventListener("change", async (e) => {
    const v = e.target.value; if (!v) return; e.target.value = "";
    try { const d = await (await api(`/sessions/${S.sid}/documents`, { method: "POST", body: JSON.stringify({ sample: v }) })).json(); addDocChip(d); }
    catch (x) { note(x.message, "error"); }
  });
  $("lang").addEventListener("click", () => { S.lang = S.lang === "ar" ? "en" : "ar"; try { localStorage.setItem("mijhar.lang", S.lang); } catch (_) {} applyLang(); });
  $("caseBtn").addEventListener("click", () => toggleCase(true));
  $("caseClose").addEventListener("click", () => toggleCase(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") toggleCase(false); });
  $("newSession").addEventListener("click", () => { toggleCase(false); newSession(); });
  for (const id of ["prefLang", "prefDetail"]) $(id).addEventListener("change", async () => {
    try { await api("/memory", { method: "POST", body: JSON.stringify({ language: $("prefLang").value, detail: $("prefDetail").value }) }); } catch (e) { note(e.message, "error"); }
  });
  boot();
});
