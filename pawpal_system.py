"""
PawPal+ – Logic Layer
Core classes: Owner, Pet, Task, Scheduler
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


PRIORITY_INT = {"low": 1, "medium": 2, "high": 3}
PRIORITY_LABEL = {1: "low", 2: "medium", 3: "high"}

CATEGORY_EMOJI = {
    "walk": "🦮",
    "feeding": "🍖",
    "meds": "💊",
    "grooming": "✂️",
    "enrichment": "🧩",
    "other": "📋",
}


@dataclass
class Task:
    """A single pet care task (walk, feeding, meds, grooming, enrichment, etc.)."""

    name: str
    category: str           # walk | feeding | meds | grooming | enrichment | other
    duration_minutes: int   # how long the task takes
    priority: int           # 1=low, 2=medium, 3=high
    time_of_day: str = "08:00"   # HH:MM — used for ordering and conflict detection
    frequency: str = "once"      # once | daily | weekly
    due_date: date = field(default_factory=date.today)
    completed: bool = False

    def mark_complete(self) -> None:
        """Set this task as done."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to not completed."""
        self.completed = False

    def next_occurrence(self) -> Optional["Task"]:
        """
        For daily/weekly tasks, return a fresh Task for the next due date.
        Returns None for one-off tasks.
        """
        if self.frequency == "daily":
            next_date = self.due_date + timedelta(days=1)
        elif self.frequency == "weekly":
            next_date = self.due_date + timedelta(weeks=1)
        else:
            return None
        return Task(
            name=self.name,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            time_of_day=self.time_of_day,
            frequency=self.frequency,
            due_date=next_date,
            completed=False,
        )

    @property
    def priority_label(self) -> str:
        """Human-readable priority label (low / medium / high)."""
        return PRIORITY_LABEL.get(self.priority, "unknown")

    @property
    def emoji(self) -> str:
        """Category emoji for display."""
        return CATEGORY_EMOJI.get(self.category, "📋")

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return (
            f"[{status}] {self.emoji} {self.name} "
            f"({self.category}, {self.duration_minutes} min, "
            f"priority={self.priority_label}, {self.time_of_day})"
        )


@dataclass
class Pet:
    """A pet owned by an Owner; holds the list of its care tasks."""

    name: str
    species: str
    breed: str
    age: int                # in years
    _tasks: list = field(default_factory=list, init=False, repr=False)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self._tasks.append(task)

    def get_tasks(self) -> list[Task]:
        """Return all tasks assigned to this pet (completed or not)."""
        return list(self._tasks)

    def get_incomplete_tasks(self) -> list[Task]:
        """Return only tasks that have not been completed yet."""
        return [t for t in self._tasks if not t.completed]


class Owner:
    """The pet owner – top-level entry point; owns one or more pets."""

    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes  # total free time today
        self.preferences: list[str] = preferences or []
        self._pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self._pets.append(pet)

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        return list(self._pets)

    def get_pet_by_name(self, name: str) -> Optional[Pet]:
        """Look up a pet by name (case-insensitive). Returns None if not found."""
        for pet in self._pets:
            if pet.name.lower() == name.lower():
                return pet
        return None


class Scheduler:
    """Generates and explains a daily care plan for an Owner's pets."""

    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # ── data retrieval ────────────────────────────────────────────────────────

    def get_todays_tasks(self) -> list[Task]:
        """Collect all incomplete tasks across every pet owned."""
        tasks: list[Task] = []
        for pet in self.owner.get_pets():
            tasks.extend(pet.get_incomplete_tasks())
        return tasks

    # ── sorting ───────────────────────────────────────────────────────────────

    def sort_by_time(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """Return tasks sorted chronologically by time_of_day (HH:MM string)."""
        source = tasks if tasks is not None else self.get_todays_tasks()
        return sorted(source, key=lambda t: t.time_of_day)

    def sort_by_priority(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """Return tasks sorted by priority descending, then by time_of_day."""
        source = tasks if tasks is not None else self.get_todays_tasks()
        return sorted(source, key=lambda t: (-t.priority, t.time_of_day))

    # ── filtering ─────────────────────────────────────────────────────────────

    def filter_by_status(
        self, completed: bool, tasks: Optional[list[Task]] = None
    ) -> list[Task]:
        """Filter a task list to only those matching the given completion status."""
        source = tasks if tasks is not None else self.get_todays_tasks()
        return [t for t in source if t.completed == completed]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks (completed and pending) belonging to a named pet."""
        pet = self.owner.get_pet_by_name(pet_name)
        return pet.get_tasks() if pet else []

    # ── schedule generation ───────────────────────────────────────────────────

    def generate_schedule(self) -> list[Task]:
        """
        Build today's plan greedily: consider tasks highest-priority first and
        include each one until available_minutes is exhausted.  The returned
        list is sorted chronologically by time_of_day for display.
        """
        candidates = self.sort_by_priority()
        schedule: list[Task] = []
        remaining = self.owner.available_minutes
        for task in candidates:
            if task.duration_minutes <= remaining:
                schedule.append(task)
                remaining -= task.duration_minutes
        return sorted(schedule, key=lambda t: t.time_of_day)

    def explain_plan(self, schedule: list[Task]) -> str:
        """
        Return a human-readable narrative explaining which tasks were included,
        how much time is used, and which tasks were skipped and why.
        """
        all_tasks = self.sort_by_priority()
        skipped = [t for t in all_tasks if t not in schedule]

        lines = [
            f"Schedule for {self.owner.name}'s pets",
            f"Available time: {self.owner.available_minutes} min",
            "",
            "Included tasks (sorted by time):",
        ]
        used = 0
        for task in schedule:
            lines.append(
                f"  {task.emoji} {task.name} — {task.duration_minutes} min "
                f"@ {task.time_of_day} (priority: {task.priority_label})"
            )
            used += task.duration_minutes
        lines.append(
            f"\nTotal time used: {used} min  |  "
            f"Remaining: {self.owner.available_minutes - used} min"
        )
        if skipped:
            lines.append("\nSkipped (insufficient time remaining):")
            for task in skipped:
                lines.append(
                    f"  ✗ {task.name} — {task.duration_minutes} min "
                    f"(priority: {task.priority_label})"
                )
        return "\n".join(lines)

    # ── recurring tasks ───────────────────────────────────────────────────────

    def complete_task_and_reschedule(self, pet: Pet, task: Task) -> Optional[Task]:
        """
        Mark a task complete. If it is a recurring task (daily/weekly), add its
        next occurrence to the pet's list and return it; return None otherwise.
        """
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    # ── conflict detection ────────────────────────────────────────────────────

    def detect_conflicts(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """
        Return warning strings for every time slot where two or more tasks are
        scheduled simultaneously.  Checks all incomplete tasks by default.
        """
        source = tasks if tasks is not None else self.get_todays_tasks()
        seen: dict[str, list[Task]] = {}
        for task in source:
            seen.setdefault(task.time_of_day, []).append(task)

        warnings: list[str] = []
        for time_slot, group in seen.items():
            if len(group) > 1:
                names = ", ".join(t.name for t in group)
                warnings.append(
                    f"Conflict at {time_slot}: [{names}] are all scheduled at the same time."
                )
        return warnings
