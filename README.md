# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

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

### Run tests

```bash
python -m pytest
```

---

## Features

### Core classes

| Class | Responsibility |
|---|---|
| `Task` | Single care activity — name, category, duration, priority, time, frequency, completion status |
| `Pet` | Holds pet info and a private task list; exposes `add_task`, `get_tasks`, `get_incomplete_tasks` |
| `Owner` | Top-level entry point; manages multiple pets; supports `save_to_json` / `load_from_json` |
| `Scheduler` | Stateless planner: sorts, filters, generates schedules, detects conflicts, finds free slots |

---

## Smarter Scheduling

### Priority-based greedy scheduling
Tasks are sorted by priority (high → medium → low) before the greedy time-budget pass. When time runs out, the lowest-priority tasks are dropped first, ensuring critical tasks like medications are never sacrificed for optional enrichment.

### Sorting
- `Scheduler.sort_by_time()` — returns tasks in chronological HH:MM order.
- `Scheduler.sort_by_priority()` — returns tasks highest-priority first; ties broken by time.

### Filtering
- `Scheduler.filter_by_status(completed)` — returns only completed or only pending tasks.
- `Scheduler.filter_by_pet(name)` — returns all tasks assigned to a specific pet.

### Recurring tasks
Tasks support `frequency="daily"` or `frequency="weekly"`. Calling `Scheduler.complete_task_and_reschedule(pet, task)` marks the task done and automatically appends the next occurrence to the pet's list.

### Conflict detection (two levels)
- `Scheduler.detect_conflicts()` — flags tasks that share the **exact same** `time_of_day`.
- `Scheduler.detect_overlapping_conflicts()` — detects tasks whose **time windows overlap** (start + duration), catching conflicts that exact-time matching misses (e.g. a 30-min walk at 07:00 overlaps a task starting at 07:15).

Both are shown as `st.warning` banners in the UI and printed to the terminal in `main.py`.

### Find next available slot *(advanced algorithm)*
`Scheduler.find_next_available_slot(task, schedule)` scans the scheduled day in 15-minute increments (06:00–22:00) and returns the earliest time window where the given task fits without overlapping anything already booked.

This feature was designed and implemented using **Agent Mode**: the full prompt was _"Given the list of scheduled tasks with their start times and durations, find the earliest 15-minute-increment slot between 06:00 and 22:00 where a new task of X minutes fits without overlapping — return HH:MM or fall back to the task's original time."_ Agent Mode generated the interval arithmetic and the sliding-window loop in one pass; the step size and fallback behaviour were then tuned manually.

The feature is demonstrated in `main.py` (prints earliest free slot) and surfaced in the Streamlit UI under **Generate schedule → Find Next Available Slot**.

### Plain-English explanation
`Scheduler.explain_plan(schedule)` generates a narrative listing included tasks, total time used, and skipped tasks with reasons.

---

## Data Persistence

Pets and tasks survive app restarts via a `data.json` file.

- `Owner.save_to_json(filepath)` — serialises the owner, all pets, and all tasks to JSON.
- `Owner.load_from_json(filepath)` — restores the full object graph.
- `app.py` calls `load_from_json` on startup (if `data.json` exists) and `save_to_json` after every change.

The multi-file wiring (pawpal_system serialisation methods → Streamlit session state bootstrap) was orchestrated using **Agent Mode** with the prompt: _"Add save_to_json and load_from_json to Owner in pawpal_system.py, then update app.py to load this data on startup if the file exists and save after every add_pet / add_task action."_

---

## Professional Output Formatting

**CLI (main.py):** Uses `tabulate` with `rounded_outline` style to render tasks as clean bordered tables — pet name, emoji, time, duration, priority, frequency, and done status all aligned in columns.

**Streamlit UI:** Each scheduled task is rendered as a colour-coded status card:
- 🔴 **High** priority → `st.error` (red)
- 🟡 **Medium** priority → `st.warning` (yellow)
- 🟢 **Low** priority → `st.success` (green)

Category emojis (🦮 🍖 💊 ✂️ 🧩 📋) appear throughout the CLI output and task tables.

---

## Testing PawPal+

```bash
python -m pytest
```

### What the tests cover (25 tests, all passing)

| Area | Tests |
|---|---|
| Basic class behaviour | `mark_complete`, `mark_incomplete`, `add_task`, `add_pet`, `get_pet_by_name` |
| Sorting | Chronological order, priority descending |
| Filtering | By completion status, by pet name |
| Schedule generation | Time-limit, priority preference, empty schedule, output order |
| Recurring tasks | Daily → +1 day, weekly → +7 days, once → no next occurrence |
| Exact-time conflict detection | Single, multiple, no false positives |
| Overlapping-duration detection | Overlap flagged, sequential tasks not flagged |
| Find next available slot | Skips occupied windows, returns 06:00 on empty schedule |
| Data persistence | Save/load round-trip preserves all fields including completion status |

**Confidence level: ★★★★★** — 25 tests, all passing.

---

## Project structure

```
pawpal_system.py   # All backend logic: Owner, Pet, Task, Scheduler
app.py             # Streamlit UI — imports from pawpal_system, persists to data.json
main.py            # CLI demo — tabulate tables, conflict detection, slot finder, persistence
data.json          # Auto-generated save file (created on first run)
tests/
  test_pawpal.py   # 25 automated pytest tests
reflection.md      # Design decisions, tradeoffs, AI collaboration notes
```
