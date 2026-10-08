import logging
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from database import Database

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHOOSING_ACTION, ADD_TYPE, ADD_TITLE, ADD_DESCRIPTION, ADD_DATE, DELETE_EVENT = range(6)

# Инициализация базы данных
db = Database(os.getenv("DATABASE_PATH", "reminder_bot.db"))

# Главное меню
def get_main_menu():
    keyboard = [
        ['➕ Добавить домашку', '➕ Добавить мероприятие'],
        ['📋 Мои домашки', '📅 Мои мероприятия'],
        ['🗑 Удалить событие', '📊 Все события']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом"""
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}! 👋\n\n'
        'Я помогу тебе не забывать о домашках и мероприятиях.\n'
        'Я буду напоминать тебе за неделю, 3 дня и 1 день до события.\n\n'
        'Выбери действие:',
        reply_markup=get_main_menu()
    )
    return CHOOSING_ACTION

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора в главном меню"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == '➕ Добавить домашку':
        context.user_data['event_type'] = 'homework'
        await update.message.reply_text(
            '📝 Введите название домашки:',
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TITLE

    elif text == '➕ Добавить мероприятие':
        context.user_data['event_type'] = 'event'
        await update.message.reply_text(
            '📝 Введите название мероприятия:',
            reply_markup=ReplyKeyboardRemove()
        )
        return ADD_TITLE

    elif text == '📋 Мои домашки':
        events = db.get_user_events(user_id, 'homework')
        if events:
            message = '📚 <b>Ваши домашки:</b>\n\n'
            for event in events:
                event_id, title, description, event_date, _ = event
                date_obj = datetime.strptime(event_date, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%d.%m.%Y")
                message += f'📌 <b>{title}</b>\n'
                message += f'📅 Дата: {date_formatted}\n'
                if description:
                    message += f'📄 {description}\n'
                message += '\n'
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text('У вас пока нет домашек 😊')
        return CHOOSING_ACTION

    elif text == '📅 Мои мероприятия':
        events = db.get_user_events(user_id, 'event')
        if events:
            message = '🎉 <b>Ваши мероприятия:</b>\n\n'
            for event in events:
                event_id, title, description, event_date, _ = event
                date_obj = datetime.strptime(event_date, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%d.%m.%Y")
                message += f'📌 <b>{title}</b>\n'
                message += f'📅 Дата: {date_formatted}\n'
                if description:
                    message += f'📄 {description}\n'
                message += '\n'
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text('У вас пока нет мероприятий 😊')
        return CHOOSING_ACTION

    elif text == '📊 Все события':
        events = db.get_user_events(user_id)
        if events:
            message = '📋 <b>Все ваши события:</b>\n\n'
            for event in events:
                event_id, title, description, event_date, event_type = event
                date_obj = datetime.strptime(event_date, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%d.%m.%Y")
                type_emoji = '📚' if event_type == 'homework' else '🎉'
                message += f'{type_emoji} <b>{title}</b>\n'
                message += f'📅 Дата: {date_formatted}\n'
                if description:
                    message += f'📄 {description}\n'
                message += '\n'
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text('У вас пока нет событий 😊')
        return CHOOSING_ACTION

    elif text == '🗑 Удалить событие':
        events = db.get_user_events(user_id)
        if events:
            message = '📋 <b>Ваши события:</b>\n\n'
            keyboard = []
            for event in events:
                event_id, title, description, event_date, event_type = event
                date_obj = datetime.strptime(event_date, "%Y-%m-%d")
                date_formatted = date_obj.strftime("%d.%m.%Y")
                type_emoji = '📚' if event_type == 'homework' else '🎉'
                message += f'ID: {event_id} - {type_emoji} {title} ({date_formatted})\n'
                keyboard.append([f'❌ {event_id} - {title[:20]}'])

            keyboard.append(['↩️ Назад'])
            await update.message.reply_text(
                message + '\nВыберите событие для удаления:',
                parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return DELETE_EVENT
        else:
            await update.message.reply_text('У вас пока нет событий для удаления 😊')
            return CHOOSING_ACTION

    return CHOOSING_ACTION

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение названия события"""
    context.user_data['title'] = update.message.text
    await update.message.reply_text(
        '📄 Введите описание (или отправьте "-" чтобы пропустить):'
    )
    return ADD_DESCRIPTION

async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение описания события"""
    description = update.message.text
    context.user_data['description'] = '' if description == '-' else description
    await update.message.reply_text(
        '📅 Введите дату события в формате ДД.ММ.ГГГГ\n'
        'Например: 15.12.2026'
    )
    return ADD_DATE

async def add_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение даты и создание события"""
    date_text = update.message.text
    user_id = update.effective_user.id

    try:
        # Парсим дату
        event_date = datetime.strptime(date_text, "%d.%m.%Y")

        # Проверяем что дата в будущем
        if event_date.date() < datetime.now().date():
            await update.message.reply_text(
                '❌ Дата должна быть в будущем!\n'
                'Попробуйте еще раз:'
            )
            return ADD_DATE

        # Сохраняем в базу
        event_id = db.add_event(
            user_id=user_id,
            title=context.user_data['title'],
            event_date=event_date.strftime("%Y-%m-%d"),
            event_type=context.user_data['event_type'],
            description=context.user_data.get('description', '')
        )

        event_type_text = 'Домашка' if context.user_data['event_type'] == 'homework' else 'Мероприятие'
        await update.message.reply_text(
            f'✅ {event_type_text} успешно добавлена!\n\n'
            f'📌 {context.user_data["title"]}\n'
            f'📅 {date_text}\n\n'
            'Я напомню тебе за неделю, 3 дня и 1 день до события! ⏰',
            reply_markup=get_main_menu()
        )

        # Очищаем данные
        context.user_data.clear()

        return CHOOSING_ACTION

    except ValueError:
        await update.message.reply_text(
            '❌ Неправильный формат даты!\n'
            'Используйте формат ДД.ММ.ГГГГ (например: 15.12.2026)'
        )
        return ADD_DATE

async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление события"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == '↩️ Назад':
        await update.message.reply_text(
            'Выберите действие:',
            reply_markup=get_main_menu()
        )
        return CHOOSING_ACTION

    try:
        # Извлекаем ID из текста кнопки
        event_id = int(text.split('-')[0].replace('❌', '').strip())

        if db.delete_event(event_id, user_id):
            await update.message.reply_text(
                '✅ Событие успешно удалено!',
                reply_markup=get_main_menu()
            )
        else:
            await update.message.reply_text(
                '❌ Не удалось удалить событие',
                reply_markup=get_main_menu()
            )

        return CHOOSING_ACTION

    except (ValueError, IndexError):
        await update.message.reply_text(
            '❌ Ошибка при удалении. Попробуйте еще раз.',
            reply_markup=get_main_menu()
        )
        return CHOOSING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена операции"""
    await update.message.reply_text(
        'Операция отменена',
        reply_markup=get_main_menu()
    )
    return CHOOSING_ACTION

async def check_reminders(application: Application):
    """Проверка и отправка напоминаний"""
    reminders = db.get_pending_reminders()

    for reminder in reminders:
        reminder_id, event_id, user_id, title, description, event_date, event_type, remind_date = reminder

        # Вычисляем сколько дней осталось
        event_datetime = datetime.strptime(event_date, "%Y-%m-%d")
        days_left = (event_datetime.date() - datetime.now().date()).days

        type_emoji = '📚' if event_type == 'homework' else '🎉'
        type_text = 'домашке' if event_type == 'homework' else 'мероприятии'

        message = f'⏰ <b>Напоминание!</b>\n\n'
        message += f'{type_emoji} <b>{title}</b>\n'
        message += f'📅 Дата: {event_datetime.strftime("%d.%m.%Y")}\n'

        if days_left == 7:
            message += '🕐 Осталась неделя!\n'
        elif days_left == 3:
            message += '🕒 Осталось 3 дня!\n'
        elif days_left == 1:
            message += '🕓 Завтра!\n'

        if description:
            message += f'\n📄 {description}'

        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            db.mark_reminder_sent(reminder_id)
            logger.info(f'Sent reminder {reminder_id} to user {user_id}')
        except Exception as e:
            logger.error(f'Failed to send reminder {reminder_id}: {e}')

def main():
    """Запуск бота"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задана переменная окружения TELEGRAM_BOT_TOKEN")

    # Настраиваем опциональный SOCKS5 proxy для API и long polling.
    proxy_url = os.getenv("TELEGRAM_PROXY")
    application_builder = Application.builder().token(token)
    if proxy_url:
        application_builder.request(HTTPXRequest(proxy=proxy_url))
        application_builder.get_updates_request(HTTPXRequest(proxy=proxy_url))

    application = application_builder.build()

    # Настраиваем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
            ],
            ADD_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)
            ],
            ADD_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)
            ],
            ADD_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_date)
            ],
            DELETE_EVENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_event)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Настраиваем планировщик для проверки напоминаний
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_reminders,
        'interval',
        minutes=30,
        args=[application]
    )
    scheduler.start()

    # Запускаем бота
    logger.info('Bot started')
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
