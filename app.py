# =========================================================
# RNG PRIVATE LOGIN AND PERMANENT SUPABASE STORAGE
# =========================================================
import copy
import json
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="My Dashboard", page_icon="D", layout="wide")

# =========================================================
# PERSIAN FONT: B NAZANIN (LOCAL DEPLOYMENT ASSET)
# =========================================================
# Keep B-NAZANIN.TTF beside app.py on the hosting service.
# Only deploy it if your font license permits web use and embedding.
import base64 as rng_base64
from pathlib import Path as RNGPath

RNG_FONT_FILE = RNGPath(__file__).resolve().parent / "B-NAZANIN.TTF"

if RNG_FONT_FILE.is_file():
    rng_font_base64 = rng_base64.b64encode(RNG_FONT_FILE.read_bytes()).decode("ascii")
    st.markdown(
        """<style>
        @font-face {
            font-family: 'RNG B Nazanin Persian';
            src: url('data:font/ttf;base64,""" + rng_font_base64 + """') format('truetype');
            font-style: normal;
            font-weight: 400 900;
            font-display: swap;
            unicode-range: U+0600-06FF, U+0750-077F, U+08A0-08FF,
                           U+FB50-FDFF, U+FE70-FEFF;
        }
        /* Arabic/Persian script uses Nazanin; Latin keeps the existing UI fonts. */
        .stApp, .stApp input, .stApp textarea, .stApp button,
        .stApp select, .stApp label,
        .stApp [data-testid="stMarkdownContainer"] {
            font-family: 'RNG B Nazanin Persian', 'Source Sans Pro', sans-serif !important;
        }
        </style>""",
        unsafe_allow_html=True
    )
else:
    st.warning("B-NAZANIN.TTF not found beside app.py; Persian font unavailable.")


def rng_pdf_font_name():
    """Register B Nazanin for PDF Persian text; do not need Windows fonts."""
    if not RNG_FONT_FILE.is_file():
        raise FileNotFoundError(
            "B-NAZANIN.TTF not found. Upload it beside app.py (if licensed)."
        )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    name = "RNGBNazanin"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(RNG_FONT_FILE)))
    return name


def rng_pdf_runs(visual_text):
    """B Nazanin lacks Latin letters; use Helvetica for Latin runs."""
    from reportlab.pdfbase import pdfmetrics
    persian_font = rng_pdf_font_name()
    available = pdfmetrics.getFont(persian_font).face.charWidths
    runs = []
    for ch in str(visual_text):
        code = ord(ch)
        persian = (0x0600 <= code <= 0x08FF or 0xFB50 <= code <= 0xFEFF)
        font = persian_font if code in available and (persian or not ch.isascii()) else "Helvetica"
        # Digits and punctuation can stay with B Nazanin where supported.
        if (ch.isdigit() or ch in " .,:;/-+()[]%") and code in available:
            font = persian_font
        if runs and runs[-1][0] == font:
            runs[-1] = (font, runs[-1][1] + ch)
        else:
            runs.append((font, ch))
    return runs


def rng_pdf_width(visual_text, size):
    from reportlab.pdfbase import pdfmetrics
    return sum(
        pdfmetrics.stringWidth(part, name, size)
        for name, part in rng_pdf_runs(visual_text)
    )


def rng_pdf_draw(pdf, visual_text, anchor_x, baseline, size, align="left"):
    """Draw shaped visual-order Persian/English without missing Latin letters."""
    from reportlab.pdfbase import pdfmetrics
    runs = rng_pdf_runs(visual_text)
    total_width = sum(pdfmetrics.stringWidth(s, name, size) for name, s in runs)
    x = anchor_x - (total_width / 2 if align == "center" else total_width if align == "right" else 0)
    for name, part in runs:
        pdf.setFont(name, size)
        pdf.drawString(x, baseline, part)
        x += pdfmetrics.stringWidth(part, name, size)


# Persistent record groups. UI/navigation flags remain session-local.
RNG_PERSISTENT_KEYS = (
    "sticky_notes", "tasks", "development_tasks",
    "meeting_cards", "warehouse_cards", "warehouse_card_ids",
    "warehouse_forms", "mission_report_cards",
    "mission_report_card_ids", "mission_report_forms",
    "bom_cards", "bom_card_ids", "bom_forms",
)
RNG_DYNAMIC_PREFIXES = ("meeting_data_",)


def rng_is_persistent(key):
    return key in RNG_PERSISTENT_KEYS or any(
        key.startswith(prefix) for prefix in RNG_DYNAMIC_PREFIXES
    )


def rng_snapshot():
    return {
        key: copy.deepcopy(value)
        for key, value in st.session_state.items()
        if rng_is_persistent(key)
    }


def rng_clear_private_state():
    for key in list(st.session_state.keys()):
        if rng_is_persistent(key) or key.startswith("rng_"):
            del st.session_state[key]
    # Remove pre-existing page widget values after logging out.
    for key in list(st.session_state.keys()):
        if key not in ("page",):
            del st.session_state[key]


def rng_fail(message):
    st.error(message)
    st.stop()


try:
    settings = st.secrets["supabase"]
    rng_url = str(settings["url"]).strip()
    rng_key = str(settings["key"]).strip()
    # Owner UID is an additional access-control gate on ALL Streamlit pages.
    rng_owner_uid = str(settings["owner_uid"]).strip().lower()
    if not rng_url.startswith("https://") or not rng_key or not rng_owner_uid:
        raise ValueError("Missing or invalid Supabase configuration")
except (KeyError, ValueError, TypeError) as exc:
    rng_fail(
        "Database setup is incomplete. In Streamlit Cloud → App settings → "
        "Secrets, set [supabase] url, key and owner_uid. "
        "Use your Supabase Authentication → Users UID for owner_uid."
    )

if "rng_client" not in st.session_state:
    try:
        st.session_state.rng_client = create_client(rng_url, rng_key)
    except Exception:
        rng_fail("Unable to initialize Supabase. Check your Streamlit Secrets.")

rng_client = st.session_state.rng_client

# Verify current session with Supabase before rendering any private content.
rng_user = None
if st.session_state.get("rng_logged_in"):
    try:
        response = rng_client.auth.get_user()
        rng_user = response.user
        if rng_user is None or str(rng_user.id).lower() != rng_owner_uid:
            rng_user = None
    except Exception:
        rng_user = None

if rng_user is None:
    if st.session_state.get("rng_logged_in"):
        try:
            rng_client.auth.sign_out()
        except Exception:
            pass
        rng_clear_private_state()

    st.markdown("## My Dashboard")
    st.caption("Private workspace · Sign in to continue")
    with st.form("rng_login_form"):
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign in", use_container_width=True)
    if submit:
        try:
            signed_in = rng_client.auth.sign_in_with_password({
                "email": email.strip(), "password": password
            })
            signed_user = signed_in.user
            if signed_user is None or str(signed_user.id).lower() != rng_owner_uid:
                rng_client.auth.sign_out()
                st.error("This account is not authorized to open the Dashboard.")
            else:
                st.session_state.rng_logged_in = True
                st.rerun()
        except Exception:
            st.error("Sign in failed. Check your email and password.")
    st.stop()

# Fetch stored records once per authenticated browser session.
# A failed read must stop the app (never replace server data with blank defaults).
if not st.session_state.get("rng_data_loaded"):
    try:
        rows = (
            rng_client.table("dashboard_data")
            .select("section,data")
            .execute()
            .data
        )
        for row in rows:
            section = row.get("section", "")
            if rng_is_persistent(section):
                st.session_state[section] = copy.deepcopy(row["data"])
        st.session_state.rng_data_loaded = True
        st.session_state.rng_saved_snapshot = rng_snapshot()
    except Exception as exc:
        rng_fail("Could not load your records from Supabase. No changes were made. "
                 "Check the database connection and RLS policy. " + str(exc))


def rng_save():
    """Save only changed sections, including nested forms and task lists."""
    before = st.session_state.get("rng_saved_snapshot", {})
    after = rng_snapshot()
    changed = {
        section: value for section, value in after.items()
        if section not in before or before[section] != value
    }
    if not changed:
        return
    for section, value in changed.items():
        # One row per section prevents editing notes from overwriting BOM data.
        rng_client.table("dashboard_data").upsert(
            {"section": section, "data": value},
            on_conflict="section"
        ).execute()
        # Update the baseline only after a successful database write.
        before[section] = copy.deepcopy(value)
    st.session_state.rng_saved_snapshot = before


def rng_rerun():
    try:
        rng_save()
    except Exception as exc:
        rng_fail("The change could not be saved. Please retry. Details: " + str(exc))
    st.rerun()

import pandas as pd

# =========================================================
# SESSION STATE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "sticky_notes" not in st.session_state:
    st.session_state.sticky_notes = []

if "editing_note" not in st.session_state:
    st.session_state.editing_note = None


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fa;
}

.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

section[data-testid="stSidebar"] {
    background-color: #172333;
}

section[data-testid="stSidebar"] * {
    color: white;
}

.dashboard-title {
    font-size: 38px;
    font-weight: 700;
    color: #172333;
    margin-bottom: 4px;
}

.dashboard-subtitle {
    font-size: 16px;
    color: #697586;
    margin-bottom: 25px;
}

.section-title {
    font-size: 21px;
    font-weight: 650;
    color: #172333;
    margin-top: 10px;
    margin-bottom: 16px;
}

.nav-card {
    background: white;
    border: 1px solid #e3e7ed;
    border-radius: 14px;
    padding: 22px;
    min-height: 110px;
    box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
}

.nav-card-title {
    font-size: 17px;
    font-weight: 650;
    color: #172333;
    margin-bottom: 7px;
}

.nav-card-text {
    font-size: 13px;
    color: #7b8794;
}

.note-box {
    background: #fffdf0;
    border: 1px solid #eee5b8;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 10px;
    color: #444;
}

.add-note-box {
    background: white;
    border: 1px solid #dfe4ea;
    border-radius: 14px;
    padding: 18px;
    margin-top: 15px;
    box-shadow: 0 2px 8px rgba(20, 30, 45, 0.04);
}

.stButton > button {
    border-radius: 9px;
    min-height: 42px;
}

