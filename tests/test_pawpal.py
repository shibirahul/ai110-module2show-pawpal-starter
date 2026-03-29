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
