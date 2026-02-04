import logging
import os
from datetime import datetime
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatType
from storage import json_db
from config import ADMIN_IDS, EXPORT_DIR

logger = logging.getLogger(__name__)

# Conversation states
(
    MENU,
    ADD_T_ID,
    ADD_T_NAME,
    ADD_T_TELEGRAM_ID,
    REPORT_DAYS,
    EXCEL_DAYS,
    REPORT_GROUP_SELECT,
    REPORT_GROUP_DAYS,
    MYSTAT_DAYS,
    TEACHER_REPORT_DAYS,
    EDIT_GROUP_TITLE,
    EDIT_TEACHER_NAME
) = range(12)

def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS

# ============================================================================
# UNIFIED FORMATTING HELPERS
# ============================================================================

def get_overall_total(counters: dict) -> int:
    """Calculate sum of all message types."""
    types = ["text", "photo", "video", "audio", "voice", "document"]
    return sum(counters.get(t, 0) for t in types)

def format_breakdown(counters: dict) -> str:
    """Return 2-line breakdown with fixed icon order."""
    # Fixed icon order: 📝 📸 🎥 🎵 🎤 📎
    line1 = f"📝 {counters.get('text', 0)} | 📸 {counters.get('photo', 0)} | 🎥 {counters.get('video', 0)}"
    line2 = f"🎵 {counters.get('audio', 0)} | 🎤 {counters.get('voice', 0)} | 📎 {counters.get('document', 0)}"
    return f"{line1}\n   {line2}"

def format_entity_block(title_line: str, counters: dict) -> str:
    """Return title line + indented breakdown."""
    return f"{title_line}\n   {format_breakdown(counters)}"

def format_short_name(full_name: str) -> str:
    """Return First Last name only."""
    parts = full_name.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return full_name

