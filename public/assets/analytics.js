(() => {
  const GA_MEASUREMENT_ID = "";

  if (!/^G-[A-Z0-9]+$/i.test(GA_MEASUREMENT_ID)) {
    return;
  }

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () {
    window.dataLayer.push(arguments);
  };

  window.gtag("js", new Date());
  window.gtag("config", GA_MEASUREMENT_ID);

  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href*="hb.afl.rakuten.co.jp"]');
    if (!link) return;

    const quickCard = link.closest(".quick-card");
    const rankingCard = link.closest(".card");
    const container = quickCard || rankingCard;

    let itemName = "";
    let rank = "";
    let placement = "affiliate_link";

    if (quickCard) {
      itemName = quickCard.querySelector("h3")?.textContent?.trim() || "";
      rank = quickCard.querySelector(".quick-label")?.textContent?.trim() || "";
      placement = "quick_pick";
    } else if (rankingCard) {
      itemName = rankingCard.querySelector("h2")?.textContent?.trim() || "";
      rank = rankingCard.querySelector(".rank")?.textContent?.trim() || "";
      placement = "ranking_card";
    }

    window.gtag("event", "affiliate_click", {
      item_name: itemName,
      item_rank: rank,
      placement,
      page_path: window.location.pathname,
      link_url: link.href,
    });
  }, true);
})();
