"""
Automated tests for PawPal+ core logic.
Run with:  python -m pytest
"""

import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT


# ── helpers ───────────────────────────────────────────────────────────────────

def make_owner(minutes: int = 120) -> Owner:
    return Owner("Test Owner", available_minutes=minutes)


def make_pet(name: str = "Rex") -> Pet:
    return Pet(name, "dog", "Lab", 2)


def make_task(
    name: str = "Walk",
    duration: int = 20,
    priority: int = 2,
    time: str = "08:00",
    freq: str = "once",
) -> Task:
    return Task(name, "walk", duration, priority, time_of_day=time, frequency=freq)


# ── Phase 2: basic class behaviour ────────────────────────────────────────────

def test_mark_complete():
    """Calling mark_complete() should flip completed to True."""
    task = make_task()
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_mark_incomplete():
    """Calling mark_incomplete() after completion should reset the flag."""
    task = make_task()
    task.mark_complete()
    task.mark_incomplete()
    assert task.completed is False


def test_add_task_increases_count():
    """Adding tasks to a Pet should grow its task list."""
    pet = make_pet()
    assert len(pet.get_tasks()) == 0
    pet.add_task(make_task("Task A"))
    assert len(pet.get_tasks()) == 1
    pet.add_task(make_task("Task B"))
    assert len(pet.get_tasks()) == 2


def test_owner_add_and_get_pets():
    """Owner.add_pet / get_pets should manage the pet list correctly."""
    owner = make_owner()
    assert owner.get_pets() == []
    p1 = make_pet("Mochi")
    p2 = make_pet("Luna")
    owner.add_pet(p1)
    owner.add_pet(p2)
    assert len(owner.get_pets()) == 2


def test_get_pet_by_name_case_insensitive():
    """get_pet_by_name should match regardless of case."""
    owner = make_owner()
    owner.add_pet(make_pet("Mochi"))
    assert owner.get_pet_by_name("mochi") is not None
    assert owner.get_pet_by_name("MOCHI") is not None
    assert owner.get_pet_by_name("Buddy") is None


# ── Phase 4: sorting ──────────────────────────────────────────────────────────

def test_sort_by_time_chronological():
    """sort_by_time should return tasks in ascending HH:MM order."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("C", time="10:00"))
    pet.add_task(make_task("A", time="07:00"))
    pet.add_task(make_task("B", time="08:30"))
    scheduler = Scheduler(owner)
    times = [t.time_of_day for t in scheduler.sort_by_time()]
    assert times == sorted(times)


def test_sort_by_priority_descending():
    """sort_by_priority should return highest-priority tasks first."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Low",  priority=1))
    pet.add_task(make_task("High", priority=3))
    pet.add_task(make_task("Med",  priority=2))
    scheduler = Scheduler(owner)
    priorities = [t.priority for t in scheduler.sort_by_priority()]
    assert priorities == [3, 2, 1]


# ── Phase 4: filtering ────────────────────────────────────────────────────────

