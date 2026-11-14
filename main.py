import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Простейший HTTP-сервер, чтобы Render видел открытый порт и не сбрасывал бота
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Запускаем веб-сервер в фоновом потоке
threading.Thread(target=run_web_server, daemon=True).start()
import asyncio
import logging
import sys
import json
import os
import random
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.filters import Command, StateFilter, CommandStart, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    PreCheckoutQuery,
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    ErrorEvent,
    ChatMemberUpdated
)
from aiogram.exceptions import TelegramAPIError

# ==============================================================================ы
# 1. ЗАЩИЩЕННЫЙ ИМПОРТ СЛОВАРЕЙ ВСЕХ УРОВНЕЙ (A1, A2, B1, B2, C1)
# ==============================================================================
try:
    from vocabulary_a1 import WORDS_A1
except ImportError:
    WORDS_A1 = [
        {"word": "Hello", "trans": "[həˈloʊ]", "ru": "Привет", "ex": "Hello world, nice to meet you."},
        {"word": "Cat", "trans": "[kæt]", "ru": "Кот", "ex": "The cat is sleeping on the warm sofa."},
        {"word": "Water", "trans": "[ˈwɔː.tər]", "ru": "Вода", "ex": "Please give me a glass of water."}
    ]

try:
    from vocabulary_a2 import WORDS_A2
except ImportError:
    WORDS_A2 = [
        {"word": "Example", "trans": "[ɪɡˈzɑːm.pəl]", "ru": "Пример", "ex": "This is a classic example of clean code."},
        {"word": "Journey", "trans": "[ˈdʒɜː.ni]", "ru": "Путешествие", "ex": "Life is a long and exciting journey."}
    ]

try:
    from vocabulary_b1 import WORDS_B1
except ImportError:
    WORDS_B1 = [
        {"word": "Access", "trans": "[ˈæk.ses]", "ru": "Доступ", "ex": "Get access to confidential system files."},
        {"word": "Develop", "trans": "[dɪˈvel.əp]", "ru": "Развивать", "ex": "Develop high-performance applications in Python."}
    ]

try:
    from vocabulary_b2 import WORDS_B2
except ImportError:
    WORDS_B2 = [
        {"word": "Ability", "trans": "[əˈbɪl.ə.ti]", "ru": "Способность", "ex": "Natural ability to solve complex mathematical problems."},
        {"word": "Efficient", "trans": "[ɪˈfɪʃ.ənt]", "ru": "Эффективный", "ex": "Efficient algorithms save CPU time and memory."}
    ]

try:
    from vocabulary_c1 import WORDS_C1
except ImportError:
    WORDS_C1 = [
        {"word": "Abundant", "trans": "[əˈbʌn.dənt]", "ru": "Изобильный", "ex": "Abundant natural resources in this specific region."},
        {"word": "Ephemeral", "trans": "[ɪˈfem.ər.əl]", "ru": "Эфемерный", "ex": "Ephemeral digital trends come and go rapidly."}
    ]

# ==============================================================================
# 2. ПРОДВИНУТАЯ СИСТЕМА ЛОГИРОВАНИЯ И КОНФИГУРАЦИЯ
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("LanguageBotCore")

# Токен бота (интегрирован из твоего запроса)
BOT_TOKEN = "9084719584:AAGuBzbaD9qtOEoR4Hw4Ok_eL9Miic35Nb4"
ADMIN_TELEGRAM_ID = 9136166835

# Конфигурация файлов базы данных
DB_FILENAME = "users_database.json"
DB_BACKUP_FILENAME = "users_database_backup.json"
CONFIG_FILENAME = "bot_config.json"

def initialize_database() -> None:
    """Проверка существования файлов базы данных и создание базовой структуры."""
    if not os.path.exists(DB_FILENAME):
        logger.info("Создание нового файла базы данных пользователей...")
        initial_data = {}
        with open(DB_FILENAME, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)

