const HOST = "com.livewiki.me";
const $ = (id) => document.getElementById(id);

let current = { url: null, tabId: null, vid: null, path: null, markdown: "", sections: [], active: 0 };
let busy = false;

// ── 화면 전환 ─────────────────────────────────────
let viewState = "idle";
function show(state) {
  viewState = state;
  for (const id of ["idle", "loading", "error", "result", "settings"]) $(id).hidden = id !== state;
  $("tools").hidden = state !== "result";
  $("tabs").hidden = state !== "result";
}

function videoId(url) {
  try {
    const u = new URL(url);
    if (u.hostname.endsWith("youtube.com") && u.pathname === "/watch") return u.searchParams.get("v");
    if (u.hostname === "youtu.be") return u.pathname.slice(1, 12);
  } catch (_) {}
  return null;
}

// ── 내 Mac의 요약기와 대화 ───────────────────────
function askHost(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(HOST, message, (reply) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: "요약기에 연결하지 못했어요.\n(설치 프로그램 install.sh를 실행했는지 확인해 주세요)\n\n" + chrome.runtime.lastError.message });
      } else resolve(reply || { ok: false, error: "응답이 비어 있어요." });
    });
  });
}

let pending = null; // 요약 중에 다른 영상 요약을 누르면 여기에 대기
let syncing = 0;    // 탭 따라가기 요청 번호 (오래된 응답 무시용)

function freshCurrent(url, tabId) {
  return { url, tabId, vid: videoId(url), path: null, markdown: "", sections: [], active: 0 };
}

async function summarize(url, tabId, force = false) {
  if (busy) {
    if (videoId(url) !== current.vid || force) {
      pending = { url, tabId, force };
      $("loading-next").hidden = false;
    }
    return;
  }
  busy = true;
  syncing++;
  current = freshCurrent(url, tabId);
  $("loading-next").hidden = true;
  show("loading");
  const reply = await askHost({ action: "summarize", url, force });
  busy = false;
  if (pending) {
    // 대기 중인 다음 영상으로 (방금 것도 summaries 폴더에는 저장됨)
    const next = pending;
    pending = null;
    return summarize(next.url, next.tabId, next.force);
  }
  showReply(reply);
}

function showReply(reply) {
  if (!reply.ok) {
    $("error-text").textContent = reply.error;
    show("error");
    return;
  }
  current.path = reply.path;
  current.markdown = reply.markdown;
  current.saved = !!reply.saved;
  current.folder = reply.folder;
  renderResult(reply.markdown);
  updateSaveUI();
  show("result");
}

// ── 저장: 요약은 먼저 보여 주기만 하고, 💾 저장을 눌러야 summaries 폴더에 들어감 ──
let saveDir = "";

function shortPath(p) {
  return (p || "").replace(/^\/Users\/[^/]+/, "~").replace(/^[A-Za-z]:\\Users\\[^\\]+/, "~");
}
function folderName(p) {
  return (p || "").split(/[\\/]/).filter(Boolean).pop() || p;
}

function updateSaveUI() {
  $("save").disabled = current.saved;
  $("save").textContent = current.saved ? "저장됨 ✓" : "💾 저장";
  $("save").title = current.saved ? shortPath(current.folder) : "저장 위치: " + shortPath(saveDir);
  $("reveal").hidden = !current.saved;
  $("save-note").textContent = current.saved ? "📁 " + folderName(current.folder) : "아직 저장 안 됨";
  $("save-note").title = current.saved ? shortPath(current.folder) : "";
}

async function loadSettings() {
  const r = await askHost({ action: "settings" });
  if (r.ok) {
    saveDir = r.save_dir;
    $("save-dir-name").textContent = shortPath(saveDir);
    if (!$("result").hidden) updateSaveUI();
  }
}

async function doSave(other) {
  if (!current.path) return;
  const vid = current.vid;
  $("save-menu").hidden = true;
  $("save").disabled = true;
  if (other) $("save-note").textContent = "폴더 선택 창을 확인하세요…";
  const reply = await askHost({ action: "save", path: current.path, other });
  if (current.vid !== vid) return;
  if (!reply.ok) {
    updateSaveUI();
    if (!reply.cancelled) $("save-note").textContent = "저장 실패: " + reply.error;
    return;
  }
  current.path = reply.path;
  current.folder = reply.folder;
  current.saved = true;
  updateSaveUI();
}

