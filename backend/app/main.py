"""Сервер «Шаг за шагом» — точка входа.

Запуск без Docker (из папки backend):
    uvicorn app.main:app --reload
"""
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import knowledge, llm, safety
from .config import settings
from .db import Base, SessionLocal, engine, get_db
from .models import ChatSession, Clinic, Event, Message
from .schemas import (
    ChatIn, ChatOut, ClinicInfo, HelpContact, MessageOut, RatingIn,
    SessionCreate, SessionOut, SoberDateIn, StatsOut,
)

MSK = ZoneInfo("Europe/Moscow")


def init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        clinic = db.scalar(select(Clinic).where(Clinic.key == settings.demo_clinic_key))
        if not clinic:
            # Токен не задан в .env — придумываем случайный, чтобы кабинет не открывался стандартным паролем
            clinic = Clinic(
                key=settings.demo_clinic_key,
                name="Демо-клиника",
                phone=settings.demo_clinic_phone,
                admin_token=settings.demo_admin_token or secrets.token_urlsafe(12),
            )
            db.add(clinic)
        elif settings.demo_admin_token:
            clinic.admin_token = settings.demo_admin_token
        db.commit()
        print(f"Кабинет клиники: ключ «{clinic.key}», токен «{clinic.admin_token}»", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Шаг за шагом — API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


# ---------- вспомогательное ----------

_rate: dict[str, deque] = defaultdict(deque)


def check_rate_limit(key: str, limit: int) -> None:
    now = time.monotonic()
    if len(_rate) > 10_000:  # чистим старые ключи, чтобы словарь не рос бесконечно
        for k in [k for k, q in _rate.items() if not q or now - q[-1] > 60]:
            del _rate[k]
    q = _rate[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Слишком много сообщений подряд. Подожди немного и напиши снова.")
    q.append(now)


def client_ip(request: Request) -> str:
    # shortcut: X-Real-IP ставит наш nginx; без nginx перед сервером заголовок можно подделать
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def get_session_or_404(db: Session, session_id: str) -> ChatSession:
    s = db.get(ChatSession, session_id)
    if not s:
        raise HTTPException(404, "Сессия не найдена")
    return s


def sober_days(d: date | None) -> int | None:
    if not d:
        return None
    return max((datetime.now(MSK).date() - d).days, 0)


def session_out(s: ChatSession) -> SessionOut:
    return SessionOut(
        session_id=s.id,
        mode=s.mode,
        clinic=ClinicInfo(key=s.clinic.key, name=s.clinic.name) if s.clinic else None,
        sober_since=s.sober_since,
        sober_days=sober_days(s.sober_since),
    )


def help_contacts(clinic: Clinic | None) -> list[HelpContact]:
    contacts = [HelpContact(title="Экстренная помощь", subtitle="если есть угроза жизни", phone="112")]
    if settings.helpline_phone:
        contacts.append(HelpContact(title="Телефон доверия", subtitle="бесплатно, анонимно", phone=settings.helpline_phone))
    if clinic and clinic.phone:
        contacts.append(HelpContact(title="Твоя клиника", subtitle=clinic.name, phone=clinic.phone))
    return contacts


def log_event(db: Session, clinic_id: int | None, kind: str) -> None:
    db.add(Event(clinic_id=clinic_id, kind=kind))


# ---------- API ----------

@app.get("/api/health")
def health():
    # llm_error не пустой — последний запрос к YandexGPT не прошёл, и бот отвечает шаблонами
    return {"status": "ok", "llm": "yandexgpt" if settings.llm_enabled else "demo", "llm_error": llm.last_error}


@app.post("/api/sessions", response_model=SessionOut)
def create_session(data: SessionCreate, request: Request, db: Session = Depends(get_db)):
    check_rate_limit("new:" + client_ip(request), settings.max_new_sessions_per_minute)
    clinic = None
    if data.clinic_key:
        clinic = db.scalar(select(Clinic).where(Clinic.key == data.clinic_key))
    s = ChatSession(mode=data.mode, clinic_id=clinic.id if clinic else None)
    db.add(s)
    log_event(db, s.clinic_id, "session")
    db.commit()
    db.refresh(s)
    return session_out(s)


@app.get("/api/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return session_out(get_session_or_404(db, session_id))


@app.get("/api/sessions/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    s = get_session_or_404(db, session_id)
    return [MessageOut.model_validate(m, from_attributes=True) for m in s.messages]


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    s = get_session_or_404(db, session_id)
    db.delete(s)
    db.commit()
    _rate.pop(session_id, None)
    return {"deleted": True}


@app.put("/api/sessions/{session_id}/sober-date", response_model=SessionOut)
def set_sober_date(session_id: str, data: SoberDateIn, db: Session = Depends(get_db)):
    s = get_session_or_404(db, session_id)
    if data.sober_since and data.sober_since > datetime.now(MSK).date():
        raise HTTPException(400, "Дата не может быть в будущем")
    s.sober_since = data.sober_since
    db.commit()
    return session_out(s)


@app.get("/api/sessions/{session_id}/help", response_model=list[HelpContact])
def get_help(session_id: str, db: Session = Depends(get_db)):
    return help_contacts(get_session_or_404(db, session_id).clinic)


@app.get("/api/step-of-day")
def get_step_of_day():
    return knowledge.step_of_day(datetime.now(MSK).timetuple().tm_yday)


@app.post("/api/chat", response_model=ChatOut)
async def chat(data: ChatIn, request: Request, db: Session = Depends(get_db)):
    s = get_session_or_404(db, data.session_id)
    text = data.text.strip()
    if not text:
        raise HTTPException(400, "Пустое сообщение")
    if len(text) > settings.max_message_length:
        raise HTTPException(400, f"Сообщение слишком длинное (максимум {settings.max_message_length} символов)")
    check_rate_limit("ip:" + client_ip(request), settings.max_messages_per_minute_per_ip)
    check_rate_limit(s.id, settings.max_messages_per_minute)

    user_msg = Message(session_id=s.id, role="user", text=text)
    db.add(user_msg)
    log_event(db, s.clinic_id, "message")

    # Слой 1: код (работает всегда, нейросеть не может его отменить)
    crisis = safety.detect_crisis(text)
    distress = not crisis and safety.detect_distress(text)
    attack = safety.detect_attack(text)
    # Слой 2: ИИ-проверка (если подключён YandexGPT)
    if not (crisis or distress or attack):
        guard = await llm.guard_check(text)
        crisis = guard["crisis"]
        attack = guard["attack"]

    help_list = None
    blocked = False
    if crisis:
        reply = safety.CRISIS_REPLY
        help_list = help_contacts(s.clinic)
        user_msg.is_crisis = True
        log_event(db, s.clinic_id, "crisis")
    elif distress:
        # «Мне плохо» и похожее — сразу карточка помощи, как в экстренном случае
        reply = safety.DISTRESS_REPLY
        help_list = help_contacts(s.clinic)
        user_msg.is_crisis = True
        crisis = True
        log_event(db, s.clinic_id, "distress")
    elif attack:
        reply = safety.ATTACK_REPLY
        blocked = True
        log_event(db, s.clinic_id, "blocked")
    else:
        found = knowledge.search(text, s.mode)
        history = [{"role": m.role, "text": m.text} for m in s.messages][-settings.history_messages_for_llm:]
        if not history or history[-1]["text"] != text:
            history.append({"role": "user", "text": text})
        try:
            reply = await llm.generate_reply(history, s.mode, found)
        except llm.LLMError:
            reply = llm.demo_reply(text, s.mode, found)
        # Слой 3: проверка ответа перед показом
        if not safety.check_bot_reply(reply):
            reply = safety.UNSAFE_REPLY_FALLBACK
            blocked = True
            log_event(db, s.clinic_id, "blocked")

    bot_msg = Message(session_id=s.id, role="bot", text=reply, is_crisis=crisis)
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)
    return ChatOut(message_id=bot_msg.id, reply=reply, crisis=crisis, blocked=blocked, help=help_list)


@app.post("/api/messages/{message_id}/rating")
def rate_message(message_id: int, data: RatingIn, db: Session = Depends(get_db)):
    m = db.get(Message, message_id)
    if not m or m.session_id != data.session_id or m.role != "bot":
        raise HTTPException(404, "Сообщение не найдено")
    if m.rating is None:  # засчитываем только первую оценку, иначе статистика раздувается
        m.rating = data.value
        log_event(db, m.session.clinic_id, "rating_up" if data.value == 1 else "rating_down")
        db.commit()
    return {"ok": True}


@app.get("/api/clinics/{key}/stats", response_model=StatsOut)
def clinic_stats(key: str, x_admin_token: str = Header(default=""), db: Session = Depends(get_db)):
    clinic = db.scalar(select(Clinic).where(Clinic.key == key))
    if not clinic or not secrets.compare_digest(x_admin_token.encode(), clinic.admin_token.encode()):
        raise HTTPException(403, "Нет доступа")
    count = defaultdict(int, db.execute(
        select(Event.kind, func.count()).where(Event.clinic_id == clinic.id).group_by(Event.kind)
    ).all())
    by_hour = [0] * 24
    for created in db.scalars(
        select(Event.created_at).where(Event.clinic_id == clinic.id, Event.kind == "message")
    ):
        created = created if created.tzinfo else created.replace(tzinfo=ZoneInfo("UTC"))
        by_hour[created.astimezone(MSK).hour] += 1
    night = sum(by_hour[h] for h in list(range(22, 24)) + list(range(0, 6)))
    total = sum(by_hour)
    return StatsOut(
        clinic=clinic.name,
        sessions=count["session"],
        messages=count["message"],
        crisis=count["crisis"],
        distress=count["distress"],
        blocked=count["blocked"],
        rating_up=count["rating_up"],
        rating_down=count["rating_down"],
        night_share=round(night / total, 2) if total else 0.0,
        by_hour=by_hour,
    )


# ---------- раздача сайта (для запуска без Docker) ----------

if settings.static_dir and Path(settings.static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")
