"""
PawPal+ – Logic Layer
Core classes: Owner, Pet, Task, Scheduler
"""

import json
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


# ── time helpers ──────────────────────────────────────────────────────────────

def _time_to_minutes(time_str: str) -> int:
    """Convert a HH:MM string to minutes since midnight."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def _minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight back to a HH:MM string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ── core classes ──────────────────────────────────────────────────────────────

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

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "time_of_day": self.time_of_day,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat(),
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserialise a Task from a dictionary (e.g. loaded from JSON)."""
        return cls(
            name=data["name"],
            category=data["category"],
            duration_minutes=data["duration_minutes"],
            priority=data["priority"],
            time_of_day=data.get("time_of_day", "08:00"),
            frequency=data.get("frequency", "once"),
            due_date=date.fromisoformat(data.get("due_date", date.today().isoformat())),
            completed=data.get("completed", False),
        )


@dataclass
class Pet:
    """A pet owned (or co-managed) by one or more owners."""

    name: str
    species: str
    breed: str
    age: int                        # in years
    shared_with: list = field(default_factory=list)   # list of owner names with co-access
    _tasks: list = field(default_factory=list, init=False, repr=False)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self._tasks.append(task)

    def remove_task(self, task: Task) -> bool:
        """Remove a task by identity. Returns True if removed."""
        for i, t in enumerate(self._tasks):
            if t is task:
                self._tasks.pop(i)
                return True
        return False

    def get_tasks(self) -> list[Task]:
        """Return all tasks assigned to this pet (completed or not)."""
        return list(self._tasks)

    def get_incomplete_tasks(self) -> list[Task]:
        """Return only tasks that have not been completed yet."""
        return [t for t in self._tasks if not t.completed]

    def is_shared_with(self, owner_name: str) -> bool:
        """Return True if this pet is shared with the given owner name."""
        return owner_name.lower() in [n.lower() for n in self.shared_with]

    def add_co_owner(self, owner_name: str) -> None:
        """Grant co-access to an additional owner (idempotent)."""
        if not self.is_shared_with(owner_name):
            self.shared_with.append(owner_name)

    def remove_co_owner(self, owner_name: str) -> None:
        """Revoke co-access from an owner."""
        self.shared_with = [n for n in self.shared_with if n.lower() != owner_name.lower()]

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "age": self.age,
            "shared_with": self.shared_with,
            "tasks": [t.to_dict() for t in self._tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Deserialise a Pet (and its tasks) from a dictionary."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            breed=data["breed"],
            age=data["age"],
            shared_with=data.get("shared_with", []),
        )
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet


class Owner:
    """The pet owner – top-level entry point; owns one or more pets."""

    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes
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

    def remove_pet(self, name: str) -> bool:
        """Remove a pet by name. Returns True if removed, False if not found."""
        for i, pet in enumerate(self._pets):
            if pet.name.lower() == name.lower():
                self._pets.pop(i)
                return True
        return False

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "preferences": self.preferences,
            "pets": [p.to_dict() for p in self._pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Deserialise an Owner (with pets and tasks) from a dictionary."""
        owner = cls(
            name=data["name"],
            available_minutes=data["available_minutes"],
            preferences=data.get("preferences", []),
        )
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, filepath: str) -> None:
        """Persist this owner (and all pets/tasks) to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str) -> "Owner":
        """Restore an Owner from a single-owner JSON file."""
        with open(filepath) as f:
            return cls.from_dict(json.load(f))


class Scheduler:
    """Generates and explains a daily care plan for an Owner's pets."""

    def __init__(self, owner: Owner, extra_pets: Optional[list[Pet]] = None) -> None:
        """
        owner       — the active owner.
        extra_pets  — shared pets from other owners that this owner co-manages.
        """
        self.owner = owner
        self._extra_pets: list[Pet] = extra_pets or []

    def _all_pets(self) -> list[Pet]:
        """Return the owner's own pets plus any shared pets."""
        return self.owner.get_pets() + self._extra_pets

    # ── data retrieval ────────────────────────────────────────────────────────

    def get_todays_tasks(self) -> list[Task]:
        """Collect all incomplete tasks across every pet (own + shared)."""
        tasks: list[Task] = []
        for pet in self._all_pets():
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
        """Return all tasks belonging to a named pet (own or shared)."""
        for pet in self._all_pets():
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []

    # ── schedule generation ───────────────────────────────────────────────────

    def generate_schedule(self) -> list[Task]:
        """
        Build today's plan greedily: consider tasks highest-priority first and
        include each one until available_minutes is exhausted. Returns the chosen
        tasks sorted chronologically by time_of_day.
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
        Uses object identity (is) to match tasks — safe even if fields are equal.
        """
        all_tasks = self.sort_by_priority()
        # FIX: use identity (is) not equality (==) to avoid false matches
        # between two tasks that happen to have identical field values
        schedule_ids = {id(t) for t in schedule}
        skipped = [t for t in all_tasks if id(t) not in schedule_ids]

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
        Mark a task complete. If it is recurring (daily/weekly), add the next
        occurrence to the pet's list and return it; return None otherwise.
        """
        task.mark_complete()
        next_task = task.next_occurrence()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    # ── conflict detection (exact time) ──────────────────────────────────────

    def detect_conflicts(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """
        Return warning strings for every time slot where two or more tasks share
        the exact same time_of_day. Checks all incomplete tasks by default.
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

    # ── advanced: overlapping duration detection ──────────────────────────────

    def detect_overlapping_conflicts(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """
        Detect tasks whose actual time windows overlap (start_time + duration).
        More precise than detect_conflicts() which only catches identical start times.
        Returns deduplicated warnings.
        """
        source = sorted(
            tasks if tasks is not None else self.get_todays_tasks(),
            key=lambda t: t.time_of_day,
        )
        seen_pairs: set[frozenset] = set()
        warnings: list[str] = []
        for i, a in enumerate(source):
            a_start = _time_to_minutes(a.time_of_day)
            a_end = a_start + a.duration_minutes
            for b in source[i + 1:]:
                b_start = _time_to_minutes(b.time_of_day)
                b_end = b_start + b.duration_minutes
                if a_start < b_end and a_end > b_start:
                    pair = frozenset({id(a), id(b)})
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        warnings.append(
                            f"Overlap: '{a.name}' ({a.time_of_day}, {a.duration_minutes} min) "
                            f"and '{b.name}' ({b.time_of_day}, {b.duration_minutes} min) overlap."
                        )
        return warnings

    # ── advanced: find next available slot ────────────────────────────────────

    def find_next_available_slot(
        self,
        task: Task,
        schedule: Optional[list[Task]] = None,
        day_start: str = "06:00",
        day_end: str = "22:00",
        step_minutes: int = 15,
    ) -> str:
        """
        Find the earliest HH:MM start time (stepping in step_minutes increments)
        where task can be placed without overlapping any task already in schedule.
        Returns the task's original time_of_day if no free slot is found.
        """
        booked = schedule if schedule is not None else self.generate_schedule()
        intervals = [
            (
                _time_to_minutes(t.time_of_day),
                _time_to_minutes(t.time_of_day) + t.duration_minutes,
            )
            for t in booked
        ]
        start_min = _time_to_minutes(day_start)
        end_min = _time_to_minutes(day_end)

        for slot_start in range(start_min, end_min, step_minutes):
            slot_end = slot_start + task.duration_minutes
            if slot_end > end_min:
                break
            if not any(slot_start < e and slot_end > s for s, e in intervals):
                return _minutes_to_time(slot_start)

        return task.time_of_day  # fallback