$("save").addEventListener("click", () => !current.saved && doSave(false));
$("save-more").addEventListener("click", (e) => {
  e.stopPropagation();
  $("save-menu").hidden = !$("save-menu").hidden;
});
document.addEventListener("click", (e) => {
  if (!e.target.closest("#save-menu")) $("save-menu").hidden = true;
});
$("save-menu").addEventListener("click", async (e) => {
  const act = e.target.closest("button")?.dataset.act;
  if (act === "other") doSave(true);
  if (act === "setdir") {
    $("save-menu").hidden = true;
    $("save-note").textContent = "폴더 선택 창을 확인하세요…";
    const r = await askHost({ action: "set_save_dir" });
    if (r.ok) {
      saveDir = r.save_dir;
      $("save-dir-name").textContent = shortPath(saveDir);
    }
    updateSaveUI();
  }
});
loadSettings();

// ── 섹션(## 제목)별로 나눠 탭으로 보여주기 ─────────────
const SHORT = { "핵심 요약": "핵심", "아티클 요약": "아티클", "타임라인 요약": "타임라인", "전체 스크립트": "스크립트", "구성별 요약": "구성별" };

function splitSections(md) {
  const head = [], sections = [];
  for (const line of md.split("\n")) {
    const m = line.match(/^## (.+)$/);
    if (m) sections.push({ title: m[1].trim(), lines: [] });
    else if (sections.length) sections[sections.length - 1].lines.push(line);
    else head.push(line);
  }
  return { head: head.join("\n"), sections: sections.map((s) => ({ title: s.title, md: s.lines.join("\n").trim() })) };
}

function renderResult(md) {
  const { head, sections } = splitSections(md);
  current.sections = sections;
  $("doc-head").innerHTML = renderMarkdown(head);
  $("sections").innerHTML = sections
    .map((s, i) => {
      const isScript = s.title === "전체 스크립트";
      const toggle = isScript
        ? `<label class="autoscroll"><input type="checkbox" id="auto"${autoOn() ? " checked" : ""}> 자동 스크롤 <span class="muted">(재생 위치 따라가기)</span></label>`
        : "";
      return `<div class="section${isScript ? " script" : ""}" data-i="${i}" hidden>${toggle}${renderMarkdown(s.md)}</div>`;
    })
    .join("") + chatSectionHtml(sections.length);
  setupChat();
  // 스크립트 줄마다 시작 시간(초) 기억
  document.querySelectorAll("#sections .script p.line").forEach((p) => {
    const a = p.querySelector("a.ts");
    try { p.dataset.t = new URL(a.href).searchParams.get("t") || "0"; } catch (_) {}
  });
  $("auto")?.addEventListener("change", (e) => {
    try { localStorage.setItem("lw-auto", e.target.checked ? "1" : "0"); } catch (_) {}
    if (e.target.checked) pausedUntil = 0;
  });
  lastLine = null;
  $("tabs").innerHTML = sections
    .map((s, i) => `<a data-i="${i}">${esc(SHORT[s.title] || s.title)}</a>`)
    .join("") + `<a data-i="${sections.length}">💬 AI 채팅</a>`;
  let saved = 0;
  try { saved = Number(localStorage.getItem("lw-tab")) || 0; } catch (_) {}
  selectTab(saved <= sections.length ? saved : 0);
}

function selectTab(i) {
  current.active = i;
  document.querySelectorAll("#sections .section").forEach((el) => (el.hidden = Number(el.dataset.i) !== i));
  document.querySelectorAll("#tabs a").forEach((el) => el.classList.toggle("active", Number(el.dataset.i) === i));
  try { localStorage.setItem("lw-tab", String(i)); } catch (_) {}
  const s = current.sections[i];
  const isChat = i === current.sections.length;
  $("tools").hidden = isChat;
  $("copy-sec").textContent = s ? `${SHORT[s.title] || "섹션"} 복사` : "복사";
  window.scrollTo(0, isChat ? document.body.scrollHeight : 0);
  if (isChat) $("chat-input")?.focus();
  lastLine?.classList.remove("now");
  lastLine = null;
  followVideo();
}

// ── AI 채팅 ──────────────────────────────────────
const SUGGEST = ["이 영상의 결론은 뭔가요?", "내 삶에 적용할 점 3가지", "어려운 용어를 쉽게 풀어 주세요", "가장 인상적인 예화는?"];
let chat = { vid: null, msgs: [], waiting: false };

function chatKey(vid) { return "lw-chat-" + vid; }

function chatSectionHtml(i) {
  return `<div class="section chat" data-i="${i}" hidden>
    <div class="chat-top"><span class="muted">영상 내용을 바탕으로 답해요. 답 속 시간을 누르면 그 장면으로 가요.</span>
      <button id="chat-clear" class="link">대화 지우기</button></div>
    <div id="chat-log"></div>
    <div id="chat-suggest">${SUGGEST.map((q) => `<button class="chip">${esc(q)}</button>`).join("")}</div>
    <form id="chat-form">
      <textarea id="chat-input" rows="2" placeholder="영상에 대해 물어보세요 (Enter 보내기 · Shift+Enter 줄바꿈)"></textarea>
      <button type="submit" class="primary" id="chat-send">보내기</button>
    </form>
  </div>`;
}

function setupChat() {
  chat = { vid: current.vid, msgs: [], waiting: false };
  try { chat.msgs = JSON.parse(localStorage.getItem(chatKey(current.vid)) || "[]"); } catch (_) {}
  drawChat();
  $("chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat($("chat-input").value); });
  $("chat-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendChat($("chat-input").value); }
  });
  $("chat-suggest").addEventListener("click", (e) => {
    const b = e.target.closest("button.chip");
    if (b) sendChat(b.textContent);
  });
  $("chat-clear").addEventListener("click", () => {
    chat.msgs = [];
    saveChat();
    drawChat();
  });
  $("chat-log").addEventListener("click", (e) => {
    const b = e.target.closest("button.msg-copy");
    if (b) copyText(b, plainText(chat.msgs[Number(b.dataset.i)].content), "복사");
  });
}

function saveChat() {
  try { localStorage.setItem(chatKey(chat.vid), JSON.stringify(chat.msgs.slice(-40))); } catch (_) {}
}

function drawChat() {
  const log = $("chat-log");
  log.innerHTML = chat.msgs
    .map((m, i) =>
      m.role === "user"
        ? `<div class="msg user">${esc(m.content).replace(/\n/g, "<br>")}</div>`
        : `<div class="msg bot${m.error ? " err" : ""}">${renderMarkdown(m.content)}${m.error ? "" : `<button class="msg-copy link" data-i="${i}">복사</button>`}</div>`
    )
    .join("") + (chat.waiting ? `<div class="msg bot thinking"><span class="dot"></span><span class="dot"></span><span class="dot"></span> 생각 중…</div>` : "");
  $("chat-suggest").hidden = chat.msgs.length > 0 || chat.waiting;
  $("chat-send").disabled = chat.waiting;
  if (current.active === current.sections.length) window.scrollTo(0, document.body.scrollHeight);
}

async function sendChat(text) {
  const question = (text || "").trim();
  if (!question || chat.waiting || !current.path) return;
  $("chat-input").value = "";
  const history = chat.msgs.filter((m) => !m.error).map(({ role, content }) => ({ role, content }));
  chat.msgs.push({ role: "user", content: question });
  chat.waiting = true;
  drawChat();
  const vid = chat.vid;
  const reply = await askHost({ action: "chat", path: current.path, history, question });
  if (chat.vid !== vid) return; // 그 사이 다른 영상으로 바뀜
  chat.waiting = false;
  chat.msgs.push(reply.ok ? { role: "assistant", content: reply.answer } : { role: "assistant", content: "⚠️ " + reply.error, error: true });
  saveChat();
  drawChat();
}

// ── 자동 스크롤: 1초마다 영상 재생 위치를 물어보고, 그 줄을 강조·가운데로 ──
let lastLine = null;
let pausedUntil = 0;

function autoOn() {
  try { return localStorage.getItem("lw-auto") !== "0"; } catch (_) { return true; }
}

// 사용자가 직접 스크롤하면 5초 동안은 따라가지 않음
for (const ev of ["wheel", "touchmove"]) {
  window.addEventListener(ev, () => (pausedUntil = Date.now() + 5000), { passive: true });
}

async function followVideo() {
  const section = document.querySelector("#sections .section.script");
  if (!section || section.hidden || $("result").hidden || !current.tabId) return;
  let state;
  try {
    state = await chrome.tabs.sendMessage(current.tabId, { type: "time" });
  } catch (_) {
    return; // 탭이 닫혔거나 유튜브가 아직 준비 안 됨
  }
  if (!state || state.t == null || state.vid !== current.vid) return;
  let line = null;
  for (const p of section.querySelectorAll("p.line")) {
    if (Number(p.dataset.t) <= state.t) line = p;
    else break;
  }
  if (line === lastLine) return;
  lastLine?.classList.remove("now");
  line?.classList.add("now");
  lastLine = line;
  if (line && $("auto")?.checked && Date.now() > pausedUntil) {
    line.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}
setInterval(followVideo, 1000);

// 복사용 일반 텍스트: [00:30](링크) → [00:30], **굵게** → 굵게, ### 제거
function plainText(md) {
  return md
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, t, href) => (/^\d{1,2}(:\d{2}){1,2}$/.test(t) ? `[${t}]` : `${t} (${href})`))
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/^#{1,3} /gm, "")
    .trim();
}

