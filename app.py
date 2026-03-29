"""
PawPal+ – Streamlit UI
Multi-owner support with shared pets.
Any number of owners can co-manage the same pet.
Data persisted to data.json.
"""

import os
import json
from typing import Optional
import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, PRIORITY_INT

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

PRIORITY_COLOR = {
    "high":   ("🔴", "error"),
    "medium": ("🟡", "warning"),
    "low":    ("🟢", "success"),
}

# ── persistence ───────────────────────────────────────────────────────────────

def load_data() -> tuple[list[Owner], int]:
    """Load all owners + active index from data.json.
    Auto-migrates old single-owner format."""
    if not os.path.exists(DATA_FILE):
        return [], 0
    with open(DATA_FILE) as f:
        raw = json.load(f)
    if "owners" not in raw:          # migrate old single-owner format
        raw = {"owners": [raw], "active_index": 0}
    owners = [Owner.from_dict(o) for o in raw["owners"]]
    active = min(raw.get("active_index", 0), max(0, len(owners) - 1))
    return owners, active


def save_data(owners: list[Owner], active_index: int) -> None:
    """Persist all owners + active index to data.json."""
    with open(DATA_FILE, "w") as f:
        json.dump(
            {"owners": [o.to_dict() for o in owners], "active_index": active_index},
            f, indent=2,
        )


# ── shared-pet helpers ────────────────────────────────────────────────────────

def get_shared_pets_for(owner: Owner, all_owners: list[Owner]) -> list[tuple[Pet, Owner]]:
    """
    Return (pet, primary_owner) pairs for pets owned by OTHER owners
    but shared with this owner.
    """
    result = []
    for other in all_owners:
        if other is owner:
            continue
        for pet in other.get_pets():
            if pet.is_shared_with(owner.name):
                result.append((pet, other))
    return result


def find_pet_primary_owner(pet: Pet, all_owners: list[Owner]) -> Optional[Owner]:
    """Return the owner whose _pets list contains this exact pet object."""
    for o in all_owners:
        for p in o.get_pets():
            if p is pet:
                return o
    return None


def _pet_of(task: Task, owner: Owner, shared_pets: list[Pet]) -> str:
    """
    Return the pet name that contains this exact task object.
    Uses identity (is) not equality — safe even if two tasks have identical fields.
    """
    all_pets = owner.get_pets() + shared_pets
    for pet in all_pets:
        for t in pet.get_tasks():
            if t is task:
                return pet.name
    return "—"


# ── session state bootstrap ───────────────────────────────────────────────────

if "owners" not in st.session_state:
    owners_loaded, active_loaded = load_data()
    st.session_state.owners = owners_loaded
    st.session_state.active_index = active_loaded
    st.session_state._just_loaded = bool(owners_loaded)

owners: list[Owner] = st.session_state.owners

# clamp active_index defensively (guards against stale state after delete)
if owners:
    st.session_state.active_index = min(
        st.session_state.active_index, len(owners) - 1
    )
active_index: int = st.session_state.active_index

# ── page header ───────────────────────────────────────────────────────────────

st.title("🐾 PawPal+")
st.caption("A smart daily planner for busy pet owners.")

if st.session_state.pop("_just_loaded", False) and owners:
    st.success(f"✅ Loaded saved data — {len(owners)} owner(s).")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — OWNER DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("👥 Owners")

if owners:
    cols = st.columns(min(len(owners), 4))
    for i, owner in enumerate(owners):
        with cols[i % 4]:
            total_tasks = sum(len(p.get_tasks()) for p in owner.get_pets())
            pending = sum(len(p.get_incomplete_tasks()) for p in owner.get_pets())
            is_active = (i == active_index)
            border = "2px solid #4CAF50" if is_active else "1px solid #555"
            st.markdown(
                f"""<div style="border:{border};border-radius:10px;padding:12px;text-align:center;margin-bottom:8px">
                    <b>{"✅ " if is_active else ""}{owner.name}</b><br>
                    🐾 {len(owner.get_pets())} pet(s)<br>
                    📋 {pending} pending / {total_tasks} task(s)<br>
                    ⏱️ {owner.available_minutes} min/day
                </div>""",
                unsafe_allow_html=True,
            )
            if not is_active:
                if st.button(f"Switch →", key=f"switch_{i}", use_container_width=True):
                    st.session_state.active_index = i
                    save_data(owners, i)
                    st.rerun()
    st.markdown(f"**Total owners: {len(owners)}**")
