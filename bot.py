import logging
import sys
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters, 
    ConversationHandler
)
from config import BOT_TOKEN, PROXY_URL
from handlers import tracking, admin, registration

# ============================================================================
# LOGGING CONFIGURATION - STRICT: ONLY ADMIN ACTIONS AND ERRORS
# ============================================================================
class CleanFormatter(logging.Formatter):
    """Custom formatter with clean output."""
    def format(self, record):
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        level = record.levelname.ljust(5)
        return f"[{timestamp}] {level} | {record.getMessage()}"

# Configure root logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler with clean format
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CleanFormatter())
logger.addHandler(console_handler)

# File handler with clean format
file_handler = logging.FileHandler("bot.log", encoding='utf-8')
file_handler.setFormatter(CleanFormatter())
logger.addHandler(file_handler)

# SILENCE all library loggers
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Enable tracking logger for important events (added/removed from groups)
logging.getLogger("handlers.tracking").setLevel(logging.INFO)
logging.getLogger("storage.json_db").setLevel(logging.INFO)

async def error_handler(update: object, context) -> None:
    """Log errors."""
    logger.error(f"Error: {context.error}")
    
    # Try to notify user
    if update and hasattr(update, 'effective_message') and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or contact support."
            )
        except:
            pass

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in .env file")
        return
    
    # Create the Application with increased timeouts for stability
    builder = ApplicationBuilder().token(BOT_TOKEN)
    builder.connect_timeout(30).read_timeout(30)
    
    if PROXY_URL:
        logger.info(f"Using proxy: {PROXY_URL}")
        builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)

    application = builder.build()
    
    logger.info("Bot initializing...")

    # ========================================================================
    # ADMIN CONVERSATION HANDLER (private chat only)
    # ========================================================================
    # ========================================================================
    # REGISTRATION CONVERSATION
    # ========================================================================
    registration_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(registration.start_registration, pattern="^start_registration$")],
        states={
            registration.WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.handle_name_input)],
        },
        fallbacks=[CommandHandler("cancel", registration.cancel_registration)],
        per_message=False,
        per_chat=True,
        per_user=True,
    )
    application.add_handler(registration_conv)
    
    # Global handler for Admin Actions (Approve/Reject)
    application.add_handler(CallbackQueryHandler(registration.handle_registration_callback, pattern="^reg:"))

    # ========================================================================
    # ADMIN CONVERSATION HANDLER (private chat only)
    # ========================================================================
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("start", admin.start, filters=filters.ChatType.PRIVATE)],
        states={
            admin.MENU: [CallbackQueryHandler(admin.handle_callback)],
            admin.ADD_T_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_teacher_id)],
            admin.ADD_T_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.add_teacher_name)],
            admin.ADD_T_TELEGRAM_ID: [
                MessageHandler(
                    (filters.TEXT | filters.FORWARDED) & ~filters.COMMAND, 
                    admin.add_teacher_telegram_id
                )
            ],
            admin.REPORT_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_report_days)],
            admin.EXCEL_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_excel_days)],
            admin.REPORT_GROUP_SELECT: [CallbackQueryHandler(admin.handle_callback)],
            admin.REPORT_GROUP_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_report_group_days)],
            admin.MYSTAT_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_mystat_days)],
            admin.TEACHER_REPORT_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_teacher_report_days)],
            admin.EDIT_GROUP_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_edit_group_title)],
            admin.EDIT_TEACHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_edit_teacher_name)],
        },
        fallbacks=[
            CommandHandler("cancel", admin.cancel),
            CommandHandler("start", admin.start)
        ],
        per_message=False,
        per_chat=True,
        per_user=True,
    )
    application.add_handler(admin_conv)

    # ========================================================================
    # GROUP COMMANDS
    # ========================================================================
    # /confirm_group - register a group (must be run in the group)
    application.add_handler(CommandHandler("confirm_group", admin.confirm_group))
    
    # /sync_groups - manual cleanup (private chat only)
    application.add_handler(CommandHandler("sync_groups", admin.sync_groups, filters=filters.ChatType.PRIVATE))
    
    # /diag - diagnostics (works anywhere)
    application.add_handler(CommandHandler("diag", admin.diag_command))

    # ========================================================================
    # MEMBERSHIP TRACKING
    # ========================================================================
    from telegram.ext import ChatMemberHandler
    application.add_handler(ChatMemberHandler(tracking.handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    # ========================================================================
    # ACTIVITY TRACKING (groups only)
    # ========================================================================
    # This handler captures ALL non-command messages in groups
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND & filters.ALL,
            tracking.track_activity
        ),
        group=1
    )

    # ========================================================================
    # ERROR HANDLER
    # ========================================================================
    application.add_error_handler(error_handler)

    logger.info("Bot started successfully")
    try:
        application.run_polling(drop_pending_updates=True, bootstrap_retries=5)
    except Exception as e:
        if "ConnectError" in str(e) or "NetworkError" in str(e):
            logger.error("\n" + "="*50 + 
                         "\n❌ CONNECTION ERROR: Cannot reach Telegram API." +
                         "\n1. Check if Telegram is blocked in your network." +
                         "\n2. If you use a VPN/Proxy, enable it and set PROXY_URL in .env." +
                         "\n3. Run 'python test_connection.py' for diagnostics." +
                         "\n" + "="*50)
        else:
            logger.error(f"Bot crashed: {e}")

if __name__ == '__main__':
    main()
