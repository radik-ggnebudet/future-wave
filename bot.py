"""
Telegram бот для регистрации на форум Future Wave
"""
import os
import re
from datetime import datetime
from typing import Dict

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init

from config import (
    UNIVERSITIES,
    COURSES,
    PERSONAL_DATA_CONSENT,
    ORGANIZATION_INFO,
    ADMIN_USERNAMES,
    INTERNSHIP_CHAT_ID
)
from database import Database

# Инициализация colorama для Windows
init(autoreset=True)


def log_info(message: str, user=None):
    """Логирование информационных сообщений"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    user_info = f"@{user.username} ({user.id})" if user else "System"
    print(f"{Fore.CYAN}[{timestamp}] ℹ️  {Style.BRIGHT}{message}{Style.RESET_ALL} | {Fore.YELLOW}{user_info}{Style.RESET_ALL}")


def log_success(message: str, user=None):
    """Логирование успешных действий"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    user_info = f"@{user.username} ({user.id})" if user else "System"
    print(f"{Fore.GREEN}[{timestamp}] ✅ {Style.BRIGHT}{message}{Style.RESET_ALL} | {Fore.YELLOW}{user_info}{Style.RESET_ALL}")


def log_warning(message: str, user=None):
    """Логирование предупреждений"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    user_info = f"@{user.username} ({user.id})" if user else "System"
    print(f"{Fore.YELLOW}[{timestamp}] ⚠️  {Style.BRIGHT}{message}{Style.RESET_ALL} | {Fore.YELLOW}{user_info}{Style.RESET_ALL}")


def log_error(message: str, user=None):
    """Логирование ошибок"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    user_info = f"@{user.username} ({user.id})" if user else "System"
    print(f"{Fore.RED}[{timestamp}] ❌ {Style.BRIGHT}{message}{Style.RESET_ALL} | {Fore.YELLOW}{user_info}{Style.RESET_ALL}")


def log_admin(message: str, user=None):
    """Логирование действий администраторов"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    user_info = f"@{user.username} ({user.id})" if user else "Admin"
    print(f"{Fore.MAGENTA}[{timestamp}] 👑 {Style.BRIGHT}{message}{Style.RESET_ALL} | {Fore.YELLOW}{user_info}{Style.RESET_ALL}")


def log_registration(message: str, data: Dict):
    """Логирование регистраций"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{Fore.GREEN}{Back.BLACK}[{timestamp}] 🎉 {Style.BRIGHT}{message}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    👤 {data.get('full_name', 'N/A')}")
    print(f"{Fore.CYAN}    📧 {data.get('email', 'N/A')}")
    print(f"{Fore.CYAN}    🎓 {data.get('university', 'N/A')}")
    print(f"{Fore.CYAN}    📚 {data.get('course', 'N/A')}{Style.RESET_ALL}")

# Загрузка переменных окружения
load_dotenv()

# Инициализация базы данных
db = Database()

# Состояния диалога
(
    CONSENT,
    FULL_NAME,
    BIRTH_DATE,
    EMAIL,
    PHONE,
    UNIVERSITY,
    UNIVERSITY_CUSTOM,
    COURSE,
    INTERNSHIP_INTEREST,
    CONFIRMATION
) = range(10)


def is_admin(user) -> bool:
    """Проверка является ли пользователь администратором"""
    if user.username:
        return user.username.lower() in [admin.lower() for admin in ADMIN_USERNAMES]
    return False


