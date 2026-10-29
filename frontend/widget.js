/*
 * Виджет «Шаг за шагом» для сайта клиники.
 * Клиника вставляет на свой сайт одну строку:
 *   <script src="https://АДРЕС-СЕРВИСА/widget.js" data-clinic="КЛЮЧ"></script>
 * В правом нижнем углу появится кнопка «Поговорить», которая открывает чат.
 */
(function () {
  "use strict";
  const script = document.currentScript;
  if (!script) return;
  const clinic = script.getAttribute("data-clinic") || "";
  const base = new URL(script.src).origin;
  const chatUrl = base + "/index.html?embed=1" + (clinic ? "&clinic=" + encodeURIComponent(clinic) : "");

  const style = document.createElement("style");
  style.textContent = `
    .shag-btn{position:fixed;right:24px;bottom:24px;z-index:2147483000;display:flex;align-items:center;gap:10px;
      padding:16px 24px;border:none;border-radius:999px;background:#2F7D6D;color:#fff;font:700 17px Arial,sans-serif;
      box-shadow:0 8px 24px rgba(47,125,109,.35);cursor:pointer}
    .shag-btn:hover{background:#1F5C50}
    .shag-hint{position:fixed;right:24px;bottom:96px;z-index:2147483000;width:280px;padding:16px 18px;background:#fff;
      border:1px solid #E3E8E7;border-radius:16px;box-shadow:0 8px 24px rgba(31,42,46,.12);font:14px/1.45 Arial,sans-serif;color:#4A565C}
    .shag-hint b{display:block;margin-bottom:4px;color:#1F2A2E;font-size:16px}
    .shag-frame{position:fixed;right:24px;bottom:24px;z-index:2147483001;width:400px;height:680px;max-width:calc(100vw - 32px);
      max-height:calc(100vh - 48px);border:none;border-radius:20px;box-shadow:0 16px 48px rgba(31,42,46,.25);background:#fff}
    @media (max-width:520px){.shag-frame{right:0;bottom:0;width:100vw;height:100vh;max-width:100vw;max-height:100vh;border-radius:0}}
  `;
  document.head.appendChild(style);

  const hint = document.createElement("div");
  hint.className = "shag-hint";
  hint.innerHTML = "<b>Тяжело прямо сейчас?</b>Поговорите анонимно с консультантом «Шаг за шагом». Без регистрации, 24/7.";

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "shag-btn";
  btn.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>Поговорить';

  let frame = null;
  function open() {
    if (!frame) {
      frame = document.createElement("iframe");
      frame.className = "shag-frame";
      frame.title = "Чат «Шаг за шагом»";
      frame.src = chatUrl;
      document.body.appendChild(frame);
    }
    frame.style.display = "block";
    btn.style.display = "none";
    hint.style.display = "none";
  }
  function close() {
    if (frame) frame.style.display = "none";
    btn.style.display = "flex";
  }

  btn.addEventListener("click", open);
  window.addEventListener("message", (e) => {
    if (e.origin === base && e.data && e.data.type === "shag:close") close();
  });

  document.body.appendChild(hint);
  document.body.appendChild(btn);
  setTimeout(() => { hint.style.display = "none"; }, 10000);
})();
