import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from database import Database
import config
import threading
import time
from parsers import fetch_all_news


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SET_DEFAULT_SOURCE, SET_ITEMS_PER_PAGE = range(2)

COMMANDS = {
    'start': 'Запуск бота и описание функций',
    'news': 'Получить последние новости',
    'settings': 'Настройки параметров',
    'subscriptions': 'Управление подписками',
    'help': 'Помощь по командам'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = Database()
    
    try:
        db.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES (%s, %s, %s) "
            "ON CONFLICT (telegram_id) DO NOTHING",
            (user.id, user.username, user.full_name),
            commit=True
        )
        
        db.execute(
            "INSERT INTO user_settings (user_id) "
            "SELECT id FROM users WHERE telegram_id = %s "
            "ON CONFLICT (user_id) DO NOTHING",
            (user.id,),
            commit=True
        )
        
        logger.info(f"Пользователь зарегистрирован: {user.full_name} (ID: {user.id})")
        
        message = (
            f"👋 Привет, {user.full_name}!\n\n"
            " В мои возможности входит: \n"
            "-Присылать свежие новости по запросу\n"
            "-Отправлять новости автоматически по подписке\n\n"
            "-Доступные команды:\n"
        )
        message += "\n".join([f"/{cmd} - {desc}" for cmd, desc in COMMANDS.items()])
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка регистрации пользователя: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации. Попробуйте снова.")
    finally:
        db.close()