async function copyText(btn, text, label) {
  await navigator.clipboard.writeText(text);
  btn.textContent = "복사됨 ✓";
  setTimeout(() => (btn.textContent = label), 1500);
}

// ── 간단한 마크다운 → HTML (요약 형식에 맞춘 최소 기능) ──
function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function inline(s) {
  s = esc(s);
  s = s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (_, text, href) => {
    const isTs = /^\d{1,2}(:\d{2}){1,2}$/.test(text);
    return `<a href="${href}"${isTs ? ' class="ts"' : ""}>${text}</a>`;
  });
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]+)/g, '$1<a href="$2">$2</a>');
  return s;
}
function renderMarkdown(md) {
  const out = [];
  let list = null; // "ul" | "ol"
  let lastOl = 0; // 마지막 번호 목록 번호
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { closeList(); continue; }
    if ((m = line.match(/^(#{1,3}) (.*)$/))) {
      closeList();
      lastOl = 0;
      const level = m[1].length;
      const id = level === 2 ? ` id="sec-${m[2].trim().replace(/\s+/g, "-")}"` : "";
      out.push(`<h${level}${id}>${inline(m[2])}</h${level}>`);
    } else if ((m = line.match(/^> ?(.*)$/))) {
      closeList();
      out.push(`<blockquote>${inline(m[1])}</blockquote>`);
    } else if ((m = line.match(/^(\s*)[-*] (.*)$/))) {
      // 번호 목록 아래 들여쓴 하위 목록은 들여서 표시
      const sub = m[1].length >= 2 && lastOl > 0 ? ' class="sub"' : "";
      if (list !== "ul") { closeList(); out.push(`<ul${sub}>`); list = "ul"; }
      out.push(`<li>${inline(m[2])}</li>`);
    } else if ((m = line.match(/^\s*(\d+)\. (.*)$/))) {
      // 중간에 하위 목록이 끼어도 번호가 이어지게 start 지정
      if (list !== "ol") { closeList(); out.push(`<ol start="${m[1]}">`); list = "ol"; }
      lastOl = Number(m[1]);
      out.push(`<li>${inline(m[2])}</li>`);
    } else {
      closeList();
      const isLine = /^\[\d{1,2}(:\d{2}){1,2}\]\(/.test(line);
      out.push(`<p${isLine ? ' class="line"' : ""}>${inline(line)}</p>`);
    }
  }
  closeList();
  return out.join("\n");
}

// ── 링크 클릭: 시간 링크면 보던 영상을 그 장면으로 이동 ──
$("result").addEventListener("click", async (e) => {
  const a = e.target.closest("a");
  if (!a) return;
  e.preventDefault();
  const href = a.getAttribute("href");
  let u;
  try { u = new URL(href); } catch (_) { return; }
  const t = u.searchParams.get("t");
  if (t !== null && current.tabId && videoId(href) === current.vid) {
    try {
      const tab = await chrome.tabs.get(current.tabId);
      if (videoId(tab.url) === current.vid) {
        await chrome.tabs.sendMessage(current.tabId, { type: "seek", t: Number(t) });
        await chrome.tabs.update(current.tabId, { active: true });
        return;
      }
    } catch (_) {}
  }
  chrome.tabs.create({ url: href });
});

// ── 위쪽 바로가기 ───────────────────────────────
$("tabs").addEventListener("click", (e) => {
  const i = e.target.closest("a")?.dataset.i;
  if (i !== undefined) selectTab(Number(i));
});

// ── 아래 버튼들 ─────────────────────────────────
$("copy-sec").addEventListener("click", () => {
  const s = current.sections[current.active];
  if (s) copyText($("copy-sec"), `${s.title}\n\n${plainText(s.md)}`, `${SHORT[s.title] || "섹션"} 복사`);
});
$("copy-all").addEventListener("click", () => copyText($("copy-all"), plainText(current.markdown), "전체 복사"));
$("reveal").addEventListener("click", () => current.saved && askHost({ action: "reveal", path: current.path }));
$("redo").addEventListener("click", () => current.url && summarize(current.url, current.tabId, true));
$("retry").addEventListener("click", () => current.url && summarize(current.url, current.tabId));
$("start").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && videoId(tab.url)) summarize(tab.url, tab.id);
});

