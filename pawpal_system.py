"""
PawPal+ – Logic Layer
Core classes: Owner, Pet, Task, Scheduler
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Task:
    """A single pet care task (walk, feeding, meds, grooming, enrichment, etc.)."""

    name: str
    category: str          # e.g. "walk", "feeding", "meds", "grooming", "enrichment"
    duration_minutes: int  # how long the task takes
    priority: int          # 1 (low) – 5 (high)
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        pass

    def mark_incomplete(self) -> None:
        """Reset this task to not completed."""
        pass


@dataclass
class Pet:
    """A pet owned by an Owner."""

    name: str
    species: str
    breed: str
    age: int               # in years
    _tasks: list = field(default_factory=list, init=False, repr=False)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        pass


class Owner:
    """The pet owner – entry point for the system."""

    def __init__(self, name: str, available_minutes: int, preferences: Optional[list[str]] = None):
        self.name = name
        self.available_minutes = available_minutes   # total time available today
        self.preferences: list[str] = preferences or []
        self._pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all pets belonging to this owner."""
        pass


class Scheduler:
    """Generates a daily care plan for an Owner's pets."""

    def __init__(self, owner: Owner):
        self.owner = owner

    def get_todays_tasks(self) -> list[Task]:
        """Collect all incomplete tasks across all of the owner's pets."""
        pass

    def generate_schedule(self) -> list[Task]:
        """
        Select and order tasks that fit within the owner's available time.
        Tasks are sorted by priority (highest first); lower-priority tasks
        are dropped when time runs out.
        """
        pass

    def explain_plan(self, schedule: list[Task]) -> str:
        """
        Return a human-readable explanation of why the schedule was chosen
        (which tasks were included, which were skipped, and why).
        """
        pass
