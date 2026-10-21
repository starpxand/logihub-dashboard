/* Плавный пересчёт KPI: при смене фильтров числа в карточках перетекают от прежнего значения к новому.
   Dash подключает файлы из assets/ автоматически. */
(() => {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const last = new Map();                                   // заголовок карточки -> прежние числа
  const NUM = /\d+(?:,\d+)?/g;
  const parse = (t) => (t.match(NUM) || []).map((s) => parseFloat(s.replace(",", ".")));
  const fmt = (v, like) => { const dec = (like.split(",")[1] || "").length; return v.toFixed(dec).replace(".", ","); };

  function animate(el, from, to) {
    const tpl = el.textContent, parts = tpl.match(NUM) || [];
    const t0 = performance.now(), dur = 650;
    const step = (now) => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      let i = 0;
      el.textContent = tpl.replace(NUM, (m) => { const a = from[i] ?? to[i], b = to[i]; i += 1; return fmt(a + (b - a) * e, m); });
      if (k < 1 && el.isConnected) requestAnimationFrame(step); else el.textContent = tpl;
    };
    if (parts.length) requestAnimationFrame(step);
  }

  new MutationObserver(() => {
    document.querySelectorAll("#kpi-indicators .lh-kpi").forEach((card) => {
      const el = card.querySelector(".lh-kpi-value"), key = card.querySelector(".lh-kpi-title")?.textContent;
      if (!el || el.dataset.seen) return;
      el.dataset.seen = "1";
      const to = parse(el.textContent), from = last.get(key) || to.map(() => 0);
      last.set(key, to);
      if (to.some((v, i) => v !== from[i])) animate(el, from, to);
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
