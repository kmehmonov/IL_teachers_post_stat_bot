import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from storage import json_db
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Registration States
WAIT_NAME = 1

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process."""
    user = update.effective_user
    query = update.callback_query
    
    # Always answer callback query
    if query:
        await query.answer()
    
    # Double check if already pending
    pending = json_db.get_pending_registration(user.id)
    if pending:
        msg = (
            "⏳ Your registration request is pending approval.\n"
            "Please wait for admin confirmation."
        )
        if query:
            # Edit the message with the button, or send new one
            await query.edit_message_text(msg)
        elif update.effective_message:
             await update.effective_message.reply_text(msg)
             
        return ConversationHandler.END

    msg = (
        "📝 *Registration*\n\n"
        "Please enter your *Full Name (F.I.SH)* to register as a teacher.\n"
        "Example: _Aliyev Vali Valiyevich_"
    )
    
    if query:
        await query.edit_message_text(msg, parse_mode='Markdown')
    elif update.effective_message:
        await update.effective_message.reply_text(msg, parse_mode='Markdown')
        
    return WAIT_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input and send request to admin."""
    full_name = update.message.text.strip()
    user = update.effective_user
    
    if len(full_name) < 5:
        await update.message.reply_text("❌ Name is too short. Please enter your full name (F.I.SH):")
        return WAIT_NAME
        
    # Save pending request
    json_db.add_pending_registration(user.id, full_name)
    
    # Notify User
    await update.message.reply_text(
        "✅ *Request Sent!*\n\n"
        "Your registration request has been sent to the administrators.\n"
        "You will be notified once approved.",
        parse_mode='Markdown'
    )
    
    # Notify Admins
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"reg:ap:{user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reg:rj:{user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = (
        "🆕 *New Registration Request*\n\n"
        f"👤 Name: {full_name}\n"
        f"🆔 Telegram ID: `{user.id}`\n"
        f"🔗 Username: @{user.username if user.username else 'None'}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=msg_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send request to admin {admin_id}: {e}")
            
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration."""
    await update.message.reply_text("❌ Registration cancelled.")
    return ConversationHandler.END

# ADMIN ACTIONS

async def handle_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin decision."""
    query = update.callback_query
    data = query.data
    
    # Format: reg:action:user_id
    parts = data.split(":")
    if len(parts) != 3:
        return
        
    action, user_id_str = parts[1], parts[2]
    try:
        user_id = int(user_id_str)
    except ValueError:
        return

    # Load pending data
    pending = json_db.get_pending_registration(user_id)
    if not pending and action == "ap": # Only matter if approving, if rejecting and already gone, fine
        await query.answer("❌ Request expired or already processed.", show_alert=True)
        await query.edit_message_text(f"{query.message.text}\n\n⚠️ *Expired/Processed*", parse_mode='Markdown')
        return

    if action == "ap": # Approve
        full_name = pending["full_name"]
        
        # transform name to teacher ID
        teacher_id = json_db.generate_teacher_id()
        
        # Add to DB
        success, msg = json_db.add_teacher(teacher_id, full_name, user_id)
        
        if success:
            # Remove from pending
            json_db.remove_pending_registration(user_id)
            
            # Check memberships in all enabled groups
            groups = json_db.load_groups()
            assigned_count = 0
            
            for chat_id_str, g_data in groups.items():
                if not g_data.get("enabled", True):
                    continue
                    
                try:
                    # Check if user is member
                    member = await context.bot.get_chat_member(chat_id=int(chat_id_str), user_id=user_id)
                    from telegram.constants import ChatMemberStatus
                    
                    if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                        json_db.toggle_assignment(teacher_id, chat_id_str)
                        # Ensure it was Added (toggle adds if not present)
                        assigned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Could not check membership for {user_id} in {chat_id_str}: {e}")

            # Notify Admin
            status_msg = f"✅ *Approved* by {update.effective_user.first_name}\n"
            status_msg += f"Assigned ID: `{teacher_id}`\n"
            status_msg += f"🔗 Auto-joined {assigned_count} groups."
            
            await query.edit_message_text(f"{query.message.text}\n\n{status_msg}", parse_mode='Markdown')
            
            # Notify User
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎉 *Registration Approved!*\n\n"
                        f"Welcome, {full_name}!\n"
                        f"Your Teacher ID: `{teacher_id}`\n\n"
                        "You can now use the bot menu."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            await query.answer(f"Error: {msg}", show_alert=True)
            
    elif action == "rj": # Reject
        json_db.remove_pending_registration(user_id)
        
        await query.edit_message_text(
            f"{query.message.text}\n\n❌ *Rejected* by {update.effective_user.first_name}",
            parse_mode='Markdown'
        )
        
        # Notify User (Optional, but polite)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Your registration request was declined by an administrator."
            )
        except:
            pass
