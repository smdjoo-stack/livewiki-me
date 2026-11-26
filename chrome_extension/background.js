// 툴바의 확장 아이콘을 눌러도 패널이 열리게
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});

// 유튜브 화면의 "✨ 요약" 버튼 → 패널 열고 요약 시작
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type !== "open-and-summarize" || !sender.tab) return;
  const tabId = sender.tab.id;
  // sidePanel.open은 버튼 클릭 직후에 바로 불러야 해서 await 없이 먼저 호출
  chrome.sidePanel.open({ tabId }).catch((e) => console.warn(e));
  chrome.storage.session.set({ autostart: { url: msg.url, tabId, at: Date.now() } });
});