else:
    st.info("No owners yet. Add one below to get started.")

st.divider()

# ── add new owner ─────────────────────────────────────────────────────────────

with st.expander("➕ Add a new owner"):
    with st.form("new_owner_form", clear_on_submit=True):
        new_name = st.text_input("Name", placeholder="e.g. Alex")
        new_mins = st.number_input("Minutes available today", min_value=10,
                                   max_value=480, value=90, step=10)
        new_prefs = st.text_input("Preferences (comma-separated, optional)",
                                  placeholder="morning walks, no weekday grooming")
        if st.form_submit_button("Add owner"):
            if not new_name.strip():
                st.warning("Please enter a name.")
            elif any(o.name.lower() == new_name.strip().lower() for o in owners):
                st.warning(f"An owner named **{new_name}** already exists.")
            else:
                pref_list = [p.strip() for p in new_prefs.split(",") if p.strip()]
                new_owner = Owner(new_name.strip(), int(new_mins), pref_list)
                owners.append(new_owner)
                st.session_state.owners = owners
                save_data(owners, active_index)
                st.success(f"Added owner **{new_name.strip()}**!")
                st.rerun()

if not owners:
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ACTIVE OWNER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

owner: Owner = owners[active_index]
shared_pet_pairs = get_shared_pets_for(owner, owners)
shared_pets_only: list[Pet] = [p for p, _ in shared_pet_pairs]
all_visible_pets: list[Pet] = owner.get_pets() + shared_pets_only

st.subheader(f"📋 Managing: **{owner.name}**")

# ── edit / delete active owner ────────────────────────────────────────────────

col_edit, col_del = st.columns([3, 1])
with col_edit:
    with st.expander("✏️ Edit owner details"):
        with st.form("edit_owner_form"):
            upd_name = st.text_input("Name", value=owner.name)
            upd_mins = st.number_input("Minutes available today", min_value=10,
                                       max_value=480, value=owner.available_minutes, step=10)
            upd_prefs = st.text_input("Preferences",
                                      value=", ".join(owner.preferences))
            if st.form_submit_button("Save changes"):
                new_name_stripped = upd_name.strip()
                name_conflict = any(
                    o.name.lower() == new_name_stripped.lower()
                    for o in owners if o is not owner
                )
                if not new_name_stripped:
                    st.warning("Name cannot be empty.")
                elif name_conflict:
                    st.warning(f"Another owner named **{new_name_stripped}** already exists.")
                else:
                    old_name = owner.name
                    owner.name = new_name_stripped
                    owner.available_minutes = int(upd_mins)
                    owner.preferences = [p.strip() for p in upd_prefs.split(",") if p.strip()]
                    # update shared_with references on all pets if name changed
                    if old_name != new_name_stripped:
                        for o in owners:
                            for pet in o.get_pets():
                                if pet.is_shared_with(old_name):
                                    pet.remove_co_owner(old_name)
                                    pet.add_co_owner(new_name_stripped)
                    st.session_state.owners = owners
                    save_data(owners, active_index)
                    st.success("Owner updated!")
                    st.rerun()

with col_del:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🗑️ Delete owner"):
        st.warning(f"This will permanently delete **{owner.name}** and all their pets.")
        if st.button(f"Confirm delete {owner.name}", type="primary"):
            owners.pop(active_index)
            # FIX: clamp index to valid range after removal
            new_active = min(active_index, len(owners) - 1) if owners else 0
            st.session_state.owners = owners
            st.session_state.active_index = new_active
            save_data(owners, new_active)
            st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PET MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("🐶 Pets")

# ── add a new pet ─────────────────────────────────────────────────────────────