def test_filter_by_status_separates_done_and_pending():
    """filter_by_status should correctly split completed vs pending tasks."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    done = make_task("Done")
    pending = make_task("Pending")
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(pending)
    scheduler = Scheduler(owner)
    all_tasks = pet.get_tasks()
    assert len(scheduler.filter_by_status(completed=True,  tasks=all_tasks)) == 1
    assert len(scheduler.filter_by_status(completed=False, tasks=all_tasks)) == 1


def test_filter_by_pet_returns_only_that_pets_tasks():
    """filter_by_pet should return tasks from the named pet only."""
    owner = make_owner()
    mochi = make_pet("Mochi")
    luna = make_pet("Luna")
    owner.add_pet(mochi)
    owner.add_pet(luna)
    mochi.add_task(make_task("Walk"))
    luna.add_task(make_task("Feed"))
    luna.add_task(make_task("Play"))
    scheduler = Scheduler(owner)
    assert len(scheduler.filter_by_pet("Mochi")) == 1
    assert len(scheduler.filter_by_pet("Luna")) == 2
    assert scheduler.filter_by_pet("Unknown") == []


# ── Phase 4: schedule generation ─────────────────────────────────────────────

def test_generate_schedule_respects_time_limit():
    """generate_schedule must not exceed available_minutes."""
    owner = make_owner(minutes=30)
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Long",  duration=25, priority=3))
    pet.add_task(make_task("Short", duration=10, priority=2))
    schedule = Scheduler(owner).generate_schedule()
    assert sum(t.duration_minutes for t in schedule) <= 30


def test_generate_schedule_prefers_high_priority():
    """When only one task fits, it should be the highest-priority one."""
    owner = make_owner(minutes=25)
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Low priority",  duration=20, priority=1))
    pet.add_task(make_task("High priority", duration=20, priority=3))
    schedule = Scheduler(owner).generate_schedule()
    assert len(schedule) == 1
    assert schedule[0].name == "High priority"


def test_generate_schedule_empty_when_no_time():
    """With zero available minutes, the schedule should be empty."""
    owner = make_owner(minutes=0)
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task())
    assert Scheduler(owner).generate_schedule() == []


def test_generate_schedule_sorted_by_time():
    """Returned schedule should be sorted chronologically, not by priority."""
    owner = make_owner(minutes=120)
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Evening", duration=10, priority=3, time="20:00"))
    pet.add_task(make_task("Morning", duration=10, priority=1, time="07:00"))
    schedule = Scheduler(owner).generate_schedule()
    assert schedule[0].time_of_day == "07:00"


# ── Phase 4: recurring tasks ──────────────────────────────────────────────────

def test_recurring_daily_creates_next_day():
    """Completing a daily task should add a new task due tomorrow."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    today = date.today()
    task = Task("Daily walk", "walk", 20, 3,
                time_of_day="07:00", frequency="daily", due_date=today)
    pet.add_task(task)
    next_task = Scheduler(owner).complete_task_and_reschedule(pet, task)
    assert task.completed is True
    assert next_task is not None
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.completed is False
    assert len(pet.get_tasks()) == 2


def test_recurring_weekly_creates_next_week():
    """Completing a weekly task should add a new task due in 7 days."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    today = date.today()
    task = Task("Weekly groom", "grooming", 45, 2,
                time_of_day="10:00", frequency="weekly", due_date=today)
    pet.add_task(task)
    next_task = Scheduler(owner).complete_task_and_reschedule(pet, task)
    assert next_task is not None
    assert next_task.due_date == today + timedelta(weeks=1)


def test_once_task_produces_no_next_occurrence():
    """Completing a one-off task should not add a follow-up task."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    task = make_task(freq="once")
    pet.add_task(task)
    next_task = Scheduler(owner).complete_task_and_reschedule(pet, task)
    assert next_task is None
    assert len(pet.get_tasks()) == 1


# ── Phase 4: conflict detection ───────────────────────────────────────────────

def test_conflict_detected_for_same_time():
    """Two tasks at the same time_of_day should trigger one conflict warning."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Walk", time="07:00"))
    pet.add_task(make_task("Feed", time="07:00"))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 1
    assert "07:00" in warnings[0]


def test_no_conflict_for_different_times():
    """Tasks at different times should produce no conflict warnings."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("Walk", time="07:00"))
    pet.add_task(make_task("Feed", time="08:00"))
    assert Scheduler(owner).detect_conflicts() == []


