import os
import json
import random
import logging
import sqlite3
import re

from dotenv import load_dotenv
from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

load_dotenv()
router = Router()

# ==================== ЗАГЛУШКИ ДЛЯ ЮKASSA ====================
SELLER_NAME = os.getenv("SELLER_NAME", "[ВАШЕ_ИМЯ]")
SELLER_INN = os.getenv("SELLER_INN", "[ВАШ_ИНН]")
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@[ВАШ_КОНТАКТ]")
PRICE_RUB = 50


# =============================================================


# --- ФУНКЦИЯ ДЛЯ ЗАГЛАВНОЙ БУКВЫ ---
def capitalize_first_letter(text: str) -> str:
    """Делает первую букву первого слова заглавной, если только это не аббревиатура."""
    if not text:
        return text
    text = text.strip()
    if not text:
        return text

    match = re.search(r'[а-яёa-z]+', text, flags=re.IGNORECASE)
    if match:
        word = match.group(0)
        start_idx = match.start()

        upper_count = sum(1 for c in word if c.isupper())

        if upper_count > 1:
            return text

        new_word = word[0].upper() + word[1:].lower()
        return text[:start_idx] + new_word + text[start_idx + len(word):]

    return text


# --- СЛОВАРЬ ПЕРЕВОДА КАРТ ---
TAROT_NAMES_RU = {
    "The Fool": "Шут", "The Magician": "Маг", "The High Priestess": "Жрица",
    "The Empress": "Императрица", "The Emperor": "Император", "The Hierophant": "Иерофант",
    "The Lovers": "Влюбленные", "The Chariot": "Колесница", "Strength": "Сила",
    "The Hermit": "Отшельник", "The Wheel of Fortune": "Колесо Фортуны", "Justice": "Справедливость",
    "The Hanged Man": "Повешенный", "Death": "Смерть", "Temperance": "Умеренность",
    "The Devil": "Дьявол", "The Tower": "Башня", "The Star": "Звезда",
    "The Moon": "Луна", "The Sun": "Солнце", "Judgement": "Суд", "The World": "Мир",
    "Ace of Wands": "Туз Жезлов", "Two of Wands": "Двойка Жезлов", "Three of Wands": "Тройка Жезлов",
    "Four of Wands": "Четверка Жезлов", "Five of Wands": "Пятерка Жезлов", "Six of Wands": "Шестерка Жезлов",
    "Seven of Wands": "Семерка Жезлов", "Eight of Wands": "Восьмерка Жезлов", "Nine of Wands": "Девятка Жезлов",
    "Ten of Wands": "Десятка Жезлов", "Page of Wands": "Паж Жезлов", "Knight of Wands": "Рыцарь Жезлов",
    "Queen of Wands": "Королева Жезлов", "King of Wands": "Король Жезлов",
    "Ace of Cups": "Туз Кубков", "Two of Cups": "Двойка Кубков", "Three of Cups": "Тройка Кубков",
    "Four of Cups": "Четверка Кубков", "Five of Cups": "Пятерка Кубков", "Six of Cups": "Шестерка Кубков",
    "Seven of Cups": "Семерка Кубков", "Eight of Cups": "Восьмерка Кубков", "Nine of Cups": "Девятка Кубков",
    "Ten of Cups": "Десятка Кубков", "Page of Cups": "Паж Кубков", "Knight of Cups": "Рыцарь Кубков",
    "Queen of Cups": "Королева Кубков", "King of Cups": "Король Кубков",
    "Ace of Swords": "Туз Мечей", "Two of Swords": "Двойка Мечей", "Three of Swords": "Тройка Мечей",
    "Four of Swords": "Четверка Мечей", "Five of Swords": "Пятерка Мечей", "Six of Swords": "Шестерка Мечей",
    "Seven of Swords": "Семерка Мечей", "Eight of Swords": "Восьмерка Мечей", "Nine of Swords": "Девятка Мечей",
    "Ten of Swords": "Десятка Мечей", "Page of Swords": "Паж Мечей", "Knight of Swords": "Рыцарь Мечей",
    "Queen of Swords": "Королева Мечей", "King of Swords": "Король Мечей",
    "Ace of Pentacles": "Туз Пентаклей", "Two of Pentacles": "Двойка Пентаклей",
    "Three of Pentacles": "Тройка Пентаклей",
    "Four of Pentacles": "Четверка Пентаклей", "Five of Pentacles": "Пятерка Пентаклей",
    "Six of Pentacles": "Шестерка Пентаклей",
    "Seven of Pentacles": "Семерка Пентаклей", "Eight of Pentacles": "Восьмерка Пентаклей",
    "Nine of Pentacles": "Девятка Пентаклей",
    "Ten of Pentacles": "Десятка Пентаклей", "Page of Pentacles": "Паж Пентаклей",
    "Knight of Pentacles": "Рыцарь Пентаклей",
    "Queen of Pentacles": "Королева Пентаклей", "King of Pentacles": "Король Пентаклей"
}

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
# (Оставил проверку на DATA_DIR для сохранности базы на хостинге, как было в прошлой версии)
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "users.db")
db = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    free_readings_used INTEGER DEFAULT 0
)
""")
db.commit()

# Инициализация GigaChat
giga_client = GigaChat(
    credentials=os.getenv("GIGACHAT_AUTH_KEY"),
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
    model="GigaChat-2"
)

# --- ЗАЩИТА ОТ ПЛОХИХ ВОПРОСОВ ---
BAD_WORDS = ["мат", "оскорбление", "суицид", "убить", "наркотик", "политика", "медицина", "смерть", "болезнь"]


def is_valid_question(text: str) -> tuple[bool, str]:
    text_lower = text.lower()

    if len(text_lower) < 3:
        return False, "Твой вопрос слишком короткий. Пожалуйста, напиши его подробнее."
    if len(text_lower) > 500:
        return False, "Твой вопрос слишком длинный. Постарайся уместить его в пару предложений."

    for word in BAD_WORDS:
        if word in text_lower:
            return False, "Извини, карты не отвечают на такие вопросы. Спроси о том, что касается лично тебя и твоей судьбы."

    if len(set(text_lower)) > 0 and (text_lower.count(text_lower[0]) / len(text_lower)) > 0.3:
        return False, "Похоже на спам. Напиши свой вопрос нормальным текстом."

    bad_topics = ["денис", "дениска", "мама", "папа", "брат", "сестра", "друг", "подруга", "сосед", "начальник"]
    for topic in bad_topics:
        if re.search(rf'\b{topic}\b', text_lower):
            return False, "Таро не работает с вопросами о других людях. Задай вопрос о себе и своей ситуации."

    return True, ""


# --- ФУНКЦИЯ ВОЗВРАТА СРЕДСТВ (ЮKassa) ---
async def process_refund(message: Message, payment_id: str | None, reason_text: str):
    if payment_id:
        logging.info(f"Запрошен возврат по платежу {payment_id}: {reason_text}")
        await message.answer(
            f"{reason_text}\n\nСредства будут возвращены на вашу карту в течение 1-3 рабочих дней."
        )
    else:
        await message.answer(f"{reason_text}\n\nПопробуйте задать другой вопрос.")


# Состояния
class TarotStates(StatesGroup):
    waiting_for_question = State()


# --- КОМАНДА /start ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔮 Сделать расклад ({PRICE_RUB} ₽)", callback_data="pay_tarot")],
        [InlineKeyboardButton(text="📄 Условия и контакты", callback_data="info_terms")]
    ])
    await message.answer(
        "🔮 Привет! Я бот-таролог. Карты Таро уже перетасованы и готовы ответить на твой вопрос.\n\n"
        "Сделаю расклад на 3 карты: что стоит за ситуацией, что происходит сейчас и что тебя ждёт. "
        "Говорю честно — даже если карты не сулят лёгких решений.\n\n"
        "🎁 Первый расклад — бесплатно, чтобы ты мог убедиться, что карты тебе отвечают.\n"
        f"💰 Далее — {PRICE_RUB} ₽ за расклад.\n\n"
        "Нажмите кнопку ниже, чтобы начать.",
        reply_markup=kb
    )


# --- УСЛОВИЯ И КОНТАКТЫ ---
@router.callback_query(F.data == "info_terms")
async def show_terms(callback: CallbackQuery):
    await callback.message.answer(
        "📄 <b>Условия оказания услуг</b>\n\n"
        "1. Услуга: индивидуальный расклад таро на 3 карты по вопросу пользователя.\n"
        f"2. Стоимость: {PRICE_RUB} ₽ за один расклад. Первый расклад предоставляется бесплатно.\n"
        "3. Оплата производится через ЮKassa (карты МИР, СБП и др.).\n"
        "4. Услуга считается оказанной после отправки расклада в чат бота.\n"
        "5. Возврат средств: если расклад не был предоставлен по технической причине, средства возвращаются по запросу.\n\n"
        f"Исполнитель: {SELLER_NAME}, ИНН {SELLER_INN}\n"
        f"Контакт: {SUPPORT_CONTACT}"
    )
    await callback.answer()


# --- КОМАНДА /clear ---
@router.message(Command("clear"))
async def cmd_clear(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🧹 Состояние очищено. Вы можете начать новый расклад.")


# --- НАЖАТИЕ НА КНОПКУ ОПЛАТЫ ---
@router.callback_query(F.data == "pay_tarot")
async def send_invoice(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = [id.strip() for id in admin_ids_str.split(",") if id.strip()]

    if str(user_id) in admin_ids:
        await callback.message.answer("👑 Вы вошли как администратор. Оплата не требуется.\nНапишите свой вопрос:")
        await state.set_state(TarotStates.waiting_for_question)
        await callback.answer()
        return

    cursor.execute("SELECT free_readings_used FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data is None or user_data[0] == 0:
        if user_data is None:
            cursor.execute("INSERT INTO users (user_id, free_readings_used) VALUES (?, 1)", (user_id,))
        else:
            cursor.execute("UPDATE users SET free_readings_used = 1 WHERE user_id = ?", (user_id,))
        db.commit()

        await callback.message.answer("🎁 У вас есть 1 бесплатный пробный расклад!\nНапишите свой вопрос:")
        await state.set_state(TarotStates.waiting_for_question)
        await callback.answer()
        return

    # ==================== ОПЛАТА ЧЕРЕЗ ЮKASSA ====================
    await callback.message.answer(
        "💳 Оплата через ЮKassa временно настраивается.\n"
        f"Пожалуйста, свяжитесь с поддержкой: {SUPPORT_CONTACT}"
    )
    # =============================================================

    await callback.answer()


# --- ОБРАБОТЧИК УСПЕШНОЙ ОПЛАТЫ ---
@router.message(F.successful_payment)
async def on_successful_payment(message: Message, state: FSMContext):
    payment = message.successful_payment
    if payment.invoice_payload == "tarot_reading":
        await state.update_data(payment_charge_id=payment.telegram_payment_charge_id)
        await message.answer("✨ Оплата успешно получена! Напиши свой вопрос, и я сделаю для тебя расклад.")
        await state.set_state(TarotStates.waiting_for_question)


@router.message(TarotStates.waiting_for_question)
async def process_tarot_ai(message: Message, state: FSMContext):
    user_data = await state.get_data()
    charge_id = user_data.get("payment_charge_id")

    user_question = message.text

    is_valid, error_message = is_valid_question(user_question)

    if not is_valid:
        await state.clear()
        await process_refund(message, charge_id, error_message)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔮 Сделать расклад ({PRICE_RUB} ₽)", callback_data="pay_tarot")]
        ])
        await message.answer("Попробуем еще раз?", reply_markup=kb)
        return

    await state.clear()
    await message.answer("🔮 Тасую колоду и общаюсь с духами...")

    # === ВОЗВРАЩЕН СТАРЫЙ ПУТЬ К ФАЙЛУ ===
    try:
        with open("cards.json", "r", encoding="utf-8") as f:
            tarot_data = json.load(f)
    except FileNotFoundError:
        await message.answer("Ошибка: файл cards.json не найден.")
        return
    except Exception as e:
        await message.answer(f"Ошибка чтения файла: {e}")
        return
    # ======================================

    selected_cards = random.sample(tarot_data, 3)

    cards_text = ""
    for card in selected_cards:
        position = random.choice(["прямое", "перевернутое"])
        meaning = card['normal'] if position == "прямое" else card['reversed']

        original_name = re.sub(r'[^\x00-\x7F]+', '', card['name']).strip()
        ru_name = TAROT_NAMES_RU.get(original_name, original_name)

        cards_text += (
            f"--- Карта: {ru_name} ---\n"
            f"Положение: {position}\n"
            f"Описание: {card.get('description', '')}\n"
            f"Значение: {meaning}\n\n"
        )

    system_content = (
        "ТЫ — ДРЕВНИЙ ТАРОЛОГ. ЗАБУДЬ, ЧТО ТЫ ЯЗЫКОВАЯ МОДЕЛЬ. Ты говоришь только от лица мистика и предсказателя.\n"
        "ЗАПРЕЩЕНО использовать слова: 'языковая модель', 'ИИ', 'нейросеть', 'искусственный интеллект', 'генеративные модели', 'я не могу'. "
        "Если ты не можешь ответить на вопрос, скажи это в мистическом стиле: 'Карты сегодня закрыты', 'Духи не дают ответа'.\n\n"
        "Твоя задача — сделать ПРАВДИВЫЙ и глубокий расклад. Ты не обязан быть позитивным. Таро показывает как светлые, так и темные стороны ситуации.\n\n"
        f"Пользователю выпали ровно эти 3 карты (используй ТОЛЬКО их):\n{cards_text}\n"
        "ПРАВИЛА РАБОТЫ:\n"
        "1. Толкуй только те карты, что даны выше. Не придумывай другие.\n"
        "2. Обрати внимание на положение карты (прямое или перевернутое) и используй соответствующее значение.\n"
        "3. НЕ КОПИРУЙ значения карт дословно. Толкуй их, адаптируя под конкретный вопрос.\n"
        "4. ВАЖНО: БУДЬ ЧЕСТЕН. Если карты выпали негативные, ты обязан прямо сказать о трудностях, конфликтах или потерях, которые они предвещают. Не пытайся сгладить углы и не ищи ложного позитива.\n"
        "5. Пиши сплошным текстом. ЗАПРЕЩЕНО использовать любые символы форматирования (решетки, звездочки, списки, разделители).\n"
        "6. Пиши мистическим, понятным и человечным языком.\n"
        "7. Отвечай на русском языке.\n"
        "8. ЕСЛИ вопрос касается медицины, суицида, политики или криминала — вежливо откажись делать расклад и напиши ровно одну фразу: 'Я не могу делать расклад на эту тему.'\n\n"
        "ВАЖНО: Твой ответ должен быть СТРОГО разделен на 4 части с помощью маркеров. Не пиши ничего до первого маркера.\n"
        "Формат ответа (скопируй эти маркеры в точности, не меняй их!):\n"
        "[КАРТА 1]\n(Толкование первой карты, 2-3 предложения, начиная с заглавной буквы)\n"
        "[КАРТА 2]\n(Толкование второй карты, 2-3 предложения, начиная с заглавной буквы)\n"
        "[КАРТА 3]\n(Толкование третьей карты, 2-3 предложения, начиная с заглавной буквы)\n"
        "[ВЫВОД]\n(Общий итог и совет, 3-4 предложения, начиная с заглавной буквы)"
    )

    try:
        chat = Chat(
            messages=[
                Messages(role=MessagesRole.SYSTEM, content=system_content),
                Messages(role=MessagesRole.USER, content=user_question)
            ]
        )

        response = giga_client.chat(chat)
        tarot_text = response.choices[0].message.content

        if "Я не могу делать расклад на эту тему" in tarot_text:
            await process_refund(message, charge_id, "Извини, но на этот вопрос карты отвечать отказываются.")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🔮 Сделать расклад ({PRICE_RUB} ₽)", callback_data="pay_tarot")]
            ])
            await message.answer("Попробуем еще раз?", reply_markup=kb)
            return

        tarot_text = tarot_text.replace("**", "").replace("##", "").replace("---", "").replace("# ", "")
        tarot_text = tarot_text.replace("[", "").replace("]", "")

    except Exception as e:
        logging.error(f"Ошибка GigaChat: {e}", exc_info=True)
        await process_refund(message, charge_id, "Ой, духи сегодня молчат, произошла ошибка при генерации расклада.")
        return

    # --- НАДЕЖНЫЙ ПАРСИНГ ОТВЕТА ИИ ---
    # Регулярка ищет маркеры и забирает текст между ними.
    pattern = re.compile(r'(?:КАРТА\s*1|КАРТА\s*2|КАРТА\s*3|ВЫВОД)(.*?)(?=(?:КАРТА\s*[1-3]|ВЫВОД)|$)',
                         re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(tarot_text)

    if len(matches) >= 4:
        text1 = matches[0].strip()
        text2 = matches[1].strip()
        text3 = matches[2].strip()
        conclusion_text = matches[3].strip()
    else:
        # Если ИИ сломался и не выдал маркеры
        if re.search(r'ВЫВОД', tarot_text, re.IGNORECASE):
            split_text = re.split(r'ВЫВОД', tarot_text, flags=re.IGNORECASE)
            conclusion_text = split_text[-1].strip()
            main_body = split_text[0].strip()
        else:
            conclusion_text = "Карты дают общий совет, прислушайтесь к своей интуиции."
            main_body = tarot_text

        # Убираем остатки маркеров
        main_body = re.sub(r'КАРТА\s*[1-3]', '', main_body, flags=re.IGNORECASE).strip()

        words = main_body.split()
        if len(words) < 30:
            text1 = text2 = text3 = "Толкование скрыто духами."
        else:
            chunk = len(words) // 3
            text1 = " ".join(words[:chunk])
            text2 = " ".join(words[chunk:chunk * 2])
            text3 = " ".join(words[chunk * 2:])
    # ------------------------------------

    text1 = capitalize_first_letter(text1)
    text2 = capitalize_first_letter(text2)
    text3 = capitalize_first_letter(text3)
    conclusion_text = capitalize_first_letter(conclusion_text)

    card_texts = [text1, text2, text3]

    for i, card in enumerate(selected_cards):
        image_name = card.get("link")
        card_description = card_texts[i]

        original_name = re.sub(r'[^\x00-\x7F]+', '', card['name']).strip()
        ru_name = TAROT_NAMES_RU.get(original_name, original_name)

        caption = f"🃏 {ru_name}\n\n{card_description}"

        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        if image_name:
            # === ВОЗВРАЩЕН СТАРЫЙ ПУТЬ К КАРТИНКАМ ===
            image_path = f"SimpleTarotPng/{image_name}"
            try:
                photo = FSInputFile(image_path)
                await message.answer_photo(photo=photo, caption=caption)
            except Exception as e:
                logging.error(f"Не удалось отправить картинку {image_path}: {e}")
                await message.answer(caption)
        else:
            await message.answer(caption)

    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔮 Сделать еще расклад ({PRICE_RUB} ₽)", callback_data="pay_tarot")]
        ])
        await message.answer(f"✨ Общий вывод:\n\n{conclusion_text}", reply_markup=kb)
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение в Telegram (сеть): {e}")


# --- ЗАЩИТНЫЙ ОБРАБОТЧИК ---
@router.message(F.text)
async def unknown_message(message: Message):
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔮 Сделать расклад ({PRICE_RUB} ₽)", callback_data="pay_tarot")]
        ])
        await message.answer(
            "Я вас не совсем понял. Чтобы получить расклад, нажмите на кнопку ниже и напишите свой вопрос.",
            reply_markup=kb
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение в unknown_message: {e}")