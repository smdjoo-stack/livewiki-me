// 툴바의 확장 아이콘을 눌러도 패널이 열리게
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});

// 마우스 오른쪽 클릭 메뉴: 아무 페이지에서나 "라이브위키로 이 페이지 요약"
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "lw-summarize-page",
    title: "라이브위키로 이 페이지 요약",
    contexts: ["page", "selection", "link", "image"],
    documentUrlPatterns: ["https://*/*", "http://*/*"],
  });
});

function startSummary(tab, url) {
  // sidePanel.open은 사용자 동작 직후에 바로 불러야 해서 await 없이 먼저 호출
  chrome.sidePanel.open({ tabId: tab.id }).catch((e) => console.warn(e));
  chrome.storage.session.set({ autostart: { url, tabId: tab.id, at: Date.now() } });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "lw-summarize-page" && tab) startSummary(tab, tab.url);
});

// 유튜브 화면의 "✨ 요약" 버튼 → 패널 열고 요약 시작
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type !== "open-and-summarize" || !sender.tab) return;
  startSummary(sender.tab, msg.url);
});
