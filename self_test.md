# 🧪 Bot Self-Test Checklist

Follow these steps to confirm your bot is fully functional.

## 1. Connection & Setup
- [ ] Run `python test_connection.py`. Does it show **✅ SUCCESS**?
- [ ] Run `python bot.py`. Does it say **Bot started successfully**?

## 2. Admin Authentication
- [ ] Open a private chat with the bot.
- [ ] Send `/start`. Do you see the rich menu with buttons?
- [ ] Send `/start` from an account NOT in `ADMIN_IDS`. Does the bot ignore you? (It should).

## 3. Teacher Management
- [ ] Click **➕ Add Teacher**.
- [ ] Enter a unique ID (e.g., `TEST1`).
- [ ] Enter a name (e.g., `Local Tester`).
- [ ] **Forward a message** from your own account to the bot.
- [ ] Verify the bot says: `✅ Got ID from forwarded message`.
- [ ] Go to **👨‍🏫 Teachers** -> **Local Tester**. Are the details correct?

## 4. Group Registration
- [ ] Add the bot to a new Telegram group.
- [ ] **Promote the bot to Administrator**.
- [ ] Send `/confirm_group` in that group.
- [ ] Verify the bot says: `✅ Group Registered!`.
- [ ] Go back to private chat -> **🏫 Groups**. Is the new group listed?

## 5. Activity Tracking (THE CORE)
- [ ] Go to **👨‍🏫 Teachers** -> **Local Tester**.
- [ ] Click the group name to toggle it to **✅**.
- [ ] **In the group**, send:
    - [ ] A text message.
    - [ ] A photo (with or without caption).
    - [ ] A voice message.
- [ ] Go back to private chat -> **👨‍🏫 Teachers** -> **Local Tester**.
- [ ] Check the **📊 Last 7 days** section. Do the numbers increment? (May take a few seconds).

## 6. Diagnostics
- [ ] In the group chat, send `/diag`.
- [ ] Does it show your correct ID and "Assigned: ✅ Yes"?
- [ ] Does it correctly detect the "Last Message Type"?

## 7. Reporting & Excel
- [ ] Click **📊 Reports** -> Enter `1`. Does it show the top teacher list?
- [ ] Click **📥 Excel** -> Enter `1`. Does the bot send you a `.xlsx` file?
- [ ] Open the Excel file. Are the counts accurate?

---
### 💡 Troubleshooting Tip
If activity stays at 0, remember to **Disable Privacy Mode** in @BotFather and **re-add** the bot to the group!