async def send_to_internship_chat(context: ContextTypes.DEFAULT_TYPE, registration_data: Dict) -> None:
    """Отправка регистрации в групповой чат (только если заинтересован в стажировках)"""
    interested = registration_data.get('interested_in_internship', False)

    # Отправляем только если заинтересован в стажировках
    if not interested:
        log_info("Пользователь не заинтересован в стажировках, отправка в групповой чат пропущена")
        return

    # Если ID чата не настроен, просто выходим
    if not INTERNSHIP_CHAT_ID:
        log_warning("ID группового чата для стажировок не настроен (INTERNSHIP_CHAT_ID = None)")
        return

    username_display = f"@{registration_data['telegram_username']}" if registration_data['telegram_username'] else "не указан"

    message_text = (
        f"🆕 НОВАЯ ЗАЯВКА (ЗАИНТЕРЕСОВАН В СТАЖИРОВКАХ)\n\n"
        f"👤 ФИО: {registration_data['full_name']}\n"
        f"📅 Дата рождения: {registration_data['birth_date']}\n"
        f"📧 Email: {registration_data['email']}\n"
        f"📱 Телефон: {registration_data['phone']}\n"
        f"🎓 Университет: {registration_data['university']}\n"
        f"📚 Курс: {registration_data['course']}\n"
        f"💼 Стажировки: ✅ Да, интересны\n"
        f"🆔 Telegram: {username_display}\n"
        f"🕐 Время: {datetime.fromisoformat(registration_data['registration_datetime']).strftime('%d.%m.%Y %H:%M:%S')}\n"
    )

    try:
        await context.bot.send_message(chat_id=INTERNSHIP_CHAT_ID, text=message_text)
        log_success(f"Заявка со стажировкой отправлена в групповой чат (chat_id: {INTERNSHIP_CHAT_ID})")
    except Exception as e:
        log_error(f"Ошибка при отправке в групповой чат стажировок {INTERNSHIP_CHAT_ID}: {e}")


