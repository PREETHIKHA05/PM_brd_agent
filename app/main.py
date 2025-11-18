import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import sqlite3
import json
from dotenv import load_dotenv
import io
from pathlib import Path

from services.llm import ask_clarifying_questions, generate_user_stories, style_check_stories
from services.export import export_markdown, export_csv

load_dotenv()

def init_db():
    conn = sqlite3.connect("pm_agent.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS brds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brd_id INTEGER,
        clarify_meta TEXT,
        questions TEXT,
        answers TEXT,
        stories TEXT,
        FOREIGN KEY (brd_id) REFERENCES brds(id)
    )
    """)

    conn.commit()
    conn.close()


# Ensure DB/tables exist before any UI code runs
init_db()


def save_run(brd_text, clarify_meta, questions_json, answers_json, stories_json):
    conn = sqlite3.connect("pm_agent.db", timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO brds (text) VALUES (?)", (brd_text,))
        brd_id = cur.lastrowid
        cur.execute(
            "INSERT INTO runs (brd_id, clarify_meta, questions, answers, stories) VALUES (?, ?, ?, ?, ?)",
            (brd_id, json.dumps(clarify_meta), json.dumps(questions_json), json.dumps(answers_json), json.dumps(stories_json))
        )
        conn.commit()
    finally:
        conn.close()


def get_last_runs(limit=5):
    conn = sqlite3.connect("pm_agent.db", timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT r.id, b.text, r.questions, r.answers, r.stories 
        FROM runs r 
        JOIN brds b ON r.brd_id = b.id 
        ORDER BY r.id DESC 
        LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        return rows
    finally:
        conn.close()


def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from a PDF file."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")


def extract_text_from_txt(txt_file) -> str:
    """Extract text from a TXT file."""
    try:
        content = txt_file.read().decode('utf-8')
        return content.strip()
    except Exception as e:
        raise ValueError(f"Failed to read TXT file: {e}")


def extract_text_from_document(uploaded_file) -> str:
    """Extract text from uploaded document (PDF or TXT)."""
    file_ext = Path(uploaded_file.name).suffix.lower()
    
    if file_ext == '.pdf':
        return extract_text_from_pdf(uploaded_file)
    elif file_ext == '.txt':
        return extract_text_from_txt(uploaded_file)
    else:
        raise ValueError(f"Unsupported file format: {file_ext}. Only PDF and TXT are supported.")


st.set_page_config(page_title="PM Agent", page_icon="🧩", layout="wide")
st.title("🧩 Product Manager Agent")

if "questions" not in st.session_state:
    st.session_state.questions = None
if "clarify_meta" not in st.session_state:
    st.session_state.clarify_meta = None
if "answers" not in st.session_state:
    st.session_state.answers = None
if "brd_text" not in st.session_state:
    st.session_state.brd_text = ""
if "domain" not in st.session_state:
    st.session_state.domain = "generic"
if "stories" not in st.session_state:
    st.session_state.stories = None
if "last_error" not in st.session_state:
    st.session_state.last_error = None

tab1, tab2, tab3 = st.tabs(["BRD → Questions", "Answer Questions", "Generate User Stories"])

with tab1:
    st.header("Step 1: Enter BRD")
    
    st.session_state.domain = st.selectbox(
        "Domain Profile ",
        ["generic", "Logistics", "Fintech", "Healthcare"],
        index=0
    )
    
    st.subheader("📄 Upload Document or Paste BRD")
    
    col_upload, col_paste = st.columns(2)
    
    with col_upload:
        st.write("**Upload Document**")
        uploaded_file = st.file_uploader(
            "Upload BRD (PDF or TXT)",
            type=["pdf", "txt"],
            key="brd_uploader"
        )
        
        if uploaded_file:
            try:
                extracted_text = extract_text_from_document(uploaded_file)
                st.session_state.brd_text = extracted_text
                st.success(f"Extracted text from {uploaded_file.name}")
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    
    brd_text = st.text_area(
        "BRD Content",
        value=st.session_state.brd_text,
        height=250,
        help="Paste your BRD text or upload a document above"
    )

    if st.button("Generate 8 Clarifying Questions"):
        if not brd_text.strip():
            st.error("Please paste a BRD first.")
        else:
            st.session_state.brd_text = brd_text
            with st.spinner("Generating questions..."):
                try:
                    output = ask_clarifying_questions(brd_text, st.session_state.domain)
                    st.session_state.questions = output["questions"]
                    st.session_state.clarify_meta = output["meta"]
                    st.session_state.last_error = None
                    st.success("✅ Generated 8 questions successfully!")
                except Exception as e:
                    st.session_state.last_error = str(e)
                    st.error(f"❌ Failed: {e}")
                    with st.expander("📋 Debug Info"):
                        st.write(f"**Error Details:**\n{st.session_state.last_error}")

    if st.session_state.questions:
        st.subheader("Generated Questions (JSON)")
        st.json(st.session_state.questions)
    
    st.markdown("---")
    st.subheader("📋 Last 5 Runs")
    last_runs = get_last_runs(5)
    
    if last_runs:
        for run_id, brd, questions_json, answers_json, stories_json in last_runs:
            with st.expander(f"Run #{run_id}"):
                st.write("**BRD:**")
                st.text(brd[:200] + "..." if len(brd) > 200 else brd)
                
                if questions_json:
                    st.write("**Questions:**")
                    st.json(json.loads(questions_json))
                
                if answers_json:
                    st.write("**Answers:**")
                    st.json(json.loads(answers_json))
                
                if stories_json:
                    st.write("**Stories:**")
                    st.json(json.loads(stories_json))
    else:
        st.info("No previous runs yet.")

with tab2:
    st.header("Step 2: Answer the Questions")

    if not st.session_state.questions:
        st.info("Generate questions first.")
    else:
        answers = {}
        for q in st.session_state.questions:
            answers[q["id"]] = st.text_area(f"{q['id']} — {q['text']}", height=80)

        if st.button("Save Answers"):
            st.session_state.answers = answers
            st.success("Answers saved!")

with tab3:
    st.header("Step 3: Generate User Stories")

    if not st.session_state.answers:
        st.info("Answer all questions first.")
    else:
        if st.button("Generate User Stories JSON"):
            with st.spinner("Generating stories..."):
                try:
                    result = generate_user_stories(
                        st.session_state.brd_text,
                        st.session_state.answers,
                        st.session_state.domain
                    )
                    st.session_state.stories = result
                    st.session_state.last_error = None
                    
                    check_result = style_check_stories(result)
                    
                    if not check_result["valid"]:
                        st.warning("⚠️ Style Issues Found:")
                        for issue in check_result["issues"]:
                            st.write(f"- {issue}")
                    else:
                        st.success("✅ All stories pass style check!")

                    save_run(
                        st.session_state.brd_text,
                        st.session_state.clarify_meta,
                        st.session_state.questions,
                        st.session_state.answers,
                        result
                    )

                    st.success("✅ User stories generated and saved!")
                    st.json(result)
                    
                    st.markdown("---")
                    st.subheader("📥 Export Options")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        md_content = export_markdown(result)
                        st.download_button(
                            label="📄 Markdown",
                            data=md_content,
                            file_name="stories.md",
                            mime="text/markdown"
                        )
                    
                    with col2:
                        csv_content = export_csv(result)
                        st.download_button(
                            label="📊 CSV (Jira)",
                            data=csv_content,
                            file_name="stories.csv",
                            mime="text/csv"
                        )
                    
                    with col3:
                        st.download_button(
                            label="📋 JSON",
                            data=json.dumps(result, indent=2),
                            file_name="stories.json",
                            mime="application/json"
                        )

                except Exception as e:
                    st.session_state.last_error = str(e)
                    st.error(f"❌ Failed: {e}")
                    with st.expander("📋 Debug Info"):
                        st.write(f"**Error Details:**\n{st.session_state.last_error}")

