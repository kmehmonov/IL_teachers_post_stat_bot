# Telegram Teacher Activity Tracker

A production-ready Telegram bot that tracks teacher activity across multiple groups and generates comprehensive reports. Built with python-telegram-bot v20+ (async).

## Features

✅ **Privacy-First**: Stores ONLY message counters, never content or media  
✅ **Multi-Group Tracking**: Monitor activity across unlimited groups  
✅ **Teacher Management**: Add teachers via forwarded messages or Telegram ID  
✅ **Group Management**: Register groups with `/confirm_group` command  
✅ **Assignment Control**: Toggle teacher-group assignments with one click  
✅ **Rich Reports**: Text summaries and Excel exports for any time period  
✅ **Diagnostics**: Built-in `/diag` command for troubleshooting  
✅ **Atomic Operations**: File locking ensures data integrity  

## Installation

### 1. Clone and Setup

```bash
cd d:/tStat
pip install -r requirements.txt
```

### 2. Configure Environment

Create/edit `.env` file:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=123456789,987654321
DATA_DIR=./data
EXPORT_DIR=./exports
TZ=Asia/Tashkent
# PROXY_URL=http://127.0.0.1:1080  # Optional if Telegram is blocked
```

**How to get your Telegram ID:**
- Message [@userinfobot](https://t.me/userinfobot) on Telegram
- It will reply with your user ID

### 3. Initialize Data

```bash
python init_demo_data.py
```

This creates the initial JSON structure. You can delete the demo data after testing.

### 4. Run the Bot

```bash
python bot.py
```

## Quick Start Guide

### Step 1: Add a Teacher

1. Start a private chat with your bot
2. Send `/start`
3. Click **➕ Add Teacher**
4. Enter teacher ID (e.g., `T001` or `DB8F99C3`)
5. Enter full name (e.g., `John Smith`)
6. **Either:**
   - Send their Telegram user ID as a number, **OR**
   - Forward any message from that teacher to the bot (recommended!)

The bot will extract the ID automatically from forwarded messages.

### Step 2: Add a Group

1. Add your bot to the target Telegram group
2. Promote the bot to **Administrator** (required for reading messages)
3. **In that group**, send: `/confirm_group`
4. The bot will register the group automatically

### Step 3: Assign Teacher to Group

1. In private chat with bot, send `/start`
2. Click **👨‍🏫 Teachers**
3. Click on a teacher
4. You'll see a list of all groups with ✅/❌ toggles
5. Click to toggle assignments

### Step 4: Start Tracking

Once a teacher is:
- ✅ Active
- ✅ Assigned to a group
- ✅ The group is enabled

Their messages will be tracked automatically! The bot counts:
- 📝 Text messages
- 📸 Photos
- 🎥 Videos
- 🎵 Audio files
- 🎤 Voice messages
- 📎 Documents

## Admin Commands

### Private Chat Commands

- `/start` - Open admin menu
- `/diag` - Show system diagnostics
- `/cancel` - Cancel current operation

### Group Chat Commands

- `/confirm_group` - Register the group (must be run inside the group)
- `/diag` - Show quick diagnostics

## Admin Menu

```
🤖 Teacher Activity Tracker

👨‍🏫 Teachers        ➕ Add Teacher
🏫 Groups           ➕ Add Group
📊 Reports          📥 Excel
🔍 Diagnostics
```

### Teachers Section
- View all registered teachers
- Click a teacher to see:
  - Last 7 days activity breakdown
  - Per-group statistics
  - Assignment toggles

### Groups Section
- View all registered groups
- Toggle groups enabled/disabled
- See group details

### Reports
- Enter number of days (1-365)
- Get text summary with:
  - Top 10 most active teachers
  - Activity by group
  - Total message counts

### Excel Export
- Enter number of days (1-365)
- Receive `.xlsx` file with detailed breakdown
- Columns: TeacherID, FullName, ChatID, GroupTitle, Text, Photo, Video, Audio, Voice, Document, Total, FromDate, ToDate

### Diagnostics
- Teachers count (active/total)
- Groups count (enabled/total)
- Stats files count
- Quick health check

## Data Storage

All data is stored in JSON files with atomic file locking:

```
data/
  teachers.json          # Teacher registry
  groups.json            # Group registry
  teacher_groups.json    # Teacher-group assignments
  stats/
    2026-01-29.json      # Daily activity counters
    2026-01-30.json
    ...
exports/
  report_20260129_143022.xlsx
