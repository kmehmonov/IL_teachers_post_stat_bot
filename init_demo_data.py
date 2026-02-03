import json
import os
from datetime import datetime
import pytz

# Mock data initialization script
DATA_DIR = "./data"
os.makedirs(os.path.join(DATA_DIR, "stats"), exist_ok=True)

teachers = {
    "T001": {
        "teacher_id": "T001",
        "full_name": "Aliyev Akmal",
        "telegram_user_id": 111111111, # Update with real ID
        "active": True,
        "created_at": datetime.now().isoformat()
    },
    "T002": {
        "teacher_id": "T002",
        "full_name": "Karimova Mohira",
        "telegram_user_id": 222222222, # Update with real ID
        "active": True,
        "created_at": datetime.now().isoformat()
    }
}

groups = {
    "-1001234567890": {
        "chat_id": -1001234567890, # Update with real ID
        "title": "Test Group 1",
        "enabled": True,
        "created_at": datetime.now().isoformat()
    }
}

teacher_groups = {
    "T001": ["-1001234567890"],
    "T002": ["-1001234567890"]
}

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Created {path}")

if __name__ == "__main__":
    save_json("teachers.json", teachers)
    save_json("groups.json", groups)
    save_json("teacher_groups.json", teacher_groups)
    print("\nInitialization complete. IMPORTANT: Update telegram_user_id and chat_id in JSON files with real values!")
