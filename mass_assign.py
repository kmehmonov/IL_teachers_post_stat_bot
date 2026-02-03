from storage import json_db
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_all_assignments():
    """Assign ALL teachers to ALL enabled groups."""
    print("🔄 Starting mass assignment...")
    
    teachers = json_db.load_teachers()
    groups = json_db.load_groups()
    tg = json_db.load_teacher_groups()
    
    updates_count = 0
    
    # Filter enabled groups
    enabled_groups = [gid for gid, g in groups.items() if g.get("enabled", True)]
    
    if not teachers:
        print("❌ No teachers found.")
        return

    if not enabled_groups:
        print("❌ No enabled groups found.")
        return
        
    for t_id in teachers:
        if t_id not in tg:
            tg[t_id] = []
            
        current_assignments = set(tg[t_id])
        assigned_for_this = 0
        
        for g_id in enabled_groups:
            if g_id not in current_assignments:
                tg[t_id].append(g_id)
                assigned_for_this += 1
                updates_count += 1
        
        if assigned_for_this > 0:
            print(f"✅ Assigned {teachers[t_id]['full_name']} to {assigned_for_this} new groups.")
            
    if updates_count > 0:
        json_db._write_json(json_db.TEACHER_GROUPS_FILE, tg)
        print(f"\n🎉 DONE! Total new assignments created: {updates_count}")
    else:
        print("\n✅ All teachers are already assigned to all enabled groups.")

if __name__ == "__main__":
    sync_all_assignments()