def load_db() -> Dict[str, Any]:
    """Атомарная загрузка базы данных с обработкой исключений и автовосстановлением."""
    initialize_database()
    try:
        with open(DB_FILENAME, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as jde:
        logger.error(f"Поврежден файл JSON базы данных ({jde}). Попытка восстановления из резервной копии...")
        if os.path.exists(DB_BACKUP_FILENAME):
            try:
                with open(DB_BACKUP_FILENAME, "r", encoding="utf-8") as backup_file:
                    data = json.load(backup_file)
                logger.info("База данных успешно восстановлена из бэкапа.")
                return data
            except Exception as be:
                logger.critical(f"Не удалось восстановить базу из бэкапа: {be}")
        return {}
    except Exception as e:
        logger.error(f"Непредвиденная ошибка чтения базы данных: {e}")
        return {}

def save_db(data: Dict[str, Any]) -> None:
    """Безопасное сохранение базы данных с созданием актуального бэкапа."""
    try:
        if os.path.exists(DB_FILENAME):
            shutil.copy(DB_FILENAME, DB_BACKUP_FILENAME)
        with open(DB_FILENAME, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
            logger.error(f"Критическая ошибка при сохранении базы данных: {e}")

# Инициализируем БД при старте модуля
initialize_database()


# ==============================================================================
# 3. РАСШИРЕННЫЕ СОСТОЯНИЯ МАШИНЫ СОСТОЯНИЙ (FSM)
# ==============================================================================
class BotStates(StatesGroup):
    selecting_vocabulary_level = State()
    active_learning_session = State()
    quiz_question_active = State()
    settings_editing_profile = State()
    admin_broadcast_message = State()
    support_dialogue = State()


# ==============================================================================
# 4. ПОЛНЫЙ ДЕТАЛИЗИРОВАННЫЙ СПРАВОЧНИК ПАДЕЖЕЙ И ГРАММАТИКИ
# ==============================================================================
EXTENDED_GRAMMAR_DATABASE = {
    "nominatiivi": {
        "title": "Nominatiivi (Именительный падеж)",
        "questions": "Kuka? Miká? (Кто? Что?)",
        "purpose": "Словарная форма слова, выражающая подлежащее или именную часть сказуемого.",
        "rules": "Не имеет специальных окончаний (нулевое окончание в ед. числе).",
        "examples": [
            "Tämä on auto. (Это машина.)",
            "Koira nukkuu. (Собака спит.)"
        ],
        "tips": "Используется всегда при прямом упоминании предмета в словарях."
    },
    "genetiivi": {
        "title": "Genetiivi (Родительный падеж)",
        "questions": "Kenen? Minkä? (Кого? Чего?)",
        "purpose": "Обозначает принадлежность предмета кому-либо или является объектом для послелогов.",
        "rules": "Стандартное окончание в единственном числе: -n.",
        "examples": [
            "Tämä on isän auto. (Это машина отца.)",
            "Koiran talo. (Дом собаки.)"
        ],
        "tips": "Обратите внимание на чередование ступеней согласных (k-p-t) при добавлении -n."
    },
    "partitiivi": {
        "title": "Partitiivi (Партитив / Частичный падеж)",
        "questions": "Ketä? Mitä? (Кого? Что? / Часть от целого)",
        "purpose": "Применяется после числительных (от 2 и выше), с неисчисляемыми существительными и при отрицании глаголов.",
        "rules": "Основные окончания: -a, -ä, -ta, -tä в зависимости от гармонии гласных.",
        "examples": [
            "Minä syön leipää. (Я ем хлеб — часть буханки.)",
            "Pöydällä on kolme omenaa. (На столе три яблока.)",
            "En ymmärrä. (Я не понимаю — глагол с отрицанием требует партитива.)"
        ],
        "tips": "Самый частый падеж в финском языке, составляющий основу разговорной речи."
    },
    "inessiivi": {
        "title": "Inessiivi (Инессив / Внутренне-местный падеж)",
        "questions": "Missä? (Где? В чем?)",
        "purpose": "Указывает на нахождение объекта внутри закрытого пространства или области.",
        "rules": "Окончание падежа: -ssa / -ssä.",
        "examples": [
            "Olen koulussa. (Я нахожусь в школе.)",
            "Kahvissa on sokeria. (В кофе есть сахар.)"
        ],
        "tips": "Противопоставляется элативу и иллативу (покой внутри объекта)."
    },
    "elatiivi": {
        "title": "Elatiivi (Элатив / Изнутри-исходный падеж)",
        "questions": "Mistä? (Откуда? Из чего?)",
        "purpose": "Обозначает движение изнутри наружу, а также материал, из которого что-то сделано.",
        "rules": "Окончание падежа: -sta / -stä.",
        "examples": [
            "Tulen kaupasta. (Я иду из магазина.)",
            "Pöytä on tehty puusta. (Стол сделан из дерева.)"
        ],
        "tips": "Часто используется с глаголами мнения и ощущения (pitää jostakin — нравиться что-то)."
    },
    "illatiivi": {
        "title": "Illatiivi (Иллатив / Направленно-внутренний падеж)",
        "questions": "Mihin? Minne? (Куда? Внутрь чего?)",
        "purpose": "Обозначает направление движения внутрь объекта или сферы.",
        "rules": "Имеет несколько вариантов: -hVn, -Vn или удлинение конечной гласной + n.",
        "examples": [
            "Menen huoneeseen. (Я иду в комнату.)",
            "Muutan Suomeen. (Я переезжаю в Финляндию.)"
        ],
        "tips": "Один из самых сложных падежей для заучивания из-за множества типов образования."
    },
    "adessiivi": {
        "title": "Adessiivi (Адессив / На-местный падеж)",
        "questions": "Millä? Kenellä? (На чем? У кого? С помощью чего?)",
        "purpose": "Означает нахождение на поверхности, инструмент действия, а также конструкцию принадлежности (у меня есть).",
        "rules": "Окончание падежа: -lla / -llä.",
        "examples": [
            "Avain on pöydällä. (Ключ лежит на столе.)",
            "Minulla on koira. (У меня есть собака / У меня [наличествует] собака.)"
        ],
        "tips": "Конструкция 'Minulla on' заменяет глагол 'иметь' (to have) в финском языке."
    }
}


# ==============================================================================
# 5. ГЕНЕРАТОРЫ ИНТЕРАКТИВНЫХ КЛАВИАТУР
# ==============================================================================
def build_main_menu_keyboard(is_administrator: bool = False) -> ReplyKeyboardMarkup:
    """Создание главной клавиатуры управления ботом с учетом прав администратора."""
    rows = [
        [KeyboardButton(text="📚 Учить слова"), KeyboardButton(text="🎯 Режим тестов")],
        [KeyboardButton(text="👤 Профиль и Статистика"), KeyboardButton(text="⭐ Купить Премиум")],
        [KeyboardButton(text="📖 Справочник падежей"), KeyboardButton(text="⚙️ Настройки")]
    ]
    if is_administrator:
        rows.append([KeyboardButton(text="👑 Панель администратора")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, persistent=True)

def build_levels_selection_keyboard() -> InlineKeyboardMarkup:
    """Генерация инлайн-клавиатуры выбора уровней владения языком от A1 до C1."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Уровень A1 (Начальный)", callback_data="setlevel_a1")],
            [InlineKeyboardButton(text="🟢 Уровень A2 (Базовый)", callback_data="setlevel_a2")],
            [InlineKeyboardButton(text="🟡 Уровень B1 (Средний)", callback_data="setlevel_b1")],
            [InlineKeyboardButton(text="🟠 Уровень B2 (Продвинутый)", callback_data="setlevel_b2")],
            [InlineKeyboardButton(text="🔴 Уровень C1 (Профессиональный ⭐)", callback_data="setlevel_c1")],
            [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="action_main_menu")]
        ]
    )

def build_learning_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления карточками слов во время тренировки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующее слово", callback_data="action_next_word")],
            [InlineKeyboardButton(text="🔤 Изменить уровень", callback_data="action_change_level")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]
        ]
    )

def build_grammar_directory_keyboard() -> InlineKeyboardMarkup:
    """Генерация клавиатуры со списком всех падежей для интерактивной справки."""
    keyboard_rows = []
    for code, info in EXTENDED_GRAMMAR_DATABASE.items():
        short_title = info["title"].split(" ")[0]
        keyboard_rows.append([InlineKeyboardButton(text=f"📌 {short_title}", callback_data=f"grammar_info_{code}")])
    keyboard_rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


# ==============================================================================
# 6. РОУТЕРЫ И БАЗОВЫЕ ОБРАБОТЧИКИ (СТАРТ И ПРОФИЛЬ)
# ==============================================================================
router = Router()

@router.message(CommandStart())
async def handle_start_command(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start с инициализацией профиля пользователя в JSON БД."""
    await state.clear()
    uid_str = str(message.from_user.id)
    database = load_db()
    
    if uid_str not in database:
        database[uid_str] = {
            "username": message.from_user.username or "NoUsername",
            "first_name": message.from_user.first_name or "Ученик",
            "level": "a1",
            "words_learned": 0,
            "correct_answers": 0,
            "quiz_score": 0,
            "is_premium": False,
            "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_db(database)
        logger.info(f"Зарегистрирован новый пользователь в системе: ID {message.from_user.id}")

    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    
    welcome_message = (
        f"👋 Здравствуй, **{html.quote(message.from_user.first_name)}**!\n\n"
        "Добро пожаловать в профессиональную систему изучения языковой лексики и грамматики.\n"
        "В твоем распоряжении базы слов от **уровня A1 до C1**, интерактивные тесты, справочник падежей "
        "и мгновенная премиум-подписка за Telegram Stars ⭐.\n\n"
        "Выбирай нужный раздел в меню ниже 👇"
    )
    
    await message.answer(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(is_administrator=is_admin)
    )

@router.message(F.text == "👤 Профиль и Статистика")
async def handle_profile_request(message: Message) -> None:
    """Вывод детальной персональной статистики и состояния подписки ученика."""
    uid_str = str(message.from_user.id)
    database = load_db()
    user_info = database.get(uid_str, {
        "level": "a1",
        "words_learned": 0,
        "correct_answers": 0,
        "quiz_score": 0,
        "is_premium": False,
        "joined_date": "Неизвестно"
    })
    
    subscription_status = "🟢 Активна (Премиум ⭐)" if user_info.get("is_premium") else "⚪️ Базовый (Бесплатный)"
    
    profile_text = (
        f"📊 **Твой персональный профиль:**\n\n"
        f"👤 Имя: {html.quote(message.from_user.first_name)}\n"
        f"🆔 ID аккаунта: `{message.from_user.id}`\n"
        f"📈 Активный уровень: `{user_info.get('level').upper()}`\n"
        f"🧠 Просмотрено карточек слов: `{user_info.get('words_learned', 0)}`\n"
        f"✨ Правильных ответов в тестах: `{user_info.get('correct_answers', 0)}`\n"
        f"🏆 Общий рейтинг (очки): `{user_info.get('quiz_score', 0)}`\n"
        f"💎 Статус подписки: {subscription_status}\n"
        f"📅 Дата регистрации: {user_info.get('joined_date')}"
    )
    
    await message.answer(profile_text, parse_mode="Markdown")

@router.message(F.text == "📖 Справочник падежей")
async def handle_grammar_menu_request(message: Message) -> None:
    """Отображение главного меню грамматического справочника."""
    directory_intro = (
        "📚 **Интерактивный справочник финской грамматики и падежей:**\n\n"
        "Выбери нужный падеж из списка ниже, чтобы изучить его вопросы, правила и практические примеры:"
    )
    await message.answer(
        directory_intro,
        parse_mode="Markdown",
        reply_markup=build_grammar_directory_keyboard()
    )

@router.callback_query(F.data.startswith("grammar_info_"))
async def process_grammar_card_callback(callback: CallbackQuery) -> None:
    """Вывод подробной информации по выбранному падежу при нажатии кнопки."""
    grammar_code = callback.data.split("_")[2]
    card_data = EXTENDED_GRAMMAR_DATABASE.get(grammar_code)
    
    if not card_data:
        await callback.answer("⚠️ Информация по данному падежу не найдена в базе.", show_alert=True)
        return
        
    examples_formatted = "\n".join([f"• {ex}" for ex in card_data["examples"]])
    
    card_output = (
        f"📖 **{card_data['title']}**\n\n"
        f"❓ **Вопросы:** `{card_data['questions']}`\n\n"
        f"🎯 **Назначение:** {card_data['purpose']}\n\n"
        f"⚙️ **Правила образования:** {card_data['rules']}\n\n"
        f"💡 **Примеры использования:**\n{examples_formatted}\n\n"
        f"📌 *Совет:* {card_data['tips']}"
    )
    
    await callback.message.edit_text(
        card_output,
        parse_mode="Markdown",
        reply_markup=build_grammar_directory_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "action_main_menu")
async def process_return_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Универсальный сброс состояния и возврат в главное меню бота."""
    await state.clear()
    is_admin = callback.from_user.id == ADMIN_TELEGRAM_ID
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🏠 Вы возвращены в главное меню:",
        reply_markup=build_main_menu_keyboard(is_administrator=is_admin)
    )
    await callback.answer()
    # ==============================================================================
# 🚀 ENTERPRISE-GRADE TELEGRAM VOCABULARY & GRAMMAR BOT — main.py (PART 2 / 2)
# Модули: Тренировка слов | Интерактивные тесты | Настройки | Админка | Stars ⭐
# ==============================================================================

# ==============================================================================
# 7. ПОЛНОЦЕННЫЙ МОДУЛЬ ТРЕНИРОВКИ СЛОВАРНОГО ЗАПАСА (Уровни A1 - C1)
# ==============================================================================
@router.message(F.text == "📚 Учить слова")
async def entry_vocabulary_training(message: Message, state: FSMContext) -> None:
    """Точка входа в режим изучения слов. Вывод меню выбора уровней."""
    await message.answer(
        "🔤 **Выбери языковой уровень для тренировки лексики:**\n\n"
        "• **A1–B2** — доступны бесплатно для каждого ученика.\n"
        "• **C1** — профессиональный сложный уровень (требуется Премиум-подписка ⭐).",
        parse_mode="Markdown",
        reply_markup=build_levels_selection_keyboard()
    )
    await state.set_state(BotStates.selecting_vocabulary_level)

@router.callback_query(F.data.startswith("setlevel_"), StateFilter(BotStates.selecting_vocabulary_level, BotStates.active_learning_session))
async def process_vocabulary_level_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора уровня сложности и проверка прав доступа для C1."""
    level_identifier = callback.data.split("_")[1] # a1, a2, b1, b2, c1
    uid_str = str(callback.from_user.id)
    
    # Проверка платного доступа к уровню C1
    if level_identifier == "c1":
        database = load_db()
        user_record = database.get(uid_str, {})
        if not user_record.get("is_premium", False):
            logger.warning(f"Пользователь {callback.from_user.id} попытался открыть C1 без подписки.")
            await callback.answer(
                "⚠️ Уровень C1 (Профессиональный) эксклюзивен и доступен только по Премиум-подписке ⭐!\n"
                "Нажми кнопку «Купить Премиум» в главном меню.",
                show_alert=True
            )
            return

    # Сохраняем выбранный уровень в базе данных пользователя и стейте
    database = load_db()
    if uid_str in database:
        database[uid_str]["level"] = level_identifier
        save_db(database)

    await state.update_data(active_vocab_level=level_identifier)
    await state.set_state(BotStates.active_learning_session)
    
    logger.info(f"Пользователь {callback.from_user.id} установил уровень обучения: {level_identifier.upper()}")
    
    await callback.message.edit_text(
        f"✅ Уровень успешно изменен на **{level_identifier.upper()}**.\nГенерируем карточку слова...",
        parse_mode="Markdown"
    )
    await dispatch_random_vocabulary_card(callback.message, level_identifier, replace_message=True)
    await callback.answer()

async def dispatch_random_vocabulary_card(message: Message, level_code: str, replace_message: bool = False) -> None:
    """Генерация случайной карточки слова из соответствующего словаря уровня."""
    dictionaries_map = {
        "a1": WORDS_A1,
        "a2": WORDS_A2,
        "b1": WORDS_B1,
        "b2": WORDS_B2,
        "c1": WORDS_C1
    }
    
    target_pool = dictionaries_map.get(level_code, WORDS_A1)
    if not target_pool:
        target_pool = WORDS_A1
        
    selected_word_item = random.choice(target_pool)
    
    card_construction = (
        f"📖 **Обучающая карточка (Уровень: {level_code.upper()})**\n\n"
        f"🔤 Слово / Выражение: **{html.quote(selected_word_item.get('word', ''))}**\n"
        f"🔊 Транскрипция: `{html.quote(selected_word_item.get('trans', ''))}`\n"
        f"🇷🇺 Перевод на русский: **{html.quote(selected_word_item.get('ru', ''))}**\n\n"
        f"💡 **Пример в контексте:**\n*{html.quote(selected_word_item.get('ex', ''))}*"
    )
    
    # Обновляем счетчик просмотренных слов в JSON БД
    uid_str = str(message.chat.id)
    database = load_db()
    if uid_str in database:
        database[uid_str]["words_learned"] = database[uid_str].get("words_learned", 0) + 1
        save_db(database)

    if replace_message:
        try:
            await message.edit_text(
                card_construction,
                parse_mode="Markdown",
                reply_markup=build_learning_actions_keyboard()
            )
        except Exception:
            await message.answer(
                card_construction,
                parse_mode="Markdown",
                reply_markup=build_learning_actions_keyboard()
            )
    else:
        await message.answer(
        card_construction,
            parse_mode="Markdown",
            reply_markup=build_learning_actions_keyboard()
        )

@router.callback_query(F.data == "action_next_word", StateFilter(BotStates.active_learning_session))
async def process_next_word_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработчик нажатия кнопки 'Следующее слово' во время тренировки."""
    state_data = await state.get_data()
    current_level = state_data.get("active_vocab_level", "a1")
    await dispatch_random_vocabulary_card(callback.message, current_level, replace_message=True)
    await callback.answer()

@router.callback_query(F.data == "action_change_level")
async def process_change_level_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Вызов меню смены уровня прямо из интерфейса карточки обучения."""
    await callback.message.edit_text(
        "🔤 **Выбери новый уровень для изучения лексики:**",
        parse_mode="Markdown",
        reply_markup=build_levels_selection_keyboard()
    )
    await state.set_state(BotStates.selecting_vocabulary_level)
    await callback.answer()


# ==============================================================================
# 8. ИНТЕРАКТИВНЫЙ МОДУЛЬ ТЕСТИРОВАНИЯ И ПРОВЕРКИ ЗНАНИЙ (QUIZ SYSTEM)
# ==============================================================================
@router.message(F.text == "🎯 Режим тестов")
async def entry_quiz_session(message: Message, state: FSMContext) -> None:
    """Инициализация сеанса интерактивного тестирования словарного запаса."""
    uid_str = str(message.from_user.id)
    database = load_db()
    user_current_level = database.get(uid_str, {}).get("level", "a1")
    
    dictionaries_map = {
        "a1": WORDS_A1, "a2": WORDS_A2, "b1": WORDS_B1, "b2": WORDS_B2, "c1": WORDS_C1
    }
    pool = dictionaries_map.get(user_current_level, WORDS_A1)
    
    if len(pool) < 4:
        pool = WORDS_A1
        
    correct_target = random.choice(pool)
    distractors = random.sample([item for item in pool if item["word"] != correct_target["word"]], min(3, len(pool) - 1))
    
    quiz_options = distractors + [correct_target]
    random.shuffle(quiz_options)
    
    # Сохраняем правильный ответ в память FSM
    await state.update_data(quiz_correct_ru=correct_target["ru"], quiz_active_level=user_current_level)
    await state.set_state(BotStates.quiz_question_active)
    
    keyboard_buttons = []
    for option in quiz_options:
        keyboard_buttons.append([InlineKeyboardButton(text=option["ru"], callback_data=f"quizanswer_{option['ru']}")])
    keyboard_buttons.append([InlineKeyboardButton(text="❌ Завершить тест", callback_data="action_main_menu")])
    
    quiz_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    question_text = (
        f"🎯 **Проверка знаний (Уровень: {user_current_level.upper()})**\n\n"
        f"Как переводится на русский язык слово: **{html.quote(correct_target['word'])}**?"
    )
    
    await message.answer(question_text, parse_mode="Markdown", reply_markup=quiz_markup)

@router.callback_query(F.data.startswith("quizanswer_"), StateFilter(BotStates.quiz_question_active))
async def evaluate_user_quiz_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Валидация ответа пользователя в режиме теста и обновление его рейтинга."""
    chosen_translation = callback.data.split("_", 1)[1]
    fsm_data = await state.get_data()
    correct_translation = fsm_data.get("quiz_correct_ru")
    
    uid_str = str(callback.from_user.id)
    database = load_db()
    
    if chosen_translation == correct_translation:
        if uid_str in database:
            database[uid_str]["correct_answers"] = database[uid_str].get("correct_answers", 0) + 1
            database[uid_str]["quiz_score"] = database[uid_str].get("quiz_score", 0) + 15
            save_db(database)
            
        feedback_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="action_next_quiz")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]
        ])
        await callback.message.edit_text(
            "✅ **Абсолютно верно!** Прекрасный результат (+15 очков рейтинга). 🎉",
            parse_mode="Markdown",
            reply_markup=feedback_markup
        )
    else:
        feedback_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="action_next_quiz")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]
        ])
        await callback.message.edit_text(
            f"❌ **К сожалению, ошибка.** Правильный вариант: *{html.quote(correct_translation)}*.",
            parse_mode="Markdown",
            reply_markup=feedback_markup
        )
    await callback.answer()

@router.callback_query(F.data == "action_next_quiz")
async def process_next_quiz_question(callback: CallbackQuery, state: FSMContext) -> None:
    """Генерация следующего вопроса в серии тестов."""
    await entry_quiz_session(callback.message, state)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


# ==============================================================================
# 9. НАСТРОЙКИ ПРОФИЛЯ И ПАНЕЛЬ АДМИНИСТРАТОРА
# ==============================================================================
@router.message(F.text == "⚙️ Настройки")
async def handle_settings_menu_request(message: Message) -> None:
    """Отображение персональных настроек пользователя."""
    settings_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Сбросить всю статистику", callback_data="settings_reset_stats")],
            [InlineKeyboardButton(text="🔤 Изменить языковой уровень", callback_data="settings_change_lvl")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]
        ]
    )
    await message.answer(
        "⚙️ **Панель настроек профиля:**\n\nВыбери действие для управления своим аккаунтом:",
        parse_mode="Markdown",
        reply_markup=settings_markup
    )

@router.callback_query(F.data == "settings_reset_stats")
async def process_reset_user_statistics(callback: CallbackQuery) -> None:
    """Полный сброс игрового прогресса и счетчиков слов ученика."""
    uid_str = str(callback.from_user.id)
    database = load_db()
    if uid_str in database:
        database[uid_str]["words_learned"] = 0
        database[uid_str]["correct_answers"] = 0
        database[uid_str]["quiz_score"] = 0
        save_db(database)
        
    await callback.answer("🔄 Вся статистика успешно сброшена к нулю!", show_alert=True)
    
    return_markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]]
    )
    await callback.message.edit_text(
        "✅ Твоя личная статистика и баллы были полностью обнулены.",
        reply_markup=return_markup
    )

@router.callback_query(F.data == "settings_change_lvl")
async def process_settings_change_level_shortcut(callback: CallbackQuery) -> None:
    """Быстрый доступ к смене уровня из настроек."""
    await callback.message.edit_text(
        "🔤 Выбери желаемый уровень сложности:",
        reply_markup=build_levels_selection_keyboard()
    )
    await callback.answer()

# Админ-панель для владельца бота
@router.message(F.text == "👑 Панель администратора")
async def handle_admin_panel_entry(message: Message) -> None:
    """Проверка прав и вывод панели администратора."""
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        await message.answer("⛔ У тебя нет прав администратора для доступа к этому разделу.")
        return
        
    database = load_db()
    registered_users_count = len(database)
    active_premium_count = sum(1 for profile in database.values() if profile.get("is_premium"))
    
    admin_dashboard_text = (
        f"👑 **Панель управления администратора:**\n\n"
        f"👥 Всего зарегистрировано учеников: `{registered_users_count}`\n"
        f"💎 Активных Премиум-подписок: `{active_premium_count}`\n"
        f"💾 Файл базы данных: `{DB_FILENAME}` (Активен)\n"
    )
    
    admin_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Проверить целостность БД", callback_data="admin_check_db")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="action_main_menu")]
        ]
    )
    
    await message.answer(admin_dashboard_text, parse_mode="Markdown", reply_markup=admin_markup)

@router.callback_query(F.data == "admin_check_db")
async def process_admin_check_database(callback: CallbackQuery) -> None:
    """Диагностическая проверка целостности базы данных."""
    if callback.from_user.id != ADMIN_TELEGRAM_ID:
        await callback.answer("⛔ Отказано в доступе.", show_alert=True)
        return
        
    database = load_db()
    total_profiles = len(database)
    await callback.answer(
        f"✅ Диагностика успешна! В памяти JSON зарегистрировано профилей: {total_profiles}.",
        show_alert=True
    )


# ==============================================================================
# 10. МОДУЛЬ АВТОМАТИЗИРОВАННОЙ ОПЛАТЫ ЧЕРЕЗ TELEGRAM STARS (⭐)
# ==============================================================================
@router.message(Command("buy"))
@router.message(F.text == "⭐ Купить Премиум")
async def handle_buy_premium_request(message: Message) -> None:
    """Выставление инвойса на оплату Премиум-подписки через официальные Telegram Stars."""
    # Устанавливаем стоимость в звездах (например, 100 звезд ⭐)
    invoice_prices = [LabeledPrice(label="Премиум доступ к уровню C1 на 30 дней", amount=50)]
    
    await message.answer_invoice(
        title="⭐ Премиум-подписка Vocabulary Bot",
        description="Открывает полный бессрочный доступ к профессиональному уровню словаря C1 и всем расширенным функциям!",
        prices=invoice_prices,
        payload="monthly_premium_subscription_payload",
        currency="XTR",           # Официальная цифровая валюта Telegram Stars всегда обозначается как "XTR"
        provider_token=""         # Важное правило: для цифровых товаров и звезд провайдер токен всегда пустая строка ("")
    )
    logger.info(f"Выставлен инвойс на оплату звездами для пользователя {message.from_user.id}")

@router.pre_checkout_query()
async def process_pre_checkout_validation(pre_checkout_query: PreCheckoutQuery) -> None:
    """Обязательный этап валидации перед списанием средств с баланса пользователя."""
    # Подтверждаем транзакцию со стороны бота
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_stars_payment(message: Message) -> None:
    """Обработка успешной оплаты: моментальная выдача Премиум-статуса и уровня C1."""
    payment_details = message.successful_payment
    uid_str = str(message.from_user.id)
    
    database = load_db()
    if uid_str in database:
        database[uid_str]["is_premium"] = True
        save_db(database)
        
    logger.info(f"УСПЕШНАЯ ОПЛАТА! Пользователь {message.from_user.id} перевел {payment_details.total_amount} ⭐")
    
    congratulation_text = (
        "🎉 **Оплата прошла успешно! Огромное спасибо за поддержку!** ⭐\n\n"
        "Твоя Премиум-подписка активирована моментально в системе. "
        "Теперь тебе полностью разблокирован профессиональный уровень **C1** в меню изучения слов!"
    )
    
    is_admin = message.from_user.id == ADMIN_TELEGRAM_ID
    await message.answer(
        congratulation_text,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(is_administrator=is_admin)
    )


# ==============================================================================
# 11. ТОЧКА ВХОДА И ЗАПУСК АСИНХРОННОГО ДИСПЕТЧЕРА БОТА
# ==============================================================================
async def main() -> None:
    """Главная функция инициализации бота, хранилища состояний и пуллинга."""
    logger.info("Инициализация экземпляра бота и хранилища FSM...")
    
    bot_instance = Bot(token=BOT_TOKEN)
    memory_storage = MemoryStorage()
    dispatcher = Dispatcher(storage=memory_storage)
    
    # Подключаем наш главный роутер со всеми обработчиками
    dispatcher.include_router(router)
    
    logger.info("🚀 Бот полностью готов к работе и начинает прослушивание обновлений (polling)...")
    
    # Сбрасываем старые апдейты, накопившиеся за время простоя, и запускаем пуллинг
    try:
        await bot_instance.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot_instance)
    except TelegramAPIError as api_err:
        logger.critical(f"Ошибка Telegram API при запуске поллинга: {api_err}")
    finally:
        await bot_instance.session.close()
        logger.info("Сессия бота закрыта.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот был остановлен пользователем или системой.")