@media (max-width: 768px) {

    .block-container {
        padding: 1.2rem 1rem 2rem 1rem;
    }

    .dashboard-title {
        font-size: 30px;
    }

    .dashboard-subtitle {
        font-size: 14px;
        margin-bottom: 20px;
    }

    .nav-card {
        padding: 16px;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("MY DASHBOARD")
st.sidebar.caption("Personal Workspace")
st.sidebar.divider()

# Logout is in the existing sidebar; no page layouts or business features change.
if st.sidebar.button("Log out", key="rng_logout_button", use_container_width=True):
    try:
        rng_save()
        rng_client.auth.sign_out()
    except Exception as exc:
        st.error("Could not finish logout: " + str(exc))
        st.stop()
    rng_clear_private_state()
    st.rerun()

pages = [
    "Dashboard",
    "To Do List",
    "Meeting Minutes",
    "Warehouse",
    "Mission Report",
    "Rah Nia Development",
    "BOM",
    "Employer Report"
]

for p in pages:

    if st.sidebar.button(
        p,
        use_container_width=True
    ):
        st.session_state.page = p
        rng_rerun()

page = st.session_state.page


# =========================================================
# DASHBOARD
# =========================================================




if page == "Dashboard":

    import base64
    import mimetypes
    from pathlib import Path
    from html import escape

    # =====================================================
    # LOAD DASHBOARD IMAGES
    # =====================================================

    dashboard_folder = Path(__file__).resolve().parent

    def dashboard_image_url(filename):

        image_path = dashboard_folder / filename

        if not image_path.is_file():
            return ""

        mime = (
            mimetypes.guess_type(str(image_path))[0]
            or "image/png"
        )

        encoded = base64.b64encode(
            image_path.read_bytes()
        ).decode("ascii")

        return f"data:{mime};base64,{encoded}"

    portrait_url = dashboard_image_url("My Pic.png")
    background_url = dashboard_image_url(
        "dashboard_background.png"
    )

    # =====================================================
    # DASHBOARD MARKER
    # =====================================================

    st.markdown(
        '<div id="rng-dashboard-marker"></div>',
        unsafe_allow_html=True
    )

    # =====================================================
    # DASHBOARD-ONLY CSS
    # =====================================================

    background_css = (
        f'url("{background_url}")'
        if background_url else "none"
    )

    portrait_css = (
        f'url("{portrait_url}")'
        if portrait_url else "none"
    )

    st.markdown(
        f"""
        <style>

        /* ================================================
           MAIN DASHBOARD BACKGROUND
           ================================================ */

        section[data-testid="stMain"]:has(
            #rng-dashboard-marker
        ) {{
            position: relative !important;
            isolation: isolate;

            background-color: #8094b1 !important;
            background-image:
                {background_css},
                linear-gradient(
                    125deg,
                    #263c5b 0%,
                    #718aa9 45%,
                    #e4ecf7 100%
                ) !important;

            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;

            min-height: 100vh;
        }}

        /* ================================================
           PORTRAIT - LEFT SIDE
           ================================================ */

        section[data-testid="stMain"]:has(
            #rng-dashboard-marker
        )::before {{

            content: "";

            position: fixed;
            z-index: 0;

            pointer-events: none;

            left: 258px;
            bottom: 0;

            width: min(45vw, 690px);
            height: 91vh;

            background-image: {portrait_css};
            background-repeat: no-repeat;
            background-position: left bottom;
            background-size: contain;

            -webkit-mask-image:
                linear-gradient(
                    to right,
                    black 0%,
                    black 69%,
                    transparent 100%
                );

            mask-image:
                linear-gradient(
                    to right,
                    black 0%,
                    black 69%,
                    transparent 100%
                );
        }}

        /* ================================================
           CONTENT POSITION
           ================================================ */

        section[data-testid="stMain"]:has(
            #rng-dashboard-marker
        )
        .block-container {{

            position: relative;
            z-index: 1;

            max-width: 100% !important;

            padding-left: clamp(
                340px,
                38%,
                560px
            ) !important;

            padding-right: 32px !important;
            padding-top: 68px !important;

            padding-bottom: 55px !important;
        }}

        /* ================================================
           TITLE
           ================================================ */

        section[data-testid="stMain"]:has(
            #rng-dashboard-marker
        )
        .dashboard-title {{

            font-size: clamp(
                36px,
                3.3vw,
                58px
            ) !important;

            font-weight: 800 !important;
            letter-spacing: -1.5px;

            color: #092554 !important;

            margin-bottom: 8px !important;

            line-height: 1.2 !important;
        }}

        section[data-testid="stMain"]:has(
            #rng-dashboard-marker
        )
        .dashboard-subtitle {{

            color: #506783 !important;

            font-size: 17px !important;

            margin-top: 15px !important;
            margin-bottom: 38px !important;
        }}

        .rng-title-accent {{

            width: 245px;
            height: 3px;

            background: linear-gradient(
                90deg,
                #006dce,
                #56a5f5 55%,
                transparent
            );

            border-radius: 10px;
            margin-top: 8px;
        }}

        /* ================================================
           GLASSY STICKY NOTES CONTAINER
           ================================================ */

        .st-key-rng_glass_notes {{

            background: rgba(
                234, 243, 255, 0.30
            ) !important;

            border: 1px solid rgba(
                255, 255, 255, 0.52
            ) !important;

            border-radius: 20px !important;

            padding: 23px !important;

            -webkit-backdrop-filter:
                blur(19px) saturate(135%);

            backdrop-filter:
                blur(19px) saturate(135%);

            box-shadow:
                0 18px 48px rgba(
                    12, 32, 68, 0.15
                ),
                inset 0 1px 0 rgba(
                    255, 255, 255, 0.48
                );

            margin-top: 14px;
        }}

        /* ================================================
           STICKY NOTES HEADING
           ================================================ */

        .st-key-rng_glass_notes
        .section-title {{

            font-size: 22px !important;
            font-weight: 750 !important;

            color: #10243e !important;

            margin-bottom: 16px !important;
        }}

        /* ================================================
           INDIVIDUAL STICKY NOTES
           ================================================ */

        .st-key-rng_glass_notes
        .note-box {{

            background: rgba(
                255, 251, 234, 0.96
            ) !important;

            color: #263548 !important;

            border: 1px solid #f0dea7 !important;
            border-radius: 11px !important;

            min-height: 51px;

            padding: 14px 16px !important;

            display: flex;
            align-items: center;

            box-shadow:
                0 3px 10px rgba(
                    30, 40, 60, 0.045
                );

            font-size: 14px;
            overflow-wrap: anywhere;
        }}

        /* ================================================
           STICKY NOTE BUTTONS
           ================================================ */

        .st-key-rng_glass_notes
        .stButton button {{

            background: linear-gradient(
                145deg,
                #183b6d,
                #0b2447
            ) !important;

            color: #ffffff !important;

            border: 1px solid rgba(
                77, 147, 229, 0.40
            ) !important;

            border-radius: 9px !important;

            min-height: 46px !important;

            font-size: 13px !important;
            font-weight: 650 !important;

            box-shadow:
                0 2px 5px rgba(
                    15, 30, 60, 0.08
                );

            transition:
                background 0.2s ease,
                box-shadow 0.2s ease;
        }}

        .st-key-rng_glass_notes
        .stButton button:hover {{

            background: #22538f !important;

            color: white !important;

            border-color: #75b3fb !important;

            box-shadow:
                0 4px 12px rgba(
                    12, 51, 110, 0.22
                );
        }}

        /* ================================================
           NOTE INPUTS
           ================================================ */

        .st-key-rng_glass_notes
        div[data-testid="stTextInput"] input {{

            background: rgba(
                248, 251, 255, 0.94
            ) !important;

            color: #192d48 !important;

            border: 1px solid rgba(
                255, 255, 255, 0.80
            ) !important;

            border-radius: 10px !important;

            min-height: 49px !important;

            padding-left: 16px !important;
        }}

        .st-key-rng_glass_notes
        div[data-testid="stTextInput"] input::placeholder {{

            color: #8494ad !important;
        }}

        .st-key-rng_glass_notes
        div[data-testid="stTextArea"] textarea {{

            background: rgba(
                248, 251, 255, 0.96
            ) !important;

            color: #192d48 !important;

            border-radius: 10px !important;
        }}

        /* ================================================
           ADD NOTE BUTTON
           ================================================ */

        .st-key-rng_add_note
        .stButton button {{

            width: 100% !important;

            background: linear-gradient(
                100deg,
                #071b37,
                #132f57
            ) !important;

            min-height: 51px !important;

            font-size: 14px !important;
            font-weight: 700 !important;

            border-radius: 10px !important;
        }}

        /* ================================================
           RESPONSIVE LAYOUT
           ================================================ */

        @media (max-width: 1150px) {{

            section[data-testid="stMain"]:has(
                #rng-dashboard-marker
            )
            .block-container {{

                padding-left: 32% !important;
                padding-right: 20px !important;
            }}

            section[data-testid="stMain"]:has(
                #rng-dashboard-marker
            )::before {{

                width: 43vw;
                height: 80vh;
            }}

            .st-key-rng_glass_notes {{
                padding: 16px !important;
            }}
        }}

        @media (max-width: 700px) {{

            section[data-testid="stMain"]:has(
                #rng-dashboard-marker
            )
            .block-container {{

                padding-left: 16px !important;
                padding-right: 16px !important;
                padding-top: 32px !important;
            }}

            section[data-testid="stMain"]:has(
                #rng-dashboard-marker
            )::before {{

                left: 0;
                width: 100vw;
                height: 75vh;

                opacity: 0.17;
            }}

            .st-key-rng_glass_notes {{

                padding: 12px !important;
            }}

            section[data-testid="stMain"]:has(
                #rng-dashboard-marker
            )
            .dashboard-title {{

                font-size: 34px !important;
            }}
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

    # =====================================================
    # DASHBOARD TITLE
    # =====================================================

    st.markdown(
        '<div class="dashboard-title">My Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="rng-title-accent"></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Your personal workspace'
        '</div>',
        unsafe_allow_html=True
    )

    if not portrait_url:
        st.warning(
            "My Pic.png not found beside app.py."
        )

    if not background_url:
        st.warning(
            "dashboard_background.png not found beside app.py."
        )

    # =====================================================
    # GLASSY STICKY NOTES PANEL
    # =====================================================

    with st.container(key="rng_glass_notes"):

        st.markdown(
            '<div class="section-title">'
            'Sticky Notes'
            '</div>',
            unsafe_allow_html=True
        )

        # =================================================
        # EXISTING STICKY NOTES
        # =================================================

        for i, note in enumerate(
            st.session_state.sticky_notes
        ):

            if st.session_state.editing_note == i:

                edited_note = st.text_area(
                    "Edit note",
                    value=note,
                    key=f"edit_text_{i}",
                    height=100
                )

                edit_col1, edit_col2 = st.columns(2)

                with edit_col1:

                    if st.button(
                        "Save",
                        key=f"save_{i}",
                        use_container_width=True
                    ):

                        if edited_note.strip():

                            st.session_state.sticky_notes[i] = (
                                edited_note.strip()
                            )

                        st.session_state.editing_note = None
                        rng_rerun()

                with edit_col2:

                    if st.button(
                        "Cancel",
                        key=f"cancel_{i}",
                        use_container_width=True
                    ):

                        st.session_state.editing_note = None
                        rng_rerun()

            else:

                note_col, edit_col, delete_col = st.columns(
                    [7, 1.5, 1.5],
                    gap="small"
                )

                with note_col:

                    st.markdown(
                        f"""
                        <div class="note-box">
                            {escape(str(note))}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with edit_col:

                    if st.button(
                        "Edit",
                        key=f"edit_{i}",
                        use_container_width=True
                    ):

                        st.session_state.editing_note = i
                        rng_rerun()

                with delete_col:

                    if st.button(
                        "Delete",
                        key=f"delete_{i}",
                        use_container_width=True
                    ):

                        st.session_state.sticky_notes.pop(i)
                        rng_rerun()

        # =================================================
        # ADD NEW STICKY NOTE
        # =================================================

        st.markdown(
            '<div style="height: 12px;"></div>',
            unsafe_allow_html=True
        )

        new_note = st.text_input(
            "New sticky note",
            placeholder="Type a new note here...",
            label_visibility="collapsed",
            key="rng_new_sticky_note"
        )

        with st.container(key="rng_add_note"):

            if st.button(
                "+  Add Sticky Note",
                key="rng_add_sticky_note_button",
                use_container_width=True
            ):

                if new_note.strip():

                    st.session_state.sticky_notes.append(
                        new_note.strip()
                    )

                    rng_rerun()

    # =====================================================
    # END DASHBOARD
    # WORKSPACE REMOVED
    # OTHER TABS UNCHANGED
    # =====================================================

# =========================================================
# SIDEBAR PAGES
# =========================================================

elif page == "To Do List":
    from datetime import datetime

    # =========================================================
    # TASK DATA
    # =========================================================

    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    if "creating_task" not in st.session_state:
        st.session_state.creating_task = False

    if "editing_task" not in st.session_state:
        st.session_state.editing_task = None

    if "new_subtask_count" not in st.session_state:
        st.session_state.new_subtask_count = 1

    # =========================================================
    # CSS
    # =========================================================

    st.markdown("""
    <style>

    .todo-card {
        background-color: #ffffff;
        border: 1px solid #d7dde5;
        border-radius: 14px;
        margin-bottom: 18px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.06);
    }

    .todo-card-done {
        background-color: #edf8ef;
        border: 1px solid #a8d5b0;
        border-radius: 14px;
        margin-bottom: 18px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
    }

    .todo-title {
        color: #172333 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 16px;
        margin: 0;
    }

    .todo-section-title {
        color: #172333 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        padding: 12px 16px 5px 16px;
        margin: 0;
    }

    .todo-date {
        color: #596579 !important;
        font-size: 12px !important;
        padding: 5px 16px;
        margin: 0;
    }

    .todo-completed {
        color: #218739 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 5px 16px 14px 16px;
        margin: 0;
    }

    .todo-divider {
        height: 1px;
        background-color: #dfe4ea;
        margin: 0;
        padding: 0;
    }

    div[data-testid="stCheckbox"] label p {
        color: #263241 !important;
        font-size: 14px !important;
    }

    div[data-testid="stCheckbox"] label {
        color: #263241 !important;
    }

    div[data-testid="stCheckbox"] {
        padding-left: 16px;
        padding-right: 16px;
        margin-top: 2px;
        margin-bottom: 2px;
    }

    @media (max-width: 768px) {

        .todo-title {
            font-size: 17px !important;
            padding: 14px;
        }

        .todo-section-title {
            padding-left: 14px;
        }

        .todo-date,
        .todo-completed {
            padding-left: 14px;
            padding-right: 14px;
        }

        div[data-testid="stCheckbox"] {
            padding-left: 14px;
            padding-right: 14px;
        }
    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # PAGE TITLE
    # =========================================================

    st.markdown(
        '<div class="dashboard-title">To Do List</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Manage your tasks and track your progress.'
        '</div>',
        unsafe_allow_html=True
    )

    # =========================================================
    # CREATE TASK BUTTON
    # =========================================================

    if st.button(
        "Create Task",
        key="create_task_button",
        use_container_width=True
    ):
        st.session_state.creating_task = True
        st.session_state.new_subtask_count = 1
        rng_rerun()

    # =========================================================
    # CREATE TASK FORM
    # =========================================================

    if st.session_state.creating_task:

        st.markdown("### Create New Task")

        new_title = st.text_input(
            "Task Title",
            placeholder="Enter task title...",
            key="new_task_title"
        )

        st.markdown("Sub Tasks")

        subtask_values = []

        for i in range(st.session_state.new_subtask_count):

            value = st.text_input(
                f"Sub Task {i + 1}",
                placeholder="Enter sub task...",
                key=f"create_subtask_{i}"
            )

            subtask_values.append(value)

        add_col, create_col, cancel_col = st.columns(3)

        with add_col:
            if st.button(
                "Add Sub Task",
                key="add_subtask_button",
                use_container_width=True
            ):
                st.session_state.new_subtask_count += 1
                rng_rerun()

        with create_col:
            if st.button(
                "Save Task",
                key="save_new_task",
                use_container_width=True
            ):

                if new_title.strip():

                    subtasks = []

                    for value in subtask_values:

                        if value.strip():
                            subtasks.append({
                                "text": value.strip(),
                                "done": False
                            })

                    st.session_state.tasks.append({
                        "title": new_title.strip(),
                        "subtasks": subtasks,
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "completed": None,
                        "done": False,
                    })

                    st.session_state.creating_task = False
                    st.session_state.new_subtask_count = 1

                    rng_rerun()

        with cancel_col:
            if st.button(
                "Cancel",
                key="cancel_new_task",
                use_container_width=True
            ):
                st.session_state.creating_task = False
                st.session_state.new_subtask_count = 1
                rng_rerun()

        st.divider()

    # =========================================================
    # SORT TASKS
    # =========================================================

    unfinished = [
        task for task in st.session_state.tasks
        if not task["done"]
    ]

    completed = [
        task for task in st.session_state.tasks
        if task["done"]
    ]

    sorted_tasks = unfinished + completed

    # =========================================================
    # TASK CARDS
    # =========================================================

    for row_start in range(0, len(sorted_tasks), 3):

        row_tasks = sorted_tasks[row_start:row_start + 3]

        columns = st.columns(3)

        for column_number, task in enumerate(row_tasks):

            with columns[column_number]:

                task_index = st.session_state.tasks.index(task)

                # =================================================
                # EDIT MODE
                # =================================================

                if st.session_state.editing_task == task_index:

                    st.markdown(
                        '<div class="todo-card">',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div class="todo-title">Edit Task</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div class="todo-divider"></div>',
                        unsafe_allow_html=True
                    )

                    edited_title = st.text_input(
                        "Task Title",
                        value=task["title"],
                        key=f"edit_title_{task_index}"
                    )

                    st.markdown("Sub Tasks")

                    edited_subtasks = []

                    for sub_index, subtask in enumerate(task["subtasks"]):

                        edited_text = st.text_input(
                            f"Sub Task {sub_index + 1}",
                            value=subtask["text"],
                            key=f"edit_subtask_{task_index}_{sub_index}"
                        )

                        edited_subtasks.append({
                            "text": edited_text,
                            "done": subtask["done"]
                        })

                    new_edit_subtask = st.text_input(
                        "Add another sub task",
                        placeholder="Optional",
                        key=f"edit_new_subtask_{task_index}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save Changes",
                            key=f"save_edit_{task_index}",
                            use_container_width=True
                        ):

                            if edited_title.strip():
                                task["title"] = edited_title.strip()

                            task["subtasks"] = [
                                subtask
                                for subtask in edited_subtasks
                                if subtask["text"].strip()
                            ]

                            if new_edit_subtask.strip():
                                task["subtasks"].append({
                                    "text": new_edit_subtask.strip(),
                                    "done": False
                                })

                            if (
                                len(task["subtasks"]) > 0
                                and all(
                                    subtask["done"]
                                    for subtask in task["subtasks"]
                                )
                            ):

                                task["done"] = True

                                if not task["completed"]:
                                    task["completed"] = (
                                        datetime.now().strftime("%Y-%m-%d")
                                    )

                            else:

                                task["done"] = False
                                task["completed"] = None

                            st.session_state.editing_task = None
                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"cancel_edit_{task_index}",
                            use_container_width=True
                        ):
                            st.session_state.editing_task = None
                            rng_rerun()

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

                    continue

                # =================================================
                # CARD TITLE
                # =================================================

                if task["done"]:
                    card_class = "todo-card-done"
                else:
                    card_class = "todo-card"

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="todo-title">
                            {task["title"]}
                        </div>
                        <div class="todo-divider"></div>
                    """,
                    unsafe_allow_html=True
                )


                # =================================================
                # MAIN TASK CHECKBOX
                # =================================================

                main_done = st.checkbox(
                    "Task completed",
                    value=task["done"],
                    key=f"main_checkbox_{task_index}"
                )

                if main_done != task["done"]:

                    task["done"] = main_done

                    if main_done:
                        task["completed"] = datetime.now().strftime(
                            "%Y-%m-%d"
                        )
                    else:
                        task["completed"] = None

                    rng_rerun()

                # =================================================
                # SUBTASKS
                # =================================================

                st.markdown(
                    '<div class="todo-divider"></div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="todo-section-title">Sub Tasks</div>',
                    unsafe_allow_html=True
                )

                for sub_index, subtask in enumerate(task["subtasks"]):

                    sub_done = st.checkbox(
                        subtask["text"],
                        value=subtask["done"],
                        key=f"sub_checkbox_{task_index}_{sub_index}"
                    )

                    if sub_done != subtask["done"]:

                        subtask["done"] = sub_done

                        if (
                            len(task["subtasks"]) > 0
                            and all(
                                item["done"]
                                for item in task["subtasks"]
                            )
                        ):

                            task["done"] = True
                            task["completed"] = (
                                datetime.now().strftime("%Y-%m-%d")
                            )

                        else:

                            task["done"] = False
                            task["completed"] = None

                        rng_rerun()

                # =================================================
                # DATES
                # =================================================

                st.markdown(
                    '<div class="todo-divider"></div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="todo-date">
                        Created: {task["created"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if task["completed"]:

                    st.markdown(
                        f"""
                        <div class="todo-completed">
                            Completed: {task["completed"]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.markdown(
                        """
                        <div class="todo-date">
                            Completed: -
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # =================================================
                # CLOSE CARD
                # =================================================

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

                # =================================================
                # EDIT BUTTON
                # =================================================

                if st.button(
                    "Edit",
                    key=f"edit_button_{task_index}",
                    use_container_width=True
                ):

                    st.session_state.editing_task = task_index
                    rng_rerun()



elif page == "Meeting Minutes":

    if "meeting_cards" not in st.session_state:
        st.session_state.meeting_cards = []

    if "selected_meeting" not in st.session_state:
        st.session_state.selected_meeting = None

    if "editing_meeting" not in st.session_state:
        st.session_state.editing_meeting = None

    if "deleting_meeting" not in st.session_state:
        st.session_state.deleting_meeting = None

    if "adding_meeting" not in st.session_state:
        st.session_state.adding_meeting = False

    # =========================================================
    # MEETING DETAIL PAGE
    # =========================================================

    if st.session_state.selected_meeting is not None:

        meeting_name = st.session_state.selected_meeting

        if st.button(
            "Back to Meeting Minutes",
            key="back_to_meetings"
        ):
            st.session_state.selected_meeting = None
            rng_rerun()

        st.markdown(
            f'<div class="dashboard-title">{meeting_name}</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="dashboard-subtitle">Meeting records</div>',
            unsafe_allow_html=True
        )

        # =====================================================
        # MEETING TABLE DATA
        # =====================================================

        meeting_key = "meeting_data_" + meeting_name

        if meeting_key not in st.session_state:
            st.session_state[meeting_key] = [
                ["", "", "", "", "", ""]
                for _ in range(11)
            ]
        else:
            st.session_state[meeting_key] = (
                st.session_state[meeting_key][:11]
            )

            while len(st.session_state[meeting_key]) < 11:
                st.session_state[meeting_key].append(
                    ["", "", "", "", "", ""]
                )

        # =====================================================
        # TABLE CSS
        # =====================================================

        st.markdown("""
        <style>

        .meeting-table-container {
            width: 100%;
            max-width: 1123px;
            margin: 20px auto 0 auto;
            direction: rtl;
        }

        .meeting-grid-header {
            background-color: #172333;
            color: white;
            border: 1px solid #cfd6df;
            min-height: 45px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            text-align: center;
            direction: rtl;
            box-sizing: border-box;
            margin: 0 !important;
            padding: 4px;
            overflow-wrap: anywhere;
        }

        div[data-testid="stTextInput"],
        div[data-testid="stSelectbox"] {
            margin: 0 !important;
            padding: 0 !important;
            min-width: 0 !important;
        }

        div[data-testid="stTextInput"] > div,
        div[data-testid="stSelectbox"] > div {
            margin: 0 !important;
            padding: 0 !important;
            min-width: 0 !important;
        }

        div[data-testid="stTextInput"] input {
            border-radius: 0 !important;
            border: 1px solid #cfd6df !important;
            min-height: 42px !important;
            height: 42px !important;
            font-size: 13px !important;
            text-align: right !important;
            direction: rtl !important;
            box-sizing: border-box !important;
            margin: 0 !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            border-radius: 0 !important;
            border: 1px solid #cfd6df !important;
            min-height: 42px !important;
            height: 42px !important;
            font-size: 12px !important;
            box-sizing: border-box !important;
            margin: 0 !important;
            padding-left: 2px !important;
            padding-right: 2px !important;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] * {
            font-size: 12px !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border: 2px solid #6b7c93 !important;
            outline: none !important;
        }

        div[data-testid="column"] {
            padding-left: 0 !important;
            padding-right: 0 !important;
            min-width: 0 !important;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0 !important;
        }

        .meeting-table-a4 {
            width: 100%;
            max-width: 1123px;
            margin: 20px auto 0 auto;
            direction: rtl;
        }

        /* A4 LANDSCAPE TABLE */

        .st-key-meeting_a4_table {
            width: 297mm !important;
            min-width: 297mm !important;
            max-width: none !important;
            height: 210mm !important;
            margin: 20px auto 0 auto;
        }

        .st-key-meeting_a4_table [data-testid="stVerticalBlock"],
        .st-key-meeting_a4_table [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
        }

        .st-key-meeting_a4_table [data-testid="stHorizontalBlock"] {
            height: 17.5mm !important;
            min-height: 17.5mm !important;
        }

        .st-key-meeting_a4_table .meeting-grid-header {
            height: 17.5mm !important;
            min-height: 17.5mm !important;
        }

        .st-key-meeting_a4_table div[data-testid="stTextInput"] input,
        .st-key-meeting_a4_table div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
            height: 17.5mm !important;
            min-height: 17.5mm !important;
        }

        @media (max-width: 768px) {

            .meeting-table-container {
                width: 100%;
                overflow-x: auto;
            }

            .meeting-grid-header {
                font-size: 11px;
                min-height: 42px;
            }

            div[data-testid="stTextInput"] input {
                font-size: 12px !important;
                min-height: 40px !important;
                height: 40px !important;
            }

            div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
                min-height: 40px !important;
                height: 40px !important;
            }
        }

        @page {
            size: A4 landscape;
            margin: 0;
        }

        @media print {
            .st-key-meeting_a4_table {
                margin: 0 !important;
            }
        }

        </style>
        """, unsafe_allow_html=True)

        # =====================================================
        # TABLE HEADERS
        # =====================================================

        headers = [
            "Agenda",
            "Title",
            "Person in charge",
            "Status",
            "Minute",
            "Status"
        ]

        # Keep the baseline column proportions.

        widths = [
            1.0,
            2.4,
            1.0,
            1.0,
            1.0,
            2.4
        ]

        # =====================================================
        # A4 TABLE CONTAINER
        # =====================================================

        with st.container(key="meeting_a4_table"):

            # -------------------------------------------------
            # HEADER ROW
            # -------------------------------------------------

            header_columns = st.columns(widths, gap=None)

            for col, header in zip(
                header_columns,
                reversed(headers)
            ):

                with col:
                    st.markdown(
                        f'<div class="meeting-grid-header">{header}</div>',
                        unsafe_allow_html=True
                    )

            # -------------------------------------------------
            # 11 EDITABLE DATA ROWS
            # -------------------------------------------------

            for row in range(11):

                row_columns = st.columns(widths, gap=None)

                column_order = [5, 4, 3, 2, 1, 0]

                for col, data_col in zip(
                    row_columns,
                    column_order
                ):

                    with col:

                        current_value = st.session_state[
                            meeting_key
                        ][row][data_col]

                        # -------------------------------------
                        # FIRST STATUS DROPDOWN
                        # -------------------------------------

                        if data_col == 3:

                            options = [
                                "Raised",
                                "not Raised"
                            ]

                            if current_value not in options:
                                selected_index = 0
                            else:
                                selected_index = options.index(
                                    current_value
                                )

                            new_value = st.selectbox(
                                "First Status",
                                options=options,
                                index=selected_index,
                                key=(
                                    f"{meeting_key}_select_"
                                    f"{row}_{data_col}"
                                ),
                                label_visibility="collapsed"
                            )

                        # -------------------------------------
                        # SECOND STATUS DROPDOWN
                        # -------------------------------------

                        elif data_col == 5:

                            options = [
                                "Done",
                                "not Started",
                                "In Progress",
                                "Stopped"
                            ]

                            if current_value not in options:
                                selected_index = 0
                            else:
                                selected_index = options.index(
                                    current_value
                                )

                            new_value = st.selectbox(
                                "Last Status",
                                options=options,
                                index=selected_index,
                                key=(
                                    f"{meeting_key}_select_"
                                    f"{row}_{data_col}"
                                ),
                                label_visibility="collapsed"
                            )

                        # -------------------------------------
                        # EDITABLE TEXT CELLS
                        # -------------------------------------

                        else:

                            new_value = st.text_input(
                                "",
                                value=current_value,
                                key=(
                                    f"{meeting_key}_cell_"
                                    f"{row}_{data_col}"
                                ),
                                label_visibility="collapsed"
                            )

                        st.session_state[
                            meeting_key
                        ][row][data_col] = new_value

        # =====================================================
        # PDF GENERATION
        # =====================================================

        import io
        import os
        import re
        import arabic_reshaper

        from bidi.algorithm import get_display

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        def create_meeting_pdf(meeting_data):

            buffer = io.BytesIO()

            page_width, page_height = landscape(A4)

            pdf = canvas.Canvas(
                buffer,
                pagesize=(page_width, page_height)
            )

            # -------------------------------------------------
            # PDF FONT SUPPORT
            # -------------------------------------------------

            font_name = rng_pdf_font_name()

            # -------------------------------------------------
            # PAGE AND TABLE DIMENSIONS
            # -------------------------------------------------

            margin_x = 7 * mm
            margin_y = 7 * mm

            table_width = page_width - 2 * margin_x
            table_height = page_height - 2 * margin_y

            number_of_rows = 12

            row_height = table_height / number_of_rows

            column_ratios = [
                1.0,
                2.4,
                1.0,
                1.0,
                1.0,
                2.4
            ]

            ratio_total = sum(column_ratios)

            column_widths = [
                table_width * ratio / ratio_total
                for ratio in column_ratios
            ]

            column_order = [5, 4, 3, 2, 1, 0]

            pdf_headers = [
                "Status",
                "Minute",
                "Status",
                "Person in charge",
                "Title",
                "Agenda"
            ]

            # -------------------------------------------------
            # PERSIAN AND ENGLISH TEXT SUPPORT
            # -------------------------------------------------

            def format_text(value):

                value = str(
                    value if value is not None else ""
                )

                return get_display(
                    arabic_reshaper.reshape(value)
                )

            def text_width(value, font_size):

                return rng_pdf_width(format_text(value), font_size)

            # -------------------------------------------------
            # WRAP TEXT INTO CELL
            # -------------------------------------------------

            def wrap_text(value, max_width, font_size):

                value = str(
                    value if value is not None else ""
                ).strip()

                words = re.split(r"\s+", value)

                lines = []
                current_line = ""

                for word in words:

                    if not word:
                        continue

                    candidate = (
                        current_line + " " + word
                        if current_line
                        else word
                    )

                    if text_width(
                        candidate,
                        font_size
                    ) <= max_width:

                        current_line = candidate

                    else:

                        if current_line:
                            lines.append(current_line)

                        # Split oversized words so they cannot
                        # cross the cell's right border.

                        current_line = ""

                        for character in word:

                            candidate = current_line + character

                            if (
                                current_line
                                and text_width(
                                    candidate,
                                    font_size
                                ) > max_width
                            ):

                                lines.append(current_line)
                                current_line = character

                            else:
                                current_line = candidate

                if current_line:
                    lines.append(current_line)

                return lines or [""]

            # -------------------------------------------------
            # DRAW TEXT IN CELL
            # -------------------------------------------------

            def draw_cell_text(
                value,
                x,
                y,
                width,
                height,
                is_header=False
            ):

                padding = 4

                available_width = max(
                    width - 2 * padding,
                    1
                )

                font_size = 9.0

                while font_size > 6.0:

                    lines = wrap_text(
                        value,
                        available_width,
                        font_size
                    )

                    line_height = font_size * 1.3

                    if (
                        len(lines) * line_height
                        <= height - 2 * padding
                    ):
                        break

                    font_size -= 0.5

                lines = wrap_text(
                    value,
                    available_width,
                    font_size
                )

                line_height = font_size * 1.3

                max_lines = max(
                    1,
                    int(
                        (height - 2 * padding)
                        / line_height
                    )
                )

                # A fixed A4 table cannot fit unlimited text.
                # Truncate overflow with an ellipsis.

                if len(lines) > max_lines:

                    lines = lines[:max_lines]

                    last_line = lines[-1]

                    while (
                        last_line
                        and text_width(
                            last_line + "...",
                            font_size
                        ) > available_width
                    ):
                        last_line = last_line[:-1]

                    lines[-1] = last_line + "..."

                pdf.setFont(font_name, font_size)

                if is_header:
                    pdf.setFillColorRGB(1, 1, 1)
                else:
                    pdf.setFillColorRGB(
                        0.12,
                        0.17,
                        0.23
                    )

                text_height = len(lines) * line_height

                baseline = (
                    y
                    + (height + text_height) / 2
                    - line_height
                    + 2
                )

                for line in lines:

                    rendered = format_text(line)

                    rng_pdf_draw(pdf, rendered, x + width / 2, baseline, font_size, "center")

                    baseline -= line_height

            # -------------------------------------------------
            # DRAW TABLE HEADER
            # -------------------------------------------------

            current_y = (
                page_height
                - margin_y
                - row_height
            )

            current_x = margin_x

            for column_index, header in enumerate(
                pdf_headers
            ):

                cell_width = column_widths[column_index]

                pdf.setFillColorRGB(
                    23 / 255,
                    35 / 255,
                    51 / 255
                )

                pdf.rect(
                    current_x,
                    current_y,
                    cell_width,
                    row_height,
                    fill=1,
                    stroke=0
                )

                draw_cell_text(
                    header,
                    current_x,
                    current_y,
                    cell_width,
                    row_height,
                    is_header=True
                )

                current_x += cell_width

            # -------------------------------------------------
            # DRAW 11 EDITABLE DATA ROWS
            # -------------------------------------------------

            for row_index in range(11):

                current_y = (
                    page_height
                    - margin_y
                    - row_height * (row_index + 2)
                )

                current_x = margin_x

                for column_index, data_col in enumerate(
                    column_order
                ):

                    cell_width = column_widths[column_index]

                    value = meeting_data[
                        row_index
                    ][data_col]

                    if data_col == 3 and not value:
                        value = "Raised"

                    if data_col == 5 and not value:
                        value = "Done"

                    pdf.setFillColorRGB(1, 1, 1)

                    pdf.rect(
                        current_x,
                        current_y,
                        cell_width,
                        row_height,
                        fill=1,
                        stroke=0
                    )

                    draw_cell_text(
                        value,
                        current_x,
                        current_y,
                        cell_width,
                        row_height
                    )

                    current_x += cell_width

            # -------------------------------------------------
            # DRAW TABLE BORDERS
            # -------------------------------------------------

            pdf.setStrokeColorRGB(
                0.72,
                0.76,
                0.81
            )

            pdf.setLineWidth(0.45)

            for row_number in range(number_of_rows + 1):

                y = (
                    page_height
                    - margin_y
                    - row_number * row_height
                )

                pdf.line(
                    margin_x,
                    y,
                    margin_x + table_width,
                    y
                )

            x = margin_x

            pdf.line(
                x,
                margin_y,
                x,
                margin_y + table_height
            )

            for cell_width in column_widths:

                x += cell_width

                pdf.line(
                    x,
                    margin_y,
                    x,
                    margin_y + table_height
                )

            # -------------------------------------------------
            # COMPLETE SINGLE-PAGE PDF
            # -------------------------------------------------

            pdf.showPage()
            pdf.save()

            buffer.seek(0)

            return buffer.getvalue()

        # =====================================================
        # PDF DOWNLOAD BUTTON
        # =====================================================

        st.markdown("---")

        try:

            pdf_bytes = create_meeting_pdf(
                st.session_state[meeting_key]
            )

            safe_meeting_name = re.sub(
                r'[^\w.-]+',
                "_",
                meeting_name
            )

            st.download_button(
                label="Download Meeting Table (A4 PDF)",
                data=pdf_bytes,
                file_name=(
                    f"Meeting_Minutes_{safe_meeting_name}.pdf"
                ),
                mime="application/pdf",
                key="download_meeting_pdf",
                use_container_width=True
            )

        except Exception as error:

            st.error(
                f"Unable to generate the meeting PDF: {error}"
            )

    # =========================================================
    # MEETING MINUTES MAIN PAGE
    # =========================================================

    else:

        st.markdown(
            '<div class="dashboard-title">Meeting Minutes</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="dashboard-subtitle">'
            'Manage and review your meeting records'
            '</div>',
            unsafe_allow_html=True
        )

        # =====================================================
        # MEETING CARD CSS
        # =====================================================

        st.markdown("""
        <style>

        .meeting-card {
            background: white;
            border: 1px solid #e3e7ed;
            border-radius: 14px;
            padding: 24px;
            min-height: 120px;
            box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
            margin-bottom: 10px;
        }

        .meeting-card-title {
            font-size: 18px;
            font-weight: 650;
            color: #172333;
        }

        .meeting-card-text {
            font-size: 13px;
            color: #7b8794;
            margin-top: 6px;
        }

        .delete-warning {
            background: #fff4f4;
            border: 1px solid #f0caca;
            border-radius: 10px;
            padding: 12px;
            margin-top: 8px;
            margin-bottom: 8px;
            color: #7a1f1f;
            font-size: 14px;
            font-weight: 600;
        }

        .delete-warning * {
            color: #7a1f1f !important;
        }

        div[data-testid="stButton"] button {
            font-size: 13px;
            padding: 4px 8px;
            min-height: 36px;
        }

        @media (max-width: 768px) {

            .meeting-card {
                min-height: 100px;
                padding: 18px;
            }

        }

        </style>
        """, unsafe_allow_html=True)

        # =====================================================
        # ADD MEETING
        # =====================================================

        if st.session_state.adding_meeting:

            st.markdown(
                '<div class="section-title">Add New Meeting</div>',
                unsafe_allow_html=True
            )

            new_meeting_title = st.text_input(
                "Meeting title",
                placeholder="Enter meeting title",
                key="new_meeting_title"
            )

            add_col1, add_col2 = st.columns(2)

            with add_col1:

                if st.button(
                    "Add Meeting",
                    key="add_meeting_confirm",
                    use_container_width=True
                ):

                    if new_meeting_title.strip():

                        st.session_state.meeting_cards.append(
                            new_meeting_title.strip()
                        )

                        st.session_state.adding_meeting = False
                        rng_rerun()

            with add_col2:

                if st.button(
                    "Cancel",
                    key="add_meeting_cancel",
                    use_container_width=True
                ):

                    st.session_state.adding_meeting = False
                    rng_rerun()

        else:

            if st.button(
                "+ Add Meeting",
                key="add_meeting_button",
                use_container_width=False
            ):

                st.session_state.adding_meeting = True
                rng_rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # =====================================================
        # MEETING CARDS
        # =====================================================

        cols = st.columns(3)

        for i, meeting in enumerate(
            st.session_state.meeting_cards
        ):

            with cols[i % 3]:

                # -------------------------------------------------
                # DELETE CONFIRMATION
                # -------------------------------------------------

                if st.session_state.deleting_meeting == i:

                    st.markdown(
                        f"""
                        <div class="meeting-card">
                            <div class="meeting-card-title">
                                {meeting}
                            </div>
                            <div class="meeting-card-text">
                                Meeting records
                            </div>
                        </div>

                        <div class="delete-warning">
                            Are you sure you want to delete "{meeting}"?
                            This cannot be undone.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:

                        if st.button(
                            "Confirm Delete",
                            key=f"confirm_delete_{i}",
                            use_container_width=True
                        ):

                            st.session_state.meeting_cards.pop(i)

                            st.session_state.deleting_meeting = None

                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"cancel_delete_{i}",
                            use_container_width=True
                        ):

                            st.session_state.deleting_meeting = None

                            rng_rerun()

                # -------------------------------------------------
                # EDIT MODE
                # -------------------------------------------------

                elif st.session_state.editing_meeting == i:

                    new_title = st.text_input(
                        "Meeting title",
                        value=meeting,
                        key=f"meeting_edit_input_{i}"
                    )

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:

                        if st.button(
                            "Save",
                            key=f"meeting_save_{i}",
                            use_container_width=True
                        ):

                            if new_title.strip():

                                st.session_state.meeting_cards[i] = (
                                    new_title.strip()
                                )

                                st.session_state.editing_meeting = None

                                rng_rerun()

                    with edit_col2:

                        if st.button(
                            "Cancel",
                            key=f"meeting_cancel_{i}",
                            use_container_width=True
                        ):

                            st.session_state.editing_meeting = None

                            rng_rerun()

                # -------------------------------------------------
                # NORMAL MODE
                # -------------------------------------------------

                else:

                    st.markdown(
                        f"""
                        <div class="meeting-card">
                            <div class="meeting-card-title">
                                {meeting}
                            </div>
                            <div class="meeting-card-text">
                                Meeting records
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    button_col1, button_col2, button_col3 = st.columns(3)

                    with button_col1:

                        open_button = st.button(
                            "Open",
                            key=f"meeting_open_{i}",
                            use_container_width=True
                        )

                    with button_col2:

                        edit_button = st.button(
                            "Edit",
                            key=f"meeting_edit_{i}",
                            use_container_width=True
                        )

                    with button_col3:

                        delete_button = st.button(
                            "Delete",
                            key=f"meeting_delete_{i}",
                            use_container_width=True
                        )

                    if open_button:

                        st.session_state.selected_meeting = meeting

                        rng_rerun()

                    if edit_button:

                        st.session_state.editing_meeting = i

                        rng_rerun()

                    if delete_button:

                        st.session_state.deleting_meeting = i

                        rng_rerun()






elif page == "Warehouse":

    import io
    import os
    import re
    import zipfile
    import hashlib
    import xml.etree.ElementTree as ET

    from pathlib import Path
    from uuid import uuid4
    from html import escape

    # =========================================================
    # ORIGINAL EXCEL TEMPLATE
    # =========================================================

    WAREHOUSE_TEMPLATE = (
        Path(__file__).resolve().parent
        / "\u0641\u0631\u0645 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u06a9\u0627\u0644\u0627.xlsx"
    )

    def load_warehouse_template():

        if not WAREHOUSE_TEMPLATE.is_file():
            raise FileNotFoundError(
                "Warehouse Excel template not found: "
                + str(WAREHOUSE_TEMPLATE)
            )

        ns = {
            "x": (
                "http://schemas.openxmlformats.org/"
                "spreadsheetml/2006/main"
            )
        }

        with zipfile.ZipFile(WAREHOUSE_TEMPLATE) as z:

            strings_xml = ET.fromstring(
                z.read("xl/sharedStrings.xml")
            )

            strings = []

            for item in strings_xml.findall("x:si", ns):
                value = "".join(
                    element.text or ""
                    for element in item.findall(".//x:t", ns)
                )
                strings.append(value)

            logo = z.read("xl/media/image1.png")

        if len(strings) < 10:
            raise ValueError(
                "The original Excel form labels are missing."
            )

        date_number_labels = strings[5].splitlines()
        defaults = strings[9].splitlines()
        requester_lines = strings[8].splitlines()

        return {
            "headers": strings[0:5],
            "date_label": date_number_labels[0],
            "number_label": date_number_labels[1],
            "title": strings[6],
            "approver_label": strings[7].split(":")[0] + ":",
            "requester_label": requester_lines[0],
            "signature_label": "\u0627\u0645\u0636\u0627",
            "default_requester": requester_lines[1].strip(),
            "default_date": defaults[0].strip(),
            "default_number": defaults[1].strip(),
            "logo": logo
        }

    warehouse_template = None
    template_error = None

    try:
        warehouse_template = load_warehouse_template()
    except Exception as error:
        template_error = str(error)

    # =========================================================
    # SESSION STATE
    # =========================================================

    if "warehouse_cards" not in st.session_state:
        st.session_state.warehouse_cards = []

    if "selected_warehouse" not in st.session_state:
        st.session_state.selected_warehouse = None

    if "editing_warehouse" not in st.session_state:
        st.session_state.editing_warehouse = None

    if "deleting_warehouse" not in st.session_state:
        st.session_state.deleting_warehouse = None

    if "adding_warehouse" not in st.session_state:
        st.session_state.adding_warehouse = False

    if "warehouse_card_ids" not in st.session_state:
        st.session_state.warehouse_card_ids = [
            uuid4().hex
            for _ in st.session_state.warehouse_cards
        ]

    if "warehouse_forms" not in st.session_state:
        st.session_state.warehouse_forms = {}

    while len(st.session_state.warehouse_card_ids) < len(
        st.session_state.warehouse_cards
    ):
        st.session_state.warehouse_card_ids.append(
            uuid4().hex
        )

    # =========================================================
    # EMPTY WAREHOUSE FORM
    # =========================================================

    def create_empty_warehouse_form():

        return {
            "date": "",
            "number": "",
            "items": [
                ["", "", "", "", ""]
                for _ in range(10)
            ],
            "requester": "",
            "approver": "",
            "requester_signature": "",
            "approver_signature": ""
        }

    # =========================================================
    # WAREHOUSE CSS
    # =========================================================

    st.markdown("""
    <style>

    .warehouse-card {
        background: white;
        border: 1px solid #e3e7ed;
        border-radius: 14px;
        padding: 24px;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
        margin-bottom: 10px;
    }

    .warehouse-card-title {
        font-size: 18px;
        font-weight: 650;
        color: #172333;
    }

    .warehouse-card-text {
        font-size: 13px;
        color: #7b8794;
        margin-top: 6px;
    }

    .warehouse-delete-warning {
        background: #fff4f4;
        border: 1px solid #f0caca;
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #7a1f1f;
        font-size: 14px;
        font-weight: 600;
    }

    .warehouse-form-title {
        text-align: center;
        direction: rtl;
        font-size: 25px;
        font-weight: 700;
        color: #172333;
        margin: 15px 0;
    }

    .warehouse-form-header {
        background: white;
        border: 1px solid #444;
        color: #172333;
        font-size: 13px;
        font-weight: 700;
        min-height: 55px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        direction: rtl;
        unicode-bidi: plaintext;
        padding: 4px;
        box-sizing: border-box;
    }

    /* Warehouse editable table */

    .st-key-warehouse_form_table
    div[data-testid="stHorizontalBlock"] {
        gap: 0 !important;
    }

    .st-key-warehouse_form_table
    div[data-testid="column"] {
        min-width: 0 !important;
        padding: 0 !important;
    }

    .st-key-warehouse_form_table
    div[data-testid="stTextInput"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    .st-key-warehouse_form_table
    input {
        direction: rtl !important;
        text-align: right !important;
        unicode-bidi: plaintext;
        border-radius: 0 !important;
        border: 1px solid #555 !important;
        min-height: 42px !important;
        font-size: 13px !important;
        padding-right: 7px !important;
    }

    /* All Warehouse detail input fields */

    .st-key-warehouse_detail
    input {
        direction: rtl !important;
        text-align: right !important;
        unicode-bidi: plaintext;
    }

    .st-key-warehouse_detail
    div[data-testid="stWidgetLabel"] {
        direction: rtl !important;
        text-align: right !important;
    }

    .st-key-warehouse_detail
    div[data-testid="stWidgetLabel"] p {
        text-align: right !important;
    }

    @media (max-width: 768px) {

        .warehouse-card {
            min-height: 100px;
            padding: 18px;
        }

        .warehouse-form-header {
            font-size: 11px;
        }

    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # A5 LANDSCAPE PDF GENERATOR
    # =========================================================

    def create_warehouse_pdf(form, template):

        import arabic_reshaper
        from bidi.algorithm import get_display

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A5, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import ImageReader

        buffer = io.BytesIO()

        page_width, page_height = landscape(A5)

        pdf = canvas.Canvas(
            buffer,
            pagesize=(page_width, page_height),
            pageCompression=1
        )

        pdf.setTitle(template["title"])

        # =====================================================
        # UNICODE FONT FOR PERSIAN
        # =====================================================

        font_name = rng_pdf_font_name()

        # =====================================================
        # RIGHT-TO-LEFT PERSIAN TEXT
        # =====================================================

        def shape_text(value):

            value = str(
                value if value is not None else ""
            )

            reshaped = arabic_reshaper.reshape(value)

            return get_display(reshaped)

        def text_width(value, size):

            return rng_pdf_width(shape_text(value), size)

        # =====================================================
        # TEXT FITTING INSIDE PDF CELLS
        # =====================================================

        def draw_cell_text(
            value,
            x,
            y,
            width,
            height,
            font_size=9,
            align="right"
        ):

            text = str(
                value if value is not None else ""
            ).strip()

            if not text:
                return

            padding = 3

            available_width = max(
                width - 2 * padding,
                1
            )

            available_height = max(
                height - 2 * padding,
                1
            )

            def make_lines(size):

                lines = []

                for paragraph in text.splitlines():

                    if not paragraph.strip():
                        lines.append("")
                        continue

                    words = paragraph.split()

                    current = ""

                    for word in words:

                        candidate = (
                            current + " " + word
                            if current else word
                        )

                        if text_width(
                            candidate,
                            size
                        ) <= available_width:

                            current = candidate

                        else:

                            if current:
                                lines.append(current)

                            current = ""

                            for character in word:

                                candidate = current + character

                                if (
                                    current
                                    and text_width(
                                        candidate,
                                        size
                                    ) > available_width
                                ):
                                    lines.append(current)
                                    current = character
                                else:
                                    current = candidate

                    if current:
                        lines.append(current)

                return lines or [""]

            size = float(font_size)

            while size > 5:

                lines = make_lines(size)
                line_height = size * 1.3

                if (
                    len(lines) * line_height
                    <= available_height
                ):
                    break

                size -= 0.5

            lines = make_lines(size)
            line_height = size * 1.3

            max_lines = max(
                1,
                int(available_height / line_height)
            )

            if len(lines) > max_lines:

                lines = lines[:max_lines]

                final_line = lines[-1]

                while (
                    final_line
                    and text_width(
                        final_line + "...",
                        size
                    ) > available_width
                ):
                    final_line = final_line[:-1]

                lines[-1] = final_line + "..."

            pdf.saveState()

            clip = pdf.beginPath()

            clip.rect(
                x + 1,
                y + 1,
                max(width - 2, 0),
                max(height - 2, 0)
            )

            pdf.clipPath(
                clip,
                stroke=0,
                fill=0
            )

            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont(font_name, size)

            total_height = len(lines) * line_height

            baseline = (
                y
                + (height + total_height) / 2
                - line_height
                + 2
            )

            for line in lines:

                rendered = shape_text(line)

                if align == "center":

                    rng_pdf_draw(pdf, rendered, x + width / 2, baseline, size, "center")

                elif align == "left":

                    rng_pdf_draw(pdf, rendered, x + padding, baseline, size, "left")

                else:

                    rng_pdf_draw(pdf, rendered, x + width - padding, baseline, size, "right")

                baseline -= line_height

            pdf.restoreState()

        # =====================================================
        # A5 PAGE AND EXCEL DIMENSIONS
        # =====================================================

        margin_x = 6 * mm
        margin_y = 6 * mm

        left = margin_x
        right = page_width - margin_x

        top = page_height - margin_y
        bottom = margin_y

        table_width = right - left
        table_height = top - bottom

        # Same row proportions as the original Excel file.

        excel_row_heights = [
            60,
            42
        ] + [21.75] * 10 + [66]

        height_scale = (
            table_height / sum(excel_row_heights)
        )

        row_heights = [
            height * height_scale
            for height in excel_row_heights
        ]

        # Original A-G Excel widths.

        excel_col_widths = [
            5.85546875,
            17.42578125,
            27.0,
            10.140625,
            15.5703125,
            6.42578125,
            16.7109375
        ]

        width_scale = (
            table_width / sum(excel_col_widths)
        )

        col_widths = [
            width * width_scale
            for width in excel_col_widths
        ]

        # =====================================================
        # RIGHT-TO-LEFT COLUMN COORDINATES
        # =====================================================

        # Excel column A is at the RIGHT.
        # Excel column G is at the LEFT.
        #
        # x_positions[0] = right edge of column A
        # x_positions[7] = left edge of column G

        x_positions = [right]

        for width in col_widths:
            x_positions.append(
                x_positions[-1] - width
            )

        y_positions = [top]

        for height in row_heights:
            y_positions.append(
                y_positions[-1] - height
            )

        pdf.setStrokeColorRGB(0, 0, 0)
        pdf.setLineWidth(0.65)

        # =====================================================
        # DRAW RIGHT-TO-LEFT MERGED CELL
        # =====================================================

        def draw_cell(
            first_col,
            last_col,
            row_index,
            value="",
            font_size=9,
            align="center"
        ):

            # RTL: last column has the smaller X coordinate.

            x = x_positions[last_col + 1]

            width = (
                x_positions[first_col]
                - x_positions[last_col + 1]
            )

            y = y_positions[row_index + 1]
            height = row_heights[row_index]

            pdf.rect(
                x,
                y,
                width,
                height,
                fill=0,
                stroke=1
            )

            draw_cell_text(
                value,
                x,
                y,
                width,
                height,
                font_size=font_size,
                align=align
            )

        # =====================================================
        # ROW 1: LOGO, TITLE, DATE AND NUMBER
        # =====================================================

        # Original Excel:
        # A1:B1 = logo, now on the RIGHT
        # C1:E1 = title, CENTER
        # F1:G1 = date and number, LEFT

        draw_cell(0, 1, 0)

        draw_cell(
            2,
            4,
            0,
            template["title"],
            font_size=16,
            align="center"
        )

        draw_cell(5, 5, 0)
        draw_cell(6, 6, 0)

        # -----------------------------------------------------
        # ORIGINAL EXCEL LOGO AT UPPER-RIGHT
        # -----------------------------------------------------

        logo_reader = ImageReader(
            io.BytesIO(template["logo"])
        )

        logo_x = x_positions[2]
        logo_y = y_positions[1]

        logo_width = x_positions[0] - x_positions[2]
        logo_height = row_heights[0]

        image_width, image_height = logo_reader.getSize()

        logo_scale = min(
            logo_width * 0.94 / image_width,
            logo_height * 0.94 / image_height
        )

        rendered_width = image_width * logo_scale
        rendered_height = image_height * logo_scale

        pdf.drawImage(
            logo_reader,
            logo_x + (logo_width - rendered_width) / 2,
            logo_y + (logo_height - rendered_height) / 2,
            width=rendered_width,
            height=rendered_height,
            preserveAspectRatio=True,
            mask="auto"
        )

        # -----------------------------------------------------
        # DATE AND NUMBER ON LEFT SIDE
        # -----------------------------------------------------

        f_x = x_positions[6]
        f_width = col_widths[5]

        g_x = x_positions[7]
        g_width = col_widths[6]

        half_height = row_heights[0] / 2

        draw_cell_text(
            template["date_label"],
            f_x,
            logo_y + half_height,
            f_width,
            half_height,
            font_size=9,
            align="right"
        )

        draw_cell_text(
            template["number_label"],
            f_x,
            logo_y,
            f_width,
            half_height,
            font_size=9,
            align="right"
        )

        draw_cell_text(
            form["date"],
            g_x,
            logo_y + half_height,
            g_width,
            half_height,
            font_size=9,
            align="right"
        )

        draw_cell_text(
            form["number"],
            g_x,
            logo_y,
            g_width,
            half_height,
            font_size=9,
            align="right"
        )

        # =====================================================
        # ROW 2: TABLE HEADERS, RIGHT TO LEFT
        # =====================================================

        # RIGHT TO LEFT:
        # A = Item code
        # B:C = Description
        # D = Requested quantity
        # E = Usage
        # F:G = Notes

        draw_cell(
            0, 0, 1,
            template["headers"][0],
            font_size=9
        )

        draw_cell(
            1, 2, 1,
            template["headers"][1],
            font_size=10
        )

        draw_cell(
            3, 3, 1,
            template["headers"][2],
            font_size=9
        )

        draw_cell(
            4, 4, 1,
            template["headers"][3],
            font_size=9
        )

        draw_cell(
            5, 6, 1,
            template["headers"][4],
            font_size=10
        )

        # =====================================================
        # ROWS 3-12: TEN DATA ROWS, RIGHT TO LEFT
        # =====================================================

        merged_columns = [
            (0, 0),
            (1, 2),
            (3, 3),
            (4, 4),
            (5, 6)
        ]

        for item_index in range(10):

            excel_row_index = item_index + 2

            for field_index, col_range in enumerate(
                merged_columns
            ):

                draw_cell(
                    col_range[0],
                    col_range[1],
                    excel_row_index,
                    form["items"][item_index][field_index],
                    font_size=8.5,
                    align="right"
                )

        # =====================================================
        # ROW 13: SIGNATURES, RIGHT TO LEFT
        # =====================================================

        footer_row = 12

        # A13:C13 = Requester, RIGHT side
        # D13:G13 = Approver, LEFT side

        draw_cell(0, 2, footer_row)
        draw_cell(3, 6, footer_row)

        footer_y = y_positions[13]
        footer_height = row_heights[12]

        # Requester on RIGHT.

        requester_x = x_positions[3]
        requester_width = (
            x_positions[0] - x_positions[3]
        )

        # Approver on LEFT.

        approver_x = x_positions[7]
        approver_width = (
            x_positions[3] - x_positions[7]
        )

        draw_cell_text(
            template["requester_label"],
            requester_x,
            footer_y + footer_height * 0.70,
            requester_width,
            footer_height * 0.25,
            font_size=10,
            align="right"
        )

        draw_cell_text(
            form["requester"],
            requester_x,
            footer_y + footer_height * 0.43,
            requester_width,
            footer_height * 0.25,
            font_size=10,
            align="right"
        )

        draw_cell_text(
            template["signature_label"] + ": "
            + form["requester_signature"],
            requester_x,
            footer_y + footer_height * 0.05,
            requester_width,
            footer_height * 0.25,
            font_size=9,
            align="right"
        )

        draw_cell_text(
            template["approver_label"],
            approver_x,
            footer_y + footer_height * 0.70,
            approver_width,
            footer_height * 0.25,
            font_size=10,
            align="right"
        )

        draw_cell_text(
            form["approver"],
            approver_x,
            footer_y + footer_height * 0.43,
            approver_width,
            footer_height * 0.25,
            font_size=10,
            align="right"
        )

        draw_cell_text(
            template["signature_label"] + ": "
            + form["approver_signature"],
            approver_x,
            footer_y + footer_height * 0.05,
            approver_width,
            footer_height * 0.25,
            font_size=9,
            align="right"
        )

        # =====================================================
        # FINALIZE PDF
        # =====================================================

        pdf.showPage()
        pdf.save()

        buffer.seek(0)

        return buffer.getvalue()

    # =========================================================
    # WAREHOUSE DETAIL VIEW
    # =========================================================

    selected = st.session_state.selected_warehouse

    if (
        isinstance(selected, int)
        and 0 <= selected < len(st.session_state.warehouse_cards)
    ):

        warehouse_name = st.session_state.warehouse_cards[selected]
        warehouse_id = st.session_state.warehouse_card_ids[selected]

        if warehouse_id not in st.session_state.warehouse_forms:
            st.session_state.warehouse_forms[
                warehouse_id
            ] = create_empty_warehouse_form()

        form = st.session_state.warehouse_forms[warehouse_id]

        if st.button(
            "Back to Warehouse",
            key="warehouse_back"
        ):
            st.session_state.selected_warehouse = None
            rng_rerun()

        st.markdown(
            f'<div class="dashboard-title">{escape(warehouse_name)}</div>',
            unsafe_allow_html=True
        )

        if warehouse_template is None:

            st.error(
                "Unable to load original Excel template: "
                + str(template_error)
            )

        else:

            with st.container(key="warehouse_detail"):

                # =================================================
                # FORM TITLE
                # =================================================

                st.markdown(
                    '<div class="warehouse-form-title">'
                    + escape(warehouse_template["title"])
                    + '</div>',
                    unsafe_allow_html=True
                )

                # =================================================
                # DATE AND NUMBER FIELDS
                # =================================================

                # Right-to-left visual order.
                # Number is rendered in the left column.
                # Date is rendered in the right column.

                info_cols = st.columns(2)

                with info_cols[0]:

                    form["number"] = st.text_input(
                        warehouse_template["number_label"],
                        value=form["number"],
                        key=f"warehouse_number_{warehouse_id}"
                    )

                with info_cols[1]:

                    form["date"] = st.text_input(
                        warehouse_template["date_label"],
                        value=form["date"],
                        key=f"warehouse_date_{warehouse_id}"
                    )

                st.divider()

                # =================================================
                # TABLE HEADERS AND EDITABLE ROWS
                # =================================================

                headers = warehouse_template["headers"]

                # Logical Excel order A to G:
                # Item code, Description, Quantity, Usage, Notes.

                logical_widths = [
                    5.85546875,
                    44.42578125,
                    10.140625,
                    15.5703125,
                    23.13671875
                ]

                # Streamlit creates columns left to right.
                # Reverse the visual order so the first
                # logical Excel field appears at the far right.

                visual_order = [4, 3, 2, 1, 0]

                visual_widths = [
                    logical_widths[index]
                    for index in visual_order
                ]

                with st.container(key="warehouse_form_table"):

                    header_cols = st.columns(
                        visual_widths,
                        gap=None
                    )

                    for visual_index, col in enumerate(
                        header_cols
                    ):

                        data_index = visual_order[visual_index]

                        with col:

                            st.markdown(
                                '<div class="warehouse-form-header">'
                                + escape(headers[data_index])
                                + '</div>',
                                unsafe_allow_html=True
                            )

                    # ---------------------------------------------
                    # TEN EDITABLE ROWS
                    # ---------------------------------------------

                    for row_index in range(10):

                        row_cols = st.columns(
                            visual_widths,
                            gap=None
                        )

                        for visual_index, col in enumerate(
                            row_cols
                        ):

                            data_index = visual_order[visual_index]

                            with col:

                                current_value = form[
                                    "items"
                                ][row_index][data_index]

                                new_value = st.text_input(
                                    (
                                        f"Row {row_index + 1}: "
                                        f"{headers[data_index]}"
                                    ),
                                    value=current_value,
                                    key=(
                                        f"warehouse_{warehouse_id}_"
                                        f"cell_{row_index}_{data_index}"
                                    ),
                                    label_visibility="collapsed"
                                )

                                form["items"][row_index][data_index] = (
                                    new_value
                                )

                # =================================================
                # REQUESTER AND APPROVER FIELDS
                # =================================================

                st.divider()

                footer_cols = st.columns(2)

                # Approver on LEFT.

                with footer_cols[0]:

                    form["approver"] = st.text_input(
                        warehouse_template["approver_label"],
                        value=form["approver"],
                        key=f"warehouse_approver_{warehouse_id}"
                    )

                    form["approver_signature"] = st.text_input(
                        warehouse_template["signature_label"],
                        value=form["approver_signature"],
                        key=f"warehouse_app_sign_{warehouse_id}"
                    )

                # Requester on RIGHT.

                with footer_cols[1]:

                    form["requester"] = st.text_input(
                        warehouse_template["requester_label"],
                        value=form["requester"],
                        key=f"warehouse_requester_{warehouse_id}"
                    )

                    form["requester_signature"] = st.text_input(
                        warehouse_template["signature_label"],
                        value=form["requester_signature"],
                        key=f"warehouse_req_sign_{warehouse_id}"
                    )

                # =================================================
                # DOWNLOAD A5 LANDSCAPE PDF
                # =================================================

                st.divider()

                try:

                    pdf_bytes = create_warehouse_pdf(
                        form,
                        warehouse_template
                    )

                    safe_filename = re.sub(
                        r"[^\w.-]+",
                        "_",
                        warehouse_name
                    )

                    st.download_button(
                        label="Download A5 Landscape PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"Purchase_Request_{safe_filename}.pdf"
                        ),
                        mime="application/pdf",
                        key=f"warehouse_pdf_{warehouse_id}",
                        use_container_width=True
                    )

                except Exception as error:

                    st.error(
                        "Unable to generate the PDF: "
                        + str(error)
                    )

    # =========================================================
    # WAREHOUSE MAIN PAGE
    # =========================================================

    else:

        st.session_state.selected_warehouse = None

        st.markdown(
            '<div class="dashboard-title">Warehouse</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="dashboard-subtitle">'
            'Manage your warehouse records'
            '</div>',
            unsafe_allow_html=True
        )

        # =====================================================
        # ADD NEW WAREHOUSE
        # =====================================================

        if st.session_state.adding_warehouse:

            st.markdown(
                '<div class="section-title">Add New Warehouse</div>',
                unsafe_allow_html=True
            )

            new_title = st.text_input(
                "Warehouse title",
                placeholder="Enter warehouse title",
                key="new_warehouse_title"
            )

            add_col, cancel_col = st.columns(2)

            with add_col:

                if st.button(
                    "Add Warehouse",
                    key="warehouse_add_confirm",
                    use_container_width=True
                ):

                    if new_title.strip():

                        st.session_state.warehouse_cards.append(
                            new_title.strip()
                        )

                        st.session_state.warehouse_card_ids.append(
                            uuid4().hex
                        )

                        st.session_state.adding_warehouse = False

                        rng_rerun()

                    else:

                        st.warning(
                            "Please enter a warehouse title."
                        )

            with cancel_col:

                if st.button(
                    "Cancel",
                    key="warehouse_add_cancel",
                    use_container_width=True
                ):

                    st.session_state.adding_warehouse = False

                    rng_rerun()

        else:

            if st.button(
                "+ Add Warehouse",
                key="warehouse_add_button"
            ):

                st.session_state.adding_warehouse = True

                rng_rerun()

        st.markdown(
            "<br>",
            unsafe_allow_html=True
        )

        # =====================================================
        # WAREHOUSE CARDS
        # =====================================================

        cols = st.columns(3)

        for i, warehouse in enumerate(
            st.session_state.warehouse_cards
        ):

            with cols[i % 3]:

                safe_title = escape(warehouse)

                # =============================================
                # DELETE CONFIRMATION
                # =============================================

                if st.session_state.deleting_warehouse == i:

                    st.markdown(
                        f"""
                        <div class="warehouse-card">
                            <div class="warehouse-card-title">
                                {safe_title}
                            </div>
                            <div class="warehouse-card-text">
                                Warehouse records
                            </div>
                        </div>

                        <div class="warehouse-delete-warning">
                            Are you sure you want to delete
                            "{safe_title}"?
                            This cannot be undone.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:

                        if st.button(
                            "Confirm Delete",
                            key=f"warehouse_confirm_delete_{i}",
                            use_container_width=True
                        ):

                            deleted_id = (
                                st.session_state.warehouse_card_ids.pop(i)
                            )

                            st.session_state.warehouse_cards.pop(i)

                            st.session_state.warehouse_forms.pop(
                                deleted_id,
                                None
                            )

                            st.session_state.deleting_warehouse = None
                            st.session_state.editing_warehouse = None

                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"warehouse_cancel_delete_{i}",
                            use_container_width=True
                        ):

                            st.session_state.deleting_warehouse = None

                            rng_rerun()

                # =============================================
                # EDIT WAREHOUSE TITLE
                # =============================================

                elif st.session_state.editing_warehouse == i:

                    edited_title = st.text_input(
                        "Warehouse title",
                        value=warehouse,
                        key=f"warehouse_edit_input_{i}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save",
                            key=f"warehouse_save_{i}",
                            use_container_width=True
                        ):

                            if edited_title.strip():

                                st.session_state.warehouse_cards[i] = (
                                    edited_title.strip()
                                )

                                st.session_state.editing_warehouse = None

                                rng_rerun()

                            else:

                                st.warning(
                                    "Please enter a warehouse title."
                                )

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"warehouse_edit_cancel_{i}",
                            use_container_width=True
                        ):

                            st.session_state.editing_warehouse = None

                            rng_rerun()

                # =============================================
                # NORMAL WAREHOUSE CARD
                # =============================================

                else:

                    st.markdown(
                        f"""
                        <div class="warehouse-card">
                            <div class="warehouse-card-title">
                                {safe_title}
                            </div>
                            <div class="warehouse-card-text">
                                Warehouse records
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    button_col1, button_col2, button_col3 = st.columns(3)

                    with button_col1:

                        open_button = st.button(
                            "Open",
                            key=f"warehouse_open_{i}",
                            use_container_width=True
                        )

                    with button_col2:

                        edit_button = st.button(
                            "Edit",
                            key=f"warehouse_edit_{i}",
                            use_container_width=True
                        )

                    with button_col3:

                        delete_button = st.button(
                            "Delete",
                            key=f"warehouse_delete_{i}",
                            use_container_width=True
                        )

                    if open_button:

                        st.session_state.selected_warehouse = i

                        rng_rerun()

                    if edit_button:

                        st.session_state.editing_warehouse = i

                        st.session_state.deleting_warehouse = None

                        rng_rerun()

                    if delete_button:

                        st.session_state.deleting_warehouse = i

                        st.session_state.editing_warehouse = None

                        rng_rerun()







elif page == "Mission Report":

    import io
    import re
    import hashlib
    import zipfile

    from pathlib import Path
    from uuid import uuid4
    from html import escape

    # =========================================================
    # ORIGINAL EXCEL TEMPLATE
    # =========================================================

    MISSION_TEMPLATE_PATH = (
        Path(__file__).resolve().parent
        / "\u0641\u0631\u0645 \u06af\u0632\u0627\u0631\u0634 \u0645\u0627\u0645\u0648\u0631\u06cc\u062a.xlsx"
    )

    def load_mission_template():

        from openpyxl import load_workbook

        if not MISSION_TEMPLATE_PATH.is_file():
            raise FileNotFoundError(
                "Excel template not found: "
                + str(MISSION_TEMPLATE_PATH)
            )

        wb = load_workbook(
            MISSION_TEMPLATE_PATH,
            read_only=False,
            data_only=True
        )

        if "RAW" not in wb.sheetnames:
            wb.close()
            raise ValueError("RAW worksheet not found.")

        ws = wb["RAW"]

        cells = {}

        for row in range(1, 14):
            for col in range(1, 9):

                cell = ws.cell(row, col)

                if cell.value is not None:
                    cells[cell.coordinate] = str(cell.value)

        column_widths = [
            ws.column_dimensions[letter].width or 10
            for letter in "ABCDEFGH"
        ]

        row_heights = [
            ws.row_dimensions[row].height or 25
            for row in range(1, 14)
        ]

        wb.close()

        logo = None

        with zipfile.ZipFile(MISSION_TEMPLATE_PATH) as archive:

            images = [
                name for name in archive.namelist()
                if name.startswith("xl/media/")
                and name.lower().endswith(
                    (".png", ".jpg", ".jpeg")
                )
            ]

            if images:
                logo = archive.read(images[0])

        return {
            "cells": cells,
            "column_widths": column_widths,
            "row_heights": row_heights,
            "logo": logo
        }

    mission_template = None
    mission_template_error = None

    try:
        mission_template = load_mission_template()

    except Exception as error:
        mission_template_error = str(error)

    # =========================================================
    # SESSION STATE
    # =========================================================

    if "mission_report_cards" not in st.session_state:
        st.session_state.mission_report_cards = []

    if "selected_mission_report" not in st.session_state:
        st.session_state.selected_mission_report = None

    if "editing_mission_report" not in st.session_state:
        st.session_state.editing_mission_report = None

    if "deleting_mission_report" not in st.session_state:
        st.session_state.deleting_mission_report = None

    if "adding_mission_report" not in st.session_state:
        st.session_state.adding_mission_report = False

    if "mission_report_card_ids" not in st.session_state:
        st.session_state.mission_report_card_ids = [
            uuid4().hex
            for _ in st.session_state.mission_report_cards
        ]

    if "mission_report_forms" not in st.session_state:
        st.session_state.mission_report_forms = {}

    while len(st.session_state.mission_report_card_ids) < len(
        st.session_state.mission_report_cards
    ):
        st.session_state.mission_report_card_ids.append(
            uuid4().hex
        )

    # =========================================================
    # UNICODE-SAFE PERSIAN LABELS
    # =========================================================

    FIELD_LABELS = {
        "report_date": "\u062a\u0627\u0631\u06cc\u062e \u06af\u0632\u0627\u0631\u0634",
        "employee": "\u0646\u0627\u0645 \u0648 \u0646\u0627\u0645 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc",
        "position": "\u067e\u0633\u062a \u0633\u0627\u0632\u0645\u0627\u0646\u06cc",
        "dispatcher": "\u0627\u0639\u0632\u0627\u0645 \u06a9\u0646\u0646\u062f\u0647",
        "city": "\u0634\u0647\u0631 \u0645\u0627\u0645\u0648\u0631\u06cc\u062a",
        "company": "\u0646\u0627\u0645 \u0634\u0631\u06a9\u062a / \u06a9\u0627\u0631\u062e\u0627\u0646\u0647",
        "companions": "\u0647\u0645\u0631\u0627\u0647\u0627\u0646",
        "duration": "\u0645\u062f\u062a \u0645\u0627\u0645\u0648\u0631\u06cc\u062a",
        "start_date": "\u062a\u0627\u0631\u06cc\u062e \u0634\u0631\u0648\u0639",
        "departure_time": "\u0633\u0627\u0639\u062a \u0631\u0641\u062a",
        "end_date": "\u062a\u0627\u0631\u06cc\u062e \u067e\u0627\u06cc\u0627\u0646",
        "return_time": "\u0633\u0627\u0639\u062a \u0628\u0631\u06af\u0634\u062a",
        "transport": "\u0627\u0633\u062a\u0641\u0627\u062f\u0647 \u0627\u0632 \u0648\u0633\u0627\u06cc\u0644 \u0646\u0642\u0644\u06cc\u0647",
        "distance": "\u0645\u0633\u0627\u0641\u062a \u0637\u06cc \u0634\u062f\u0647 (\u06a9\u06cc\u0644\u0648\u0645\u062a\u0631)",
        "equipment": "\u062a\u062c\u0647\u06cc\u0632\u0627\u062a \u0645\u0648\u0631\u062f \u0627\u0633\u062a\u0641\u0627\u062f\u0647",
        "description": "\u0634\u0631\u062d \u0645\u0627\u0645\u0648\u0631\u06cc\u062a",
        "objective": "\u0647\u062f\u0641 \u0645\u0627\u0645\u0648\u0631\u06cc\u062a",
        "result": "\u0646\u062a\u06cc\u062c\u0647 \u0645\u0627\u0645\u0648\u0631\u06cc\u062a",
        "manager_comment": "\u0646\u0638\u0631 \u0645\u062f\u06cc\u0631 / \u0631\u0626\u06cc\u0633 \u0645\u0631\u0628\u0648\u0637\u0647",
        "manager_signature": "\u0627\u0645\u0636\u0627\u06cc \u0645\u062f\u06cc\u0631",
        "employee_signature": "\u0627\u0645\u0636\u0627\u06cc \u0645\u0627\u0645\u0648\u0631"
    }

    # =========================================================
    # UNICODE-SAFE SECTION HEADINGS
    # =========================================================

    MISSION_HEADINGS = {
        "title": (
            "\u0641\u0631\u0645 \u06af\u0632\u0627\u0631\u0634 "
            "\u0645\u0627\u0645\u0648\u0631\u06cc\u062a"
        ),
        "schedule": (
            "\u0632\u0645\u0627\u0646 \u0628\u0646\u062f\u06cc "
            "\u0645\u0627\u0645\u0648\u0631\u06cc\u062a"
        ),
        "transport": (
            "\u0627\u0637\u0644\u0627\u0639\u0627\u062a "
            "\u062d\u0645\u0644 \u0648 \u0646\u0642\u0644"
        ),
        "description": (
            "\u0634\u0631\u062d \u0627\u062c\u0631\u0627\u06cc "
            "\u0645\u0627\u0645\u0648\u0631\u06cc\u062a "
            "\u0648 \u0647\u062f\u0641 \u0622\u0646"
        ),
        "manager": (
            "\u0627\u06cc\u0646 \u0642\u0633\u0645\u062a "
            "\u062a\u0648\u0633\u0637 \u0645\u062f\u06cc\u0631 "
            "\u0645\u0631\u0628\u0648\u0637\u0647 "
            "\u062a\u06a9\u0645\u06cc\u0644 \u06af\u0631\u062f\u062f."
        )
    }

    # =========================================================
    # FORM DATA
    # =========================================================

    def create_empty_mission_form():

        return {
            field: ""
            for field in FIELD_LABELS
        }

    # =========================================================
    # CSS
    # =========================================================

    st.markdown("""
    <style>

    .mission-report-card {
        background: white;
        border: 1px solid #e3e7ed;
        border-radius: 14px;
        padding: 24px;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
        margin-bottom: 10px;
    }

    .mission-report-card-title {
        font-size: 18px;
        font-weight: 650;
        color: #172333;
    }

    .mission-report-card-text {
        font-size: 13px;
        color: #7b8794;
        margin-top: 6px;
    }

    .mission-report-delete-warning {
        background: #fff4f4;
        border: 1px solid #f0caca;
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #7a1f1f;
        font-size: 14px;
        font-weight: 600;
    }

    .mission-form-heading {
        font-size: 25px;
        font-weight: 700;
        color: #172333;
        text-align: center;
        direction: rtl;
        margin: 12px 0 25px;
    }

    .mission-section-heading {
        background: #edf0f4;
        border: 1px solid #cfd6df;
        border-radius: 8px;
        padding: 12px;
        font-size: 16px;
        font-weight: 700;
        color: #172333;
        direction: rtl;
        text-align: right;
        margin: 18px 0 12px;
    }

    /* Visible Persian field labels */

    .st-key-mission_detail
    div[data-testid="stWidgetLabel"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        justify-content: flex-end !important;
        direction: rtl !important;
    }

    .st-key-mission_detail
    div[data-testid="stWidgetLabel"] p {
        color: #172333 !important;
        font-weight: 650 !important;
        font-size: 15px !important;
        direction: rtl !important;
        text-align: right !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    .st-key-mission_detail input,
    .st-key-mission_detail textarea {
        direction: rtl !important;
        text-align: right !important;
        color: #172333 !important;
        background-color: #ffffff !important;
        font-size: 15px !important;
        unicode-bidi: plaintext;
    }

    .st-key-mission_detail input::placeholder,
    .st-key-mission_detail textarea::placeholder {
        color: #788596 !important;
        opacity: 1 !important;
    }

    @media (max-width: 768px) {

        .mission-report-card {
            min-height: 100px;
            padding: 18px;
        }

        .mission-form-heading {
            font-size: 20px;
        }

    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # PDF GENERATOR
    # =========================================================

    def create_mission_pdf(form, template):

        import arabic_reshaper

        from bidi.algorithm import get_display

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import ImageReader

        buffer = io.BytesIO()

        pdf = canvas.Canvas(
            buffer,
            pagesize=A4,
            pageCompression=1
        )

        page_width, page_height = A4

        pdf.setTitle(
            template["cells"].get(
                "C1",
                MISSION_HEADINGS["title"]
            )
        )

        # =====================================================
        # PERSIAN FONT SELECTION
        # =====================================================

        font_name = rng_pdf_font_name()

        def shape_text(value):
            value = str(value if value is not None else "")
            return get_display(arabic_reshaper.reshape(value))

        # =====================================================
        # PDF DIMENSIONS - A4 PORTRAIT
        # =====================================================

        margin_x = 7 * mm
        margin_y = 7 * mm

        left = margin_x
        right = page_width - margin_x

        top = page_height - margin_y
        bottom = margin_y

        usable_width = right - left
        usable_height = top - bottom

        col_source = template["column_widths"]
        row_source = template["row_heights"]

        col_total = sum(col_source)
        row_total = sum(row_source)

        col_widths = [
            usable_width * width / col_total
            for width in col_source
        ]

        row_heights = [
            usable_height * height / row_total
            for height in row_source
        ]

        # -----------------------------------------------------
        # RIGHT-TO-LEFT COORDINATES
        # -----------------------------------------------------

        x_edges = [right]

        for width in col_widths:
            x_edges.append(
                x_edges[-1] - width
            )

        y_edges = [top]

        for height in row_heights:
            y_edges.append(
                y_edges[-1] - height
            )

        # =====================================================
        # PDF TEXT HANDLING
        # =====================================================

        def text_width(value, size):

            return rng_pdf_width(shape_text(value), size)

        def wrap_text(value, max_width, size):

            lines = []

            for paragraph in str(value).splitlines():

                if not paragraph.strip():
                    lines.append("")
                    continue

                current = ""

                for word in paragraph.split():

                    candidate = (
                        current + " " + word
                        if current else word
                    )

                    if text_width(
                        candidate,
                        size
                    ) <= max_width:

                        current = candidate

                    else:

                        if current:
                            lines.append(current)

                        current = ""

                        for character in word:

                            candidate = current + character

                            if (
                                current
                                and text_width(
                                    candidate,
                                    size
                                ) > max_width
                            ):

                                lines.append(current)
                                current = character

                            else:
                                current = candidate

                if current:
                    lines.append(current)

            return lines or [""]

        # =====================================================
        # DRAW PDF TEXT
        # =====================================================

        def draw_text(
            value,
            x,
            y,
            width,
            height,
            size=10,
            align="right"
        ):

            text = str(
                value if value is not None else ""
            ).strip()

            if not text:
                return

            padding = 3

            max_width = max(
                width - 2 * padding,
                1
            )

            max_height = max(
                height - 2 * padding,
                1
            )

            font_size = float(size)

            while font_size > 5:

                lines = wrap_text(
                    text,
                    max_width,
                    font_size
                )

                line_height = font_size * 1.3

                if (
                    len(lines) * line_height
                    <= max_height
                ):
                    break

                font_size -= 0.5

            lines = wrap_text(
                text,
                max_width,
                font_size
            )

            line_height = font_size * 1.3

            max_lines = max(
                1,
                int(max_height / line_height)
            )

            if len(lines) > max_lines:

                lines = lines[:max_lines]

                final_line = lines[-1]

                while (
                    final_line
                    and text_width(
                        final_line + "...",
                        font_size
                    ) > max_width
                ):
                    final_line = final_line[:-1]

                lines[-1] = final_line + "..."

            # -------------------------------------------------
            # PREVENT TEXT OVERFLOW
            # -------------------------------------------------

            pdf.saveState()

            clipping = pdf.beginPath()

            clipping.rect(
                x + 1,
                y + 1,
                max(width - 2, 0),
                max(height - 2, 0)
            )

            pdf.clipPath(
                clipping,
                stroke=0,
                fill=0
            )

            pdf.setFont(
                font_name,
                font_size
            )

            pdf.setFillColorRGB(
                0.08,
                0.12,
                0.18
            )

            total_height = len(lines) * line_height

            baseline = (
                y
                + (height + total_height) / 2
                - line_height
                + 2
            )

            for line in lines:

                rendered = shape_text(line)

                if align == "center":

                    rng_pdf_draw(pdf, rendered, x + width / 2, baseline, font_size, "center")

                else:

                    rng_pdf_draw(pdf, rendered, x + width - padding, baseline, font_size, "right")

                baseline -= line_height

            pdf.restoreState()

        # =====================================================
        # DRAW PDF CELL
        # =====================================================

        def draw_cell(
            first_col,
            last_col,
            row,
            text="",
            font_size=10,
            align="right",
            shaded=False
        ):

            x = x_edges[last_col + 1]

            width = (
                x_edges[first_col]
                - x_edges[last_col + 1]
            )

            y = y_edges[row]

            height = row_heights[row - 1]

            if shaded:

                pdf.setFillColorRGB(
                    0.92,
                    0.93,
                    0.95
                )

                pdf.rect(
                    x,
                    y,
                    width,
                    height,
                    fill=1,
                    stroke=0
                )

            pdf.setStrokeColorRGB(
                0.3,
                0.3,
                0.3
            )

            pdf.setLineWidth(0.55)

            pdf.rect(
                x,
                y,
                width,
                height,
                fill=0,
                stroke=1
            )

            draw_text(
                text,
                x,
                y,
                width,
                height,
                size=font_size,
                align=align
            )

        # =====================================================
        # FIELD TEXT HELPER
        # =====================================================

        def field_text(field):

            return (
                FIELD_LABELS[field]
                + ": "
                + str(form.get(field, ""))
            )

        # =====================================================
        # ROW 1 - LOGO / TITLE / DATE
        # =====================================================

        draw_cell(0, 1, 1)

        draw_cell(
            2,
            5,
            1,
            template["cells"].get(
                "C1",
                MISSION_HEADINGS["title"]
            ),
            font_size=16,
            align="center"
        )

        draw_cell(
            6,
            7,
            1,
            field_text("report_date")
        )

        # -----------------------------------------------------
        # ORIGINAL EXCEL LOGO
        # -----------------------------------------------------

        if template["logo"]:

            image = ImageReader(
                io.BytesIO(template["logo"])
            )

            image_width, image_height = image.getSize()

            logo_x = x_edges[2]
            logo_y = y_edges[1]

            logo_width = x_edges[0] - x_edges[2]
            logo_height = row_heights[0]

            scale = min(
                logo_width * 0.92 / image_width,
                logo_height * 0.92 / image_height
            )

            render_width = image_width * scale
            render_height = image_height * scale

            pdf.drawImage(
                image,
                logo_x + (logo_width - render_width) / 2,
                logo_y + (logo_height - render_height) / 2,
                width=render_width,
                height=render_height,
                preserveAspectRatio=True,
                mask="auto"
            )

        # =====================================================
        # ROW 2 - EMPLOYEE AND POSITION
        # =====================================================

        draw_cell(
            0, 3, 2,
            field_text("employee")
        )

        draw_cell(
            4, 7, 2,
            field_text("position")
        )

        # =====================================================
        # ROW 3 - MISSION DESTINATION
        # =====================================================

        draw_cell(
            0, 2, 3,
            field_text("dispatcher")
        )

        draw_cell(
            3, 4, 3,
            field_text("city")
        )

        draw_cell(
            5, 7, 3,
            field_text("company")
        )

        # =====================================================
        # ROW 4 - COMPANIONS
        # =====================================================

        draw_cell(
            0, 7, 4,
            field_text("companions")
        )

        # =====================================================
        # ROW 5 - DATE AND TIME
        # =====================================================

        draw_cell(
            0, 0, 5,
            field_text("duration"),
            font_size=8
        )

        draw_cell(
            1, 2, 5,
            field_text("start_date"),
            font_size=9
        )

        draw_cell(
            3, 3, 5,
            field_text("departure_time"),
            font_size=8
        )

        draw_cell(
            4, 5, 5,
            field_text("end_date"),
            font_size=9
        )

        draw_cell(
            6, 7, 5,
            field_text("return_time"),
            font_size=9
        )

        # =====================================================
        # ROW 6 - TRANSPORTATION
        # =====================================================

        draw_cell(
            0, 7, 6,
            field_text("transport")
            + "       "
            + field_text("distance")
        )

        # =====================================================
        # ROW 7 - DESCRIPTION HEADING
        # =====================================================

        draw_cell(
            0, 7, 7,
            template["cells"].get(
                "A7",
                MISSION_HEADINGS["description"]
            ),
            font_size=11,
            shaded=True
        )

        # =====================================================
        # ROW 8 - EQUIPMENT
        # =====================================================

        draw_cell(
            0, 7, 8,
            field_text("equipment")
        )

        # =====================================================
        # ROW 9 - MISSION DESCRIPTION
        # =====================================================

        draw_cell(
            0, 7, 9,
            FIELD_LABELS["description"]
            + ":\n"
            + str(form.get("description", "")),
            font_size=10
        )

        # =====================================================
        # ROW 10 - OBJECTIVE
        # =====================================================

        draw_cell(
            0, 7, 10,
            field_text("objective")
        )

        # =====================================================
        # ROW 11 - RESULT
        # =====================================================

        draw_cell(
            0, 7, 11,
            field_text("result")
        )

        # =====================================================
        # ROW 12 - MANAGER HEADING
        # =====================================================

        draw_cell(
            0, 7, 12,
            template["cells"].get(
                "A12",
                MISSION_HEADINGS["manager"]
            ),
            font_size=10,
            align="center",
            shaded=True
        )

        # =====================================================
        # ROW 13 - MANAGER REVIEW / SIGNATURES
        # =====================================================

        draw_cell(
            0, 3, 13,
            FIELD_LABELS["manager_comment"]
            + ":\n"
            + str(form.get("manager_comment", ""))
            + "\n"
            + field_text("manager_signature")
        )

        draw_cell(
            4, 7, 13,
            field_text("employee_signature")
        )

        # =====================================================
        # COMPLETE SINGLE-PAGE PDF
        # =====================================================

        pdf.showPage()
        pdf.save()

        buffer.seek(0)

        return buffer.getvalue()

    # =========================================================
    # MISSION REPORT DETAIL VIEW
    # =========================================================

    selected = st.session_state.selected_mission_report

    if (
        isinstance(selected, int)
        and 0 <= selected < len(
            st.session_state.mission_report_cards
        )
    ):

        mission_name = st.session_state.mission_report_cards[
            selected
        ]

        mission_id = st.session_state.mission_report_card_ids[
            selected
        ]

        if mission_id not in st.session_state.mission_report_forms:

            st.session_state.mission_report_forms[
                mission_id
            ] = create_empty_mission_form()

        form = st.session_state.mission_report_forms[
            mission_id
        ]

        if st.button(
            "Back to Mission Reports",
            key="mission_report_back"
        ):

            st.session_state.selected_mission_report = None
            rng_rerun()

        st.markdown(
            f'<div class="dashboard-title">{escape(mission_name)}</div>',
            unsafe_allow_html=True
        )

        if mission_template is None:

            st.error(
                "Unable to load the Excel template: "
                + str(mission_template_error)
            )

        else:

            with st.container(key="mission_detail"):

                # =================================================
                # FORM TITLE
                # =================================================

                form_title = mission_template["cells"].get(
                    "C1",
                    MISSION_HEADINGS["title"]
                )

                st.markdown(
                    '<div class="mission-form-heading">'
                    + escape(form_title)
                    + '</div>',
                    unsafe_allow_html=True
                )

                # =================================================
                # INPUT HELPERS
                # =================================================

                def mission_input(field):

                    form[field] = st.text_input(
                        label=FIELD_LABELS[field],
                        value=form.get(field, ""),
                        placeholder=FIELD_LABELS[field],
                        key=f"mission_{mission_id}_{field}",
                        label_visibility="visible"
                    )

                def mission_text_area(field, height):

                    form[field] = st.text_area(
                        label=FIELD_LABELS[field],
                        value=form.get(field, ""),
                        placeholder=FIELD_LABELS[field],
                        height=height,
                        key=f"mission_{mission_id}_{field}",
                        label_visibility="visible"
                    )

                def mission_section(title):

                    st.markdown(
                        '<div class="mission-section-heading">'
                        + escape(title)
                        + '</div>',
                        unsafe_allow_html=True
                    )

                # =================================================
                # REPORT DATE
                # =================================================

                mission_input("report_date")

                st.divider()

                # =================================================
                # EMPLOYEE INFORMATION
                # =================================================

                cols = st.columns(2)

                with cols[0]:
                    mission_input("position")

                with cols[1]:
                    mission_input("employee")

                # =================================================
                # MISSION DESTINATION
                # =================================================

                cols = st.columns(3)

                with cols[0]:
                    mission_input("company")

                with cols[1]:
                    mission_input("city")

                with cols[2]:
                    mission_input("dispatcher")

                mission_input("companions")

                # =================================================
                # MISSION SCHEDULE
                # =================================================

                mission_section(
                    MISSION_HEADINGS["schedule"]
                )

                cols = st.columns(3)

                with cols[0]:
                    mission_input("duration")

                with cols[1]:
                    mission_input("start_date")

                with cols[2]:
                    mission_input("departure_time")

                cols = st.columns(2)

                with cols[0]:
                    mission_input("return_time")

                with cols[1]:
                    mission_input("end_date")

                # =================================================
                # TRANSPORTATION
                # =================================================

                mission_section(
                    MISSION_HEADINGS["transport"]
                )

                cols = st.columns(2)

                with cols[0]:
                    mission_input("distance")

                with cols[1]:
                    mission_input("transport")

                # =================================================
                # MISSION DESCRIPTION
                # =================================================

                mission_section(
                    MISSION_HEADINGS["description"]
                )

                mission_input("equipment")

                mission_text_area(
                    "description",
                    220
                )

                mission_text_area(
                    "objective",
                    110
                )

                mission_text_area(
                    "result",
                    110
                )

                # =================================================
                # MANAGER REVIEW
                # =================================================

                mission_section(
                    MISSION_HEADINGS["manager"]
                )

                mission_text_area(
                    "manager_comment",
                    140
                )

                cols = st.columns(2)

                with cols[0]:
                    mission_input("employee_signature")

                with cols[1]:
                    mission_input("manager_signature")

                # =================================================
                # PDF DOWNLOAD
                # =================================================

                st.divider()

                try:

                    pdf_bytes = create_mission_pdf(
                        form,
                        mission_template
                    )

                    safe_name = re.sub(
                        r"[^\w.-]+",
                        "_",
                        mission_name
                    )

                    st.download_button(
                        label="Download A4 Portrait PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"Mission_Report_{safe_name}.pdf"
                        ),
                        mime="application/pdf",
                        key=f"mission_pdf_{mission_id}",
                        use_container_width=True
                    )

                except Exception as error:

                    st.error(
                        "PDF generation error: "
                        + str(error)
                    )

    # =========================================================
    # MISSION REPORT MAIN PAGE
    # =========================================================

    else:

        st.session_state.selected_mission_report = None

        st.markdown(
            '<div class="dashboard-title">Mission Report</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="dashboard-subtitle">'
            'Manage and review your mission reports'
            '</div>',
            unsafe_allow_html=True
        )

        # =====================================================
        # ADD MISSION REPORT
        # =====================================================

        if st.session_state.adding_mission_report:

            st.markdown(
                '<div class="section-title">'
                'Add New Mission Report'
                '</div>',
                unsafe_allow_html=True
            )

            new_title = st.text_input(
                "Mission report title",
                placeholder="Enter mission report title",
                key="new_mission_report_title"
            )

            add_col, cancel_col = st.columns(2)

            with add_col:

                if st.button(
                    "Add Mission Report",
                    key="mission_report_add_confirm",
                    use_container_width=True
                ):

                    if new_title.strip():

                        st.session_state.mission_report_cards.append(
                            new_title.strip()
                        )

                        st.session_state.mission_report_card_ids.append(
                            uuid4().hex
                        )

                        st.session_state.adding_mission_report = False
                        rng_rerun()

                    else:

                        st.warning(
                            "Please enter a mission report title."
                        )

            with cancel_col:

                if st.button(
                    "Cancel",
                    key="mission_report_add_cancel",
                    use_container_width=True
                ):

                    st.session_state.adding_mission_report = False
                    rng_rerun()

        else:

            if st.button(
                "+ Add Mission Report",
                key="mission_report_add_button"
            ):

                st.session_state.adding_mission_report = True
                rng_rerun()

        st.markdown(
            "<br>",
            unsafe_allow_html=True
        )

        # =====================================================
        # MISSION REPORT CARDS
        # =====================================================

        cols = st.columns(3)

        for i, mission in enumerate(
            st.session_state.mission_report_cards
        ):

            with cols[i % 3]:

                safe_title = escape(mission)

                # =================================================
                # DELETE CONFIRMATION
                # =================================================

                if st.session_state.deleting_mission_report == i:

                    st.markdown(
                        f"""
                        <div class="mission-report-card">
                            <div class="mission-report-card-title">
                                {safe_title}
                            </div>
                            <div class="mission-report-card-text">
                                Mission report records
                            </div>
                        </div>

                        <div class="mission-report-delete-warning">
                            Are you sure you want to delete
                            "{safe_title}"?
                            This cannot be undone.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:

                        if st.button(
                            "Confirm Delete",
                            key=f"mission_report_confirm_delete_{i}",
                            use_container_width=True
                        ):

                            deleted_id = (
                                st.session_state.mission_report_card_ids.pop(i)
                            )

                            st.session_state.mission_report_cards.pop(i)

                            st.session_state.mission_report_forms.pop(
                                deleted_id,
                                None
                            )

                            st.session_state.deleting_mission_report = None
                            st.session_state.editing_mission_report = None

                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"mission_report_cancel_delete_{i}",
                            use_container_width=True
                        ):

                            st.session_state.deleting_mission_report = None

                            rng_rerun()

                # =================================================
                # EDIT MISSION REPORT TITLE
                # =================================================

                elif st.session_state.editing_mission_report == i:

                    edited_title = st.text_input(
                        "Mission report title",
                        value=mission,
                        key=f"mission_report_edit_input_{i}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save",
                            key=f"mission_report_save_{i}",
                            use_container_width=True
                        ):

                            if edited_title.strip():

                                st.session_state.mission_report_cards[i] = (
                                    edited_title.strip()
                                )

                                st.session_state.editing_mission_report = None

                                rng_rerun()

                            else:

                                st.warning(
                                    "Please enter a mission report title."
                                )

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"mission_report_cancel_{i}",
                            use_container_width=True
                        ):

                            st.session_state.editing_mission_report = None

                            rng_rerun()

                # =================================================
                # NORMAL MISSION REPORT CARD
                # =================================================

                else:

                    st.markdown(
                        f"""
                        <div class="mission-report-card">
                            <div class="mission-report-card-title">
                                {safe_title}
                            </div>
                            <div class="mission-report-card-text">
                                Mission report records
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    button_col1, button_col2, button_col3 = st.columns(3)

                    with button_col1:

                        open_button = st.button(
                            "Open",
                            key=f"mission_report_open_{i}",
                            use_container_width=True
                        )

                    with button_col2:

                        edit_button = st.button(
                            "Edit",
                            key=f"mission_report_edit_{i}",
                            use_container_width=True
                        )

                    with button_col3:

                        delete_button = st.button(
                            "Delete",
                            key=f"mission_report_delete_{i}",
                            use_container_width=True
                        )

                    if open_button:

                        st.session_state.selected_mission_report = i

                        rng_rerun()

                    if edit_button:

                        st.session_state.editing_mission_report = i
                        st.session_state.deleting_mission_report = None

                        rng_rerun()

                    if delete_button:

                        st.session_state.deleting_mission_report = i
                        st.session_state.editing_mission_report = None

                        rng_rerun()



elif page == "Rah Nia Development":
    from datetime import datetime

    # =========================================================
    # TASK DATA
    # =========================================================

    if "development_tasks" not in st.session_state:
        st.session_state.development_tasks = []

    if "development_creating_task" not in st.session_state:
        st.session_state.development_creating_task = False

    if "development_editing_task" not in st.session_state:
        st.session_state.development_editing_task = None

    if "development_new_subtask_count" not in st.session_state:
        st.session_state.development_new_subtask_count = 1

    # =========================================================
    # CSS
    # =========================================================

    st.markdown("""
    <style>

    .todo-card {
        background-color: #ffffff;
        border: 1px solid #d7dde5;
        border-radius: 14px;
        margin-bottom: 18px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.06);
    }

    .todo-card-done {
        background-color: #edf8ef;
        border: 1px solid #a8d5b0;
        border-radius: 14px;
        margin-bottom: 18px;
        padding: 0;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
    }

    .todo-title {
        color: #172333 !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        padding: 16px;
        margin: 0;
    }

    .todo-section-title {
        color: #172333 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        padding: 12px 16px 5px 16px;
        margin: 0;
    }

    .todo-date {
        color: #596579 !important;
        font-size: 12px !important;
        padding: 5px 16px;
        margin: 0;
    }

    .todo-completed {
        color: #218739 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 5px 16px 14px 16px;
        margin: 0;
    }

    .todo-divider {
        height: 1px;
        background-color: #dfe4ea;
        margin: 0;
        padding: 0;
    }

    div[data-testid="stCheckbox"] label p {
        color: #263241 !important;
        font-size: 14px !important;
    }

    div[data-testid="stCheckbox"] label {
        color: #263241 !important;
    }

    div[data-testid="stCheckbox"] {
        padding-left: 16px;
        padding-right: 16px;
        margin-top: 2px;
        margin-bottom: 2px;
    }

    @media (max-width: 768px) {

        .todo-title {
            font-size: 17px !important;
            padding: 14px;
        }

        .todo-section-title {
            padding-left: 14px;
        }

        .todo-date,
        .todo-completed {
            padding-left: 14px;
            padding-right: 14px;
        }

        div[data-testid="stCheckbox"] {
            padding-left: 14px;
            padding-right: 14px;
        }
    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # PAGE TITLE
    # =========================================================

    st.markdown(
        '<div class="dashboard-title">Rah Nia Development</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">'
        'Manage Rah Nia development tasks and track progress.'
        '</div>',
        unsafe_allow_html=True
    )

    # =========================================================
    # CREATE TASK BUTTON
    # =========================================================

    if st.button(
        "Create Task",
        key="development_create_task_button",
        use_container_width=True
    ):
        st.session_state.development_creating_task = True
        st.session_state.development_new_subtask_count = 1
        rng_rerun()

    # =========================================================
    # CREATE TASK FORM
    # =========================================================

    if st.session_state.development_creating_task:

        st.markdown("### Create New Task")

        new_title = st.text_input(
            "Task Title",
            placeholder="Enter task title...",
            key="development_new_task_title"
        )

        st.markdown("Sub Tasks")

        subtask_values = []

        for i in range(st.session_state.development_new_subtask_count):

            value = st.text_input(
                f"Sub Task {i + 1}",
                placeholder="Enter sub task...",
                key=f"development_create_subtask_{i}"
            )

            subtask_values.append(value)

        add_col, create_col, cancel_col = st.columns(3)

        with add_col:
            if st.button(
                "Add Sub Task",
                key="development_add_subtask_button",
                use_container_width=True
            ):
                st.session_state.development_new_subtask_count += 1
                rng_rerun()

        with create_col:
            if st.button(
                "Save Task",
                key="development_save_new_task",
                use_container_width=True
            ):

                if new_title.strip():

                    subtasks = []

                    for value in subtask_values:

                        if value.strip():
                            subtasks.append({
                                "text": value.strip(),
                                "done": False
                            })

                    st.session_state.development_tasks.append({
                        "title": new_title.strip(),
                        "subtasks": subtasks,
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "completed": None,
                        "done": False,
                    })

                    st.session_state.development_creating_task = False
                    st.session_state.development_new_subtask_count = 1

                    rng_rerun()

        with cancel_col:
            if st.button(
                "Cancel",
                key="development_cancel_new_task",
                use_container_width=True
            ):
                st.session_state.development_creating_task = False
                st.session_state.development_new_subtask_count = 1
                rng_rerun()

        st.divider()

    # =========================================================
    # SORT TASKS
    # =========================================================

    unfinished = [
        task for task in st.session_state.development_tasks
        if not task["done"]
    ]

    completed = [
        task for task in st.session_state.development_tasks
        if task["done"]
    ]

    sorted_tasks = unfinished + completed

    # =========================================================
    # TASK CARDS
    # =========================================================

    for row_start in range(0, len(sorted_tasks), 3):

        row_tasks = sorted_tasks[row_start:row_start + 3]

        columns = st.columns(3)

        for column_number, task in enumerate(row_tasks):

            with columns[column_number]:

                task_index = st.session_state.development_tasks.index(task)

                # =================================================
                # EDIT MODE
                # =================================================

                if st.session_state.development_editing_task == task_index:

                    st.markdown(
                        '<div class="todo-card">',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div class="todo-title">Edit Task</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div class="todo-divider"></div>',
                        unsafe_allow_html=True
                    )

                    edited_title = st.text_input(
                        "Task Title",
                        value=task["title"],
                        key=f"development_edit_title_{task_index}"
                    )

                    st.markdown("Sub Tasks")

                    edited_subtasks = []

                    for sub_index, subtask in enumerate(task["subtasks"]):

                        edited_text = st.text_input(
                            f"Sub Task {sub_index + 1}",
                            value=subtask["text"],
                            key=f"development_edit_subtask_{task_index}_{sub_index}"
                        )

                        edited_subtasks.append({
                            "text": edited_text,
                            "done": subtask["done"]
                        })

                    new_edit_subtask = st.text_input(
                        "Add another sub task",
                        placeholder="Optional",
                        key=f"development_edit_new_subtask_{task_index}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save Changes",
                            key=f"development_save_edit_{task_index}",
                            use_container_width=True
                        ):

                            if edited_title.strip():
                                task["title"] = edited_title.strip()

                            task["subtasks"] = [
                                subtask
                                for subtask in edited_subtasks
                                if subtask["text"].strip()
                            ]

                            if new_edit_subtask.strip():
                                task["subtasks"].append({
                                    "text": new_edit_subtask.strip(),
                                    "done": False
                                })

                            if (
                                len(task["subtasks"]) > 0
                                and all(
                                    subtask["done"]
                                    for subtask in task["subtasks"]
                                )
                            ):

                                task["done"] = True

                                if not task["completed"]:
                                    task["completed"] = (
                                        datetime.now().strftime("%Y-%m-%d")
                                    )

                            else:

                                task["done"] = False
                                task["completed"] = None

                            st.session_state.development_editing_task = None
                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"development_cancel_edit_{task_index}",
                            use_container_width=True
                        ):
                            st.session_state.development_editing_task = None
                            rng_rerun()

                    st.markdown(
                        "</div>",
                        unsafe_allow_html=True
                    )

                    continue

                # =================================================
                # CARD TITLE
                # =================================================

                if task["done"]:
                    card_class = "todo-card-done"
                else:
                    card_class = "todo-card"

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="todo-title">
                            {task["title"]}
                        </div>
                        <div class="todo-divider"></div>
                    """,
                    unsafe_allow_html=True
                )

                # =================================================
                # MAIN TASK CHECKBOX
                # =================================================

                main_done = st.checkbox(
                    "Task completed",
                    value=task["done"],
                    key=f"development_main_checkbox_{task_index}"
                )

                if main_done != task["done"]:

                    task["done"] = main_done

                    if main_done:
                        task["completed"] = datetime.now().strftime(
                            "%Y-%m-%d"
                        )
                    else:
                        task["completed"] = None

                    rng_rerun()

                # =================================================
                # SUBTASKS
                # =================================================

                st.markdown(
                    '<div class="todo-divider"></div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    '<div class="todo-section-title">Sub Tasks</div>',
                    unsafe_allow_html=True
                )

                for sub_index, subtask in enumerate(task["subtasks"]):

                    sub_done = st.checkbox(
                        subtask["text"],
                        value=subtask["done"],
                        key=f"development_sub_checkbox_{task_index}_{sub_index}"
                    )

                    if sub_done != subtask["done"]:

                        subtask["done"] = sub_done

                        if (
                            len(task["subtasks"]) > 0
                            and all(
                                item["done"]
                                for item in task["subtasks"]
                            )
                        ):

                            task["done"] = True
                            task["completed"] = (
                                datetime.now().strftime("%Y-%m-%d")
                            )

                        else:

                            task["done"] = False
                            task["completed"] = None

                        rng_rerun()

                # =================================================
                # DATES
                # =================================================

                st.markdown(
                    '<div class="todo-divider"></div>',
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <div class="todo-date">
                        Created: {task["created"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if task["completed"]:

                    st.markdown(
                        f"""
                        <div class="todo-completed">
                            Completed: {task["completed"]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                else:

                    st.markdown(
                        """
                        <div class="todo-date">
                            Completed: -
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # =================================================
                # CLOSE CARD
                # =================================================

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True
                )

                # =================================================
                # EDIT BUTTON
                # =================================================

                if st.button(
                    "Edit",
                    key=f"development_edit_button_{task_index}",
                    use_container_width=True
                ):

                    st.session_state.development_editing_task = task_index
                    rng_rerun()




elif page == "BOM":

    import io
    import re
    import hashlib
    from pathlib import Path
    from uuid import uuid4
    from html import escape

    # =========================================================
    # ORIGINAL BOM EXCEL TEMPLATE
    # =========================================================

    BOM_TEMPLATE_PATH = (
        Path(__file__).resolve().parent / "BOM Raw.xlsx"
    )

    def load_bom_template():

        from openpyxl import load_workbook

        if not BOM_TEMPLATE_PATH.is_file():
            raise FileNotFoundError(
                "BOM Raw.xlsx was not found beside app.py"
            )

        workbook = load_workbook(
            BOM_TEMPLATE_PATH,
            read_only=False,
            data_only=False
        )

        if "RAW" not in workbook.sheetnames:
            workbook.close()
            raise ValueError("RAW worksheet not found.")

        ws = workbook["RAW"]

        labels = {
            "title": str(ws["C1"].value or ""),
            "metadata": str(ws["J1"].value or ""),
            "headers": [
                str(ws[f"{col}2"].value or "")
                for col in "ABDEFGHI"
            ],
            "preparer": str(ws["A18"].value or ""),
            "approver": str(ws["D18"].value or "")
        }

        widths = [
            ws.column_dimensions[c].width or 10
            for c in "ABCDEFGHIJK"
        ]

        heights = [
            ws.row_dimensions[r].height or 25
            for r in range(1, 19)
        ]

        workbook.close()

        return {
            "labels": labels,
            "widths": widths,
            "heights": heights
        }

    bom_template = None
    bom_template_error = None

    try:
        bom_template = load_bom_template()

    except Exception as error:
        bom_template_error = str(error)

    # =========================================================
    # BOM SESSION STATE
    # =========================================================

    if "bom_cards" not in st.session_state:
        st.session_state.bom_cards = []

    if "selected_bom" not in st.session_state:
        st.session_state.selected_bom = None

    if "editing_bom" not in st.session_state:
        st.session_state.editing_bom = None

    if "deleting_bom" not in st.session_state:
        st.session_state.deleting_bom = None

    if "adding_bom" not in st.session_state:
        st.session_state.adding_bom = False

    if "bom_card_ids" not in st.session_state:
        st.session_state.bom_card_ids = [
            uuid4().hex
            for _ in st.session_state.bom_cards
        ]

    if "bom_forms" not in st.session_state:
        st.session_state.bom_forms = {}

    while len(st.session_state.bom_card_ids) < len(
        st.session_state.bom_cards
    ):
        st.session_state.bom_card_ids.append(
            uuid4().hex
        )

    # =========================================================
    # BOM DATA STRUCTURE
    # =========================================================

    def create_empty_bom_table():

        return [
            {
                "description": "",
                "size": "",
                "actual": "",
                "over": "",
                "unit": "",
                "notes": ""
            }
            for _ in range(15)
        ]

    def create_empty_bom():

        return {
            "date": "",
            "number": "",
            "code": "",
            "preparer": "",
            "approver": "",
            "items": create_empty_bom_table(),
            "extra_tables": []
        }

    # =========================================================
    # SUPPORT EXISTING BOM DATA
    # =========================================================

    def prepare_bom_form(form):

        # The original items list remains the first table.
        # This preserves previously entered data.

        if "items" not in form:
            form["items"] = create_empty_bom_table()

        if "extra_tables" not in form:
            form["extra_tables"] = []

        for field in [
            "date",
            "number",
            "code",
            "preparer",
            "approver"
        ]:
            if field not in form:
                form[field] = ""

        # Ensure every existing table has 15 rows.
        all_tables = [form["items"]] + form["extra_tables"]

        for table in all_tables:

            while len(table) < 15:
                table.append({
                    "description": "",
                    "size": "",
                    "actual": "",
                    "over": "",
                    "unit": "",
                    "notes": ""
                })

            for item in table:

                for field in [
                    "description",
                    "size",
                    "actual",
                    "over",
                    "unit",
                    "notes"
                ]:
                    if field not in item:
                        item[field] = ""

    # =========================================================
    # NUMBER CALCULATION
    # =========================================================

    def parse_bom_number(value):

        text = str(value).strip()

        if not text:
            return 0.0

        digit_map = str.maketrans(
            "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
            "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
            "01234567890123456789"
        )

        text = text.translate(digit_map)

        text = text.replace("\u066c", "")
        text = text.replace(",", "")
        text = text.replace("\u066b", ".")

        return float(text)

    def calculate_bom_quantity(item):

        actual_text = str(
            item.get("actual", "")
        ).strip()

        over_text = str(
            item.get("over", "")
        ).strip()

        if not actual_text and not over_text:
            return ""

        try:

            actual = parse_bom_number(actual_text)
            over = parse_bom_number(over_text)

            total = actual + over

            if not (
                float("-inf") < total < float("inf")
            ):
                return "Invalid"

            if total.is_integer():
                return str(int(total))

            return f"{total:.6f}".rstrip("0").rstrip(".")

        except (ValueError, TypeError):
            return "Invalid"

    # =========================================================
    # BOM CSS
    # =========================================================

    st.markdown("""
    <style>

    .bom-card {
        background: white;
        border: 1px solid #e3e7ed;
        border-radius: 14px;
        padding: 24px;
        min-height: 120px;
        box-shadow: 0 2px 8px rgba(20, 30, 45, 0.05);
        margin-bottom: 10px;
    }

    .bom-card-title {
        font-size: 18px;
        font-weight: 650;
        color: #172333;
    }

    .bom-card-text {
        font-size: 13px;
        color: #7b8794;
        margin-top: 6px;
    }

    .bom-delete-warning {
        background: #fff4f4;
        border: 1px solid #f0caca;
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #7a1f1f;
        font-size: 14px;
        font-weight: 600;
    }

    .bom-form-title {
        font-size: 25px;
        font-weight: 700;
        color: #172333;
        text-align: center;
        direction: rtl;
        margin: 12px 0 24px;
    }

    .bom-section-title {
        background: #edf0f4;
        border: 1px solid #cfd6df;
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
        font-weight: 700;
        color: #172333;
        direction: rtl;
        text-align: right;
        margin: 16px 0;
    }

    .bom-table-heading {
        min-height: 58px;
        background: #edf0f4;
        color: #172333;
        border: 1px solid #cfd6df;
        padding: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        direction: rtl;
        font-size: 12px;
        font-weight: 700;
        box-sizing: border-box;
    }

    .bom-row-number {
        height: 42px;
        background: #f5f7fa;
        border: 1px solid #cfd6df;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
        color: #172333;
        box-sizing: border-box;
    }

    .bom-row-quantity {
        height: 42px;
        background: #edf8ef;
        border: 1px solid #cfd6df;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
        color: #172333;
        box-sizing: border-box;
    }

    .st-key-bom_detail input,
    .st-key-bom_detail textarea {
        direction: rtl !important;
        text-align: right !important;
        unicode-bidi: plaintext;
        background: white !important;
        color: #172333 !important;
        font-size: 14px !important;
    }

    .st-key-bom_detail
    div[data-testid="stWidgetLabel"] p {
        color: #172333 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        direction: rtl !important;
        text-align: right !important;
    }

    /* Apply table styling to all BOM tables */

    .st-key-bom_detail
    div[data-testid="stHorizontalBlock"] {
        column-gap: 0;
    }

    .bom-table-heading {
        overflow-wrap: anywhere;
    }

    @media (max-width: 768px) {

        .bom-card {
            min-height: 100px;
            padding: 18px;
        }

        .bom-table-heading {
            font-size: 10px;
        }

    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # PDF GENERATOR - MULTIPLE A4 PORTRAIT PAGES
    # =========================================================

    def create_bom_pdf(form, template):

        import arabic_reshaper

        from bidi.algorithm import get_display
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        buffer = io.BytesIO()

        page_width, page_height = A4

        pdf = canvas.Canvas(
            buffer,
            pagesize=A4,
            pageCompression=1
        )

        labels = template["labels"]

        pdf.setTitle(labels["title"])

        # -----------------------------------------------------
        # PERSIAN FONT
        # -----------------------------------------------------

        font_name = rng_pdf_font_name()

        def shape_text(value):
            return get_display(arabic_reshaper.reshape(str(value if value is not None else "")))

        # -----------------------------------------------------
        # A4 GEOMETRY
        # -----------------------------------------------------

        margin_x = 6 * mm
        margin_y = 6 * mm

        left = margin_x
        right = page_width - margin_x

        top = page_height - margin_y
        bottom = margin_y

        usable_width = right - left
        usable_height = top - bottom

        source_widths = template["widths"]
        source_heights = template["heights"]

        width_total = sum(source_widths)
        height_total = sum(source_heights)

        col_widths = [
            usable_width * w / width_total
            for w in source_widths
        ]

        row_heights = [
            usable_height * h / height_total
            for h in source_heights
        ]

        # RTL: Excel column A is on the far right.

        x_edges = [right]

        for width in col_widths:
            x_edges.append(
                x_edges[-1] - width
            )

        y_edges = [top]

        for height in row_heights:
            y_edges.append(
                y_edges[-1] - height
            )

        # -----------------------------------------------------
        # PDF TEXT WRAPPING
        # -----------------------------------------------------

        def text_width(value, size):

            return rng_pdf_width(shape_text(value), size)

        def wrap_text(value, width, size):

            result = []

            for paragraph in str(value).splitlines():

                if not paragraph.strip():
                    result.append("")
                    continue

                current = ""

                for word in paragraph.split():

                    candidate = (
                        current + " " + word
                        if current else word
                    )

                    if text_width(candidate, size) <= width:
                        current = candidate

                    else:

                        if current:
                            result.append(current)

                        current = ""

                        for char in word:

                            candidate = current + char

                            if (
                                current
                                and text_width(candidate, size) > width
                            ):
                                result.append(current)
                                current = char

                            else:
                                current = candidate

                if current:
                    result.append(current)

            return result or [""]

        # -----------------------------------------------------
        # DRAW TEXT
        # -----------------------------------------------------

        def draw_text(
            value,
            x,
            y,
            width,
            height,
            size=8,
            align="center"
        ):

            value = str(
                value if value is not None else ""
            ).strip()

            if not value:
                return

            padding = 2.5

            available_width = max(
                width - 2 * padding,
                1
            )

            available_height = max(
                height - 2 * padding,
                1
            )

            font_size = float(size)

            while font_size > 4.5:

                lines = wrap_text(
                    value,
                    available_width,
                    font_size
                )

                line_height = font_size * 1.25

                if (
                    len(lines) * line_height
                    <= available_height
                ):
                    break

                font_size -= 0.5

            lines = wrap_text(
                value,
                available_width,
                font_size
            )

            line_height = font_size * 1.25

            maximum_lines = max(
                1,
                int(available_height / line_height)
            )

            if len(lines) > maximum_lines:

                lines = lines[:maximum_lines]

                last = lines[-1]

                while (
                    last
                    and text_width(
                        last + "...",
                        font_size
                    ) > available_width
                ):
                    last = last[:-1]

                lines[-1] = last + "..."

            pdf.saveState()

            clipping = pdf.beginPath()

            clipping.rect(
                x + 1,
                y + 1,
                max(width - 2, 0),
                max(height - 2, 0)
            )

            pdf.clipPath(
                clipping,
                stroke=0,
                fill=0
            )

            pdf.setFont(font_name, font_size)
            pdf.setFillColorRGB(0, 0, 0)

            total_height = len(lines) * line_height

            baseline = (
                y
                + (height + total_height) / 2
                - line_height
                + 2
            )

            for line in lines:

                shaped = shape_text(line)

                if align == "right":

                    rng_pdf_draw(pdf, shaped, x + width - padding, baseline, font_size, "right")

                elif align == "left":

                    rng_pdf_draw(pdf, shaped, x + padding, baseline, font_size, "left")

                else:

                    rng_pdf_draw(pdf, shaped, x + width / 2, baseline, font_size, "center")

                baseline -= line_height

            pdf.restoreState()

        # -----------------------------------------------------
        # DRAW EXCEL-STYLE CELL
        # -----------------------------------------------------

        def draw_cell(
            first_col,
            last_col,
            row,
            text="",
            size=8,
            shaded=False,
            align="center"
        ):

            x = x_edges[last_col + 1]

            width = (
                x_edges[first_col]
                - x_edges[last_col + 1]
            )

            y = y_edges[row]
            height = row_heights[row - 1]

            if shaded:

                pdf.setFillColorRGB(
                    0.93,
                    0.94,
                    0.96
                )

                pdf.rect(
                    x,
                    y,
                    width,
                    height,
                    fill=1,
                    stroke=0
                )

            pdf.setStrokeColorRGB(
                0.25,
                0.25,
                0.25
            )

            pdf.setLineWidth(0.5)

            pdf.rect(
                x,
                y,
                width,
                height,
                fill=0,
                stroke=1
            )

            draw_text(
                text,
                x,
                y,
                width,
                height,
                size=size,
                align=align
            )

        # =====================================================
        # DRAW ONE COMPLETE BOM PAGE FOR EACH TABLE
        # =====================================================

        for table_index, table_items in enumerate(all_tables):

            # -------------------------------------------------
            # ROW 1: TITLE AND DOCUMENT INFORMATION
            # -------------------------------------------------

            draw_cell(0, 1, 1)

            draw_cell(
                2,
                8,
                1,
                labels["title"],
                size=17
            )

            metadata_labels = labels["metadata"].splitlines()

            date_label = (
                metadata_labels[0]
                if len(metadata_labels) > 0
                else "Date:"
            )

            number_label = (
                metadata_labels[1]
                if len(metadata_labels) > 1
                else "Number:"
            )

            code_label = (
                metadata_labels[2]
                if len(metadata_labels) > 2
                else "Code:"
            )

            draw_cell(
                9,
                9,
                1,
                "\n".join([
                    date_label,
                    number_label,
                    code_label
                ]),
                size=9,
                align="right"
            )

            draw_cell(
                10,
                10,
                1,
                "\n".join([
                    form["date"],
                    form["number"],
                    form["code"]
                ]),
                size=9
            )

            # -------------------------------------------------
            # ROW 2: TABLE HEADINGS
            # -------------------------------------------------

            headers = labels["headers"]

            merged_ranges = [
                (0, 0),
                (1, 2),
                (3, 3),
                (4, 4),
                (5, 5),
                (6, 6),
                (7, 7),
                (8, 10)
            ]

            for index, (start, end) in enumerate(
                merged_ranges
            ):

                draw_cell(
                    start,
                    end,
                    2,
                    headers[index],
                    size=8,
                    shaded=True
                )

            # -------------------------------------------------
            # ROWS 3-17: FIFTEEN MATERIAL ITEMS
            # -------------------------------------------------

            for item_index in range(15):

                item = table_items[item_index]

                row_number = item_index + 3

                values = [
                    str(item_index + 1),
                    item["description"],
                    item["size"],
                    item["actual"],
                    item["over"],
                    calculate_bom_quantity(item),
                    item["unit"],
                    item["notes"]
                ]

                for column_index, (start, end) in enumerate(
                    merged_ranges
                ):

                    draw_cell(
                        start,
                        end,
                        row_number,
                        values[column_index],
                        size=8
                    )

            # -------------------------------------------------
            # ROW 18: PREPARER AND APPROVER
            # -------------------------------------------------

            draw_cell(
                0,
                2,
                18,
                labels["preparer"]
                + "\n"
                + form["preparer"],
                size=10,
                align="right"
            )

            draw_cell(
                3,
                10,
                18,
                labels["approver"]
                + "\n"
                + form["approver"],
                size=10,
                align="right"
            )

            # -------------------------------------------------
            # END THIS PAGE
            # -------------------------------------------------

            pdf.showPage()

        # =====================================================
        # FINALIZE MULTI-PAGE PDF
        # =====================================================

        pdf.save()

        buffer.seek(0)

        return buffer.getvalue()

    # =========================================================
    # BOM DETAIL PAGE
    # =========================================================

    selected = st.session_state.selected_bom

    if (
        isinstance(selected, int)
        and 0 <= selected < len(st.session_state.bom_cards)
    ):

        bom_name = st.session_state.bom_cards[selected]
        bom_id = st.session_state.bom_card_ids[selected]

        if bom_id not in st.session_state.bom_forms:

            st.session_state.bom_forms[
                bom_id
            ] = create_empty_bom()

        form = st.session_state.bom_forms[bom_id]

        prepare_bom_form(form)

        if st.button(
            "Back to BOM",
            key="bom_back"
        ):
            st.session_state.selected_bom = None
            rng_rerun()

        st.markdown(
            f'<div class="dashboard-title">{escape(bom_name)}</div>',
            unsafe_allow_html=True
        )

        if bom_template is None:

            st.error(
                "Unable to load BOM Excel template: "
                + str(bom_template_error)
            )

        else:

            with st.container(key="bom_detail"):

                labels = bom_template["labels"]

                # =================================================
                # FORM TITLE
                # =================================================

                st.markdown(
                    '<div class="bom-form-title">'
                    + escape(labels["title"])
                    + '</div>',
                    unsafe_allow_html=True
                )

                # =================================================
                # DOCUMENT INFORMATION
                # =================================================

                metadata_labels = labels["metadata"].splitlines()

                info_fields = [
                    ("date", 0),
                    ("number", 1),
                    ("code", 2)
                ]

                info_cols = st.columns(3)

                for visual_index, (field, label_index) in enumerate(
                    reversed(info_fields)
                ):

                    with info_cols[visual_index]:

                        label = (
                            metadata_labels[label_index]
                            if label_index < len(metadata_labels)
                            else field.capitalize()
                        )

                        form[field] = st.text_input(
                            label,
                            value=form[field],
                            key=f"bom_{bom_id}_{field}"
                        )

                # =================================================
                # BOM TABLE CONFIGURATION
                # =================================================

                headers = labels["headers"]

                logical_widths = [
                    5.85546875,
                    15.5703125 + 19.28515625,
                    8.5703125,
                    6.0,
                    5.85546875,
                    8.42578125,
                    6.42578125,
                    6.42578125 + 5.42578125 + 10.5703125
                ]

                visual_order = list(reversed(range(8)))

                visual_widths = [
                    logical_widths[i]
                    for i in visual_order
                ]

                field_names = [
                    "row",
                    "description",
                    "size",
                    "actual",
                    "over",
                    "quantity",
                    "unit",
                    "notes"
                ]

                # =================================================
                # DISPLAY ALL BOM TABLES
                # =================================================

                all_tables = (
                    [form["items"]]
                    + form["extra_tables"]
                )

                for table_index, table_items in enumerate(
                    all_tables
                ):

                    # ---------------------------------------------
                    # TABLE TITLE
                    # ---------------------------------------------

                    st.markdown(
                        '<div class="bom-section-title">'
                        + escape(labels["title"])
                        + f" - Table {table_index + 1}"
                        + '</div>',
                        unsafe_allow_html=True
                    )

                    # ---------------------------------------------
                    # TABLE HEADER
                    # ---------------------------------------------

                    with st.container(
                        key=f"bom_form_table_{table_index}"
                    ):

                        header_cols = st.columns(
                            visual_widths,
                            gap=None
                        )

                        for visual_index, col in enumerate(
                            header_cols
                        ):

                            data_index = visual_order[
                                visual_index
                            ]

                            with col:

                                st.markdown(
                                    '<div class="bom-table-heading">'
                                    + escape(headers[data_index])
                                    + '</div>',
                                    unsafe_allow_html=True
                                )

                        # -----------------------------------------
                        # FIFTEEN EDITABLE ROWS
                        # -----------------------------------------

                        for row_index in range(15):

                            item = table_items[row_index]

                            quantity = calculate_bom_quantity(
                                item
                            )

                            row_cols = st.columns(
                                visual_widths,
                                gap=None
                            )

                            for visual_index, col in enumerate(
                                row_cols
                            ):

                                data_index = visual_order[
                                    visual_index
                                ]

                                field = field_names[
                                    data_index
                                ]

                                with col:

                                    if field == "row":

                                        st.markdown(
                                            '<div class="bom-row-number">'
                                            + str(row_index + 1)
                                            + '</div>',
                                            unsafe_allow_html=True
                                        )

                                    elif field == "quantity":

                                        st.markdown(
                                            '<div class="bom-row-quantity">'
                                            + escape(str(quantity))
                                            + '</div>',
                                            unsafe_allow_html=True
                                        )

                                    else:

                                        value = st.text_input(
                                            (
                                                f"Table {table_index + 1}, "
                                                f"Item {row_index + 1}: "
                                                f"{headers[data_index]}"
                                            ),
                                            value=item[field],
                                            key=(
                                                f"bom_{bom_id}_"
                                                f"table_{table_index}_"
                                                f"row_{row_index}_"
                                                f"{field}"
                                            ),
                                            label_visibility="collapsed"
                                        )

                                        item[field] = value

                    st.markdown(
                        "<div style='height:14px'></div>",
                        unsafe_allow_html=True
                    )

                # =================================================
                # ADD ANOTHER TABLE BUTTON
                # =================================================

                if st.button(
                    "+ Add Another Table",
                    key=f"bom_add_table_{bom_id}",
                    use_container_width=True
                ):

                    form["extra_tables"].append(
                        create_empty_bom_table()
                    )

                    rng_rerun()

                st.caption(
                    f"Total tables: {1 + len(form['extra_tables'])} "
                    f"| Total material rows: "
                    f"{15 * (1 + len(form['extra_tables']))}"
                )

                # =================================================
                # PREPARER AND APPROVER
                # =================================================

                st.divider()

                footer_cols = st.columns(2)

                with footer_cols[0]:

                    form["approver"] = st.text_input(
                        labels["approver"],
                        value=form["approver"],
                        key=f"bom_{bom_id}_approver"
                    )

                with footer_cols[1]:

                    form["preparer"] = st.text_input(
                        labels["preparer"],
                        value=form["preparer"],
                        key=f"bom_{bom_id}_preparer"
                    )

                # =================================================
                # VALIDATION FOR ALL TABLES
                # =================================================

                st.divider()

                invalid_rows = []

                all_tables = (
                    [form["items"]]
                    + form["extra_tables"]
                )

                for table_index, table_items in enumerate(
                    all_tables
                ):

                    for row_index, item in enumerate(
                        table_items
                    ):

                        if calculate_bom_quantity(item) == "Invalid":

                            invalid_rows.append(
                                f"Table {table_index + 1}, "
                                f"Row {row_index + 1}"
                            )

                if invalid_rows:

                    st.warning(
                        "Check Actual and Over values in: "
                        + "; ".join(invalid_rows)
                    )

                # =================================================
                # MULTI-PAGE PDF DOWNLOAD
                # =================================================

                try:

                    pdf_bytes = create_bom_pdf(
                        form,
                        bom_template
                    )

                    safe_name = re.sub(
                        r"[^\w.-]+",
                        "_",
                        bom_name
                    )

                    page_count = len(all_tables)

                    st.download_button(
                        label=(
                            f"Download Complete BOM "
                            f"({page_count} A4 Pages)"
                        ),
                        data=pdf_bytes,
                        file_name=f"BOM_{safe_name}.pdf",
                        mime="application/pdf",
                        key=f"bom_pdf_{bom_id}",
                        use_container_width=True,
                        disabled=bool(invalid_rows)
                    )

                except Exception as error:

                    st.error(
                        "BOM PDF generation error: "
                        + str(error)
                    )

    # =========================================================
    # BOM MAIN PAGE
    # =========================================================

    else:

        st.session_state.selected_bom = None

        st.markdown(
            '<div class="dashboard-title">BOM</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="dashboard-subtitle">'
            'Manage your Bills of Materials'
            '</div>',
            unsafe_allow_html=True
        )

        # =====================================================
        # ADD NEW BOM
        # =====================================================

        if st.session_state.adding_bom:

            st.markdown(
                '<div class="section-title">Add New BOM</div>',
                unsafe_allow_html=True
            )

            new_title = st.text_input(
                "BOM title",
                placeholder="Enter BOM title",
                key="new_bom_title"
            )

            add_col, cancel_col = st.columns(2)

            with add_col:

                if st.button(
                    "Add BOM",
                    key="bom_add_confirm",
                    use_container_width=True
                ):

                    if new_title.strip():

                        st.session_state.bom_cards.append(
                            new_title.strip()
                        )

                        st.session_state.bom_card_ids.append(
                            uuid4().hex
                        )

                        st.session_state.adding_bom = False
                        rng_rerun()

                    else:

                        st.warning(
                            "Please enter a BOM title."
                        )

            with cancel_col:

                if st.button(
                    "Cancel",
                    key="bom_add_cancel",
                    use_container_width=True
                ):

                    st.session_state.adding_bom = False
                    rng_rerun()

        else:

            if st.button(
                "+ Add BOM",
                key="bom_add_button"
            ):

                st.session_state.adding_bom = True
                rng_rerun()

        st.markdown(
            "<br>",
            unsafe_allow_html=True
        )

        # =====================================================
        # BOM CARDS
        # =====================================================

        cols = st.columns(3)

        for i, bom in enumerate(
            st.session_state.bom_cards
        ):

            with cols[i % 3]:

                safe_title = escape(bom)

                # =============================================
                # DELETE CONFIRMATION
                # =============================================

                if st.session_state.deleting_bom == i:

                    st.markdown(
                        f"""
                        <div class="bom-card">
                            <div class="bom-card-title">
                                {safe_title}
                            </div>
                            <div class="bom-card-text">
                                Bill of Materials
                            </div>
                        </div>

                        <div class="bom-delete-warning">
                            Are you sure you want to delete
                            "{safe_title}"?
                            This cannot be undone.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    confirm_col, cancel_col = st.columns(2)

                    with confirm_col:

                        if st.button(
                            "Confirm Delete",
                            key=f"bom_confirm_delete_{i}",
                            use_container_width=True
                        ):

                            deleted_id = (
                                st.session_state.bom_card_ids.pop(i)
                            )

                            st.session_state.bom_cards.pop(i)

                            st.session_state.bom_forms.pop(
                                deleted_id,
                                None
                            )

                            st.session_state.deleting_bom = None
                            st.session_state.editing_bom = None

                            rng_rerun()

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"bom_cancel_delete_{i}",
                            use_container_width=True
                        ):

                            st.session_state.deleting_bom = None

                            rng_rerun()

                # =============================================
                # EDIT BOM TITLE
                # =============================================

                elif st.session_state.editing_bom == i:

                    edited_title = st.text_input(
                        "BOM title",
                        value=bom,
                        key=f"bom_edit_input_{i}"
                    )

                    save_col, cancel_col = st.columns(2)

                    with save_col:

                        if st.button(
                            "Save",
                            key=f"bom_save_{i}",
                            use_container_width=True
                        ):

                            if edited_title.strip():

                                st.session_state.bom_cards[i] = (
                                    edited_title.strip()
                                )

                                st.session_state.editing_bom = None

                                rng_rerun()

                            else:

                                st.warning(
                                    "Please enter a BOM title."
                                )

                    with cancel_col:

                        if st.button(
                            "Cancel",
                            key=f"bom_edit_cancel_{i}",
                            use_container_width=True
                        ):

                            st.session_state.editing_bom = None

                            rng_rerun()

                # =============================================
                # NORMAL BOM CARD
                # =============================================

                else:

                    st.markdown(
                        f"""
                        <div class="bom-card">
                            <div class="bom-card-title">
                                {safe_title}
                            </div>
                            <div class="bom-card-text">
                                Bill of Materials
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    button_col1, button_col2, button_col3 = st.columns(3)

                    with button_col1:

                        open_button = st.button(
                            "Open",
                            key=f"bom_open_{i}",
                            use_container_width=True
                        )

                    with button_col2:

                        edit_button = st.button(
                            "Edit",
                            key=f"bom_edit_{i}",
                            use_container_width=True
                        )

                    with button_col3:

                        delete_button = st.button(
                            "Delete",
                            key=f"bom_delete_{i}",
                            use_container_width=True
                        )

                    if open_button:

                        st.session_state.selected_bom = i

                        rng_rerun()

                    if edit_button:

                        st.session_state.editing_bom = i
                        st.session_state.deleting_bom = None

                        rng_rerun()

                    if delete_button:

                        st.session_state.deleting_bom = i
                        st.session_state.editing_bom = None

                        rng_rerun()


elif page == "Employer Report":

    st.title("Employer Report")
    st.write("This tab will be developed later.")

# Save text fields, checkboxes and other edits that reran the page normally.
try:
    rng_save()
except Exception as exc:
    st.error("Unable to save changes to Supabase: " + str(exc))