async def notify_admins(context: ContextTypes.DEFAULT_TYPE, registration_data: Dict) -> None:
    """Отправка уведомления всем админам о новой регистрации"""
    username_display = f"@{registration_data['telegram_username']}" if registration_data['telegram_username'] else "не указан"
    interest_text = "✅ Да" if registration_data.get('interested_in_internship', False) else "❌ Нет"

    notification_text = (
        "🆕 НОВАЯ РЕГИСТРАЦИЯ!\n\n"
        f"👤 ФИО: {registration_data['full_name']}\n"
        f"📅 Дата рождения: {registration_data['birth_date']}\n"
        f"📧 Email: {registration_data['email']}\n"
        f"📱 Телефон: {registration_data['phone']}\n"
        f"🎓 Университет: {registration_data['university']}\n"
        f"📚 Курс: {registration_data['course']}\n"
        f"💼 Стажировки: {interest_text}\n"
        f"🆔 Telegram: {username_display}\n"
        f"🕐 Время: {datetime.fromisoformat(registration_data['registration_datetime']).strftime('%d.%m.%Y %H:%M:%S')}\n"
    )

    # Получаем chat_id всех админов
    admin_chats = db.get_admin_chats()

    log_info(f"Отправка уведомлений {len(admin_chats)} администраторам о новой регистрации")

    # Отправляем уведомление каждому админу
    for chat_id in admin_chats:
        try:
            await context.bot.send_message(chat_id=chat_id, text=notification_text)
            log_success(f"Уведомление отправлено админу (chat_id: {chat_id})")
        except Exception as e:
            log_error(f"Ошибка при отправке уведомления админу {chat_id}: {e}")


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать админ-панель"""
    user = update.effective_user

    log_admin("Открытие админ-панели", user)

    # Получаем статистику
    stats = db.get_statistics()

    panel_text = (
        f"👑 АДМИН-ПАНЕЛЬ\n\n"
        f"Добро пожаловать, @{user.username}!\n\n"
        f"📊 СТАТИСТИКА РЕГИСТРАЦИЙ:\n"
        f"👥 Всего зарегистрировано: {stats['total']}\n\n"
    )

    # Добавляем статистику по университетам
    if stats['by_university']:
        panel_text += "🎓 По университетам:\n"
        for uni, count in sorted(stats['by_university'].items(), key=lambda x: x[1], reverse=True):
            panel_text += f"  • {uni}: {count}\n"
        panel_text += "\n"

    # Добавляем статистику по курсам
    if stats['by_course']:
        panel_text += "📚 По курсам:\n"
        for course, count in sorted(stats['by_course'].items(), key=lambda x: x[1], reverse=True):
            panel_text += f"  • {course}: {count}\n"

    # Кнопки админ-панели
    keyboard = [
        [InlineKeyboardButton("📋 Список всех участников", callback_data="admin_list_all")],
        [InlineKeyboardButton("📊 Обновить статистику", callback_data="admin_refresh")],
        [InlineKeyboardButton("📥 Экспорт данных", callback_data="admin_export")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(panel_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(panel_text, reply_markup=reply_markup)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопок админ-панели"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    # Проверяем права администратора
    if not is_admin(user):
        log_warning("Попытка доступа к админ-панели без прав", user)
        await query.answer("❌ У вас нет прав администратора", show_alert=True)
        return

    if query.data == "admin_refresh":
        log_admin("Обновление статистики", user)
        # Обновляем статистику
        await show_admin_panel(update, context)

    elif query.data == "admin_list_all":
        log_admin("Запрос списка всех участников", user)
        # Показываем список всех участников
        registrations = db.get_all_registrations()

        if not registrations:
            await query.edit_message_text(
                "📋 Список участников пуст.\n\n"
                "Пока никто не зарегистрировался на форум.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Назад в админ-панель", callback_data="admin_back")
                ]])
            )
            return

        # Формируем список участников (показываем первые 10)
        list_text = f"📋 СПИСОК УЧАСТНИКОВ (всего: {len(registrations)})\n\n"

        for i, reg in enumerate(registrations[:10], 1):
            username_display = f"@{reg['telegram_username']}" if reg['telegram_username'] else "—"
            list_text += (
                f"{i}. {reg['full_name']}\n"
                f"   🎓 {reg['university']}\n"
                f"   📚 {reg['course']}\n"
                f"   📱 {reg['phone']}\n"
                f"   🆔 {username_display}\n\n"
            )

        if len(registrations) > 10:
            list_text += f"... и еще {len(registrations) - 10} участников\n\n"

        keyboard = [
            [InlineKeyboardButton("◀️ Назад в админ-панель", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(list_text, reply_markup=reply_markup)

    elif query.data == "admin_export":
        log_admin("Запрос экспорта данных в CSV", user)
        # Экспорт данных в CSV формате
        registrations = db.get_all_registrations()

        if not registrations:
            log_warning("Нет данных для экспорта", user)
            await query.answer("📋 Нет данных для экспорта", show_alert=True)
            return

        # Формируем CSV
        csv_content = "ФИО,Дата рождения,Email,Телефон,Университет,Курс,Telegram,Дата регистрации\n"

        for reg in registrations:
            username = reg['telegram_username'] or ''
            csv_content += (
                f"{reg['full_name']},{reg['birth_date']},{reg['email']},"
                f"{reg['phone']},{reg['university']},{reg['course']},"
                f"@{username},{reg['registration_datetime']}\n"
            )

        # Отправляем файл
        from io import BytesIO
        file = BytesIO(csv_content.encode('utf-8'))
        file.name = f"registrations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        await query.message.reply_document(
            document=file,
            filename=file.name,
            caption=f"📊 Экспорт регистраций\nВсего участников: {len(registrations)}"
        )

        log_success(f"Экспорт выполнен: {len(registrations)} записей", user)
        await query.answer("✅ Файл отправлен")

    elif query.data == "admin_back":
        # Возврат в админ-панель
        await show_admin_panel(update, context)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для открытия админ-панели"""
    user = update.effective_user

    if not is_admin(user):
        await update.message.reply_text(
            "❌ У вас нет прав администратора.\n\n"
            "Для регистрации на форум используйте команду /start"
        )
        return

    # Сохраняем chat_id админа
    if not db.is_admin_registered(user.id):
        db.save_admin_chat(user.id, user.username or '', update.effective_chat.id)

    await show_admin_panel(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало диалога регистрации"""
    user = update.effective_user

    log_info("Команда /start", user)

    # Проверяем, является ли пользователь администратором
    if is_admin(user):
        log_admin("Администратор распознан, открытие админ-панели", user)
        # Сохраняем chat_id админа, если еще не сохранен
        if not db.is_admin_registered(user.id):
            db.save_admin_chat(user.id, user.username or '', update.effective_chat.id)
            log_success("Chat ID администратора сохранен", user)

        # Открываем админ-панель
        await show_admin_panel(update, context)
        return ConversationHandler.END

    # Проверяем флаг перезапуска
    force_restart = context.user_data.get('force_restart', False)

    # Проверяем, не зарегистрирован ли пользователь уже (только если не перезапуск)
    if not force_restart:
        registration = db.get_registration(user.id)
        if registration:
            log_info("Пользователь уже зарегистрирован", user)
            await update.message.reply_text(
                f"Здравствуйте, {registration['full_name']}!\n\n"
                f"Вы уже зарегистрированы на форум Future Wave.\n\n"
                f"📋 Ваши данные:\n"
                f"ФИО: {registration['full_name']}\n"
                f"Дата рождения: {registration['birth_date']}\n"
                f"Email: {registration['email']}\n"
                f"Телефон: {registration['phone']}\n"
                f"Университет: {registration['university']}\n"
                f"Курс: {registration['course']}\n\n"
                f"Для повторной регистрации используйте /restart"
            )
            return ConversationHandler.END

    # Очищаем флаг перезапуска, если он был установлен
    if force_restart:
        context.user_data.pop('force_restart', None)
        log_info("Перезапуск регистрации (force_restart)", user)
    else:
        log_info("Начало новой регистрации", user)

    # Приветствие
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        f"Добро пожаловать в систему регистрации на форум **Future Wave** — "
        f"форум по поиску работы!\n\n"
        f"📍 Место проведения: {ORGANIZATION_INFO['venue']}, {ORGANIZATION_INFO['city']}\n\n"
        f"Для регистрации вам необходимо будет предоставить следующие данные:\n"
        f"• ФИО\n"
        f"• Дата рождения\n"
        f"• Электронная почта\n"
        f"• Номер телефона\n"
        f"• Университет\n"
        f"• Курс обучения\n\n"
        f"Начнём с ознакомления с согласием на обработку персональных данных."
    )

    await update.message.reply_text(welcome_text, parse_mode='Markdown')

    # Отправляем согласие на обработку персональных данных с кликабельными ссылками
    await update.message.reply_text(PERSONAL_DATA_CONSENT, parse_mode='Markdown', disable_web_page_preview=True)

    # Кнопки для согласия
    keyboard = [
        [InlineKeyboardButton("✅ Даю согласие", callback_data="consent_yes")],
        [InlineKeyboardButton("❌ Не даю согласие", callback_data="consent_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Пожалуйста, ознакомьтесь с согласием выше и подтвердите своё решение:",
        reply_markup=reply_markup
    )

    return CONSENT


async def consent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка согласия на обработку персональных данных"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if query.data == "consent_yes":
        log_success("Пользователь дал согласие на обработку данных", user)
        # Сохраняем согласие и время
        context.user_data['consent_given'] = True
        context.user_data['consent_datetime'] = datetime.now().isoformat()

        await query.edit_message_text(
            "✅ Спасибо! Вы дали согласие на обработку персональных данных.\n\n"
            "Теперь давайте начнём заполнение регистрационной формы.\n\n"
            "📝 Пожалуйста, введите ваше ФИО (Фамилия Имя Отчество):"
        )

        return FULL_NAME
    else:
        log_warning("Пользователь отказался от обработки данных", user)
        await query.edit_message_text(
            "❌ Без согласия на обработку персональных данных мы не можем зарегистрировать вас на форум.\n\n"
            "Если вы передумаете, используйте команду /start для повторной регистрации.\n\n"
            "Если у вас есть вопросы, свяжитесь с организаторами."
        )

        return ConversationHandler.END


async def full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение ФИО"""
    user = update.effective_user
    name = update.message.text.strip()

    # Простая валидация (минимум 2 слова)
    if len(name.split()) < 2:
        log_warning(f"Некорректный ввод ФИО: {name}", user)
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите полное ФИО (минимум Фамилия и Имя).\n"
            "Например: Иванов Иван Иванович"
        )
        return FULL_NAME

    log_info(f"ФИО введено: {name}", user)
    context.user_data['full_name'] = name

    await update.message.reply_text(
        f"✅ ФИО: {name}\n\n"
        f"📅 Теперь введите вашу дату рождения в формате ДД.ММ.ГГГГ\n"
        f"Например: 15.03.2003"
    )

    return BIRTH_DATE


