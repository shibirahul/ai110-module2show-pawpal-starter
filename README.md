# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the CLI demo

```bash
python main.py
```

---

## Smarter Scheduling

PawPal+ includes the following algorithmic features beyond a simple task list:

### Priority-based greedy scheduling
Tasks are sorted by priority (high → medium → low) before the greedy time-budget pass. When time runs out, the lowest-priority tasks are dropped first, ensuring critical tasks like medications are never sacrificed for optional enrichment activities.

### Sorting
- `Scheduler.sort_by_time()` — returns tasks in chronological order by `time_of_day` (HH:MM string).
- `Scheduler.sort_by_priority()` — returns tasks highest-priority first; ties broken by time.

### Filtering
- `Scheduler.filter_by_status(completed)` — returns only completed or only pending tasks.
- `Scheduler.filter_by_pet(name)` — returns all tasks assigned to a specific pet.

### Recurring tasks
Tasks can be marked `frequency="daily"` or `frequency="weekly"`. Calling `Scheduler.complete_task_and_reschedule(pet, task)` marks the current occurrence done and automatically appends the next occurrence (tomorrow or next week) to the pet's task list.

### Conflict detection
`Scheduler.detect_conflicts()` scans all incomplete tasks and returns a warning string for every `time_of_day` slot where two or more tasks are scheduled simultaneously — displayed as `st.warning` banners in the UI.

### Plain-English explanation
`Scheduler.explain_plan(schedule)` generates a short paragraph listing which tasks were included, how much total time they use, and which tasks were skipped and why.

---

## Testing PawPal+

Run the full test suite with:

```bash
python -m pytest
```

### What the tests cover

| Area | Tests |
|---|---|
| Basic class behaviour | `mark_complete`, `mark_incomplete`, `add_task`, `add_pet`, `get_pet_by_name` |
| Sorting | Chronological order, priority descending |
| Filtering | By completion status, by pet name |
| Schedule generation | Time-limit respected, priority preference, empty schedule, output sorted by time |
| Recurring tasks | Daily → +1 day, weekly → +7 days, once → no next occurrence |
| Conflict detection | Single conflict, multiple conflicts, no false positives |

**Confidence level: ★★★★☆** — 19 tests, all passing. Edge cases not yet covered: owner with no pets, boundary durations, future due dates.

---

## Project structure

```
pawpal_system.py   # All backend logic: Owner, Pet, Task, Scheduler
app.py             # Streamlit UI — imports from pawpal_system
main.py            # CLI demo script — run to verify logic in the terminal
tests/
  test_pawpal.py   # Automated pytest suite (19 tests)
reflection.md      # Design decisions, tradeoffs, and AI collaboration notes
```

## Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
