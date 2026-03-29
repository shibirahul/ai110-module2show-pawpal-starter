"""
PawPal+ – Streamlit UI
Connects to the backend logic in pawpal_system.py.
Persists data to data.json so pets and tasks survive page refreshes.
"""

import os
import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT, CATEGORY_EMOJI

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A smart daily planner for busy pet owners.")
st.divider()

# ── helpers ───────────────────────────────────────────────────────────────────

PRIORITY_COLOR = {
    "high":   ("🔴", "error"),
    "medium": ("🟡", "warning"),
    "low":    ("🟢", "success"),
}


def _save(owner: Owner) -> None:
    """Persist current state to data.json."""
    owner.save_to_json(DATA_FILE)


def _pet_of(task: Task, owner: Owner) -> str:
    """Return the pet name that owns this task."""
    for pet in owner.get_pets():
        if task in pet.get_tasks():
            return pet.name
    return "—"


# ── session state bootstrap ───────────────────────────────────────────────────
# Load from disk on first run; create a blank owner if no save file exists.

if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.owner = Owner.load_from_json(DATA_FILE)
        st.session_state._loaded_from_disk = True
    else:
        st.session_state.owner = None
        st.session_state._loaded_from_disk = False

if st.session_state.get("_loaded_from_disk"):
    st.success(f"✅ Loaded saved data for **{st.session_state.owner.name}**.")
    st.session_state._loaded_from_disk = False

# ── Step 1: owner setup ───────────────────────────────────────────────────────

with st.expander("👤 Owner Setup", expanded=st.session_state.owner is None):
    with st.form("owner_form"):
        owner_name = st.text_input(
            "Your name",
            value=st.session_state.owner.name if st.session_state.owner else "Jordan",
        )
        available_min = st.number_input(
            "Minutes available today",
            min_value=10, max_value=480,
            value=st.session_state.owner.available_minutes if st.session_state.owner else 90,
            step=10,
        )
        prefs = st.text_input(
            "Preferences (comma-separated, optional)",
            value=", ".join(st.session_state.owner.preferences) if st.session_state.owner else "",
            placeholder="e.g. morning activities, no grooming on weekdays",
        )
        submitted = st.form_submit_button("Save owner")
        if submitted:
            pref_list = [p.strip() for p in prefs.split(",") if p.strip()]
            if st.session_state.owner is None:
                st.session_state.owner = Owner(owner_name, int(available_min), pref_list)
            else:
                st.session_state.owner.name = owner_name
                st.session_state.owner.available_minutes = int(available_min)
                st.session_state.owner.preferences = pref_list
            _save(st.session_state.owner)
            st.success(f"Saved **{owner_name}** with {available_min} min available.")

if st.session_state.owner is None:
    st.info("Fill in the owner form above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ── Step 2: add a pet ─────────────────────────────────────────────────────────

st.subheader("🐶 Pets")

with st.form("pet_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        pet_name = st.text_input("Name", placeholder="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
    with col3:
        breed = st.text_input("Breed", placeholder="Shiba Inu")
    with col4:
        age = st.number_input("Age (yrs)", min_value=0, max_value=30, value=2)
    add_pet = st.form_submit_button("Add pet")
    if add_pet:
        if not pet_name.strip():
            st.warning("Please enter a pet name.")
        elif owner.get_pet_by_name(pet_name.strip()):
            st.warning(f"A pet named **{pet_name}** already exists.")
        else:
            owner.add_pet(Pet(pet_name.strip(), species, breed.strip() or "unknown", int(age)))
            _save(owner)
            st.success(f"Added **{pet_name}** the {species}!")

pets = owner.get_pets()
if pets:
    for pet in pets:
        incomplete = len(pet.get_incomplete_tasks())
        total = len(pet.get_tasks())
        st.markdown(
            f"- **{pet.name}** ({pet.species}, {pet.breed}, {pet.age} yrs) "
            f"— {incomplete} pending / {total} total task(s)"
        )
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ── Step 3: add a task ────────────────────────────────────────────────────────

st.subheader("📋 Add a Task")

if not pets:
    st.info("Add a pet first, then assign tasks.")
else:
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            pet_choice = st.selectbox("Assign to pet", [p.name for p in pets])
            task_name = st.text_input("Task name", placeholder="Morning walk")
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "meds", "grooming", "enrichment", "other"],
            )
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=1)
            time_of_day = st.text_input("Time of day (HH:MM)", value="08:00")
            frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])
        add_task = st.form_submit_button("Add task")
        if add_task:
            if not task_name.strip():
                st.warning("Please enter a task name.")
            else:
                pet = owner.get_pet_by_name(pet_choice)
                pet.add_task(
                    Task(
                        name=task_name.strip(),
                        category=category,
                        duration_minutes=int(duration),
                        priority=PRIORITY_INT[priority_label],
                        time_of_day=time_of_day,
                        frequency=frequency,
                    )
                )
                _save(owner)
                st.success(f"Added **{task_name}** to {pet_choice}!")

