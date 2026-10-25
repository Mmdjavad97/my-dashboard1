"""A consistent, private file library for each project's non-financial sections."""
from __future__ import annotations

import base64
import io
import mimetypes
from datetime import datetime
from html import escape
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st

SECTIONS = {"Meeting Minutes": "meeting_files", "Plans": "plan_files", "Documents": "documents"}
MAX_FILE_MB = 5
MAX_LIBRARY_MB = 20


def _persist_files(project, field, records, save):
    had_field = field in project
    previous = project.get(field)
    project[field] = records
    try:
        save()
    except Exception:
        if had_field:
            project[field] = previous
        else:
            project.pop(field, None)
        st.error("Could not save your files. Your previous records are intact; please try again.")
        return False
    return True


def _payload(record):
    try:
        return base64.b64decode(record.get("data", ""), validate=True)
    except (ValueError, TypeError):
        return None


def _file_actions(data, record, namespace, share_file):
    filename = record.get("filename", "")
    mime = record.get("mime") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with st.container(key=f"project_file_actions_{namespace}"):
        download, share = st.columns(2)
        with download:
            st.download_button("Download", data=data, file_name=filename, mime=mime,
                               key=f"{namespace}_download", on_click="ignore", use_container_width=True)
        if share_file is not None:
            with share:
                share_file(data, filename, mime)


def _preview(record, namespace, share_file):
    data = _payload(record)
    if data is None:
        st.error("This file could not be read. Please try downloading it again later.")
        return
    filename = record.get("filename", "")
    mime = record.get("mime") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    suffix = Path(filename).suffix.lower()
    if data:
        _file_actions(data, record, f"{namespace}_preview", share_file)
    if record.get("url"):
        from urllib.parse import urlparse
        parsed = urlparse(record["url"])
        if parsed.scheme in ("http", "https") and parsed.netloc:
            st.link_button("Open document link", record["url"])
        return
    if not data:
        st.info("No file content is available for this record.")
    elif suffix == ".pdf" or mime == "application/pdf":
        st.pdf(data, height=640, key=f"{namespace}_pdf", alt=f'Preview of {record["title"]}')
    elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}:
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(data))
            st.image(image, width="stretch")
        except Exception:
            st.info("An image preview is unavailable. Download the original file to open it.")
    elif suffix in {".txt", ".csv", ".md", ".json", ".log", ".xml", ".yaml", ".yml"}:
        try:
            text = data.decode("utf-8-sig")
            st.code(text[:200_000], language=None, wrap_lines=True)
            if len(text) > 200_000:
                st.caption("Showing the first part of this file. Download it to read everything.")
        except UnicodeDecodeError:
            st.info("A text preview is unavailable. Download the original file to open it.")
    else:
        st.info("Download this file to open it. In-app previews support PDFs, images, and text files.")


