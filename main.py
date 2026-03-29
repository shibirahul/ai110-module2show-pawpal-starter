"""
PawPal+ – CLI demo / testing ground
Run with:  python main.py
"""

from datetime import date
from tabulate import tabulate
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT

DATA_FILE = "data.json"

# ── setup ─────────────────────────────────────────────────────────────────────

owner = Owner("Jordan", available_minutes=90)

mochi = Pet("Mochi", "dog", "Shiba Inu", 3)
luna = Pet("Luna", "cat", "Domestic Shorthair", 5)

owner.add_pet(mochi)
owner.add_pet(luna)

# Mochi's tasks
mochi.add_task(Task("Morning walk",     "walk",       30, PRIORITY_INT["high"],   time_of_day="07:00", frequency="daily"))
mochi.add_task(Task("Breakfast",        "feeding",    10, PRIORITY_INT["high"],   time_of_day="07:00", frequency="daily"))  # exact-time conflict
mochi.add_task(Task("Grooming session", "grooming",   45, PRIORITY_INT["low"],    time_of_day="10:00"))

# Luna's tasks — 07:20 overlaps the 07:00 walk (which ends at 07:30)
luna.add_task(Task("Breakfast",         "feeding",     5, PRIORITY_INT["high"],   time_of_day="07:30", frequency="daily"))
luna.add_task(Task("Medication",        "meds",        5, PRIORITY_INT["medium"], time_of_day="08:00", frequency="daily"))
luna.add_task(Task("Enrichment play",   "enrichment", 20, PRIORITY_INT["medium"], time_of_day="18:00"))

scheduler = Scheduler(owner)

# ── exact-time conflict check ─────────────────────────────────────────────────

exact_conflicts = scheduler.detect_conflicts()
if exact_conflicts:
    print("⚠️  Exact-time conflicts detected:")
    for w in exact_conflicts:
        print(f"   {w}")
    print()

# ── overlapping-duration conflict check ──────────────────────────────────────

overlap_conflicts = scheduler.detect_overlapping_conflicts()
if overlap_conflicts:
    print("⚠️  Duration-overlap conflicts detected:")
    for w in overlap_conflicts:
        print(f"   {w}")
    print()

# ── generate & display schedule ───────────────────────────────────────────────

schedule = scheduler.generate_schedule()
print(scheduler.explain_plan(schedule))

# ── tabulate: full task list sorted by time ───────────────────────────────────

print("\n─── All tasks (sorted by time) ─────────────────────────────────")
rows = []
for t in scheduler.sort_by_time():
    pet_name = next(
        (p.name for p in owner.get_pets() if t in p.get_tasks()), "?"
    )
    rows.append([
        t.emoji,
        t.name,
        pet_name,
        t.time_of_day,
        f"{t.duration_minutes} min",
        t.priority_label,
        t.frequency,
        "✓" if t.completed else "○",
    ])
print(tabulate(
    rows,
    headers=["", "Task", "Pet", "Time", "Duration", "Priority", "Freq", "Done"],
    tablefmt="rounded_outline",
))

# ── filtering demo ────────────────────────────────────────────────────────────

print("\n─── Luna's tasks only ──────────────────────────────────────────")
luna_rows = [[t.emoji, t.name, t.time_of_day, f"{t.duration_minutes} min", t.priority_label]
             for t in scheduler.filter_by_pet("Luna")]
print(tabulate(luna_rows, headers=["", "Task", "Time", "Duration", "Priority"], tablefmt="rounded_outline"))

# ── find next available slot (advanced algorithm) ─────────────────────────────

print("\n─── Find next available slot ────────────────────────────────────")
test_task = Task("Vet checkup", "other", 40, PRIORITY_INT["high"])
slot = scheduler.find_next_available_slot(test_task, schedule)
print(f"   Earliest free 40-min slot for '{test_task.name}': {slot}")

# ── recurring task demo ───────────────────────────────────────────────────────

print("\n─── Recurring task: mark Mochi's Morning walk complete ──────────")
walk = mochi.get_tasks()[0]
print(f"  Before: {walk}")
next_task = scheduler.complete_task_and_reschedule(mochi, walk)
print(f"  After:  {walk}")
if next_task:
    print(f"  Next:   {next_task}")

# ── data persistence ──────────────────────────────────────────────────────────

print(f"\n─── Saving to {DATA_FILE} ──────────────────────────────────────")
owner.save_to_json(DATA_FILE)
print(f"  Saved.")

restored = Owner.load_from_json(DATA_FILE)
total_tasks = sum(len(p.get_tasks()) for p in restored.get_pets())
print(f"  Loaded back: owner='{restored.name}', pets={len(restored.get_pets())}, tasks={total_tasks}")
