import json
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

AUTH_KEY = "MDFhMWZlZjUtNWJiZi03NzA5LTgzNWQtOGNhZmZjNjU0NDI1OmIwMTk1NzkwLTg5YTgtNGQ2Ny04NTY2LWVmODNiZmEwNjE0ZQ=="

client = GigaChat(
    credentials=AUTH_KEY,
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
    model="GigaChat-2"
)

# 1. Читаем файл с картами
try:
    with open("cards.json", "r", encoding="utf-8") as f:
        tarot_data = json.load(f)
except Exception as e:
    print(f"Ошибка чтения карт: {e}")
    exit()

# 2. Формируем текст базы знаний для нейросети
# Берем только названия и значения, чтобы не перегружать лимит токенов
cards_text = ""
for card in tarot_data:
    cards_text += f"Карта: {card['name']}. Значение: {card['normal']}.\n"

# 3. Отправляем запрос
system_prompt = f"Ты — опытный таролог. Вот база знаний карт:\n{cards_text}\n\nСделай расклад из 3 случайных карт на вопрос пользователя. Опиши каждую карту и дай общий совет. Отвечай мистическим тоном."

chat = Chat(
    messages=[
        Messages(role=MessagesRole.SYSTEM, content=system_prompt),
        Messages(role=MessagesRole.USER, content="Привет! Сделай мне короткий расклад Таро на сегодня.")
    ]
)

try:
    response = client.chat(chat)
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Ошибка при запросе: {e}")