def test_multiple_conflicts_reported():
    """Two separate conflicting time slots should each produce a warning."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(make_task("A", time="07:00"))
    pet.add_task(make_task("B", time="07:00"))
    pet.add_task(make_task("C", time="09:00"))
    pet.add_task(make_task("D", time="09:00"))
    warnings = Scheduler(owner).detect_conflicts()
    assert len(warnings) == 2


# ── Bonus: overlapping duration detection ─────────────────────────────────────

def test_overlap_detected_when_durations_cross():
    """A 30-min task at 07:00 and a task at 07:15 should be flagged as overlapping."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(Task("Long walk", "walk", 30, 3, time_of_day="07:00"))
    pet.add_task(Task("Feed",      "feeding", 10, 3, time_of_day="07:15"))
    warnings = Scheduler(owner).detect_overlapping_conflicts()
    assert len(warnings) == 1
    assert "Long walk" in warnings[0]


def test_no_overlap_when_tasks_are_sequential():
    """A task ending at 07:30 and one starting at 07:30 should NOT overlap."""
    owner = make_owner()
    pet = make_pet()
    owner.add_pet(pet)
    pet.add_task(Task("Walk", "walk", 30, 3, time_of_day="07:00"))   # ends 07:30
    pet.add_task(Task("Feed", "feeding", 10, 3, time_of_day="07:30"))  # starts 07:30
    warnings = Scheduler(owner).detect_overlapping_conflicts()
    assert warnings == []


# ── Bonus: find next available slot ──────────────────────────────────────────

def test_find_next_available_slot_skips_occupied_times():
    """find_next_available_slot should return a slot not occupied by existing tasks."""
    owner = make_owner(minutes=120)
    pet = make_pet()
    owner.add_pet(pet)
    # Fill 06:00–08:00 with back-to-back tasks
    pet.add_task(Task("A", "walk",    60, 3, time_of_day="06:00"))
    pet.add_task(Task("B", "feeding", 60, 3, time_of_day="07:00"))
    scheduler = Scheduler(owner)
    schedule = scheduler.generate_schedule()
    probe = Task("Vet", "other", 30, 2)
    slot = scheduler.find_next_available_slot(probe, schedule)
    # Slot should be at or after 08:00
    assert slot >= "08:00"


def test_find_next_available_slot_returns_early_slot_when_free():
    """With an empty schedule, the slot should be the day start (06:00)."""
    owner = make_owner(minutes=0)
    pet = make_pet()
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    probe = Task("Quick task", "other", 10, 1)
    slot = scheduler.find_next_available_slot(probe, schedule=[])
    assert slot == "06:00"


# ── Bonus: data persistence ───────────────────────────────────────────────────

def test_save_and_load_json(tmp_path):
    """Saving and loading an Owner should preserve all pets and tasks."""
    owner = make_owner()
    pet = make_pet("Mochi")
    task = Task("Walk", "walk", 30, 3, time_of_day="07:00", frequency="daily",
                due_date=date.today())
    pet.add_task(task)
    owner.add_pet(pet)

    filepath = str(tmp_path / "test_data.json")
    owner.save_to_json(filepath)

    restored = Owner.load_from_json(filepath)
    assert restored.name == owner.name
    assert restored.available_minutes == owner.available_minutes
    assert len(restored.get_pets()) == 1
    assert restored.get_pets()[0].name == "Mochi"
    tasks = restored.get_pets()[0].get_tasks()
    assert len(tasks) == 1
    assert tasks[0].name == "Walk"
    assert tasks[0].due_date == date.today()
    assert tasks[0].frequency == "daily"


def test_load_preserves_completion_status(tmp_path):
    """A completed task should still be marked completed after a save/load cycle."""
    owner = make_owner()
    pet = make_pet()
    task = make_task("Done task")
    task.mark_complete()
    pet.add_task(task)
    owner.add_pet(pet)

    filepath = str(tmp_path / "test_done.json")
    owner.save_to_json(filepath)

    restored = Owner.load_from_json(filepath)
    assert restored.get_pets()[0].get_tasks()[0].completed is True


# ── Bug fixes: identity-based checks ─────────────────────────────────────────