async def birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение даты рождения"""
    user = update.effective_user
    date_text = update.message.text.strip()

    # Валидация формата даты
    date_pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(date_pattern, date_text):
        log_warning(f"Некорректный формат даты: {date_text}", user)
        await update.message.reply_text(
            "⚠️ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ\n"
            "Например: 15.03.2003"
        )
        return BIRTH_DATE

    # Проверка валидности даты
    try:
        day, month, year = map(int, date_text.split('.'))
        date_obj = datetime(year, month, day)

        # Проверка возраста (должен быть не младше 14 лет)
        age = (datetime.now() - date_obj).days / 365.25
        if age < 14:
            await update.message.reply_text(
                "⚠️ К сожалению, участие в форуме доступно для лиц старше 14 лет."
            )
            return BIRTH_DATE

        if age > 100:
            await update.message.reply_text(
                "⚠️ Пожалуйста, проверьте правильность введённой даты."
            )
            return BIRTH_DATE

    except ValueError:
        log_warning(f"Некорректная дата: {date_text}", user)
        await update.message.reply_text(
            "⚠️ Указана некорректная дата. Пожалуйста, проверьте правильность ввода."
        )
        return BIRTH_DATE

    log_info(f"Дата рождения введена: {date_text}", user)
    context.user_data['birth_date'] = date_text

    await update.message.reply_text(
        f"✅ Дата рождения: {date_text}\n\n"
        f"📧 Теперь введите ваш адрес электронной почты:"
    )

    return EMAIL


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение email"""
    user = update.effective_user
    email_text = update.message.text.strip()

    # Валидация email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email_text):
        log_warning(f"Некорректный email: {email_text}", user)
        await update.message.reply_text(
            "⚠️ Неверный формат email. Пожалуйста, введите корректный адрес.\n"
            "Например: example@mail.ru"
        )
        return EMAIL

    log_info(f"Email введен: {email_text}", user)
    context.user_data['email'] = email_text

    await update.message.reply_text(
        f"✅ Email: {email_text}\n\n"
        f"📱 Теперь введите ваш номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX:"
    )

    return PHONE


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение номера телефона"""
    user = update.effective_user
    phone_text = update.message.text.strip()

    # Очистка от лишних символов
    phone_clean = re.sub(r'[^\d+]', '', phone_text)

    # Валидация номера телефона
    phone_pattern = r'^(\+7|8)\d{10}$'
    if not re.match(phone_pattern, phone_clean):
        log_warning(f"Некорректный телефон: {phone_text}", user)
        await update.message.reply_text(
            "⚠️ Неверный формат номера телефона.\n"
            "Пожалуйста, введите номер в формате: +79991234567 или 89991234567"
        )
        return PHONE

    log_info(f"Телефон введен: {phone_clean}", user)
    context.user_data['phone'] = phone_clean

    # Кнопки с университетами
    keyboard = []
    for i in range(0, len(UNIVERSITIES), 2):
        row = []
        row.append(UNIVERSITIES[i])
        if i + 1 < len(UNIVERSITIES):
            row.append(UNIVERSITIES[i + 1])
        keyboard.append(row)

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Телефон: {phone_clean}\n\n"
        f"🎓 Выберите ваш университет из списка или введите название вручную:",
        reply_markup=reply_markup
    )

    return UNIVERSITY


async def university(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение университета"""
    user = update.effective_user
    university_text = update.message.text.strip()

    if university_text == "Другой университет":
        log_info("Выбран вариант 'Другой университет'", user)
        await update.message.reply_text(
            "🎓 Пожалуйста, введите название вашего университета:",
            reply_markup=ReplyKeyboardRemove()
        )
        return UNIVERSITY_CUSTOM

    log_info(f"Университет выбран: {university_text}", user)
    context.user_data['university'] = university_text

    # Кнопки с курсами
    keyboard = []
    for i in range(0, len(COURSES), 2):
        row = []
        row.append(COURSES[i])
        if i + 1 < len(COURSES):
            row.append(COURSES[i + 1])
        keyboard.append(row)

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Университет: {university_text}\n\n"
        f"📚 Выберите ваш курс обучения:",
        reply_markup=reply_markup
    )

    return COURSE


