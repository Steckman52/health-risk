import logging
from typing import Any, Dict, List, Tuple

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, KeyboardButton, Update
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import BACKEND_URL

router = Router()
log = logging.getLogger("bot")

RISK_RU = {"low": "низкий", "medium": "умеренный", "high": "высокий"}

DIAB_FIELDS: List[Tuple[str, str]] = [
    ("Age", "Возраст (лет)"),
    ("Gender", "Пол (м/ж)"),
    ("BMI", "ИМТ (кг/м²)"),
    ("Chol", "Общий холестерин (ммоль/л)"),
    ("TG", "Триглицериды (ммоль/л)"),
    ("HDL", "ЛПВП (HDL) (ммоль/л)"),
    ("LDL", "ЛПНП (LDL) (ммоль/л)"),
    ("Cr", "Креатинин (мкмоль/л или мг/дл)"),
    ("BUN", "Мочевина (BUN) (ммоль/л или мг/дл)"),
]
HEART_FIELDS: List[Tuple[str, str]] = [
    ("age", "Возраст (лет)"),
    ("height", "Рост (см)"),
    ("weight", "Масса (кг)"),
    ("ap_hi", "Систолическое АД (ap_hi)"),
    ("ap_lo", "Диастолическое АД (ap_lo)"),
    ("cholesterol", "Холестерин (категория 1..3)"),
    ("gluc", "Глюкоза (категория 1..3)"),
    ("smoke", "Курение (0/1)"),
    ("alco", "Алкоголь (0/1)"),
    ("active", "Физ. активность (0/1)"),
]

def kb_main():
    rkb = ReplyKeyboardBuilder()
    rkb.add(
        KeyboardButton(text="Диабет"),
        KeyboardButton(text="Сердце"),
        KeyboardButton(text="История"),
        KeyboardButton(text="Отмена"),
    )
    rkb.adjust(2)
    return rkb.as_markup(resize_keyboard=True)


def kb_cancel():
    rkb = ReplyKeyboardBuilder()
    rkb.add(KeyboardButton(text="Отмена"))
    return rkb.as_markup()


def _to_float(s: str) -> float:
    s = str(s).strip().replace(",", ".")
    return float(s)


def _to_int01(s: str) -> int:
    s = str(s).strip().lower()
    return 1 if s in ("1", "да", "y", "yes", "true", "истина", "on", "вкл") else 0


def _to_gender01(s: str) -> int:
    t = str(s).strip().lower()
    return 1 if t in ("1", "m", "м", "male", "муж", "мужской") else 0


def _preview(fields: List[Tuple[str, str]]) -> str:
    lines = ["🧪 Введите данные:"]
    for _, label in fields: lines.append(f"• {label}")
    return "\n".join(lines)


class DiabetesForm(StatesGroup):
    collecting = State()


class HeartForm(StatesGroup):
    collecting = State()


#  FSM логика
async def _start_collect(message: Message, state: FSMContext, *, analysis: str, fields: List[Tuple[str, str]]):
    await message.answer(_preview(fields), reply_markup=kb_cancel())
    await state.update_data(analysis=analysis, fields=fields, answers={}, index=0)
    await _ask_next(message, state)


async def _ask_next(message: Message, state: FSMContext):
    data = await state.get_data()
    fields: List[Tuple[str, str]] = data["fields"]
    index: int = data["index"]
    if index >= len(fields):
        await _submit(message, state);
        return
    _, label = fields[index]
    await message.answer(f"Введите: <b>{label}</b>")


