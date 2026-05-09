"""
dashboard.py
------------
Streamlit workspace for monitoring campaigns and managing contacts.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import contextlib
import glob
import io
import os
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src.contact_reader import load_contacts, load_reminders
from src.email_sender import EmailSender, is_valid_email
from src.report_generator import generate_report
from src.status_tracker import StatusTracker
from src.template_engine import TemplateEngine


CONTACTS_PATH = Path("data/contacts.csv")
OUTPUT_DIR = Path("outputs")
LOG_PATH = Path("logs/email_log.txt")
REMINDERS_PATH = Path("data/reminders.csv")
TEMPLATES_DIR = Path("templates")

REQUIRED_CONTACT_COLUMNS = [
    "id",
    "name",
    "email",
    "department",
    "event",
    "event_date",
    "custom_message",
]

CONTACT_COLUMNS = REQUIRED_CONTACT_COLUMNS + ["send_enabled"]


st.set_page_config(
    page_title="Email Automation Dashboard",
    page_icon="email",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --bg: #07090d;
            --bg-2: #0b1117;
            --ink: #f6f7fb;
            --muted: #9aa7b8;
            --muted-2: #687386;
            --line: rgba(148, 163, 184, 0.18);
            --line-strong: rgba(148, 163, 184, 0.32);
            --panel: rgba(13, 18, 26, 0.84);
            --panel-2: rgba(18, 25, 36, 0.92);
            --field: rgba(8, 13, 20, 0.82);
            --brand: #14b8a6;
            --brand-2: #a3e635;
            --violet: #8b5cf6;
            --amber: #f59e0b;
            --ok: #22c55e;
            --warn: #f59e0b;
            --bad: #fb7185;
        }
        .stApp {
            background:
                radial-gradient(circle at 14% 8%, rgba(20, 184, 166, 0.20), transparent 28rem),
                radial-gradient(circle at 86% 3%, rgba(139, 92, 246, 0.16), transparent 24rem),
                linear-gradient(180deg, #06080c 0%, #0a1017 46%, #080a0f 100%);
            color: var(--ink);
        }
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.25rem;
            max-width: 1440px;
        }
        section[data-testid="stSidebar"] {
            background: rgba(5, 8, 13, 0.96);
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] * {
            color: var(--ink);
        }
        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1.35rem 1.45rem;
            border: 1px solid var(--line-strong);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(20, 184, 166, 0.12), transparent 34%),
                linear-gradient(180deg, rgba(18, 25, 36, 0.92), rgba(10, 14, 22, 0.92));
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.34);
            margin-bottom: 1.25rem;
            position: relative;
            overflow: hidden;
        }
        .app-header::after {
            content: "";
            position: absolute;
            inset: auto 1.5rem 0 1.5rem;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(163, 230, 53, 0.65), transparent);
        }
        .kicker {
            color: var(--brand-2);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .app-header h1 {
            font-size: 2.35rem;
            line-height: 1.2;
            margin: 0;
            letter-spacing: 0;
            color: var(--ink);
        }
        .app-header p {
            margin: 0.35rem 0 0 0;
            color: var(--muted);
            max-width: 680px;
        }
        .header-badge {
            border: 1px solid rgba(20, 184, 166, 0.42);
            background: rgba(20, 184, 166, 0.10);
            color: #ccfbf1;
            border-radius: 999px;
            padding: 0.45rem 0.8rem;
            font-weight: 700;
            white-space: nowrap;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);
        }
        .command-panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1.15rem 1.2rem;
            background: var(--panel);
            box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22);
            margin-bottom: 1rem;
            backdrop-filter: blur(18px);
        }
        .command-panel.accent {
            border-color: rgba(20, 184, 166, 0.34);
            background:
                linear-gradient(135deg, rgba(20, 184, 166, 0.12), transparent 42%),
                var(--panel);
        }
        .command-panel h3 {
            margin: 0 0 0.25rem 0;
            color: var(--ink);
            font-size: 1.18rem;
        }
        .command-panel p {
            margin: 0;
            color: var(--muted);
        }
        .panel-eyebrow {
            color: var(--brand);
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }
        .mini-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            background: var(--panel-2);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 12px 28px rgba(0,0,0,0.18);
        }
        .mini-card strong {
            color: var(--ink);
            display: block;
            font-size: 1.35rem;
            line-height: 1.15;
        }
        .mini-card span {
            color: var(--muted);
            font-size: 0.9rem;
        }
        .mini-card.ready {
            border-color: rgba(163, 230, 53, 0.28);
        }
        .mini-card.warn {
            border-color: rgba(245, 158, 11, 0.28);
        }
        .section-note {
            color: var(--muted);
            font-size: 0.95rem;
            margin-top: -0.5rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel-2);
            padding: 0.85rem 1rem;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.20);
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--ink);
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
            color: var(--brand-2);
        }
        div[data-testid="stTabs"] button {
            font-weight: 700;
            color: var(--muted);
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--ink);
            border-bottom-color: var(--brand) !important;
        }
        div[data-testid="stMarkdownContainer"] h4,
        div[data-testid="stMarkdownContainer"] h3,
        h1, h2, h3, h4, h5, h6,
        label, p {
            color: var(--ink);
        }
        [data-testid="stCaptionContainer"],
        .st-emotion-cache-1wivap2,
        small {
            color: var(--muted) !important;
        }
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        textarea,
        input {
            background: var(--field) !important;
            border-color: var(--line) !important;
            color: var(--ink) !important;
        }
        div[data-baseweb="radio"] label,
        div[data-testid="stCheckbox"] label {
            color: var(--ink) !important;
        }
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 18px 42px rgba(0,0,0,0.18);
        }
        .stAlert {
            border-radius: 8px;
        }
        .stDownloadButton > button,
        .stButton > button {
            background: rgba(18, 25, 36, 0.95);
            border: 1px solid var(--line-strong);
            color: var(--ink);
            border-radius: 8px;
            font-weight: 800;
            transition: all 140ms ease;
        }
        .stDownloadButton > button:hover,
        .stButton > button:hover {
            border-color: rgba(20, 184, 166, 0.70);
            color: #ccfbf1;
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #14b8a6 0%, #84cc16 100%);
            border-color: rgba(163, 230, 53, 0.6);
            color: #031014;
            box-shadow: 0 16px 34px rgba(20, 184, 166, 0.24);
        }
        .status-sent { color: var(--ok); font-weight: 700; }
        .status-failed { color: var(--bad); font-weight: 700; }
        .status-rejected { color: var(--warn); font-weight: 700; }
        .status-simulated { color: var(--brand); font-weight: 700; }
        @media (max-width: 720px) {
            .app-header {
                align-items: flex-start;
                flex-direction: column;
            }
            .app-header h1 {
                font-size: 1.8rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
        <div>
            <div class="kicker">Operations Console</div>
            <h1>Email Automation & Reminder System</h1>
            <p>Premium campaign control, contact readiness, delivery telemetry, and report review in one dark workspace.</p>
        </div>
        <div class="header-badge">SaaS Command Center</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def bool_from_csv(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "n", "off", "disabled"}


def is_blank_row(row: pd.Series) -> bool:
    for column in REQUIRED_CONTACT_COLUMNS:
        value = row.get(column, "")
        if pd.notna(value) and str(value).strip():
            return False
    return True


def normalize_contacts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for column in CONTACT_COLUMNS:
        if column not in df.columns:
            df[column] = True if column == "send_enabled" else ""

    df = df.dropna(how="all")
    if not df.empty:
        df = df[~df.apply(is_blank_row, axis=1)]

    for column in REQUIRED_CONTACT_COLUMNS:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df["send_enabled"] = df["send_enabled"].apply(bool_from_csv)

    next_id = 1
    existing_ids = pd.to_numeric(df["id"], errors="coerce").dropna()
    if not existing_ids.empty:
        next_id = int(existing_ids.max()) + 1

    for index, value in df["id"].items():
        if not str(value).strip():
            df.at[index, "id"] = str(next_id)
            next_id += 1

    extra_columns = [column for column in df.columns if column not in CONTACT_COLUMNS]
    return df[CONTACT_COLUMNS + extra_columns].reset_index(drop=True)


def load_contacts_df() -> pd.DataFrame:
    if not CONTACTS_PATH.exists():
        return pd.DataFrame(columns=CONTACT_COLUMNS)
    return normalize_contacts(pd.read_csv(CONTACTS_PATH))


def save_contacts_df(df: pd.DataFrame) -> None:
    CONTACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalize_contacts(df).to_csv(CONTACTS_PATH, index=False)


def validate_contacts(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, row in df.iterrows():
        issues = []
        for column in REQUIRED_CONTACT_COLUMNS:
            if not str(row.get(column, "")).strip():
                issues.append(f"missing {column}")

        email = str(row.get("email", "")).strip()
        if email:
            valid, message = is_valid_email(email)
            if not valid:
                issues.append(message)

        rows.append(
            {
                "row": index + 1,
                "name": row.get("name", ""),
                "email": email,
                "send_enabled": bool_from_csv(row.get("send_enabled", True)),
                "issues": "; ".join(issues),
                "ready": not issues and bool_from_csv(row.get("send_enabled", True)),
            }
        )

    validation = pd.DataFrame(rows)
    if not validation.empty:
        duplicate_mask = validation["email"].ne("") & validation["email"].duplicated(keep=False)
        validation.loc[duplicate_mask, "issues"] = validation.loc[duplicate_mask, "issues"].apply(
            lambda value: f"{value}; duplicate email".strip("; ")
        )
        validation.loc[duplicate_mask, "ready"] = False
    return validation


@st.cache_data
def load_report(filepath: str) -> pd.DataFrame:
    return pd.read_csv(filepath)


def color_status(value: str) -> str:
    colors = {
        "sent": "color: #22c55e",
        "failed": "color: #fb7185",
        "rejected": "color: #f59e0b",
        "simulated": "color: #14b8a6",
    }
    return colors.get(value, "")


def apply_chart_theme(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dbeafe"},
        legend={"font": {"color": "#dbeafe"}},
    )
    fig.update_xaxes(
        gridcolor="rgba(148, 163, 184, 0.14)",
        linecolor="rgba(148, 163, 184, 0.24)",
        tickfont={"color": "#9aa7b8"},
        title_font={"color": "#9aa7b8"},
    )
    fig.update_yaxes(
        gridcolor="rgba(148, 163, 184, 0.14)",
        linecolor="rgba(148, 163, 184, 0.24)",
        tickfont={"color": "#9aa7b8"},
        title_font={"color": "#9aa7b8"},
    )
    return fig


def run_campaign_from_dashboard(subject: str, dry_run: bool) -> tuple[list[dict], dict, str, int]:
    load_dotenv()

    contacts = load_contacts(str(CONTACTS_PATH))
    reminders = load_reminders(str(REMINDERS_PATH)) if REMINDERS_PATH.exists() else []
    if not contacts:
        raise ValueError("No contacts are selected for sending.")

    sender_email = os.getenv("SENDER_EMAIL", "demo@gmail.com")
    sender_password = os.getenv("SENDER_PASSWORD", "")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not dry_run and not sender_password:
        raise ValueError("Live send needs SENDER_PASSWORD in your .env file.")

    engine = TemplateEngine(templates_dir=str(TEMPLATES_DIR))
    sender = EmailSender(
        sender_email=sender_email,
        sender_password=sender_password,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        dry_run=dry_run,
    )

    progress = st.progress(0)
    status_line = st.empty()
    results = []
    total = len(contacts)

    for index, contact in enumerate(contacts, start=1):
        status_line.write(f"Processing {index}/{total}: {contact.get('name', 'Unknown')}")
        context = {
            "name": contact.get("name", ""),
            "event": contact.get("event", ""),
            "event_date": contact.get("event_date", ""),
            "department": contact.get("department", ""),
            "custom_message": contact.get("custom_message", ""),
        }
        html = engine.render("reminder_template.html", context)
        text = engine.render("reminder_template.txt", context)
        with contextlib.redirect_stdout(io.StringIO()):
            results.append(
                sender.send_email(
                    recipient_email=contact.get("email", ""),
                    recipient_name=contact.get("name", ""),
                    subject=subject,
                    html_content=html,
                    txt_content=text,
                )
            )
        progress.progress(index / total)
        if not dry_run and index < total:
            time.sleep(1)

    tracker = StatusTracker()
    tracker.add_results(results)
    summary = tracker.get_summary()
    with contextlib.redirect_stdout(io.StringIO()):
        report_path = generate_report(results, output_dir=str(OUTPUT_DIR))
    load_report.clear()
    status_line.write("Campaign finished.")
    return results, summary, report_path, len(reminders)


def render_launch_panel() -> None:
    contacts_df = load_contacts_df()
    validation = validate_contacts(contacts_df)
    selected_count = int(contacts_df["send_enabled"].sum()) if not contacts_df.empty else 0
    ready_count = int(validation["ready"].sum()) if not validation.empty else 0
    issue_count = int(validation["issues"].ne("").sum()) if not validation.empty else 0

    st.markdown(
        """
        <div class="command-panel accent">
            <div class="panel-eyebrow">Launch desk</div>
            <h3>Campaign Launch</h3>
            <p>Trigger a safe dry run or confirmed live send using the saved contact selection.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stat_cols = st.columns(3)
    stat_cols[0].markdown(
        f"<div class='mini-card'><strong>{selected_count}</strong><span>Selected contacts</span></div>",
        unsafe_allow_html=True,
    )
    stat_cols[1].markdown(
        f"<div class='mini-card ready'><strong>{ready_count}</strong><span>Ready contacts</span></div>",
        unsafe_allow_html=True,
    )
    stat_cols[2].markdown(
        f"<div class='mini-card warn'><strong>{issue_count}</strong><span>Validation issues</span></div>",
        unsafe_allow_html=True,
    )

    control_cols = st.columns([2, 1, 1])
    with control_cols[0]:
        subject = st.text_input("Subject", value="Reminder: Your Upcoming Event")
    with control_cols[1]:
        mode = st.radio("Mode", ["Dry run", "Live send"], horizontal=True)
    with control_cols[2]:
        live_confirmed = True
        if mode == "Live send":
            live_confirmed = st.checkbox("Confirm live send")
        else:
            st.caption("Dry run creates a report without sending real email.")

    dry_run = mode == "Dry run"
    disabled = selected_count == 0 or not subject.strip() or (not dry_run and not live_confirmed)
    button_label = "Run dry-run campaign" if dry_run else "Send live campaign"

    if st.button(button_label, type="primary", disabled=disabled, use_container_width=True):
        try:
            with st.spinner("Running campaign..."):
                results, summary, report_path, reminder_count = run_campaign_from_dashboard(subject.strip(), dry_run)
            st.success(f"Campaign complete. Report saved to {report_path}.")
            result_cols = st.columns(5)
            result_cols[0].metric("Processed", summary["total"])
            result_cols[1].metric("Sent", summary["sent"])
            result_cols[2].metric("Simulated", summary["simulated"])
            result_cols[3].metric("Rejected", summary["rejected"])
            result_cols[4].metric("Failed", summary["failed"])
            st.caption(f"Reminder rows loaded: {reminder_count}")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(str(exc))


