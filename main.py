"""
PawPal+ – CLI demo / testing ground
Run with:  python main.py
"""

from datetime import date
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT

# ── setup ─────────────────────────────────────────────────────────────────────

owner = Owner("Jordan", available_minutes=90)

mochi = Pet("Mochi", "dog", "Shiba Inu", 3)
luna = Pet("Luna", "cat", "Domestic Shorthair", 5)

owner.add_pet(mochi)
owner.add_pet(luna)

# Mochi's tasks
mochi.add_task(Task("Morning walk",     "walk",       30, PRIORITY_INT["high"],   time_of_day="07:00", frequency="daily"))
mochi.add_task(Task("Breakfast",        "feeding",    10, PRIORITY_INT["high"],   time_of_day="07:00", frequency="daily"))  # same slot → conflict
mochi.add_task(Task("Grooming session", "grooming",   45, PRIORITY_INT["low"],    time_of_day="10:00"))

# Luna's tasks
luna.add_task(Task("Breakfast",         "feeding",     5, PRIORITY_INT["high"],   time_of_day="07:30", frequency="daily"))
luna.add_task(Task("Medication",        "meds",        5, PRIORITY_INT["medium"], time_of_day="08:00", frequency="daily"))
luna.add_task(Task("Enrichment play",   "enrichment", 20, PRIORITY_INT["medium"], time_of_day="18:00"))

scheduler = Scheduler(owner)

# ── conflict check ────────────────────────────────────────────────────────────

conflicts = scheduler.detect_conflicts()
if conflicts:
    print("⚠️  Scheduling conflicts detected:")
    for w in conflicts:
        print(f"   {w}")
    print()

# ── generate & display schedule ───────────────────────────────────────────────

schedule = scheduler.generate_schedule()
print(scheduler.explain_plan(schedule))

# ── filtering demo ────────────────────────────────────────────────────────────

print("\n--- Luna's tasks only ---")
for t in scheduler.filter_by_pet("Luna"):
    print(f"  {t}")

print("\n--- All tasks sorted by time ---")
for t in scheduler.sort_by_time():
    print(f"  {t}")

# ── recurring task demo ───────────────────────────────────────────────────────

print("\n--- Recurring task: mark Mochi's Morning walk complete ---")
walk = mochi.get_tasks()[0]
print(f"  Before: {walk}")
next_task = scheduler.complete_task_and_reschedule(mochi, walk)
print(f"  After:  {walk}")
if next_task:
    print(f"  Next:   {next_task}")