# ============================================================================
# MAIN MENU
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main entry point: routes to Admin or Teacher menu."""
    if not update.effective_user or not update.effective_chat:
        return ConversationHandler.END

    if update.effective_chat.type != ChatType.PRIVATE:
        return ConversationHandler.END

    user_id = update.effective_user.id
    
    # 1. Admin Panel
    if is_admin(user_id):
        return await admin_menu(update, context)
    
    # 2. Teacher Panel
    teacher_id = json_db.find_teacher_by_telegram_id(user_id)
    if teacher_id:
        teacher = json_db.get_teacher(teacher_id)
        if teacher and teacher.get("active", True):
            return await teacher_menu(update, context, teacher_id, teacher)
    
    # 3. Unauthorized / New User
    if json_db.get_pending_registration(user_id):
        await update.message.reply_text("⏳ Your registration request is pending approval.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("📝 Ro'yxatdan o'tish", callback_data="start_registration")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "Siz tizimda ro'yxatdan o'tmagansiz.\n"
        "Botdan foydalanish uchun ro'yxatdan o'ting.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin menu."""
    msg = "🎮 *Admin Control Panel*\n\nChoose an action:"
    
    keyboard = [
        [InlineKeyboardButton("👨‍🏫 Teachers", callback_data="m:teachers")],
        [InlineKeyboardButton("🏫 Groups", callback_data="m:groups")],
        [
            InlineKeyboardButton("📊 Reports", callback_data="m:reports"),
            InlineKeyboardButton("📥 Excel", callback_data="m:excel")
        ],
        [InlineKeyboardButton("⏳ Kutilayotgan so'rovlar", callback_data="m:pending")],
        [InlineKeyboardButton(" Diagnostics", callback_data="m:diag")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                raise
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    
    return MENU

async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str, teacher: dict):
    """Teacher panel."""
    msg = f"👨‍🏫 *Teacher Panel*\n\nWelcome back, *{teacher['full_name']}*!\n\nChoose an action:"
    
    keyboard = [
        [InlineKeyboardButton("📊 MyStat", callback_data="m:mystat")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                raise
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

# ============================================================================
# CALLBACK QUERY ROUTER
# ============================================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Menu actions
    if data == "m:teachers":
        return await list_teachers(update, context)
    elif data == "m:add_teacher":
        await query.message.reply_text("📝 Enter Teacher ID (3-16 alphanumeric, e.g., T001 or DB8F99C3):")
        return ADD_T_ID
    elif data == "m:groups":
        return await list_groups(update, context)
    elif data == "m:add_group":
        await query.message.reply_text(
            "📋 *How to add a group:*\n\n"
            "1️⃣ Add this bot to the target group\n"
            "2️⃣ Promote the bot to admin\n"
            "3️⃣ In that group, send: `/confirm_group`\n\n"
            "The group will be registered automatically!",
            parse_mode='Markdown'
        )
        return await start(update, context)
    elif data == "m:reports":
        msg = "📊 *Select Report Type:*"
        keyboard = [
            [InlineKeyboardButton("Teachers Report", callback_data="r:t_simple")],
            [InlineKeyboardButton("Teachers Detailed", callback_data="r:t_detail")],
            [InlineKeyboardButton("Group Report", callback_data="r:g_simple")],
            [InlineKeyboardButton("Groups Detailed", callback_data="r:g_detail")],
            [InlineKeyboardButton("« Back", callback_data="m:back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        return MENU
        
    elif data.startswith("r:"):
        context.user_data["report_type"] = data[2:]
        await query.message.reply_text("📊 Enter number of days for report (1-365):")
        return REPORT_DAYS
    elif data == "m:excel":
        await query.message.reply_text("📥 Enter number of days for Excel export (1-365):")
        return EXCEL_DAYS
    elif data == "m:diag":
        return await show_diagnostics(update, context)
    elif data == "m:pending":
        return await show_pending_registrations(update, context)
    elif data == "m:mystat":
        await query.message.reply_text("📊 Enter number of days for your statistics (1-365):")
        return MYSTAT_DAYS
    elif data == "m:back":
        return await start(update, context)
    
    # Teacher detail
    elif data.startswith("t:"):
        teacher_id = str(data[2:])
        return await show_teacher_detail(update, context, teacher_id)
    
    # Group detail
    elif data.startswith("g:"):
        chat_id_str = str(data[2:])
        return await show_group_detail(update, context, chat_id_str)
    
    # Report by Group: Group selection
    elif data.startswith("rg:"):
        chat_id_str = str(data[3:])
        context.user_data["report_group_id"] = chat_id_str
        await query.message.reply_text("📊 Enter number of days for report (1-365):")
        return REPORT_GROUP_DAYS
    
    # Teacher groups
    elif data.startswith("tg:"):
        teacher_id = str(data[3:])
        return await show_teacher_groups(update, context, teacher_id)
        
    # Teacher report
    elif data.startswith("tr:"):
        teacher_id = str(data[3:])
        return await ask_teacher_report_days(update, context, teacher_id)

    # Teacher edit name
    elif data.startswith("te_n:"):
        teacher_id = str(data[5:])
        return await start_edit_teacher_name(update, context, teacher_id)


    # Teacher delete confirm
    elif data.startswith("td:"):
        teacher_id = str(data[3:])
        return await confirm_delete_teacher(update, context, teacher_id)
        
    # Teacher delete perform
    elif data.startswith("tdc:"):
        teacher_id = str(data[4:])
        return await perform_delete_teacher(update, context, teacher_id)

    # Show unassigned groups for adding (aa = add assignment)
    elif data.startswith("aa:"):
        teacher_id = str(data[3:])
        return await show_unassigned_groups(update, context, teacher_id)
    
    # Assignment toggle
    elif data.startswith("a:"):
        parts = data[2:].split("|")
        if len(parts) == 2:
            teacher_id, chat_id_str = parts
            return await toggle_assignment(update, context, teacher_id, chat_id_str)
    
    # Toggle group enabled
    elif data.startswith("ge:"):
        chat_id_str = data[3:]
        # After toggling, return to settings
        await toggle_group_enabled(update, context, chat_id_str)
        return await show_group_settings(update, context, chat_id_str)

    # Group settings menu
    elif data.startswith("gs:"):
        chat_id_str = data[3:]
        return await show_group_settings(update, context, chat_id_str)

    # Group delete confirm
    elif data.startswith("gd:"):
        chat_id_str = data[3:]
        return await confirm_delete_group(update, context, chat_id_str)

    # Group Edit title
    elif data.startswith("ge_t:"):
        chat_id_str = data[5:]
        return await start_edit_group_title(update, context, chat_id_str)
        
    # Group delete perform
    elif data.startswith("gdc:"):
        chat_id_str = data[4:]
        return await perform_delete_group(update, context, chat_id_str)
    return MENU

async def show_pending_registrations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending registration requests."""
    pending = json_db.load_pending_registrations()
    
    if not pending:
        await update.callback_query.message.reply_text("✅ No pending requests found.")
        return await start(update, context)
        
    await update.callback_query.message.reply_text(f"⏳ Found {len(pending)} pending requests:")
    
    for telegram_id, data in pending.items():
        name = data.get("full_name", "Unknown Request")
        created = data.get("created_at", "")[:19]
        
        msg_text = (
            f"🆕 *Pending Request*\n\n"
            f"👤 Name: {name}\n"
            f"🆔 Telegram ID: `{telegram_id}`\n"
            f"📅 Time: {created}"
        )
        
        # Reuse the 'reg:ap' and 'reg:rj' callback data format from registration.py
        # It is handled globally in bot.py by handle_registration_callback
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"reg:ap:{telegram_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reg:rj:{telegram_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.reply_text(
            msg_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    return MENU

# ============================================================================
# TEACHERS
# ============================================================================

async def list_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all teachers."""
    teachers = json_db.load_teachers()
    
    if not teachers:
        msg = "No teachers registered yet.\n\nUse *➕ Add Teacher* to add one."
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="m:back")]]
    else:
        msg = "👨‍🏫 *Teachers:*\n\n"
        keyboard = []
        
        for t_id, data in sorted(teachers.items()):
            status = "✅" if data.get("active", True) else "❌"
            msg += f"{status} `{t_id}` - {data['full_name']}\n"
            # Use short callback data
            keyboard.append([InlineKeyboardButton(
                f"{status} {t_id} - {data['full_name'][:20]}", 
                callback_data=f"t:{t_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="m:back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def list_groups_for_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all groups for selection."""
    query = update.callback_query
    groups = json_db.load_groups()
    
    if not groups:
        msg = "No groups registered yet.\n\nUse *➕ Add Group* for instructions."
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="m:back")]]
    else:
        msg = "📍 *Select a Group for Report:*\n\n"
        keyboard = []
        
        # Only show enabled groups
        active_groups = {k: v for k, v in groups.items() if v.get("enabled", True)}
        
        if not active_groups:
            msg = "No active groups found."
            keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="m:back")]]
        else:
            for chat_id_str, data in sorted(active_groups.items(), key=lambda x: x[1]['title']):
                keyboard.append([InlineKeyboardButton(
                    f"🏫 {data['title'][:30]}",
                    callback_data=f"rg:{chat_id_str}"
                )])
            
            keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="m:back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return REPORT_GROUP_SELECT

async def show_teacher_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Show teacher details and stats."""
    teacher = json_db.get_teacher(teacher_id)
    if not teacher:
        await update.callback_query.answer("Teacher not found", show_alert=True)
        return await list_teachers(update, context)
    
    # Get stats for last 7 days
    stats = json_db.get_teacher_stats_summary(teacher_id, days=7)
    groups = json_db.load_groups()
    
    
    msg = f"👨‍🏫 *{teacher['full_name']}*\n"
    msg += f"ID: `{teacher_id}`\n"
    msg += f"Telegram ID: `{teacher['telegram_user_id']}`\n"
    msg += f"Status: {'✅ Active' if teacher.get('active', True) else '❌ Inactive'}\n\n"
    msg += "Choose an action:"
    
    keyboard = [
        [InlineKeyboardButton("🏫 Ustozning guruhlari", callback_data=f"tg:{teacher_id}")],
        [InlineKeyboardButton("✏️ Ismni tahrirlash", callback_data=f"te_n:{teacher_id}")],
        [InlineKeyboardButton("📊 Ustoz bo'yicha hisobot", callback_data=f"tr:{teacher_id}")],
        [InlineKeyboardButton("❌ O'qituvchini o'chirish", callback_data=f"td:{teacher_id}")],
        [InlineKeyboardButton("« Back to Teachers", callback_data="m:teachers")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def start_edit_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Ask for new teacher name."""
    teacher = json_db.get_teacher(teacher_id)
    if not teacher:
        return await list_teachers(update, context)
        
    context.user_data['edit_teacher_id'] = teacher_id
    
    msg = (
        f"✏️ *Edit Teacher Name*\n\n"
        f"Current: `{teacher['full_name']}`\n\n"
        "Please enter the new full name (F.I.SH):"
    )
    await update.callback_query.message.reply_text(msg, parse_mode='Markdown')
    return EDIT_TEACHER_NAME

async def handle_edit_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save new teacher name."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter text:")
        return EDIT_TEACHER_NAME
        
    teacher_id = context.user_data.get('edit_teacher_id')
    if not teacher_id:
        return await start(update, context)
        
    new_name = update.message.text.strip()
    json_db.update_teacher_name(teacher_id, new_name)
    
    await update.message.reply_text(f"✅ Teacher name updated to: **{new_name}**", parse_mode='Markdown')
    return await start(update, context)

async def confirm_delete_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Ask for confirmation before deleting a teacher."""
    teacher = json_db.get_teacher(teacher_id)
    if not teacher:
        return await list_teachers(update, context)
        
    msg = (
        f"⚠️ *DELETE TEACHER?*\n\n"
        f"Are you sure you want to delete **{teacher['full_name']}**?\n"
        f"This action cannot be undone."
    )
    
    keyboard = [
        [InlineKeyboardButton("🗑️ YES, DELETE", callback_data=f"tdc:{teacher_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"t:{teacher_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def perform_delete_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Execute deletion."""
    success, msg = json_db.delete_teacher(teacher_id)
    if success:
        await update.callback_query.answer(msg, show_alert=True)
        return await list_teachers(update, context)
    else:
        await update.callback_query.answer(f"Error: {msg}", show_alert=True)
        return await show_teacher_detail(update, context, teacher_id)

async def show_teacher_groups(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Show groups assigned to a teacher."""
    teacher = json_db.get_teacher(teacher_id)
    if not teacher:
        return await list_teachers(update, context)
        
    msg = f"🏫 *Groups for {teacher['full_name']}*\n\n"
    msg += "*Assigned Groups:*"
    
    keyboard = []
    all_groups = json_db.load_groups()
    assigned_groups = json_db.get_teacher_groups(teacher_id)
    
    has_groups = False
    if assigned_groups:
        for chat_id_str in assigned_groups:
            if chat_id_str in all_groups:
                g_title = all_groups[chat_id_str]['title']
                keyboard.append([InlineKeyboardButton(
                    f"🏫 {g_title[:30]}",
                    callback_data=f"a:{teacher_id}|{chat_id_str}"
                )])
                has_groups = True
    
    if not has_groups:
        msg += "\n_No groups assigned_"

    # Button to add other groups
    keyboard.append([InlineKeyboardButton("➕ Assign to Group", callback_data=f"aa:{teacher_id}")])
    keyboard.append([InlineKeyboardButton("« Back", callback_data=f"t:{teacher_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def ask_teacher_report_days(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Ask for days for teacher report."""
    teacher = json_db.get_teacher(teacher_id)
    if not teacher:
        return await list_teachers(update, context)
        
    context.user_data["report_teacher_id"] = teacher_id
    
    await update.callback_query.message.reply_text(
        f"📊 Report for *{teacher['full_name']}*\n\n"
        "Enter number of days (1-365):",
        parse_mode='Markdown'
    )
    return TEACHER_REPORT_DAYS

async def handle_teacher_report_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate report for specific teacher."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a number:")
        return TEACHER_REPORT_DAYS
        
    try:
        days = int(update.message.text.strip())
        if not (1 <= days <= 365):
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1 and 365:")
        return TEACHER_REPORT_DAYS
    
    teacher_id = context.user_data.get("report_teacher_id")
    if not teacher_id:
        await update.message.reply_text("❌ Error: Teacher selection lost.")
        return ConversationHandler.END
        
    # Reuse mystat logic but for admin
    await generate_mystat_report(update, context, teacher_id, days)
    await update.message.reply_text("\nUse /start to return to menu.")
    return ConversationHandler.END

async def toggle_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str, chat_id_str: str):
    """Toggle teacher assignment to a group."""
    success, message = json_db.toggle_assignment(teacher_id, chat_id_str)
    
    # Check if we were in "Add Group" mode or "Show Details" mode
    # If we just added a group (message was "Include assignment"), we might want to return to detail or stay in add mode.
    # But simplifies logic is just return to detail view which now shows the new group as assigned.
    await update.callback_query.answer(message)
    return await show_teacher_detail(update, context, teacher_id)

async def show_unassigned_groups(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str):
    """Show list of groups NOT assigned to the teacher."""
    all_groups = json_db.load_groups()
    assigned_groups = json_db.get_teacher_groups(teacher_id)
    
    msg = "➕ *Assign to New Group*\n\nSelect a group to add:"
    keyboard = []
    
    # Filter only unassigned groups
    unassigned = {k: v for k, v in all_groups.items() if k not in assigned_groups}
    
    if not unassigned:
         msg = "✅ All registered groups are already assigned to this teacher."
         keyboard.append([InlineKeyboardButton("« Back", callback_data=f"t:{teacher_id}")])
    else:
        for chat_id_str, g_data in sorted(unassigned.items(), key=lambda x: x[1]['title']):
            # Callback uses same logic (toggle), so it will ADD it
            keyboard.append([InlineKeyboardButton(
                f"➕ {g_data['title'][:30]}",
                callback_data=f"a:{teacher_id}|{chat_id_str}"
            )])
        keyboard.append([InlineKeyboardButton("« Back", callback_data=f"t:{teacher_id}")])
            
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

# ============================================================================
# ADD TEACHER CONVERSATION
# ============================================================================

async def add_teacher_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Receive teacher ID."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send the teacher ID as text:")
        return ADD_T_ID
        
    teacher_id = update.message.text.strip()
    
    valid, msg = json_db.validate_teacher_id(teacher_id)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease try again:")
        return ADD_T_ID
    
    # Check if already exists
    if json_db.get_teacher(teacher_id):
        await update.message.reply_text(f"❌ Teacher ID '{teacher_id}' already exists!\n\nTry a different ID:")
        return ADD_T_ID
    
    context.user_data["new_teacher_id"] = teacher_id
    await update.message.reply_text("✅ Good!\n\n📝 Enter teacher's full name:")
    return ADD_T_NAME

async def add_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Receive teacher name."""
    if not update.message.text:
        await update.message.reply_text("❌ Please send the teacher's name as text:")
        return ADD_T_NAME
        
    full_name = update.message.text.strip()
    
    valid, msg = json_db.validate_full_name(full_name)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease try again:")
        return ADD_T_NAME
    
    context.user_data["new_teacher_name"] = full_name
    await update.message.reply_text(
        "✅ Good!\n\n"
        "📱 Now send the teacher's Telegram user ID as a number,\n"
        "*OR* forward any message from that teacher to me.\n\n"
        "I'll extract their ID automatically!",
        parse_mode='Markdown'
    )
    return ADD_T_TELEGRAM_ID

async def add_teacher_telegram_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Receive Telegram ID (text or forwarded message)."""
    telegram_user_id = None
    
    # Check if it's a forwarded message (new API uses forward_origin)
    if update.message.forward_origin:
        # Handle different forward origin types
        from telegram.constants import MessageOriginType
        
        origin = update.message.forward_origin
        if origin.type == MessageOriginType.USER:
            telegram_user_id = origin.sender_user.id
            await update.message.reply_text(f"✅ Got ID from forwarded message: `{telegram_user_id}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Cannot get user ID from this forwarded message (hidden by privacy settings).\n\n"
                "Please either:\n"
                "1. Ask the teacher to send a message directly to this bot\n"
                "2. Or send their numeric Telegram ID"
            )
            return ADD_T_TELEGRAM_ID
    else:
        # Try to parse as number
        try:
            telegram_user_id = int(update.message.text.strip())
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Send a number OR forward a message from the teacher:"
            )
            return ADD_T_TELEGRAM_ID
    
    # Validate
    valid, msg = json_db.validate_telegram_id(telegram_user_id)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease try again:")
        return ADD_T_TELEGRAM_ID
    
    # Check if already used
    existing = json_db.find_teacher_by_telegram_id(telegram_user_id)
    if existing:
        await update.message.reply_text(
            f"❌ This Telegram ID is already assigned to teacher '{existing}'!\n\n"
            "Please provide a different ID:"
        )
        return ADD_T_TELEGRAM_ID
    
    # Add teacher
    teacher_id = context.user_data["new_teacher_id"]
    full_name = context.user_data["new_teacher_name"]
    
    success, message = json_db.add_teacher(teacher_id, full_name, telegram_user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ *Teacher Added!*\n\n"
            f"ID: `{teacher_id}`\n"
            f"Name: {full_name}\n"
            f"Telegram ID: `{telegram_user_id}`\n\n"
            "Use /start to return to menu.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ Error: {message}\n\nUse /start to try again.")
    
    # Clear context
    context.user_data.clear()
    return ConversationHandler.END

# ============================================================================
# GROUPS
# ============================================================================

async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all groups."""
    groups = json_db.load_groups()
    
    if not groups:
        msg = "No groups registered yet.\n\nUse *➕ Add Group* for instructions."
        keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="m:back")]]
    else:
        msg = "🏫 Groups:\n\n"
        keyboard = []
        
        for chat_id_str, data in sorted(groups.items(), key=lambda x: x[1]['title']):
            status = "✅" if data.get("enabled", True) else "❌"
            # Removing markdown format to prevent errors with special chars in titles
            msg += f"{status} {data['title']} (ID: {chat_id_str})\n"
            keyboard.append([InlineKeyboardButton(
                f"{status} {data['title'][:30]}",
                callback_data=f"g:{chat_id_str}"
            )])
        
        keyboard.append([InlineKeyboardButton("« Back to Menu", callback_data="m:back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Removing parse_mode to be safe
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
    return MENU

async def show_group_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Show group details."""
    group = json_db.get_group(chat_id_str)
    if not group:
        await update.callback_query.answer("Group not found", show_alert=True)
        return await list_groups(update, context)
    
    status = "✅ Enabled" if group.get("enabled", True) else "❌ Disabled"
    
    msg = f"🏫 *{group['title']}*\n\n"
    msg += f"Chat ID: `{chat_id_str}`\n"
    msg += f"Status: {status}\n"
    msg += f"Created: {group.get('created_at', 'Unknown')[:10]}\n"
    
    keyboard = [
        [InlineKeyboardButton("⚙️ Guruh sozlamasi", callback_data=f"gs:{chat_id_str}")],
        [InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"ge_t:{chat_id_str}")],
        [InlineKeyboardButton("📊 Guruh bo'yicha hisobot", callback_data=f"rg:{chat_id_str}")],
        [InlineKeyboardButton("❌ Guruhni o'chirish", callback_data=f"gd:{chat_id_str}")],
        [InlineKeyboardButton("« Back", callback_data="m:groups")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def start_edit_group_title(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Ask for new group title."""
    group = json_db.get_group(chat_id_str)
    if not group:
         return await list_groups(update, context)

    context.user_data['edit_group_id'] = chat_id_str
    
    msg = (
        f"✏️ *Edit Group Title*\n\n"
        f"Current Title: `{group['title']}`\n\n"
        "Please enter the new title:"
    )
    await update.callback_query.message.reply_text(msg, parse_mode='Markdown')
    return EDIT_GROUP_TITLE

async def handle_edit_group_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save new group title."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter text:")
        return EDIT_GROUP_TITLE
        
    chat_id_str = context.user_data.get('edit_group_id')
    if not chat_id_str:
        return await start(update, context)
        
    new_title = update.message.text.strip()
    json_db.update_group_title(chat_id_str, new_title)
    
    await update.message.reply_text(f"✅ Group title updated to: **{new_title}**", parse_mode='Markdown')
    
    # Return to details (hacky way: simulate menu return or just end conv and let user navigate back)
    # Better: show menu again
    return await start(update, context)

async def confirm_delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Ask for confirmation before deleting a group."""
    group = json_db.get_group(chat_id_str)
    if not group:
        return await list_groups(update, context)
        
    msg = (
        f"⚠️ *DELETE GROUP?*\n\n"
        f"Are you sure you want to delete **{group['title']}**?\n"
        f"This will stop tracking and remove all assignments."
    )
    
    keyboard = [
        [InlineKeyboardButton("🗑️ YES, DELETE", callback_data=f"gdc:{chat_id_str}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"g:{chat_id_str}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def perform_delete_group(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Execute deletion."""
    success, msg = json_db.delete_group(chat_id_str)
    if success:
        await update.callback_query.answer(msg, show_alert=True)
        return await list_groups(update, context)
    else:
        await update.callback_query.answer(f"Error: {msg}", show_alert=True)
        return await show_group_detail(update, context, chat_id_str)

async def show_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Show group settings (enable/disable)."""
    group = json_db.get_group(chat_id_str)
    if not group:
         return await list_groups(update, context)
    
    status = "✅ Enabled" if group.get("enabled", True) else "❌ Disabled"
    msg = f"⚙️ *Settings for {group['title']}*\n\nCurrent Status: {status}\n"
    
    keyboard = [
        [InlineKeyboardButton(
            f"🔄 {'Disable' if group.get('enabled', True) else 'Enable'}",
            callback_data=f"ge:{chat_id_str}"
        )],
        [InlineKeyboardButton("« Back", callback_data=f"g:{chat_id_str}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def toggle_group_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str):
    """Toggle group enabled status."""
    success, message = json_db.toggle_group_enabled(chat_id_str)
    await update.callback_query.answer(message)
    return await show_group_detail(update, context, chat_id_str)

# ============================================================================
# CONFIRM GROUP (runs in group chat)
# ============================================================================

async def confirm_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a group (must be run inside the group)."""
    # Must be in a group
    if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ This command only works in group chats!")
        return
    
    # Sender must be admin
    if not update.effective_user or not is_admin(update.effective_user.id):
        await update.message.reply_text(f"❌ Only bot admins can register groups!\nYour ID: `{update.effective_user.id}`")
        return
    
    # Bot must be admin in the group
    try:
        bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "❌ Please promote me to admin first!\n\n"
                "I need admin rights to track messages."
            )
            return
    except Exception as e:
        logger.error(f"Error checking bot admin status: {e}")
        await update.message.reply_text("❌ Error checking permissions. Please try again.")
        return
    
    # Add group
    chat_id = update.effective_chat.id
    title = update.effective_chat.title or f"Group {chat_id}"
    
    success, message = json_db.add_group(chat_id, title)
    
    if success:
        logger.info(f"ADMIN {update.effective_user.id} registered group {chat_id} ({title})")
        await update.message.reply_text(
            f"✅ *Group Registered!*\n\n"
            f"Title: {title}\n"
            f"Chat ID: `{chat_id}`\n\n"
            "This group is now being tracked!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"ℹ️ {message}")

# ============================================================================
# REPORTS
# ============================================================================

async def handle_report_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report days input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a number:")
        return REPORT_DAYS
        
    try:
        days = int(update.message.text.strip())
        if not (1 <= days <= 365):
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1 and 365:")
        return REPORT_DAYS
    
    rtype = context.user_data.get("report_type", "t_simple")
    
    if rtype == "t_simple":
        await gen_teachers_simple(update, context, days)
    elif rtype == "t_detail":
        await gen_teachers_detail(update, context, days)
    elif rtype == "g_simple":
        await gen_groups_simple(update, context, days)
    elif rtype == "g_detail":
        await gen_groups_detail(update, context, days)
    else:
        # Default
        await gen_teachers_simple(update, context, days)
        
    await update.message.reply_text("Use /start to return to menu.")
    return ConversationHandler.END

async def gen_teachers_simple(update, context, days):
    """Teachers report: T/r | Name | XS"""
    stats = json_db.aggregate_stats(days)
    teachers = json_db.load_teachers()
    
    data_list = []
    
    for t_id, t_data in teachers.items():
        if not t_data.get('active', True): continue
        
        total = 0
        for chat_id in stats:
            if t_id in stats[chat_id]:
                total += get_overall_total(stats[chat_id][t_id])
                
        name = format_short_name(t_data['full_name'])
        data_list.append((name, total))
        
    data_list.sort(key=lambda x: x[0])
    
    msg = f"📊 <b>Teachers Report (Last {days} days)</b>\n\n"
    msg += "<pre>"
    msg += "T/r |             FISH             | XS \n"
    msg += "----+------------------------------+----\n"
    
    for i, (name, total) in enumerate(data_list, 1):
        n_pad = name[:30].ljust(28)
        msg += f"{i:<3} | {n_pad} | {total:>4}\n"
    
    msg += "</pre>"
        
    try:
        await update.message.reply_text(msg, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error sending report: {e}")
        clean_msg = msg.replace("<pre>", "").replace("</pre>", "").replace("<b>", "").replace("</b>", "")
        await update.message.reply_text(clean_msg)

async def gen_teachers_detail(update, context, days):
    """Teachers Detailed report."""
    stats = json_db.aggregate_stats(days)
    teachers = json_db.load_teachers()
    
    data_list = []
    
    for t_id, t_data in teachers.items():
        if not t_data.get('active', True): continue
        
        agg_counters = {
            "text": 0, "photo": 0, "video": 0,
            "audio": 0, "voice": 0, "document": 0
        }
        
        for chat_id in stats:
            if t_id in stats[chat_id]:
                for k, v in stats[chat_id][t_id].items():
                    agg_counters[k] += v
        
        total = get_overall_total(agg_counters)
        name = format_short_name(t_data['full_name'])
        data_list.append((name, total, agg_counters))
        
    data_list.sort(key=lambda x: x[0])
    
    msg = f"📊 <b>Teachers Detailed Report (Last {days} days)</b>\n\n"
    for i, (name, total, counters) in enumerate(data_list, 1):
        msg += f"{i}. 👨‍🏫 <b>{name}</b> — {total}\n"
        msg += f"   {format_breakdown(counters)}\n\n"
        
    try:
        await update.message.reply_text(msg, parse_mode='HTML')
    except:
        await update.message.reply_text(msg.replace('<b>','').replace('</b>',''))

async def gen_groups_simple(update, context, days):
    """Group report: T/r | GR name | XS"""
    stats = json_db.aggregate_stats(days)
    groups = json_db.load_groups()
    
    data_list = []
    
    for g_id, g_data in groups.items():
        if not g_data.get('enabled', True): continue
        
        total = 0
        if g_id in stats:
            for t_counters in stats[g_id].values():
                total += get_overall_total(t_counters)
                
        title = g_data['title']
        data_list.append((title, total))
        
    data_list.sort(key=lambda x: x[0])
    
    msg = f"📊 <b>Groups Report (Last {days} days)</b>\n\n"
    msg += "<pre>"
    msg += "T/r |           GR name              | XS \n"
    msg += "----+--------------------------------+----\n"
    
    for i, (title, total) in enumerate(data_list, 1):
        t_pad = title[:30].ljust(30)
        msg += f"{i:<3} | {t_pad} | {total:>4}\n"
    
    msg += "</pre>"
        
    try:
        await update.message.reply_text(msg, parse_mode='HTML')
    except:
        clean_msg = msg.replace("<pre>", "").replace("</pre>", "").replace("<b>", "").replace("</b>", "")
        await update.message.reply_text(clean_msg)

async def gen_groups_detail(update, context, days):
    """Groups detailed report."""
    stats = json_db.aggregate_stats(days)
    groups = json_db.load_groups()
    
    data_list = []
    
    for g_id, g_data in groups.items():
        if not g_data.get('enabled', True): continue
        
        agg_counters = {
            "text": 0, "photo": 0, "video": 0,
            "audio": 0, "voice": 0, "document": 0
        }
        
        if g_id in stats:
            for t_counters in stats[g_id].values():
                for k, v in t_counters.items():
                    agg_counters[k] += v
                    
        total = get_overall_total(agg_counters)
        title = g_data['title']
        data_list.append((title, total, agg_counters))
        
    data_list.sort(key=lambda x: x[0])
    
    msg = f"📊 <b>Groups Detailed Report (Last {days} days)</b>\n\n"
    for i, (title, total, counters) in enumerate(data_list, 1):
        msg += f"{i}. <b>{title}</b> - {total}\n"
        msg += f"   {format_breakdown(counters)}\n\n"
        
    try:
        await update.message.reply_text(msg, parse_mode='HTML')
    except:
        await update.message.reply_text(msg.replace('<b>','').replace('</b>',''))

async def handle_report_group_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle report group days input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a number:")
        return REPORT_GROUP_DAYS
        
    try:
        days = int(update.message.text.strip())
        if not (1 <= days <= 365):
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1 and 365:")
        return REPORT_GROUP_DAYS
    
    chat_id_str = context.user_data.get("report_group_id")
    if not chat_id_str:
        await update.message.reply_text("❌ Error: Group selection lost. Please start over.")
        return ConversationHandler.END
        
    await generate_group_report(update, context, chat_id_str, days)
    await update.message.reply_text("Use /start to return to menu.")
    return ConversationHandler.END

async def generate_group_report(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id_str: str, days: int):
    """Generate report for a specific group."""
    logger.info(f"ADMIN {update.effective_user.id} generated {days}-day group report for {chat_id_str}")
    
    stats = json_db.aggregate_stats(days)
    teachers = json_db.load_teachers()
    groups = json_db.load_groups()
    
    group_data = groups.get(chat_id_str)
    if not group_data:
        await update.message.reply_text("❌ Group not found.")
        return
        
    group_stats = stats.get(chat_id_str, {})
    if not group_stats:
        await update.message.reply_text(f"📊 No activity in *{group_data['title']}* for the last {days} days.", parse_mode='Markdown')
        return
    
    msg = f"📊 *Report by Group:* {group_data['title']}\n"
    msg += f"📅 *Period:* Last {days} days\n\n"
    msg += "👨‍🏫 *Teachers in this group:*\n"
    
    # Get assigned teachers for this group
    assigned_teachers = []
    for t_id in teachers:
        if json_db.is_teacher_assigned(t_id, chat_id_str):
            assigned_teachers.append(t_id)
            
    has_activity = False
    for t_id in assigned_teachers:
        if t_id not in group_stats:
            continue
            
        has_activity = True
        name = teachers[t_id]["full_name"]
        c = group_stats[t_id]
        total = get_overall_total(c)
        
        msg += f"\n{format_entity_block(f'👨‍🏫 {name} — {total}', c)}\n"
        
    if not has_activity:
        await update.message.reply_text(f"📊 No teacher activity in *{group_data['title']}* for the last {days} days.", parse_mode='Markdown')
        return
        
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============================================================================
# EXCEL EXPORT
# ============================================================================

async def handle_excel_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Excel days input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a number:")
        return EXCEL_DAYS
        
    try:
        days = int(update.message.text.strip())
        if not (1 <= days <= 365):
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1 and 365:")
        return EXCEL_DAYS
    
    await generate_excel_report(update, context, days)
    await update.message.reply_text("\nUse /start to return to menu.")
    return ConversationHandler.END

async def generate_excel_report(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    """Generate Excel report."""
    logger.info(f"ADMIN {update.effective_user.id} generated {days}-day Excel report")
    
    stats = json_db.aggregate_stats(days)
    teachers = json_db.load_teachers()
    groups = json_db.load_groups()
    
    if not stats:
        await update.message.reply_text(f"📥 No activity in the last {days} days.")
        return
    
    await update.message.reply_text("📥 Generating Excel report...")
    
    rows = []
    end_date = datetime.now(json_db.local_tz)
    from_date = (end_date - pd.Timedelta(days=days-1)).strftime("%Y-%m-%d")
    to_date = end_date.strftime("%Y-%m-%d")
    
    for chat_id, t_stats in stats.items():
        g_title = groups.get(chat_id, {}).get("title", chat_id)
        for t_id, counters in t_stats.items():
            t_name = teachers.get(t_id, {}).get("full_name", t_id)
            rows.append({
                "TeacherID": t_id,
                "FullName": t_name,
                "ChatID": chat_id,
                "GroupTitle": g_title,
                "Text": counters["text"],
                "Photo": counters["photo"],
                "Video": counters["video"],
                "Audio": counters["audio"],
                "Voice": counters["voice"],
                "Document": counters["document"],
                "Total": sum(counters.values()),
                "FromDate": from_date,
                "ToDate": to_date
            })
    
    df = pd.DataFrame(rows)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(EXPORT_DIR, filename)
    
    df.to_excel(filepath, index=False)
    
    with open(filepath, 'rb') as f:
        await update.message.reply_document(document=f, filename=filename)

# ============================================================================
# DIAGNOSTICS
# ============================================================================

async def show_diagnostics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system diagnostics."""
    diag = json_db.get_diagnostics()
    
    msg = "🔍 *System Diagnostics*\n\n"
    msg += f"👨‍🏫 Teachers: {diag['teachers_count']} ({diag['active_teachers']} active)\n"
    msg += f"🏫 Groups: {diag['groups_count']} ({diag['enabled_groups']} enabled)\n"
    msg += f"📊 Stats files: {diag['stats_files']}\n\n"
    
    if diag['teachers']:
        msg += "*Teachers:*\n"
        for t_id in diag['teachers'][:10]:
            msg += f"• `{t_id}`\n"
        if len(diag['teachers']) > 10:
            msg += f"... and {len(diag['teachers']) - 10} more\n"
    
    if diag['groups']:
        msg += "\n*Groups:*\n"
        for chat_id, title in list(diag['groups'].items())[:10]:
            msg += f"• {title} (`{chat_id}`)\n"
        if len(diag['groups']) > 10:
            msg += f"... and {len(diag['groups']) - 10} more\n"
    
    keyboard = [[InlineKeyboardButton("« Back to Menu", callback_data="m:back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def diag_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced diagnostics command for troubleshooting tracking issues."""
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    
    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    chat_id_str = str(chat.id)
    
    diag_text = "🔍 *Diagnostics*\n\n"
    diag_text += f"📍 *Chat Info:*\n"
    diag_text += f"- Type: `{chat.type}`\n"
    diag_text += f"- ID: `{chat_id_str}`\n"
    diag_text += f"- Title: `{chat.title}`\n\n"
    
    if is_group:
        group_data = json_db.get_group(chat_id_str)
        diag_text += f"🏫 *Group Status:*\n"
        diag_text += f"- Registered: `{'✅ Yes' if group_data else '❌ No'}`\n"
        if group_data:
            diag_text += f"- Enabled: `{'✅ Yes' if group_data.get('enabled', True) else '❌ No'}`\n"
        
        # Privacy warning check
        diag_text += f"\n⚠️ *Privacy Mode:* If the bot doesn't see ALL messages, use BotFather `/setprivacy` -> *Disable*.\n"
    
    diag_text += f"\n👤 *Sender Info:*\n"
    diag_text += f"- Name: {user.full_name}\n"
    diag_text += f"- ID: `{user.id}`\n"
    
    teacher_id = json_db.find_teacher_by_telegram_id(user.id)
    diag_text += f"- Recognized as teacher: `{'✅ ' + teacher_id if teacher_id else '❌ No'}`\n"
    
    if teacher_id:
        assigned = json_db.is_teacher_assigned(teacher_id, chat_id_str)
        diag_text += f"- Assigned to this group: `{'✅ Yes' if assigned else '❌ No'}`\n"
    
    # Message type detection test
    msg_type = "unknown"
    if msg.photo: msg_type = "photo"
    elif msg.video: msg_type = "video"
    elif msg.audio: msg_type = "audio"
    elif msg.voice: msg_type = "voice"
    elif msg.document: msg_type = "document"
    elif msg.text: msg_type = "text"
    
    diag_text += f"\n📝 *Last Message Type:* `{msg_type}`"
    
    await update.message.reply_text(diag_text, parse_mode='Markdown')

# ============================================================================
# CANCEL
# ============================================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation."""
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Use /start to return to menu.")
    return ConversationHandler.END

async def sync_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually sync bot membership across all registered groups."""
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text("🔄 Syncing groups... Please wait.")
    
    groups = json_db.load_groups()
    total = 0
    removed = 0
    
    for chat_id_str, data in groups.items():
        # Only check enabled groups
        if not data.get("enabled", True):
            continue
            
        total += 1
        try:
            # Attempt to get chat info - requires bot to be in the chat
            await context.bot.get_chat(int(chat_id_str))
        except Exception as e:
            # If forbidden or not found, bot was likely removed or group deleted
            removed += 1
            json_db.deactivate_group(chat_id_str)
            json_db.remove_group_from_assignments(chat_id_str)
            logger.info(f"SYNC_REMOVED_GROUP {chat_id_str} (Error: {e})")
            
    await update.message.reply_text(
        f"✅ *Sync Complete!*\n\n"
        f"📊 Active groups checked: `{total}`\n"
        f"❌ Groups removed/cleaned: `{removed}`\n"
        f"🟢 Still healthy: `{total - removed}`",
        parse_mode='Markdown'
    )

async def handle_mystat_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle MyStat days input."""
    if not update.message.text:
        await update.message.reply_text("❌ Please enter a number:")
        return MYSTAT_DAYS
        
    try:
        days = int(update.message.text.strip())
        if not (1 <= days <= 365):
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ Please enter a number between 1 and 365:")
        return MYSTAT_DAYS
    
    user_id = update.effective_user.id
    teacher_id = json_db.find_teacher_by_telegram_id(user_id)
    if not teacher_id:
        await update.message.reply_text("❌ Error: Teacher profile not found.")
        return ConversationHandler.END
        
    await generate_mystat_report(update, context, teacher_id, days)
    await update.message.reply_text("\nUse /start to return to menu.")
    return ConversationHandler.END

async def generate_mystat_report(update: Update, context: ContextTypes.DEFAULT_TYPE, teacher_id: str, days: int):
    """Generate statistic report for a specific teacher."""
    logger.info(f"TEACHER {teacher_id} generated self-stat report for {days} days")
    
    stats = json_db.aggregate_stats(days)
    groups = json_db.load_groups()
    
    msg = "📊 *My Statistics*\n"
    msg += f"📅 *Period:* Last {days} days\n\n"
    msg += "📍 *By Group:*\n\n"
    
    overall_total = 0
    has_activity = False
    
    # Filter stats for this teacher
    teacher_stats_by_group = {}
    for chat_id_str, t_stats in stats.items():
        if teacher_id in t_stats:
            teacher_stats_by_group[chat_id_str] = t_stats[teacher_id]
            
    for chat_id_str, counters in teacher_stats_by_group.items():
        group_title = groups.get(chat_id_str, {}).get("title", chat_id_str)
        total = get_overall_total(counters)
        if total == 0:
            continue
            
        has_activity = True
        overall_total += total
        
        msg += f"\n{format_entity_block(f'📍 {group_title} {total}', counters)}\n"
        
    if not has_activity:
        await update.message.reply_text(f"📊 No activity found for the last {days} days.")
        return
        
    msg += f"\n🏆 *{overall_total}*"
    await update.message.reply_text(msg, parse_mode='Markdown')