// ── 처음 열릴 때 / 탭이 바뀔 때 ─────────────────────
// ── 지금 보고 있는 탭의 영상 따라가기 ─────────────────
function showIdle(isVideo) {
  $("idle-text").textContent = isVideo ? "이 영상은 아직 요약하지 않았어요." : "유튜브 영상 페이지에서 사용할 수 있어요.";
  $("start").hidden = !isVideo;
  show("idle");
}

async function syncWithTab() {
  if (busy || viewState === "settings") return; // 요약 중·설정 중에는 화면을 바꾸지 않음
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const vid = tab && videoId(tab.url);
  if (!vid) {
    // 유튜브 홈 등: 보고 있던 요약은 그대로 두고, 빈 화면일 때만 안내
    if (!current.vid) showIdle(false);
    return;
  }
  if (vid === current.vid) {
    current.tabId = tab.id;
    current.url = tab.url;
    return;
  }
  // 다른 영상으로 바뀜 → 저장된 요약이 있으면 바로 보여 주고, 없으면 요약하기 버튼
  const my = ++syncing;
  current = freshCurrent(tab.url, tab.id);
  const reply = await askHost({ action: "summarize", url: tab.url, cached_only: true });
  if (my !== syncing || busy) return;
  if (reply.ok && reply.found !== false) showReply(reply);
  else showIdle(true);
}

