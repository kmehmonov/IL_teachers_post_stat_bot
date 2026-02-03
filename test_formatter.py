
import sys
import os

# Add current directory to path so we can import handlers
sys.path.append(os.getcwd())

from handlers.admin import format_breakdown, get_overall_total, format_entity_block

test_counters = {
    "text": 10,
    "photo": 5,
    "video": 2,
    "audio": 1,
    "voice": 3,
    "document": 4
}

print("Testing get_overall_total:")
total = get_overall_total(test_counters)
print(f"Total: {total} (Expected: 25)")

print("\nTesting format_breakdown:")
breakdown = format_breakdown(test_counters)
print(f"Breakdown:\n{breakdown}")

print("\nTesting format_entity_block:")
block = format_entity_block("📍 Group Title 25", test_counters)
print(f"Block:\n{block}")

test_partial = {"text": 5}
print("\nTesting with partial counters:")
print(f"Total: {get_overall_total(test_partial)}")
print(f"Breakdown:\n{format_breakdown(test_partial)}")