async def handle_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = Database()
    
    try:
        settings = db.fetch_one(
            "SELECT items_per_page, default_source_id FROM user_settings "
            "WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)",
            (user.id,)
        )
        
        if not settings:
            await update.message.reply_text("Ваши настройки не найдены. Используйте /start для инициализации.")
            return
        
        items_per_page = settings[0] or 5
        default_source_id = settings[1]
        
        if default_source_id:
            news = db.fetch_all(
                "SELECT n.title, n.url, s.base_url FROM news n "
                "JOIN sources s ON n.source_id = s.id "
                "WHERE s.id = %s ORDER BY n.published_at DESC LIMIT %s",
                (default_source_id, items_per_page)
            )
        else:
            news = db.fetch_all(
                "SELECT n.title, n.url, s.base_url FROM news n "
                "JOIN sources s ON n.source_id = s.id "
                "ORDER BY n.published_at DESC LIMIT %s",
                (items_per_page,)
            )
        
        if not news:
            await update.message.reply_text("Пока нет новостей. Попробуйте позже!")
            return
        
        response = "Последние новости:\n\n"
        for item in news:
            domain = item[2].replace('www.', '').split('/')[0]
            response += f"{item[0]}\n<a href='{item[1]}'>Читать</a>\n\n"
        
        await update.message.reply_text(
            text=response,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка получения новостей: {e}")
        await update.message.reply_text("Произошла ошибка при получении новостей. Попробуйте позже.")
    finally:
        db.close()

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Источник по умолчанию", callback_data='set_default_source')],
        [InlineKeyboardButton("Количество новостей на страницу", callback_data='set_items_per_page')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите настройку:', reply_markup=reply_markup)

async def settings_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'set_default_source':
        db = Database()
        try:
            sources = db.fetch_all("SELECT id, name FROM sources")
            
            keyboard = []
            for source in sources:
                keyboard.append([InlineKeyboardButton(source[1], callback_data=f'set_source_{source[0]}')])
            keyboard.append([InlineKeyboardButton("Назад", callback_data='back_to_settings')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Выберите источник по умолчанию:", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка получения источников: {e}")
            await query.edit_message_text("Произошла ошибка при загрузке источников.")
        finally:
            db.close()
    
    elif data.startswith('set_source_'):
        source_id = data.split('_')[-1]
        user_id = query.from_user.id
        db = Database()
        
        try:
            db.execute(
                "UPDATE user_settings SET default_source_id = %s "
                "WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)",
                (source_id, user_id),
                commit=True
            )
            
            source_name = db.fetch_one("SELECT name FROM sources WHERE id = %s", (source_id,))[0]
            await query.edit_message_text(text=f"Источник по умолчанию установлен: {source_name}")
        except Exception as e:
            logger.error(f"Ошибка установки источника: {e}")
            await query.edit_message_text("Произошла ошибка при установке источника.")
        finally:
            db.close()
    
    elif data == 'set_items_per_page':
        await query.edit_message_text("Введите количество новостей на страницу (1-20):")
        return SET_ITEMS_PER_PAGE
    
    elif data == 'back_to_settings':
        await settings_command(update, context)
        return ConversationHandler.END
    
    elif data == 'back_to_main':
        await query.delete_message()
        await start(update, context)
        return ConversationHandler.END
    
    return ConversationHandler.END

async def set_items_per_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    db = Database()
    
    try:
        count = int(update.message.text)
        if 1 <= count <= 20:
            db.execute(
                "UPDATE user_settings SET items_per_page = %s "
                "WHERE user_id = (SELECT id FROM users WHERE telegram_id = %s)",
                (count, user_id),
                commit=True
            )
            await update.message.reply_text(f"Установлено количество новостей: {count}")
        else:
            await update.message.reply_text("Введите число от 1 до 20")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число")
    except Exception as e:
        logger.error(f"Ошибка установки количества новостей: {e}")
        await update.message.reply_text("Произошла ошибка при установке количества.")
    finally:
        db.close()
    
    return ConversationHandler.END

async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = Database()
    
    try:
        subscriptions = db.fetch_all(
            "SELECT s.id, s.name FROM subscriptions sub "
            "JOIN sources s ON sub.source_id = s.id "
            "WHERE sub.user_id = (SELECT id FROM users WHERE telegram_id = %s)",
            (user.id,)
        )
        
        all_sources = db.fetch_all("SELECT id, name FROM sources")
        
        keyboard = []
        for source in all_sources:
            source_id, source_name = source
            is_subscribed = any(sub[0] == source_id for sub in subscriptions)
            button_text = f"{'✅ ' if is_subscribed else '❌ '}{source_name}"
            callback_data = f"toggle_sub_{source_id}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("Готово", callback_data='done_subs')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📬 Управление подписками. Выберите источники:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка получения подписок: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке подписок.")
    finally:
        db.close()

async def subscriptions_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'done_subs':
        await query.edit_message_text(text="Настройки подписок сохранены.")
        return
    
    if data.startswith('toggle_sub_'):
        source_id = data.split('_')[-1]
        user_id = query.from_user.id
        db = Database()
        
        try:
            is_subscribed = db.fetch_one(
                "SELECT id FROM subscriptions WHERE "
                "user_id = (SELECT id FROM users WHERE telegram_id = %s) AND source_id = %s",
                (user_id, source_id)
            )
            
            if is_subscribed:
                db.execute(
                    "DELETE FROM subscriptions WHERE "
                    "user_id = (SELECT id FROM users WHERE telegram_id = %s) AND source_id = %s",
                    (user_id, source_id),
                    commit=True
                )
                logger.info(f"Пользователь {user_id} отписался от источника {source_id}")
            else:
                db.execute(
                    "INSERT INTO subscriptions (user_id, source_id) VALUES "
                    "((SELECT id FROM users WHERE telegram_id = %s), %s)",
                    (user_id, source_id),
                    commit=True
                )
                logger.info(f"Пользователь {user_id} подписался на источник {source_id}")
            
            await subscriptions_command(update, context)
        except Exception as e:
            logger.error(f"Ошибка обновления подписки: {e}")
            await query.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
        finally:
            db.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "Список доступных команд:\n\n"
    help_text += "\n".join([f"/{cmd} - {desc}" for cmd, desc in COMMANDS.items()])
    await update.message.reply_text(help_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")
    if update.message:
        await update.message.reply_text("Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")

def setup_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", handle_news))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("subscriptions", subscriptions_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CallbackQueryHandler(settings_button, pattern='^(set_default_source|set_source_|set_items_per_page|back_to)'))
    application.add_handler(CallbackQueryHandler(subscriptions_button, pattern='^(toggle_sub_|done_subs)'))
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(settings_button, pattern='^set_items_per_page$')],
        states={
            SET_ITEMS_PER_PAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_items_per_page)]
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(conv_handler)
    
    application.add_error_handler(error_handler)

def news_scheduler():
    """Фоновый поток для периодического сбора новостей"""
    while True:
        try:
            fetch_all_news()
            logger.info("Новости успешно обновлены")
        except Exception as e:
            logger.error(f"Ошибка при обновлении новостей: {e}")
        time.sleep(1800)  

def main():
    scheduler_thread = threading.Thread(target=news_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Служба сбора новостей запущена")
    
    application = Application.builder().token(config.BOT_TOKEN).build()
    setup_handlers(application)
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()