st.divider()

# ── Step 4: view tasks per pet ────────────────────────────────────────────────

if pets:
    st.subheader("📝 Current Tasks by Pet")
    for pet in pets:
        tasks = pet.get_tasks()
        if tasks:
            with st.expander(f"{pet.name} — {len(tasks)} task(s)"):
                for t in tasks:
                    icon, color = PRIORITY_COLOR[t.priority_label]
                    badge = f"{icon} {t.priority_label}"
                    done_badge = "✅ done" if t.completed else "⏳ pending"
                    cols = st.columns([1, 4, 2, 2, 2, 2])
                    cols[0].write(t.emoji)
                    cols[1].write(f"**{t.name}**")
                    cols[2].write(f"{t.duration_minutes} min @ {t.time_of_day}")
                    cols[3].write(badge)
                    cols[4].write(t.frequency)
                    cols[5].write(done_badge)

st.divider()

# ── Step 5: generate schedule ─────────────────────────────────────────────────

st.subheader("🗓️ Generate Today's Schedule")

if not pets or all(len(p.get_tasks()) == 0 for p in pets):
    st.info("Add at least one task to generate a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner)

        # Exact-time conflict check
        exact = scheduler.detect_conflicts()
        for w in exact:
            st.warning(f"⚠️ {w}")

        # Overlapping-duration conflict check (advanced)
        overlaps = scheduler.detect_overlapping_conflicts()
        for w in overlaps:
            if w not in [e.replace("⚠️ ", "") for e in exact]:
                st.warning(f"⏱️ {w}")

        schedule = scheduler.generate_schedule()

        if not schedule:
            st.error(
                "No tasks fit within your available time. "
                "Try increasing your available minutes or reducing task durations."
            )
        else:
            used = sum(t.duration_minutes for t in schedule)
            st.success(
                f"Scheduled **{len(schedule)} task(s)** — "
                f"{used} of {owner.available_minutes} min used."
            )

            # Color-coded schedule table
            for t in schedule:
                icon, color = PRIORITY_COLOR[t.priority_label]
                pet_name = _pet_of(t, owner)
                fn = getattr(st, color)   # st.success / st.warning / st.error
                fn(
                    f"{t.emoji} **{t.name}** · {pet_name} · "
                    f"{t.time_of_day} · {t.duration_minutes} min · "
                    f"{icon} {t.priority_label} · _{t.frequency}_"
                )

            # Plain-text explanation
            with st.expander("📖 Why this plan?"):
                st.text(scheduler.explain_plan(schedule))

            # Skipped tasks
            all_tasks = scheduler.sort_by_priority()
            skipped = [t for t in all_tasks if t not in schedule]
            if skipped:
                with st.expander(f"⏭️ {len(skipped)} task(s) skipped (not enough time)"):
                    for t in skipped:
                        st.markdown(
                            f"- {t.emoji} **{t.name}** — {t.duration_minutes} min "
                            f"(priority: {t.priority_label})"
                        )

            # Find next available slot for a custom task
            st.divider()
            st.markdown("#### 🔍 Find Next Available Slot")
            col1, col2, col3 = st.columns(3)
            with col1:
                slot_task_name = st.text_input("Task name", value="Vet visit", key="slot_name")
            with col2:
                slot_duration = st.number_input("Duration (min)", min_value=5, max_value=240, value=30, key="slot_dur")
            with col3:
                slot_priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="slot_pri")

            if st.button("Find slot"):
                probe = Task(
                    slot_task_name, "other", int(slot_duration),
                    PRIORITY_INT[slot_priority]
                )
                slot = scheduler.find_next_available_slot(probe, schedule)
                st.info(
                    f"Earliest free **{slot_duration}-min** slot for "
                    f"**{slot_task_name}**: **{slot}**"
                )