with st.expander("➕ Add a new pet"):
    with st.form("pet_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            pet_name_in = st.text_input("Name", placeholder="Mochi")
        with col2:
            species = st.selectbox("Species", ["dog", "cat", "bird", "rabbit", "other"])
        with col3:
            breed = st.text_input("Breed", placeholder="Shiba Inu")
        with col4:
            age = st.number_input("Age (yrs)", min_value=0, max_value=30, value=2)

        # shared-with selector
        other_owner_names = [o.name for o in owners if o is not owner]
        share_with = []
        if other_owner_names:
            share_with = st.multiselect(
                "Share this pet with (optional)",
                options=other_owner_names,
                help="Selected owners will also be able to view and manage this pet's tasks.",
            )

        if st.form_submit_button("Add pet"):
            if not pet_name_in.strip():
                st.warning("Please enter a pet name.")
            elif owner.get_pet_by_name(pet_name_in.strip()):
                st.warning(f"**{pet_name_in}** already exists under {owner.name}.")
            else:
                new_pet = Pet(
                    name=pet_name_in.strip(),
                    species=species,
                    breed=breed.strip() or "unknown",
                    age=int(age),
                    shared_with=list(share_with),
                )
                owner.add_pet(new_pet)
                st.session_state.owners = owners
                save_data(owners, active_index)
                shared_msg = f" (shared with {', '.join(share_with)})" if share_with else ""
                st.success(f"Added **{pet_name_in.strip()}** the {species}{shared_msg}!")
                st.rerun()

# ── display all visible pets ──────────────────────────────────────────────────

own_pets = owner.get_pets()
if not own_pets and not shared_pets_only:
    st.info("No pets yet. Add one above.")
else:
    # OWN PETS
    if own_pets:
        st.markdown("**My Pets**")
        for pet in own_pets:
            pending = len(pet.get_incomplete_tasks())
            total = len(pet.get_tasks())
            shared_badge = (
                f"  👥 shared with: {', '.join(pet.shared_with)}"
                if pet.shared_with else ""
            )

            with st.expander(
                f"🐾 {pet.name} ({pet.species}, {pet.breed}, {pet.age} yrs) "
                f"— {pending} pending / {total} task(s){shared_badge}"
            ):
                # edit pet
                with st.form(f"edit_pet_{pet.name}"):
                    ec1, ec2, ec3, ec4 = st.columns(4)
                    with ec1:
                        upd_pname = st.text_input("Name", value=pet.name, key=f"pn_{pet.name}")
                    with ec2:
                        upd_species = st.selectbox(
                            "Species", ["dog", "cat", "bird", "rabbit", "other"],
                            index=["dog","cat","bird","rabbit","other"].index(pet.species)
                            if pet.species in ["dog","cat","bird","rabbit","other"] else 4,
                            key=f"ps_{pet.name}",
                        )
                    with ec3:
                        upd_breed = st.text_input("Breed", value=pet.breed, key=f"pb_{pet.name}")
                    with ec4:
                        upd_age = st.number_input("Age", min_value=0, max_value=30,
                                                  value=pet.age, key=f"pa_{pet.name}")

                    upd_share = st.multiselect(
                        "Shared with",
                        options=[o.name for o in owners if o is not owner],
                        default=pet.shared_with,
                        key=f"psh_{pet.name}",
                    )

                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("💾 Save pet"):
                            pet.name = upd_pname.strip() or pet.name
                            pet.species = upd_species
                            pet.breed = upd_breed.strip() or pet.breed
                            pet.age = int(upd_age)
                            pet.shared_with = list(upd_share)
                            st.session_state.owners = owners
                            save_data(owners, active_index)
                            st.success("Pet updated!")
                            st.rerun()
                    with sc2:
                        if st.form_submit_button("🗑️ Delete pet"):
                            owner.remove_pet(pet.name)
                            st.session_state.owners = owners
                            save_data(owners, active_index)
                            st.rerun()

    # SHARED PETS (read-only primary info, tasks still manageable)
    if shared_pets_only:
        st.markdown("**Shared With Me**")
        for pet, primary_owner in shared_pet_pairs:
            pending = len(pet.get_incomplete_tasks())
            total = len(pet.get_tasks())
            st.markdown(
                f"🤝 **{pet.name}** ({pet.species}) — primary owner: *{primary_owner.name}* "
                f"— {pending} pending / {total} task(s)"
            )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — TASK MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📋 Add a Task")

if not all_visible_pets:
    st.info("Add a pet first, then assign tasks.")
else:
    with st.form("task_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            pet_choice = st.selectbox(
                "Assign to pet",
                [p.name for p in all_visible_pets],
                help="Includes your own pets and pets shared with you.",
            )
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

        if st.form_submit_button("Add task"):
            if not task_name.strip():
                st.warning("Please enter a task name.")
            else:
                # FIX: search own pets first, then shared pets; null-check result
                pet = owner.get_pet_by_name(pet_choice)
                if pet is None:
                    pet = next((p for p in shared_pets_only if p.name == pet_choice), None)
                if pet is None:
                    st.error(f"Pet '{pet_choice}' not found. Please refresh and try again.")
                else:
                    pet.add_task(Task(
                        name=task_name.strip(),
                        category=category,
                        duration_minutes=int(duration),
                        priority=PRIORITY_INT[priority_label],
                        time_of_day=time_of_day,
                        frequency=frequency,
                    ))
                    st.session_state.owners = owners
                    save_data(owners, active_index)
                    st.success(f"Added **{task_name.strip()}** to {pet_choice}!")
                    st.rerun()

st.divider()

# ── current tasks by pet ──────────────────────────────────────────────────────

if all_visible_pets:
    st.subheader("📝 Current Tasks by Pet")
    for pet in all_visible_pets:
        tasks = pet.get_tasks()
        is_shared = pet in shared_pets_only
        label = f"{'🤝 ' if is_shared else '🐾 '}{pet.name} — {len(tasks)} task(s)"
        if tasks:
            with st.expander(label):
                for t in tasks:
                    icon, _ = PRIORITY_COLOR[t.priority_label]
                    done_badge = "✅ done" if t.completed else "⏳ pending"
                    c = st.columns([1, 4, 2, 2, 2, 2])
                    c[0].write(t.emoji)
                    c[1].write(f"**{t.name}**")
                    c[2].write(f"{t.duration_minutes} min @ {t.time_of_day}")
                    c[3].write(f"{icon} {t.priority_label}")
                    c[4].write(t.frequency)
                    c[5].write(done_badge)
        else:
            st.markdown(f"- {label} *(no tasks yet)*")

    st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("🗓️ Generate Today's Schedule")

if not all_visible_pets or all(len(p.get_tasks()) == 0 for p in all_visible_pets):
    st.info("Add at least one task to generate a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        # FIX: pass shared pets so scheduler includes them
        scheduler = Scheduler(owner, extra_pets=shared_pets_only)

        # conflict warnings (FIX: overlap warnings already deduplicated in scheduler)
        for w in scheduler.detect_conflicts():
            st.warning(f"⚠️ {w}")
        for w in scheduler.detect_overlapping_conflicts():
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

            for t in schedule:
                icon, color = PRIORITY_COLOR[t.priority_label]
                pet_name = _pet_of(t, owner, shared_pets_only)
                getattr(st, color)(
                    f"{t.emoji} **{t.name}** · {pet_name} · "
                    f"{t.time_of_day} · {t.duration_minutes} min · "
                    f"{icon} {t.priority_label} · _{t.frequency}_"
                )

            with st.expander("📖 Why this plan?"):
                st.text(scheduler.explain_plan(schedule))

            # FIX: use identity set for skipped tasks (same fix as explain_plan)
            schedule_ids = {id(t) for t in schedule}
            skipped = [t for t in scheduler.sort_by_priority() if id(t) not in schedule_ids]
            if skipped:
                with st.expander(f"⏭️ {len(skipped)} task(s) skipped (not enough time)"):
                    for t in skipped:
                        st.markdown(
                            f"- {t.emoji} **{t.name}** — {t.duration_minutes} min "
                            f"({t.priority_label})"
                        )

            st.divider()
            st.markdown("#### 🔍 Find Next Available Slot")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                slot_name = st.text_input("Task name", value="Vet visit", key="slot_name")
            with sc2:
                slot_dur = st.number_input("Duration (min)", min_value=5,
                                           max_value=240, value=30, key="slot_dur")
            with sc3:
                slot_pri = st.selectbox("Priority", ["low", "medium", "high"],
                                        index=1, key="slot_pri")
            if st.button("Find slot"):
                probe = Task(slot_name, "other", int(slot_dur), PRIORITY_INT[slot_pri])
                slot = scheduler.find_next_available_slot(probe, schedule)
                st.info(
                    f"Earliest free **{slot_dur}-min** slot for **{slot_name}**: **{slot}**"
                )
