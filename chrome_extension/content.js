// 유튜브 영상 페이지에 "✨ 요약" 버튼을 넣고, 패널에서 시간 링크를 누르면 영상을 그 장면으로 이동

const BTN_ID = "livewiki-summarize-btn";

function addButton() {
  if (!location.pathname.startsWith("/watch")) {
    document.getElementById(BTN_ID)?.remove();
    return;
  }
  if (document.getElementById(BTN_ID)) return;
  // 영상 제목 바로 아래 줄(채널·좋아요 버튼 줄)에 붙임. 못 찾으면 제목 옆.
  const anchor =
    document.querySelector("#above-the-fold #top-row") ||
    document.querySelector("#above-the-fold #title");
  if (!anchor) return;
  const btn = document.createElement("button");
  btn.id = BTN_ID;
  btn.textContent = "✨ 요약";
  btn.title = "라이브위키로 이 영상 요약하기";
  btn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "open-and-summarize", url: location.href });
  });
  anchor.appendChild(btn);
}

// 유튜브는 페이지를 새로 고치지 않고 영상만 바꾸므로 계속 지켜봄
document.addEventListener("yt-navigate-finish", addButton);
new MutationObserver(addButton).observe(document.body, { childList: true, subtree: true });
addButton();

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg.type === "seek") {
    const v = document.querySelector("video");
    if (v) {
      v.currentTime = msg.t;
      v.play();
    }
    reply({ ok: !!v });
  } else if (msg.type === "time") {
    // 패널의 자동 스크롤용: 지금 재생 위치와 영상 ID
    const v = document.querySelector("video");
    reply({ t: v ? v.currentTime : null, vid: new URLSearchParams(location.search).get("v") });
  }
});
