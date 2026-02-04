import logging
from telegram import Update, ChatMemberUpdated
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ChatMemberStatus
from storage import json_db

logger = logging.getLogger(__name__)

async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Track teacher activity in groups SILENTLY.
    Only tracks if:
    - Message is in a group
    - Group is registered and enabled
    - Sender is a registered and active teacher
    - Teacher is assigned to this group
    
    NO LOGS - completely silent operation.
    """
    if not update.effective_message or not update.effective_chat or not update.effective_user:
        return
    
    # Only track in groups
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    
    message = update.effective_message
    chat_id = update.effective_chat.id
    chat_id_str = str(chat_id)
    user_id = update.effective_user.id
    
    # 1. Check if group is registered and enabled
    group = json_db.get_group(chat_id_str)
    if not group or not group.get("enabled", True):
        return
    
    # 2. Check if user is a registered teacher
    teacher_id = json_db.find_teacher_by_telegram_id(user_id)
    if not teacher_id:
        return
    
    # 3. Check if teacher is active
    teacher = json_db.get_teacher(teacher_id)
    if not teacher or not teacher.get("active", True):
        return
    
    # 4. Check if teacher is assigned to this group
    if not json_db.is_teacher_assigned(teacher_id, chat_id_str):
        return
    
    # 5. Determine message type
    # We check media first because media messages often have a caption which is technically text
    msg_type = None
    
    if message.photo:
        msg_type = "photo"
    elif message.video or message.video_note:
        msg_type = "video"
    elif message.audio:
        msg_type = "audio"
    elif message.voice:
        msg_type = "voice"
    elif message.document:
        msg_type = "document"
    elif message.text:
        # Check if it's not just a command that somehow passed filters
        if not message.text.startswith('/'):
            msg_type = "text"
    
    # 6. Increment counter SILENTLY
    if msg_type:
        today_str = json_db.get_today_str()
        try:
            json_db.increment_counter(today_str, chat_id_str, teacher_id, msg_type)
            # NO LOGGING - silent operation
        except Exception as e:
            # Only log errors
            logger.error(f"Failed to increment counter: {e}")

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot membership changes."""
    result = update.my_chat_member
    if not result:
        return
    
    chat = result.chat
    chat_id_str = str(chat.id)
    chat_title = chat.title or "Unknown"
    
    new_status = result.new_chat_member.status
    
    # If the bot was removed (left or kicked)
    if new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
        json_db.deactivate_group(chat_id_str)
        json_db.remove_group_from_assignments(chat_id_str)
        logger.info(f"BOT_REMOVED_FROM_GROUP {chat_id_str} ({chat_title})")
        
    # If the bot was added (member or admin)
    elif new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
        # Log as requested
        logger.info(f"BOT_ADDED_TO_GROUP {chat_id_str} ({chat_title})")