def render_contacts_tab() -> None:
    st.markdown(
        """
        <div class="command-panel">
            <div class="panel-eyebrow">Audience CRM</div>
            <h3>Contact Management</h3>
            <p>Edit the audience list, pause recipients, and keep campaign data clean.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    contacts_df = load_contacts_df()
    validation = validate_contacts(contacts_df)

    total_contacts = len(contacts_df)
    enabled_count = int(contacts_df["send_enabled"].sum()) if total_contacts else 0
    disabled_count = total_contacts - enabled_count
    ready_count = int(validation["ready"].sum()) if not validation.empty else 0
    issue_count = int(validation["issues"].ne("").sum()) if not validation.empty else 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total contacts", total_contacts)
    metric_cols[1].metric("Selected to send", enabled_count)
    metric_cols[2].metric("Paused", disabled_count)
    metric_cols[3].metric("Ready after validation", ready_count, delta=f"-{issue_count} issues" if issue_count else "0 issues")

    controls_left, controls_right = st.columns([2, 1])
    with controls_left:
        search = st.text_input("Search contacts", placeholder="Search name, email, department, or event")
    with controls_right:
        visibility = st.selectbox("Show", ["All contacts", "Selected to send", "Paused contacts", "Rows with issues"])

    filtered_preview = contacts_df.copy()
    if search:
        pattern = re.escape(search.strip())
        text_columns = ["name", "email", "department", "event", "custom_message"]
        mask = filtered_preview[text_columns].apply(
            lambda col: col.astype(str).str.contains(pattern, case=False, na=False, regex=True)
        ).any(axis=1)
        filtered_preview = filtered_preview[mask]

    if visibility == "Selected to send":
        filtered_preview = filtered_preview[filtered_preview["send_enabled"]]
    elif visibility == "Paused contacts":
        filtered_preview = filtered_preview[~filtered_preview["send_enabled"]]
    elif visibility == "Rows with issues" and not validation.empty:
        filtered_preview = filtered_preview.loc[validation[validation["issues"].ne("")].index]

    with st.expander("Filtered review", expanded=False):
        st.dataframe(filtered_preview, use_container_width=True, hide_index=True)

    st.markdown("#### Editable Contact List")
    st.caption("Use the send_enabled checkbox to include or pause a contact for the next campaign.")

    edited_df = st.data_editor(
        contacts_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "send_enabled": st.column_config.CheckboxColumn("send_enabled", help="Checked contacts are included by main.py."),
            "id": st.column_config.TextColumn("id", required=False),
            "name": st.column_config.TextColumn("name", required=True),
            "email": st.column_config.TextColumn("email", required=True),
            "department": st.column_config.TextColumn("department", required=True),
            "event_date": st.column_config.TextColumn("event_date", required=True, help="Use YYYY-MM-DD format."),
            "custom_message": st.column_config.TextColumn("custom_message", width="large"),
        },
        key="contacts_editor",
    )

    edited_df = normalize_contacts(edited_df)
    edited_validation = validate_contacts(edited_df)

    action_cols = st.columns([1, 1, 1, 2])
    with action_cols[0]:
        save_clicked = st.button("Save contacts", type="primary", use_container_width=True)
    with action_cols[1]:
        if st.button("Select all", use_container_width=True):
            edited_df["send_enabled"] = True
            save_contacts_df(edited_df)
            st.success("All contacts are selected for sending.")
            rerun_app()
    with action_cols[2]:
        if st.button("Pause all", use_container_width=True):
            edited_df["send_enabled"] = False
            save_contacts_df(edited_df)
            st.warning("All contacts are paused.")
            rerun_app()
    with action_cols[3]:
        st.download_button(
            "Download contacts CSV",
            data=edited_df.to_csv(index=False),
            file_name=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if save_clicked:
        blocking_issues = edited_validation[
            edited_validation["issues"].str.contains("missing id|missing name|missing email|duplicate email", na=False)
        ]
        if not blocking_issues.empty:
            st.error("Fix missing names/emails/ids or duplicate emails before saving.")
            st.dataframe(blocking_issues, use_container_width=True, hide_index=True)
        else:
            save_contacts_df(edited_df)
            st.success(f"Saved {len(edited_df)} contacts to {CONTACTS_PATH}.")
            rerun_app()

    st.markdown("#### Validation")
    if edited_validation.empty:
        st.info("No contacts yet. Add a row in the editable table above.")
    else:
        issue_rows = edited_validation[edited_validation["issues"].ne("")]
        if issue_rows.empty:
            st.success("All saved contacts look ready.")
        else:
            st.warning("Some contacts need attention. They can stay saved, but invalid emails will be rejected during sending.")
            st.dataframe(issue_rows, use_container_width=True, hide_index=True)


def render_campaign_tab() -> None:
    render_launch_panel()

    st.markdown("#### Campaign Overview")

    report_files = glob.glob(str(OUTPUT_DIR / "email_report_*.csv"))
    report_files.sort(reverse=True)

    if not report_files:
        st.info("No campaign reports found yet. Run a dry-run campaign from the launch panel to generate one.")
        return

    selected_file = st.selectbox(
        "Select report",
        report_files,
        format_func=lambda path: os.path.basename(path),
    )

    if st.button("Refresh report data"):
        load_report.clear()
        rerun_app()

    df = load_report(selected_file)

    total = len(df)
    sent = len(df[df["status"] == "sent"])
    simulated = len(df[df["status"] == "simulated"])
    failed = len(df[df["status"] == "failed"])
    rejected = len(df[df["status"] == "rejected"])
    success_rate = ((sent + simulated) / total * 100) if total else 0

    cols = st.columns(5)
    cols[0].metric("Total emails", total)
    cols[1].metric("Sent / simulated", sent + simulated, delta=f"+{sent + simulated}")
    cols[2].metric("Rejected", rejected, delta=f"-{rejected}" if rejected else "0")
    cols[3].metric("Failed", failed, delta=f"-{failed}" if failed else "0")
    cols[4].metric("Success rate", f"{success_rate:.1f}%")

    left, right = st.columns(2)
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    color_map = {"sent": "#22c55e", "simulated": "#14b8a6", "rejected": "#f59e0b", "failed": "#fb7185"}

    with left:
        st.markdown("#### Status distribution")
        fig_pie = px.pie(
            status_counts,
            values="Count",
            names="Status",
            color="Status",
            color_discrete_map=color_map,
            hole=0.45,
        )
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        apply_chart_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True)

    with right:
        st.markdown("#### Emails by status")
        fig_bar = px.bar(
            status_counts,
            x="Status",
            y="Count",
            color="Status",
            color_discrete_map=color_map,
            text="Count",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(showlegend=False, margin=dict(t=20, b=0))
        apply_chart_theme(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("#### Detailed email records")
    status_filter = st.multiselect(
        "Filter by status",
        options=df["status"].unique().tolist(),
        default=df["status"].unique().tolist(),
    )
    filtered_df = df[df["status"].isin(status_filter)]
    styled_df = filtered_df.style.map(color_status, subset=["status"])
    st.dataframe(styled_df, use_container_width=True, height=350)

    download_col, log_col = st.columns(2)
    with download_col:
        st.markdown("#### Download report")
        st.download_button(
            "Download filtered report",
            data=filtered_df.to_csv(index=False),
            file_name=f"filtered_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with log_col:
        st.markdown("#### Email log preview")
        if LOG_PATH.exists():
            recent_logs = "".join(LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-15:])
            st.text_area("Recent logs", recent_logs, height=200)
        else:
            st.info("No log file found yet.")


with st.sidebar:
    st.title("Controls")
    st.caption("Use contacts first, then run the campaign.")
    st.markdown("---")
    if st.button("Refresh app", use_container_width=True):
        load_report.clear()
        rerun_app()

campaign_tab, contacts_tab = st.tabs(["Campaign dashboard", "Contact management"])

with campaign_tab:
    render_campaign_tab()

with contacts_tab:
    render_contacts_tab()

st.markdown("---")
st.caption("Email Automation & Reminder System | Python + Streamlit")
