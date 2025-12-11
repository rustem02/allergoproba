from datetime import date
from typing import Literal, Optional, Dict, List

import base64
import io
import os
import random

import qrcode
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field



TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TELEGRAM_DEFAULT_CHAT_ID = os.getenv("TELEGRAM_DEFAULT_CHAT_ID")
TELEGRAM_BOT_USERNAME = "allergoproba_bot"


def _send_telegram_message(chat_id: int, text: str) -> None:

    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
    except Exception:
        pass



class Patient(BaseModel):
    iin: str = Field(..., min_length=12, max_length=12)
    full_name: str
    phone_whatsapp: str
    date_of_birth: date
    telegram_chat_id: Optional[int] = None


class OrderCreate(BaseModel):
    clinic_name: str
    doctor_name: str
    tariff: str
    allergens: List[str]
    patient: Patient


class OrderStatusUpdate(BaseModel):
    status: Literal["blood_taken", "results_ready"]


class ResultUpdate(BaseModel):
    results: Dict[str, str]  # {"Lidocaine": "Negative", ...}


class Order(BaseModel):
    id: int
    code: str                  # code (98765)
    status: Literal[
        "created",
        "sent_to_telegram",
        "blood_taken",
        "results_ready",
    ]
    clinic_name: str
    doctor_name: str
    tariff: str
    allergens: List[str]
    patient: Patient
    qr_data_url: str           # PNG base64
    results: Optional[Dict[str, str]] = None



app = FastAPI(title="AllergoProba Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

ORDERS: Dict[str, Order] = {}   # key — order.code
NEXT_ID = 1

BASE_URL = "http://127.0.0.1:8001"


def _generate_order_code() -> str:
    # типа 98765
    num = random.randint(10000, 99999)
    return f"{num}"


def _generate_qr_data_url(text: str) -> str:
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _notify_new_order(order: Order, referral_url: str) -> None:

    chat_id = order.patient.telegram_chat_id or (
        int(TELEGRAM_DEFAULT_CHAT_ID) if TELEGRAM_DEFAULT_CHAT_ID else None
    )
    if not chat_id:
        return

    text = (
        f"Здравствуйте, {order.patient.full_name}!\n\n"
        f"Для вас оформлено направление на аллергопробы.\n"
        f"Код заказа: <b>ORD-{order.code}</b>\n\n"
        f"Перейдите по ссылке и покажите этот экран в лаборатории:\n"
        f"{referral_url}"
    )
    _send_telegram_message(chat_id, text)


def _notify_results_ready(order: Order, results_url: str) -> None:

    chat_id = order.patient.telegram_chat_id or (
        int(TELEGRAM_DEFAULT_CHAT_ID) if TELEGRAM_DEFAULT_CHAT_ID else None
    )
    if not chat_id:
        return

    text = (
        f"Здравствуйте, {order.patient.full_name}!\n\n"
        f"Результаты ваших аллергопроб готовы.\n"
        f"Код заказа: <b>ORD-{order.code}</b>\n\n"
        f"Посмотреть результаты можно по ссылке:\n"
        f"{results_url}"
    )
    _send_telegram_message(chat_id, text)


# apis

@app.get("/", response_class=HTMLResponse)
async def serve_dentist_page(request: Request):
    return templates.TemplateResponse("dentist.html", {"request": request})

@app.get("/lab", response_class=HTMLResponse)
async def serve_lab_page(request: Request):
    return templates.TemplateResponse("lab.html", {"request": request})

@app.get("/patient-referral", response_class=HTMLResponse)
async def serve_patient_referral_page(request: Request):
    return templates.TemplateResponse("patient_referral.html", {"request": request})

@app.get("/patient-results", response_class=HTMLResponse)
async def serve_patient_results_page(request: Request):
    return templates.TemplateResponse("patient_results.html", {"request": request})


@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate):

    global NEXT_ID

    order_code = _generate_order_code()
    referral_url = f"{BASE_URL}/patient_referral.html?code={order_code}"
    telegram_url = f"https://t.me/{TELEGRAM_BOT_USERNAME}?text={order_code}"
    qr = _generate_qr_data_url(telegram_url)

    order = Order(
        id=NEXT_ID,
        code=order_code,
        status="sent_to_telegram",  # created + send to Telegram
        clinic_name=payload.clinic_name,
        doctor_name=payload.doctor_name,
        tariff=payload.tariff,
        allergens=payload.allergens,
        patient=payload.patient,
        qr_data_url=qr,
        results=None,
    )

    ORDERS[order.code] = order
    NEXT_ID += 1

    _notify_new_order(order, referral_url)

    return order


@app.get("/orders/{code}", response_model=Order)
def get_order(code: str):

    order = ORDERS.get(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders/by-iin/{iin}", response_model=List[Order])
def find_orders_by_iin(iin: str):

    return [o for o in ORDERS.values() if o.patient.iin == iin]


@app.get("/patient/{code}/referral", response_model=Order)
def patient_referral(code: str):
    order = ORDERS.get(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.post("/lab/{code}/blood-taken", response_model=Order)
def mark_blood_taken(code: str):
    order = ORDERS.get(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "blood_taken"
    ORDERS[code] = order
    return order


@app.post("/lab/{code}/results", response_model=Order)
def upload_results(code: str, payload: ResultUpdate):
    order = ORDERS.get(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.results = payload.results
    order.status = "results_ready"
    ORDERS[code] = order

    results_url = f"{BASE_URL}/patient/{order.code}/results"
    _notify_results_ready(order, results_url)

    return order


@app.get("/patient/{code}/results", response_model=Order)
def get_results(code: str):
    order = ORDERS.get(code)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