```

### JSON Schemas

**teachers.json:**
```json
{
  "T001": {
    "teacher_id": "T001",
    "full_name": "John Smith",
    "telegram_user_id": 123456789,
    "active": true,
    "created_at": "2026-01-29T14:30:00+05:00"
  }
}
```

**groups.json:**
```json
{
  "-1001234567890": {
    "chat_id": -1001234567890,
    "title": "Grade 2 Class",
    "enabled": true,
    "created_at": "2026-01-29T14:30:00+05:00"
  }
}
```

**teacher_groups.json:**
```json
{
  "T001": ["-1001234567890", "-1009876543210"],
  "T002": ["-1001234567890"]
}
```

**stats/2026-01-29.json:**
```json
{
  "-1001234567890": {
    "T001": {
      "text": 45,
      "photo": 3,
      "video": 2,
      "audio": 0,
      "voice": 1,
      "document": 5
    }
  }
}
```

## Troubleshooting

### Bot doesn't respond to /start
- Check that your Telegram ID is in `ADMIN_IDS` in `.env`
- Restart the bot after changing `.env`

### Group not tracking messages
1. Run `/diag` to check if group is registered
2. Verify bot is admin in the group
3. Check if group is enabled (Groups → click group → toggle if needed)
4. Verify teacher is assigned to the group

#### ⚠️ If activity is still 0 (Privacy Mode):
By default, Telegram bots cannot see all messages in groups. You MUST disable Privacy Mode:
1. Message [@BotFather](https://t.me/botfather)
2. Send `/setprivacy`
3. Select your bot
4. Choose **Disable**
5. **CRITICAL:** After changing this, you must **remove and re-add** the bot to your groups for the change to take effect.
6. Also, ensure the bot is an **Administrator** in the group.

### "Timed out" errors
- If Telegram is blocked in your region, set `PROXY_URL` in `.env`
- Example: `PROXY_URL=socks5://127.0.0.1:1080`

### Teacher ID already exists
- Each teacher ID must be unique
- Use a different ID or check existing teachers with `/start` → Teachers

### Telegram ID already assigned
- Each Telegram user can only be one teacher
- Check which teacher has that ID: `/start` → Teachers

## Group Tracking Logic

Telegram does not provide a way for bots to "list all groups" they are in. This bot uses a dual approach to keep the group registry accurate:

1.  **Real-time Detection**: The bot listens for `my_chat_member` updates. If it is removed (kicked or leaves) or added to a group, it immediately updates `data/groups.json` and cleans up teacher assignments.
2.  **Manual Sync**: Admins can run `/sync_groups` in a private chat. The bot will attempt to contact every registered group. If it's no longer a member, it will clean up the storage.

> [!NOTE]
> For automatic tracking to work reliably, ensure the bot has permission to see membership changes (usually granted as Administrator).

## Testing Checklist

- [ ] Add yourself as a teacher using forwarded message
- [ ] Create a test group and add the bot as admin
- [ ] Run `/confirm_group` in the test group
- [ ] Assign yourself to the test group
- [ ] Send a few messages in the group
- [ ] Check stats: `/start` → Teachers → click your teacher
- [ ] Generate a report: `/start` → Reports → enter `1`
- [ ] Export Excel: `/start` → Excel → enter `1`
- [ ] Run `/diag` to verify everything is working

## Architecture

```
bot.py                    # Main application, handler registration
config.py                 # Environment configuration
storage/
  json_db.py             # Atomic JSON operations with file locking
handlers/
  admin.py               # Admin UI and conversation flows
  tracking.py            # Message tracking logic
data/                    # JSON database
exports/                 # Generated Excel reports
```

## Security Notes

- ✅ Only admins (defined in `ADMIN_IDS`) can use admin commands
- ✅ Only admins can register groups with `/confirm_group`
- ✅ Bot must be admin in groups to track messages
- ✅ No message content is ever stored
- ✅ File locking prevents data corruption
- ⚠️ Keep your `.env` file secure (contains bot token)
- ⚠️ Backup `data/` directory regularly

## Advanced Configuration

### Custom Timezone
Edit `TZ` in `.env`:
```env
TZ=America/New_York
TZ=Europe/London
TZ=Asia/Tokyo
```

### Proxy Configuration
If Telegram is blocked:
```env
PROXY_URL=http://127.0.0.1:8080
PROXY_URL=socks5://127.0.0.1:1080
```

### Data Directory
Change storage location:
```env
DATA_DIR=/path/to/data
EXPORT_DIR=/path/to/exports
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run `/diag` to check system status
3. Check `bot.log` for error messages
4. Verify all requirements are installed: `pip install -r requirements.txt`

## License

This project is provided as-is for educational and internal use.