def test_generate_schedule_excludes_completed_tasks():
    """Completed tasks must not appear in the generated schedule."""
    owner = make_owner(minutes=100)
    pet = make_pet()
    owner.add_pet(pet)
    done = make_task("Done", duration=20)
    pending = make_task("Pending", duration=20)
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(pending)
    schedule = Scheduler(owner).generate_schedule()
    assert len(schedule) == 1
    assert schedule[0].name == "Pending"


def test_explain_plan_skipped_uses_identity_not_equality():
    """
    explain_plan must not wrongly list a scheduled task as skipped
    when another task with identical fields also exists.
    """
    owner = make_owner(minutes=20)
    pet = make_pet()
    owner.add_pet(pet)
    # Two tasks with identical fields — only one will fit
    t1 = make_task("Walk", duration=20, priority=2)
    t2 = make_task("Walk", duration=20, priority=2)   # same name/fields, different object
    pet.add_task(t1)
    pet.add_task(t2)
    scheduler = Scheduler(owner)
    schedule = scheduler.generate_schedule()
    explanation = scheduler.explain_plan(schedule)
    # Exactly one task should be scheduled and one skipped
    assert len(schedule) == 1
    assert "Skipped" in explanation


def test_pet_remove_task_uses_identity():
    """remove_task should remove only the exact task object, not a twin with same fields."""
    pet = make_pet()
    t1 = make_task("Walk")
    t2 = make_task("Walk")   # same fields, different object
    pet.add_task(t1)
    pet.add_task(t2)
    removed = pet.remove_task(t1)
    assert removed is True
    assert len(pet.get_tasks()) == 1
    assert pet.get_tasks()[0] is t2


# ── Shared pet feature ────────────────────────────────────────────────────────

def test_shared_pet_visible_to_co_owner():
    """A pet shared with another owner should appear in that owner's scheduler."""
    owner_a = Owner("Alice", 60)
    owner_b = Owner("Bob", 60)
    pet = Pet("Buddy", "dog", "Lab", 3, shared_with=["Bob"])
    pet.add_task(make_task("Morning walk", duration=30))
    owner_a.add_pet(pet)

    # Bob gets access via extra_pets
    scheduler = Scheduler(owner_b, extra_pets=[pet])
    tasks = scheduler.get_todays_tasks()
    assert len(tasks) == 1
    assert tasks[0].name == "Morning walk"


def test_shared_pet_tasks_included_in_schedule():
    """Tasks from a shared pet count toward the schedule for the co-owner."""
    owner_a = Owner("Alice", 60)
    owner_b = Owner("Bob", 60)
    shared_pet = Pet("Buddy", "dog", "Lab", 3, shared_with=["Bob"])
    shared_pet.add_task(make_task("Walk", duration=30, priority=3))
    owner_a.add_pet(shared_pet)

    scheduler = Scheduler(owner_b, extra_pets=[shared_pet])
    schedule = scheduler.generate_schedule()
    assert len(schedule) == 1
    assert schedule[0].name == "Walk"


def test_add_remove_co_owner():
    """add_co_owner / remove_co_owner should maintain the shared_with list correctly."""
    pet = Pet("Mochi", "dog", "Shiba", 2)
    assert not pet.is_shared_with("Alice")
    pet.add_co_owner("Alice")
    assert pet.is_shared_with("Alice")
    assert pet.is_shared_with("alice")   # case-insensitive
    pet.add_co_owner("Alice")            # idempotent — no duplicate
    assert len(pet.shared_with) == 1
    pet.remove_co_owner("Alice")
    assert not pet.is_shared_with("Alice")


def test_shared_with_persists_through_save_load(tmp_path):
    """shared_with list should survive a JSON save/load cycle."""
    owner = make_owner()
    pet = Pet("Mochi", "dog", "Shiba", 2, shared_with=["Bob", "Carol"])
    owner.add_pet(pet)
    filepath = str(tmp_path / "shared_test.json")
    owner.save_to_json(filepath)
    restored = Owner.load_from_json(filepath)
    assert restored.get_pets()[0].shared_with == ["Bob", "Carol"]
