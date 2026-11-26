// 페이지(또는 그 안의 iframe)에서 본문을 뽑아냄. lib/Readability.js 다음에 주입됨.
// 마지막 식의 값이 executeScript 결과로 돌아감.
(() => {
  const BLOCKS = "p,h1,h2,h3,h4,h5,h6,li,blockquote,pre,figcaption,td,th,dd,dt,div,section";
  const meta = (sel) => document.querySelector(sel)?.getAttribute("content")?.trim() || "";

  // 본문 HTML → 문단 단위 텍스트 (안쪽에 다른 블록이 없는 요소만 모아 중복 방지)
  function toText(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    doc.querySelectorAll("br").forEach((br) => br.replaceWith("\n"));
    doc.querySelectorAll("script,style,noscript,button,iframe").forEach((el) => el.remove());
    const out = [];
    for (const el of doc.body.querySelectorAll(BLOCKS)) {
      if (el.querySelector(BLOCKS)) continue; // 바깥 껍데기는 건너뜀
      let t = el.textContent.replace(/[​﻿]/g, "").replace(/[ \t ]+/g, " ").replace(/\n\s*\n+/g, "\n").trim();
      if (!t) continue;
      if (/^h[1-6]$/i.test(el.tagName)) t = "### " + t;
      else if (el.tagName === "LI") t = "- " + t;
      else if (el.tagName === "BLOCKQUOTE") t = "> " + t;
      out.push(t);
    }
    // 연속 중복 제거
    const dedup = out.filter((t, i) => t !== out[i - 1]);
    const text = dedup.join("\n\n").trim();
    return text || doc.body.textContent.replace(/\s+/g, " ").trim();
  }

  let article = null;
  try {
    article = new Readability(document.cloneNode(true), { charThreshold: 200 }).parse();
  } catch (e) {
    article = null;
  }
  const text = article ? toText(article.content || "") : (document.body?.innerText || "").trim();
  const clean = (v) => (v || "").replace(/\s+/g, " ").trim();
  return {
    frameUrl: location.href,
    title: clean((article && article.title) || meta('meta[property="og:title"]') || document.title),
    site: (article && article.siteName) || meta('meta[property="og:site_name"]') || location.hostname,
    byline: clean((article && article.byline) || meta('meta[name="author"]') || meta('meta[property="article:author"]')),
    published:
      (article && article.publishedTime) ||
      meta('meta[property="article:published_time"]') ||
      meta('meta[name="date"]') ||
      meta('meta[property="og:regDate"]') ||
      "",
    lang: document.documentElement.lang || "",
    text,
    length: text.length,
  };
})();