async def university_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия другого университета"""
    user = update.effective_user
    university_text = update.message.text.strip()

    if len(university_text) < 3:
        log_warning(f"Слишком короткое название университета: {university_text}", user)
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное название университета."
        )
        return UNIVERSITY_CUSTOM

    log_info(f"Университет (вручную) введен: {university_text}", user)
    context.user_data['university'] = university_text

    # Кнопки с курсами
    keyboard = []
    for i in range(0, len(COURSES), 2):
        row = []
        row.append(COURSES[i])
        if i + 1 < len(COURSES):
            row.append(COURSES[i + 1])
        keyboard.append(row)

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"✅ Университет: {university_text}\n\n"
        f"📚 Выберите ваш курс обучения:",
        reply_markup=reply_markup
    )

    return COURSE


async def course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение курса обучения"""
    user = update.effective_user
    course_text = update.message.text.strip()

    log_info(f"Курс выбран: {course_text}", user)
    context.user_data['course'] = course_text

    # Спрашиваем о заинтересованности в стажировках
    keyboard = [
        [InlineKeyboardButton("✅ Да, интересны", callback_data="internship_yes")],
        [InlineKeyboardButton("❌ Нет, не интересны", callback_data="internship_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Курс: {course_text}\n\n"
        f"💼 Интересны ли вам стажировки?",
        reply_markup=ReplyKeyboardRemove()
    )

    await update.message.reply_text(
        "Пожалуйста, выберите ваш ответ:",
        reply_markup=reply_markup
    )

    return INTERNSHIP_INTEREST


async def internship_interest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа на вопрос о стажировках"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if query.data == "internship_yes":
        log_info("Пользователь заинтересован в стажировках", user)
        context.user_data['interested_in_internship'] = True
        interest_text = "Да, интересны"
    else:
        log_info("Пользователь не заинтересован в стажировках", user)
        context.user_data['interested_in_internship'] = False
        interest_text = "Нет, не интересны"

    # Формируем сводку всех данных
    user_data = context.user_data
    summary = (
        "📋 ПРОВЕРЬТЕ ВВЕДЁННЫЕ ДАННЫЕ\n\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Дата рождения: {user_data['birth_date']}\n"
        f"Email: {user_data['email']}\n"
        f"Телефон: {user_data['phone']}\n"
        f"Университет: {user_data['university']}\n"
        f"Курс: {user_data['course']}\n"
        f"Стажировки: {interest_text}\n\n"
        f"Всё верно?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Нет, заполнить заново", callback_data="confirm_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(summary)

    await query.message.reply_text(
        "Пожалуйста, подтвердите введённые данные:",
        reply_markup=reply_markup
    )


    return CONFIRMATION


async def confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение регистрации"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    if query.data == "confirm_yes":
        # Сохраняем данные в базу
        user_data = context.user_data

        log_info("Пользователь подтвердил данные", user)

        registration_data = {
            'user_id': user.id,
            'full_name': user_data['full_name'],
            'birth_date': user_data['birth_date'],
            'email': user_data['email'],
            'phone': user_data['phone'],
            'university': user_data['university'],
            'course': user_data['course'],
            'interested_in_internship': user_data.get('interested_in_internship', False),
            'consent_given': user_data['consent_given'],
            'consent_datetime': user_data['consent_datetime'],
            'registration_datetime': datetime.now().isoformat(),
            'telegram_username': user.username or ''
        }

        success = db.save_registration(registration_data)

        if success:
            log_registration("НОВАЯ РЕГИСТРАЦИЯ ЗАВЕРШЕНА!", registration_data)

            # Отправляем уведомления админам о новой регистрации (всегда)
            await notify_admins(context, registration_data)

            # Отправляем данные в групповой чат стажировок (только если заинтересован)
            await send_to_internship_chat(context, registration_data)

            await query.edit_message_text(
                "🎉 РЕГИСТРАЦИЯ ЗАВЕРШЕНА!\n\n"
                f"Спасибо, {user_data['full_name']}!\n\n"
                f"Вы успешно зарегистрированы на форум **Future Wave**.\n\n"
                f"📍 Место: {ORGANIZATION_INFO['venue']}, {ORGANIZATION_INFO['city']}\n\n"
                "Мы отправим дополнительную информацию на указанный вами email.\n\n"
                "До встречи на форуме! 👋",
                parse_mode='Markdown'
            )
        else:
            log_error("Ошибка при сохранении регистрации в БД", user)
            await query.edit_message_text(
                "⚠️ Произошла ошибка при сохранении данных. "
                "Пожалуйста, попробуйте зарегистрироваться позже или свяжитесь с организаторами."
            )

        context.user_data.clear()
        return ConversationHandler.END
    else:
        log_info("Пользователь отменил регистрацию на этапе подтверждения", user)
        await query.edit_message_text(
            "Регистрация отменена. Используйте /start для начала новой регистрации."
        )
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации"""
    user = update.effective_user
    log_warning("Пользователь отменил регистрацию (/cancel)", user)
    await update.message.reply_text(
        "Регистрация отменена. Используйте /start для начала новой регистрации.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Перезапуск регистрации"""
    user = update.effective_user
    log_info("Команда /restart - перезапуск регистрации", user)
    context.user_data.clear()
    # Устанавливаем флаг, что это перезапуск
    context.user_data['force_restart'] = True
    await update.message.reply_text(
        "Начинаем регистрацию заново...",
        reply_markup=ReplyKeyboardRemove()
    )
    return await start(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Помощь"""
    help_text = (
        "🤖 КОМАНДЫ БОТА:\n\n"
        "/start - Начать регистрацию\n"
        "/restart - Перезапустить регистрацию\n"
        "/cancel - Отменить текущую регистрацию\n"
        "/help - Показать эту справку\n\n"
        "По вопросам обращайтесь к организаторам форума Future Wave."
    )
    await update.message.reply_text(help_text)


def main():
    """Запуск бота"""
    # Получаем токен из .env файла
    token = os.getenv('BOT_TOKEN')

    if not token:
        print("Ошибка: BOT_TOKEN не найден в .env файле")
        return

    # Создаём приложение
    application = Application.builder().token(token).build()

    # Настраиваем ConversationHandler для регистрации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONSENT: [CallbackQueryHandler(consent_callback, pattern="^consent_")],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, birth_date)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            UNIVERSITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, university)],
            UNIVERSITY_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, university_custom)],
            COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, course)],
            INTERNSHIP_INTEREST: [CallbackQueryHandler(internship_interest, pattern="^internship_")],
            CONFIRMATION: [CallbackQueryHandler(confirmation, pattern="^confirm_")],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('restart', restart)
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('restart', restart))
    application.add_handler(CommandHandler('admin', admin_command))

    # Обработчик для кнопок админ-панели
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))

    # Запускаем бота
    print("🤖 Бот запущен! Ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