async def _submit(message: Message, state: FSMContext):
    data = await state.get_data()
    analysis: str = data["analysis"]
    answers: Dict[str, Any] = data["answers"]

    if analysis == "diabetes":
        features = {
            "Age": _to_float(answers.get("Age", '0')),
            "Gender": _to_gender01(answers.get("Gender", '0')),
            "BMI": _to_float(answers.get("BMI", '0')),
            "Chol": _to_float(answers.get("Chol", '0')),
            "TG": _to_float(answers.get("TG", '0')),
            "HDL": _to_float(answers.get("HDL", '0')),
            "LDL": _to_float(answers.get("LDL", '0')),
            "Cr": _to_float(answers.get("Cr", '0')),
            "BUN": _to_float(answers.get("BUN", '0')),
        }
        model = "rf";
        title = "Диабет"
    else:
        features = {
            "age": _to_float(answers.get("age", '0')),
            "height": _to_float(answers.get("height", '0')),
            "weight": _to_float(answers.get("weight", '0')),
            "ap_hi": _to_float(answers.get("ap_hi", '0')),
            "ap_lo": _to_float(answers.get("ap_lo", '0')),
            "cholesterol": int(_to_float(answers.get("cholesterol", '1'))),
            "gluc": int(_to_float(answers.get("gluc", '1'))),
            "smoke": _to_int01(answers.get("smoke", '0')),
            "alco": _to_int01(answers.get("alco", '0')),
            "active": _to_int01(answers.get("active", '0')),
        }
        model = "heart";
        title = "Сердце"

    payload = {"analysis_type": analysis, "model": model, "features": features}
    url = f"{BACKEND_URL}/api/v1/predict"

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=15) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"backend {resp.status}: {text}")
                data = await resp.json()
    except Exception as e:
        await message.answer(f"❗ Ошибка запроса: {e}", reply_markup=kb_main())
        await state.clear()
        return

    risk = float(data.get("risk", 0.0))
    cat_ru = data.get("risk_category_ru") or RISK_RU.get(str(data.get("risk_category", "")).lower(), "")
    rec = data.get("recommendation", "")

    await message.answer(
        "✅ Результат:\n"
        f"Тип анализа: <b>{title}</b>\n"
        f"Риск: <b>{risk:.3f}</b>\n"
        f"Категория: <b>{cat_ru}</b>\n"
        f"Рекомендация: {rec}",
        reply_markup=kb_main()
    )
    await state.clear()


# Хендлеры
@router.message(Command(commands=["start", "help"]))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Выберите анализ: «Диабет» или «Сердце». Доступна «История».",
        reply_markup=kb_main()
    )


@router.message(lambda m: m.text and m.text.lower().strip() == "отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=kb_main())


@router.message(lambda m: m.text and m.text.lower().strip() == "диабет")
async def cmd_diab(message: Message, state: FSMContext):
    await state.set_state(DiabetesForm.collecting)
    await _start_collect(message, state, analysis="diabetes", fields=DIAB_FIELDS)


@router.message(lambda m: m.text and m.text.lower().strip() == "сердце")
async def cmd_heart(message: Message, state: FSMContext):
    await state.set_state(HeartForm.collecting)
    await _start_collect(message, state, analysis="heart", fields=HEART_FIELDS)


@router.message(lambda m: m.text and m.text.lower().strip() == "история")
async def cmd_history(message: Message):
    url = f"{BACKEND_URL}/api/v1/logs?limit=10"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(f"backend {resp.status}: {text}")
                data = await resp.json()
    except Exception as e:
        await message.answer(f"❗ История недоступна: {e}", reply_markup=kb_main());
        return

    if not data:
        await message.answer("История пуста.", reply_markup=kb_main());
        return

    lines = ["🧾 Последние запросы:"]
    for item in data:
        analysis = item.get("analysis_type", "")
        risk = float(item.get("risk", 0.0))
        cat_ru = item.get("risk_category_ru") or RISK_RU.get(str(item.get("risk_category", "")).lower(), "")
        lines.append(f"• {analysis}: риск {risk:.3f}, {cat_ru}")
    await message.answer("\n".join(lines), reply_markup=kb_main())


@router.message(DiabetesForm.collecting)
@router.message(HeartForm.collecting)
async def process_input(message: Message, state: FSMContext):
    data = await state.get_data()
    fields: List[Tuple[str, str]] = data["fields"]
    index: int = data["index"]
    answers: Dict[str, Any] = data["answers"]

    key, label = fields[index]
    value = (message.text or "").strip()

    try:
        if key in ("Age", "BMI", "Chol", "TG", "HDL", "LDL", "Cr", "BUN", "age", "height", "weight", "ap_hi", "ap_lo"):
            _ = _to_float(value)
        elif key in ("cholesterol", "gluc"):
            v = int(_to_float(value))
            if v not in (1, 2, 3):
                await message.answer("Допустимо: 1, 2 или 3. Повторите ввод:");
                return
        elif key in ("smoke", "alco", "active"):
            _ = _to_int01(value)
        elif key == "Gender":
            _ = _to_gender01(value)
    except Exception:
        await message.answer("Нужно число (запятая/точка допустимы). Повторите ввод:");
        return

    answers[key] = value
    await state.update_data(answers=answers, index=index + 1)
    await _ask_next(message, state)


@router.errors()
async def errors_handler(update, error):
    log.exception("Unhandled error: %s", error)
    try:
        if isinstance(update, Update) and update.message:
            await update.message.answer("❗ Ошибка. Попробуйте ещё раз.", reply_markup=kb_main())
    except Exception as ex:
        print(ex)
    return True
