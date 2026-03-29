"""
PawPal+ – Streamlit UI
Connect the UI to the backend classes in pawpal_system.py.
"""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT, CATEGORY_EMOJI

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A smart daily planner for busy pet owners.")
st.divider()

# ── session state bootstrap ───────────────────────────────────────────────────
# st.session_state acts as persistent memory while the app is open.
# We create the Owner once and reuse it across every re-run.

if "owner" not in st.session_state:
    st.session_state.owner = None   # set after the owner form is submitted

# ── Step 1: owner setup ───────────────────────────────────────────────────────

with st.expander("👤 Owner Setup", expanded=st.session_state.owner is None):
    with st.form("owner_form"):
        owner_name = st.text_input("Your name", value="Jordan")
        available_min = st.number_input(
            "Minutes available today", min_value=10, max_value=480, value=90, step=10
        )
        prefs = st.text_input(
            "Preferences (comma-separated, optional)",
            placeholder="e.g. morning activities, no grooming on weekdays",
        )
        submitted = st.form_submit_button("Save owner")
        if submitted:
            pref_list = [p.strip() for p in prefs.split(",") if p.strip()]
            st.session_state.owner = Owner(owner_name, int(available_min), pref_list)
            st.success(f"Owner **{owner_name}** saved with {available_min} min available.")

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
            st.success(f"Added **{pet_name}** the {species}!")

pets = owner.get_pets()
if pets:
    for pet in pets:
        st.markdown(f"- **{pet.name}** ({pet.species}, {pet.breed}, {pet.age} yrs) — {len(pet.get_tasks())} task(s)")
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
                st.success(f"Added **{task_name}** to {pet_choice}!")

st.divider()

# ── Step 4: view tasks per pet ────────────────────────────────────────────────

if pets:
    st.subheader("📝 Current Tasks by Pet")
    for pet in pets:
        tasks = pet.get_tasks()
        if tasks:
            with st.expander(f"{pet.name} — {len(tasks)} task(s)"):
                rows = []
                for t in tasks:
                    rows.append({
                        "Emoji": t.emoji,
                        "Task": t.name,
                        "Category": t.category,
                        "Duration (min)": t.duration_minutes,
                        "Priority": t.priority_label,
                        "Time": t.time_of_day,
                        "Frequency": t.frequency,
                        "Done": "✓" if t.completed else "○",
                    })
                st.table(rows)

st.divider()

# ── Step 5: generate schedule ─────────────────────────────────────────────────

st.subheader("🗓️ Generate Today's Schedule")

if not pets or all(len(p.get_tasks()) == 0 for p in pets):
    st.info("Add at least one task to generate a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner)

        # Conflict check
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            for warning in conflicts:
                st.warning(f"⚠️ {warning}")

        schedule = scheduler.generate_schedule()

        if not schedule:
            st.error("No tasks fit within your available time. Try increasing your available minutes or reducing task durations.")
        else:
            st.success(f"Scheduled {len(schedule)} task(s) using {sum(t.duration_minutes for t in schedule)} of {owner.available_minutes} minutes.")

            # Display as a clean table
            rows = []
            for t in schedule:
                rows.append({
                    "": t.emoji,
                    "Task": t.name,
                    "Pet": next(
                        (p.name for p in pets if t in p.get_tasks()), "—"
                    ),
                    "Time": t.time_of_day,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": t.priority_label,
                    "Frequency": t.frequency,
                })
            st.table(rows)

            # Plain-text explanation
            with st.expander("📖 Why this plan?"):
                st.text(scheduler.explain_plan(schedule))

            # Skipped tasks
            all_tasks = scheduler.sort_by_priority()
            skipped = [t for t in all_tasks if t not in schedule]
            if skipped:
                with st.expander(f"⏭️ {len(skipped)} task(s) skipped (not enough time)"):
                    for t in skipped:
                        st.markdown(f"- {t.emoji} **{t.name}** — {t.duration_minutes} min (priority: {t.priority_label})")