async function checkAutostart() {
  const { autostart } = await chrome.storage.session.get("autostart");
  if (autostart && Date.now() - autostart.at < 30000) {
    await chrome.storage.session.remove("autostart");
    // 버튼을 누른 탭의 '지금' 주소를 다시 확인해서 사용
    let url = autostart.url;
    try {
      const tab = await chrome.tabs.get(autostart.tabId);
      if (videoId(tab.url)) url = tab.url;
    } catch (_) {}
    summarize(url, autostart.tabId);
    return true;
  }
  return false;
}

chrome.storage.session.onChanged.addListener((changes) => {
  if (changes.autostart?.newValue) checkAutostart();
});
chrome.tabs.onActivated.addListener(syncWithTab);
chrome.tabs.onUpdated.addListener((_id, info, tab) => info.url && tab.active && syncWithTab());
chrome.windows.onFocusChanged.addListener(syncWithTab);

// ── ⚙️ 설정 ────────────────────────────────────────
let beforeSettings = "idle";

async function openSettings(note) {
  if (viewState !== "settings") beforeSettings = viewState;
  show("settings");
  $("conn-test-result").textContent = note || "";
  await refreshStatus();
}

function closeSettings() {
  if (beforeSettings === "settings" || beforeSettings === "loading") beforeSettings = current.markdown ? "result" : "idle";
  show(beforeSettings);
  if (beforeSettings === "idle") syncWithTab();
}