def render_project_files(projects, project_id, section, save, share_file=None):
    """Return True on the library screen, False while viewing one file."""
    project = projects[project_id]
    field = SECTIONS[section]
    records = project.get(field, [])
    namespace = f"project_files_{project_id}_{field}"
    view_key, upload_key = f"rng_{namespace}_view", f"rng_{namespace}_upload"
    edit_key, delete_key = f"rng_{namespace}_edit", f"rng_{namespace}_delete"
    st.markdown('''<style>
    [class*="st-key-project_files_"] button[kind^="primary"], [class*="st-key-project_files_"] button[kind^="primary"] p { background: #214b7f; border-color: #214b7f; color: #fff !important; }
    [class*="st-key-project_file_actions_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px; }
    [class*="st-key-project_file_actions_"] [data-testid="stColumn"] { min-width: 0 !important; }
    .rng-files-heading { display: flex; align-items: center; justify-content: space-between; color: #243e62; margin: 8px 0 18px; }
    .rng-files-heading strong { font-size: 24px; } .rng-files-heading span { color: #7286a1; font-size: 12px; }
    .rng-files-empty { text-align: center; background: #ffffffb8; border: 1px dashed #c3d2e7; border-radius: 18px; padding: 44px 20px; color: #6a809d; }
    .rng-files-empty strong { display: block; color: #304d73; font-size: 21px; margin-bottom: 10px; }
    [class*="st-key-project_file_card_"] { background: #fff; border: 1px solid #dce5f1; border-radius: 16px; padding: 22px; box-shadow: 0 6px 20px #16335408; }
    .rng-file-type { display: inline-block; color: #355f92; background: #eaf1fb; border: 1px solid #dce7f6; font-size: 11px; font-weight: 700; border-radius: 8px; padding: 7px 10px; margin-bottom: 12px; }
    .rng-file-title { color: #243b5b; font-size: 19px; font-weight: 700; overflow-wrap: anywhere; margin-bottom: 8px; }
    .rng-file-meta { color: #7286a1; font-size: 12px; overflow-wrap: anywhere; line-height: 1.7; margin-bottom: 14px; }
    [class*="st-key-project_file_card_"] [data-testid="stAlertContainer"] { background: #fff4d6; }
    [class*="st-key-project_file_card_"] [data-testid="stAlertContainer"] p { color: #61420b !important; }
    [class*="st-key-project_file_card_"] button { color: #355780; background: #f2f6fc; border: 1px solid #dce5f1; }
    [class*="st-key-project_file_card_"] [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px; }
    [class*="st-key-project_file_card_"] [data-testid="stColumn"] { min-width: 0 !important; }
    [class*="st-key-project_files_"] [data-testid="stFileUploaderDropzone"] { background: #f1f5fc; color: #243e62; border-color: #d6e2f2; }
    [class*="st-key-project_files_"] [data-testid="stWidgetLabel"] p { color: #4a6383 !important; }
    .st-key-project_files_board [data-testid="stHorizontalBlock"]:has([class*="st-key-project_file_card_"]) { align-items: stretch; }
    @media(max-width: 700px) {
      .st-key-project_files_board [data-testid="stHorizontalBlock"]:has([class*="st-key-project_file_card_"]) { flex-wrap: wrap; }
      .st-key-project_files_board [data-testid="stHorizontalBlock"]:has([class*="st-key-project_file_card_"]) > [data-testid="stColumn"] { min-width: 100%; }
      [class*="st-key-project_file_card_"] { padding: 18px; }
    }
    </style>''', unsafe_allow_html=True)
    selected = next((record for record in records if record["id"] == st.session_state.get(view_key)), None)
    if selected is not None:
        if st.button("Back to files", key=f"{namespace}_back"):
            st.session_state[view_key] = None
            st.rerun()
        st.subheader(selected["title"])
        st.caption(selected.get("filename") or "Document link")
        if selected.get("note"):
            st.write(selected["note"])
        _preview(selected, namespace, share_file)
        return False

    with st.container(key=namespace):
        st.markdown(f'<div class="rng-files-heading"><strong>{escape(section)}</strong><span>{len(records)} file{"s" if len(records) != 1 else ""}</span></div>', unsafe_allow_html=True)
        if st.button("+ Upload file", key=f"{namespace}_add", type="primary"):
            st.session_state[upload_key] = True
        if st.session_state.get(upload_key):
            version = st.session_state.get(f"rng_{namespace}_upload_version", 0)
            with st.form(f"{namespace}_form_{version}"):
                st.subheader("Upload a named file")
                st.caption(f"Choose a file from your computer or phone. Up to {MAX_FILE_MB} MB per file and {MAX_LIBRARY_MB} MB in this section.")
                title = st.text_input("File name", key=f"{namespace}_name_{version}", placeholder="Give this file a clear name")
                upload = st.file_uploader("Choose file", max_upload_size=MAX_FILE_MB, key=f"{namespace}_file_{version}")
                note = st.text_area("Description / revision (optional)", key=f"{namespace}_note_{version}")
                add_col, cancel_col = st.columns(2)
                with add_col:
                    add = st.form_submit_button("Save file", type="primary", use_container_width=True)
                with cancel_col:
                    cancel = st.form_submit_button("Cancel", use_container_width=True)
            if cancel:
                st.session_state[upload_key] = False
                st.session_state[f"rng_{namespace}_upload_version"] = version + 1
                st.rerun()
            if add:
                if not title.strip():
                    st.error("Enter a name for this file.")
                elif upload is None:
                    st.error("Choose a file to upload.")
                else:
                    data = upload.getvalue()
                    if len(data) > MAX_FILE_MB * 1024 * 1024 or sum(record.get("size", 0) for record in records) + len(data) > MAX_LIBRARY_MB * 1024 * 1024:
                        st.error("The file exceeds this section's upload limit.")
                    else:
                        record = {"id": uuid4().hex, "title": title.strip(), "filename": upload.name,
                                  "mime": upload.type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream",
                                  "size": len(data), "data": base64.b64encode(data).decode("ascii"), "note": note.strip(), "url": "",
                                  "uploaded_at": datetime.now(ZoneInfo("Asia/Tehran")).isoformat()}
                        if _persist_files(project, field, records + [record], save):
                            st.session_state[upload_key] = False
                            st.session_state[f"rng_{namespace}_upload_version"] = version + 1
                            st.rerun()
        if not records:
            st.markdown('<div class="rng-files-empty"><strong>Your files belong here</strong>Upload a file and give it a name to start this section.</div>', unsafe_allow_html=True)
        with st.container(key="project_files_board"):
            latest = list(reversed(records))
            for offset in range(0, len(latest), 3):
                for column, record in zip(st.columns(3), latest[offset:offset + 3]):
                    record_id = record["id"]
                    prefix = f"{namespace}_{record_id}"
                    with column, st.container(key=f"project_file_card_{record_id}"):
                        suffix = Path(record.get("filename", "")).suffix.lstrip(".").upper() or "LINK"
                        st.markdown(f'<span class="rng-file-type">{escape(suffix)}</span><div class="rng-file-title">{escape(record["title"])}</div>'
                                    f'<div class="rng-file-meta">{escape(record.get("filename") or "Document link")} · {record.get("size", 0) / 1024:,.0f} KB</div>', unsafe_allow_html=True)
                        if record.get("note"):
                            st.write(record["note"])
                        if st.session_state.get(edit_key) == record_id:
                            with st.form(f"{prefix}_rename_form"):
                                renamed = st.text_input("File name", value=record["title"], key=f"{prefix}_rename_name")
                                rename = st.form_submit_button("Save name", use_container_width=True)
                                cancel = st.form_submit_button("Cancel", use_container_width=True)
                            if cancel:
                                st.session_state[edit_key] = None
                                st.rerun()
                            if rename:
                                if not renamed.strip():
                                    st.error("Enter a name for this file.")
                                elif _persist_files(project, field, [{**item, "title": renamed.strip()} if item["id"] == record_id else item for item in records], save):
                                    st.session_state[edit_key] = None
                                    st.rerun()
                        elif st.session_state.get(delete_key) == record_id:
                            st.warning("Delete this file from this project section? This cannot be undone.")
                            yes, no = st.columns(2)
                            with yes:
                                if st.button("Yes, delete", key=f"{prefix}_confirm_delete", use_container_width=True):
                                    if _persist_files(project, field, [item for item in records if item["id"] != record_id], save):
                                        st.session_state[delete_key] = None
                                        st.rerun()
                            with no:
                                if st.button("Cancel", key=f"{prefix}_cancel_delete", use_container_width=True):
                                    st.session_state[delete_key] = None
                                    st.rerun()
                        else:
                            if st.button("View file", key=f"{prefix}_view", use_container_width=True):
                                st.session_state[view_key] = record_id
                                st.rerun()
                            data = _payload(record)
                            if record.get("filename") and data is not None:
                                _file_actions(data, record, prefix, share_file)
                            edit_col, delete_col = st.columns(2)
                            with edit_col:
                                if st.button("Rename", key=f"{prefix}_rename", use_container_width=True):
                                    st.session_state[edit_key] = record_id
                                    st.session_state[delete_key] = None
                                    st.session_state.pop(f"{prefix}_rename_name", None)
                                    st.rerun()
                            with delete_col:
                                if st.button("Delete", key=f"{prefix}_delete", use_container_width=True):
                                    st.session_state[delete_key] = record_id
                                    st.session_state[edit_key] = None
                                    st.rerun()
    return True
