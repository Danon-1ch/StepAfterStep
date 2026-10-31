/* «Шаг за шагом» — логика чата. Без фреймворков, чистый JavaScript. */
(function () {
  "use strict";

  const API = "/api";
  const params = new URLSearchParams(location.search);
  const clinicKey = params.get("clinic") || "";
  const embedded = params.get("embed") === "1";
  const storageKey = "shag_session_" + (clinicKey || "none");

  const $ = (id) => document.getElementById(id);
  let sessionId = null;
  let mode = "patient";
  let sending = false;

  // ---------- хранение id сессии в браузере ----------
  function loadSessionId() {
    try { return localStorage.getItem(storageKey); } catch (e) { return null; }
  }
  function saveSessionId(id) {
    try { id ? localStorage.setItem(storageKey, id) : localStorage.removeItem(storageKey); } catch (e) { /* приватный режим */ }
  }

  // ---------- запросы к серверу ----------
  async function api(path, options = {}) {
    const res = await fetch(API + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* пустой ответ */ }
    if (!res.ok) {
      const err = new Error((data && data.detail) || "Ошибка сервера");
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // ---------- экраны ----------
  function show(screen) {
    ["welcome", "chat", "progress"].forEach((s) => $("screen-" + s).classList.toggle("hidden", s !== screen));
    const inApp = screen !== "welcome";
    $("tabs").classList.toggle("hidden", !inApp);
    $("btn-sos").classList.toggle("hidden", !inApp);
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === screen));
    if (screen === "progress") loadProgress();
    if (screen === "chat") $("input").focus();
  }

  function applySession(s) {
    sessionId = s.session_id;
    mode = s.mode;
    saveSessionId(sessionId);
    if (s.clinic) $("clinic-name").textContent = s.clinic.name;
  }

  // ---------- сообщения ----------
  const box = $("messages");
  function scrollDown() { box.scrollTop = box.scrollHeight; }

  function addUser(text) {
    const div = document.createElement("div");
    div.className = "msg user";
    div.textContent = text;
    box.appendChild(div);
    scrollDown();
  }

  function addBot(text, messageId, rating) {
    const wrap = document.createElement("div");
    wrap.className = "bot-block";
    const msg = document.createElement("div");
    msg.className = "msg bot";
    msg.textContent = text;
    wrap.appendChild(msg);
    if (messageId) wrap.appendChild(ratingRow(messageId, rating));
    box.appendChild(wrap);
    scrollDown();
  }

  function ratingRow(messageId, current) {
    const row = document.createElement("div");
    row.className = "rate";
    row.innerHTML = '<span>Ответ помог?</span>';
    const make = (value, label, rotate) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", label);
      b.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"' +
        (rotate ? ' style="transform:rotate(180deg)"' : "") +
        '><path d="M7 10v11M7 10l4-7a2 2 0 0 1 3 2v4h5a2 2 0 0 1 2 2.3l-1.4 7A2 2 0 0 1 17.6 21H7"/></svg>';
      if (current === value) b.classList.add("on");
      b.disabled = current === 1 || current === -1; // оценка ставится один раз
      b.addEventListener("click", async () => {
        try {
          await api(`/messages/${messageId}/rating`, { method: "POST", body: JSON.stringify({ session_id: sessionId, value }) });
          b.classList.add("on");
          row.querySelectorAll("button").forEach((x) => { x.disabled = true; });
        } catch (e) { /* не критично */ }
      });
      return b;
    };
    row.appendChild(make(1, "Помогло", false));
    row.appendChild(make(-1, "Не помогло", true));
    return row;
  }

  function addHelpCard(contacts) {
    const card = document.createElement("section");
    card.className = "help-card";
    card.setAttribute("aria-label", "Экстренная помощь");
    const h = document.createElement("h2");
    h.textContent = "Помощь рядом — прямо сейчас";
    card.appendChild(h);
    contacts.forEach((c, i) => {
      const a = document.createElement("a");
      a.className = "help-item " + (i === 0 ? "main" : c.title === "Твоя клиника" ? "clinic" : "second");
      a.href = "tel:" + c.phone.replace(/[^\d+]/g, "");
      const t = document.createElement("span");
      t.className = "t";
      const b = document.createElement("b"); b.textContent = c.title;
      const small = document.createElement("small"); small.textContent = c.subtitle;
      t.appendChild(b); t.appendChild(small);
      const ph = document.createElement("span"); ph.className = "ph"; ph.textContent = c.phone;
      a.appendChild(t); a.appendChild(ph);
      card.appendChild(a);
    });
    box.appendChild(card);
    scrollDown();
  }

  function addError(text) {
    const p = document.createElement("p");
    p.className = "error-line";
    p.textContent = text;
    box.appendChild(p);
    scrollDown();
  }

  function setTyping(on) {
    let t = $("typing");
    if (on && !t) {
      t = document.createElement("div");
      t.id = "typing";
      t.className = "typing";
      t.setAttribute("aria-label", "Консультант печатает");
      t.innerHTML = "<span></span><span></span><span></span>";
      box.appendChild(t);
      scrollDown();
    } else if (!on && t) {
      t.remove();
    }
  }

  async function send(text) {
    text = text.trim();
    if (!text || sending) return;
    sending = true;
    $("btn-send").disabled = true;
    addUser(text);
    setTyping(true);
    try {
      const r = await api("/chat", { method: "POST", body: JSON.stringify({ session_id: sessionId, text }) });
      setTyping(false);
      addBot(r.reply, r.crisis || r.blocked ? null : r.message_id, null);
      if (r.crisis && r.help) addHelpCard(r.help);
    } catch (e) {
      setTyping(false);
      if (e.status === 404) { resetSession(); return; }
      addError(e.message + ". Если тебе плохо — нажми «Мне плохо» вверху.");
    } finally {
      sending = false;
      $("btn-send").disabled = false;
    }
  }

  async function loadHistory() {
    const msgs = await api(`/sessions/${sessionId}/messages`);
    box.innerHTML = "";
    if (!msgs.length) {
      addBot(mode === "relative"
        ? "Здравствуйте. Расскажите, что происходит с вашим близким и как вы сами?"
        : "Привет. Я здесь. Расскажи, как ты сейчас?");
    }
    msgs.forEach((m) => (m.role === "user" ? addUser(m.text) : addBot(m.text, m.is_crisis ? null : m.id, m.rating)));
  }

  // ---------- мой путь ----------
  function plural(n, one, few, many) {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }

  async function loadProgress() {
    const [s, step] = await Promise.all([api(`/sessions/${sessionId}`), api("/step-of-day")]);
    const d = s.sober_days;
    $("days").textContent = d === null ? "—" : d;
    $("days-unit").textContent = d === null ? "дней" : plural(d, "день", "дня", "дней");
    $("since").textContent = s.sober_since
      ? "с " + new Date(s.sober_since).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })
      : "укажи дату ниже";
    if (s.sober_since) $("sober-date").value = s.sober_since;
    $("sober-date").max = new Date().toISOString().slice(0, 10);

    const marks = [[1, "день"], [7, "неделя"], [30, "месяц"], [90, "3 мес."], [365, "год"]];
    const ms = $("milestones");
    ms.innerHTML = "";
    let nextShown = false;
    let nextText = "";
    marks.forEach(([n, label]) => {
      const el = document.createElement("div");
      el.className = "ms";
      if (d !== null && d >= n) el.classList.add("done");
      else if (d !== null && !nextShown) {
        el.classList.add("next");
        nextShown = true;
        const left = n - d;
        nextText = `До этапа «${label}» — ${left} ${plural(left, "день", "дня", "дней")}`;
      }
      el.innerHTML = `<i>${n}</i><span>${label}</span>`;
      ms.appendChild(el);
    });
    $("next-ms").textContent = nextText;

    $("step-title").textContent = step.title;
    $("step-text").textContent = step.text;
  }

  // ---------- кнопки ----------
  document.querySelectorAll(".choice").forEach((b) =>
    b.addEventListener("click", () => {
      document.querySelectorAll(".choice").forEach((x) => x.classList.remove("selected"));
      b.classList.add("selected");
      mode = b.dataset.mode;
    })
  );

  $("btn-start").addEventListener("click", async () => {
    $("btn-start").disabled = true;
    try {
      const s = await api("/sessions", { method: "POST", body: JSON.stringify({ clinic_key: clinicKey || null, mode }) });
      applySession(s);
      await loadHistory();
      show("chat");
    } catch (e) {
      alert("Не удалось подключиться к серверу. Попробуй ещё раз.");
    } finally {
      $("btn-start").disabled = false;
    }
  });

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("input").value;
    $("input").value = "";
    send(text);
  });

  document.querySelectorAll("#quick button").forEach((b) =>
    b.addEventListener("click", async () => {
      if (b.textContent === "Шаг дня") {
        const step = await api("/step-of-day");
        addBot(`Шаг дня — «${step.title}». ${step.text}`);
      } else {
        send(b.textContent);
      }
    })
  );

  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => show(t.dataset.tab)));

  $("btn-sos").addEventListener("click", async () => {
    show("chat");
    try {
      addHelpCard(await api(`/sessions/${sessionId}/help`));
      addBot("Я рядом. Если есть угроза жизни — звони 112 прямо сейчас. Можешь написать мне, что происходит.");
    } catch (e) {
      addHelpCard([{ title: "Экстренная помощь", subtitle: "если есть угроза жизни", phone: "112" }]);
    }
  });

  $("btn-save-date").addEventListener("click", async () => {
    const v = $("sober-date").value || null;
    try {
      await api(`/sessions/${sessionId}/sober-date`, { method: "PUT", body: JSON.stringify({ sober_since: v }) });
      loadProgress();
    } catch (e) {
      alert(e.message);
    }
  });

  let confirmDelete = false;
  $("btn-delete").addEventListener("click", async () => {
    const btn = $("btn-delete");
    if (!confirmDelete) {
      confirmDelete = true;
      btn.textContent = "Нажми ещё раз, чтобы удалить навсегда";
      btn.classList.add("confirm");
      setTimeout(() => { confirmDelete = false; btn.textContent = "Удалить мою историю"; btn.classList.remove("confirm"); }, 4000);
      return;
    }
    try { await api(`/sessions/${sessionId}`, { method: "DELETE" }); } catch (e) { /* уже удалена */ }
    resetSession();
  });

  if (embedded) {
    $("btn-close").classList.remove("hidden");
    $("btn-close").addEventListener("click", () => window.parent.postMessage({ type: "shag:close" }, "*"));
  }

  function resetSession() {
    saveSessionId(null);
    sessionId = null;
    box.innerHTML = "";
    $("clinic-name").textContent = "на связи 24/7";
    show("welcome");
  }

  // ---------- тема ----------
  function isDark() {
    const t = document.documentElement.dataset.theme;
    if (t) return t === "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function updateThemeButton() {
    const dark = isDark();
    $("btn-theme").setAttribute("aria-label", dark ? "Светлая тема" : "Тёмная тема");
    $("btn-theme").querySelector(".ico-moon").style.display = dark ? "none" : "";
    $("btn-theme").querySelector(".ico-sun").style.display = dark ? "" : "none";
  }
  $("btn-theme").addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("shag_theme", next); } catch (e) { /* приватный режим */ }
    updateThemeButton();
  });
  if (window.matchMedia) window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", updateThemeButton);
  updateThemeButton();

  // ---------- старт ----------
  (async function init() {
    const saved = loadSessionId();
    if (!saved) return show("welcome");
    try {
      applySession(await api(`/sessions/${saved}`));
      await loadHistory();
      show("chat");
    } catch (e) {
      resetSession();
    }
  })();
})();