async function refreshStatus() {
  const st = await askHost({ action: "status" });
  const card = $("conn-status");
  if (!st.ok) {
    card.className = "status-card warn";
    card.textContent = "⚠️ " + st.error;
    return st;
  }
  let text, good = true;
  if (st.mode === "api") text = "✅ API 키로 연결돼요 (쓴 만큼 요금)";
  else if (st.mode === "token") text = "✅ Claude 구독 토큰으로 연결돼요";
  else {
    good = false;
    if (st.has_token && !st.has_cli) text = "⚠️ 구독 토큰은 있지만 Claude Code가 설치되어 있지 않아요. Claude Code를 설치하거나 API 키를 넣어 주세요.";
    else if (st.has_cli) text = "⚠️ 아직 연결 정보가 없어요. 아래 ① 구독 토큰을 넣어 주세요.";
    else text = "⚠️ 아직 연결 정보가 없어요. ② API 키를 넣거나, Claude Code를 설치한 뒤 ① 구독 토큰을 넣어 주세요.";
  }
  card.className = "status-card " + (good ? "good" : "warn");
  card.textContent = text + `  · 모델: ${st.model}`;
  $("token-input").placeholder = st.has_token ? "저장됨 — 바꾸려면 새로 붙여넣기" : "sk-ant-oat…";
  $("api-input").placeholder = st.has_api_key ? "저장됨 — 바꾸려면 새로 붙여넣기" : "sk-ant-api…";
  $("token-del").hidden = !st.has_token;
  $("api-del").hidden = !st.has_api_key;
  $("settings-savedir").textContent = shortPath(st.save_dir);
  return st;
}

async function setCredential(kind, value) {
  const r = await askHost({ action: "set_credential", kind, value });
  $("conn-test-result").textContent = r.ok ? (r.deleted ? "지웠어요." : "저장했어요. '연결 시험'을 눌러 확인해 보세요.") : "⚠️ " + r.error;
  $(kind === "token" ? "token-input" : "api-input").value = "";
  refreshStatus();
}

$("gear").addEventListener("click", () => (viewState === "settings" ? closeSettings() : openSettings()));
$("settings-close").addEventListener("click", closeSettings);
$("error-settings").addEventListener("click", () => openSettings());
$("token-save").addEventListener("click", () => setCredential("token", $("token-input").value));
$("api-save").addEventListener("click", () => setCredential("api", $("api-input").value));
$("token-del").addEventListener("click", () => setCredential("token", ""));
$("api-del").addEventListener("click", () => setCredential("api", ""));
$("conn-test").addEventListener("click", async () => {
  $("conn-test").disabled = true;
  $("conn-test-result").textContent = "시험 중… (10초쯤)";
  const r = await askHost({ action: "test" });
  $("conn-test").disabled = false;
  $("conn-test-result").textContent = r.ok ? "✅ 연결 성공! 이제 유튜브에서 ✨ 요약을 눌러 보세요." : "⚠️ " + r.error;
});
$("settings-setdir").addEventListener("click", async () => {
  const r = await askHost({ action: "set_save_dir" });
  if (r.ok) {
    saveDir = r.save_dir;
    $("save-dir-name").textContent = shortPath(saveDir);
  }
  refreshStatus();
});

(async () => {
  // 처음 설치해서 연결 정보가 없으면 설정 화면부터
  const st = await askHost({ action: "status" });
  if (st.ok && st.os === "win32") {
    $("reveal").textContent = "탐색기";
    document.body.classList.add("win");
  }
  if (st.ok && st.mode === "none") {
    await chrome.storage.session.remove("autostart");
    openSettings("처음 사용하시네요. Claude 연결부터 설정해 주세요.");
    return;
  }
  if (!st.ok) {
    $("error-text").textContent = st.error;
    show("error");
    return;
  }
  if (!(await checkAutostart())) syncWithTab();
})();

// 헤더 높이를 CSS에 알려 줘서 '자동 스크롤' 줄이 탭 바로 아래에 붙게
new ResizeObserver(([e]) =>
  document.documentElement.style.setProperty("--header-h", e.target.offsetHeight + "px")
).observe(document.querySelector("header"));
