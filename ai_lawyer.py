import streamlit as st
import sqlite3
import json
import spacy
import pyttsx3
import speech_recognition as sr
import tempfile
import os
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
from fpdf import FPDF
import io
import PyPDF2

################################################################################
# DISCLAIMER: This code is for demonstration purposes only and does not provide
# real legal advice. Always consult a qualified attorney for authoritative guidance.
################################################################################

#####################
# Global Constants
#####################
COUNTRIES = ["USA", "UK", "Pakistan", "Canada", "India", "International"]

#####################
# SETUP PAGE & CUSTOM CSS
#####################
st.set_page_config(page_title="Legal AI Advisor", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}

body {
    background: linear-gradient(120deg, #1e1e1e, #2b2b2b) fixed;
}

h1, h2, h3, h4 {
    color: #f0c929;
    text-shadow: 1px 1px 2px #000;
}

.stButton>button {
    background-color: #f0c929 !important;
    color: #000 !important;
    border-radius: 8px !important;
    border: none !important;
    box-shadow: 0 0 10px rgba(240,201,41,0.5) !important;
}

.stTextInput>div>div>input, 
.stTextArea>div>div>textarea, 
.stSelectbox>div>div>select {
    background-color: #333 !important; 
    color: #fff !important;
    border: 1px solid #555 !important;
}

.stProgress>div>div {
    background-color: #f0c929;
}
</style>
""", unsafe_allow_html=True)

#####################
# HERO SECTION
#####################
col1, col2 = st.columns([1, 3])
with col1:
    # Replace with your simpler path (file physically named "logo.webp")
    st.image("D:\AI lawyer\DALL·E 2025-02-14 02.55.41 - A professional and minimalistic logo for a legal research AI application. The design should feature a stylized balance scale, symbolizing justice, int.webp", width=120)

with col2:
    st.markdown("<h1 style='margin-bottom:0'>Legal AI Advisor</h1>", unsafe_allow_html=True)
    st.markdown("<p style='margin-top:0; color:#f0c929'>Your one‑stop hub for legal insights and analysis</p>", unsafe_allow_html=True)

#####################
# NLP, TTS, & SPEECH SETUP
#####################
nlp = spacy.load("en_core_web_sm")
engine = pyttsx3.init()
r = sr.Recognizer()

#####################
# DATABASE SETUP (SQLite for Users & Query History)
#####################
DB_NAME = "legal_ai_users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS query_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, query TEXT)''')
    conn.commit()
    conn.close()

def register_user(username, password):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?,?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def validate_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

def save_query(username, query):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO query_history (username, query) VALUES (?,?)", (username, query))
    conn.commit()
    conn.close()

def get_query_history(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT query FROM query_history WHERE username=?", (username,))
    queries = c.fetchall()
    conn.close()
    return [q[0] for q in queries]

init_db()

#####################
# SESSION STATE INITIALIZATION
#####################
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "voice_input" not in st.session_state:
    st.session_state.voice_input = ""
if "country" not in st.session_state:
    st.session_state.country = "USA"

#####################
# USER AUTHENTICATION & REGISTRATION (Using SQLite)
#####################
if not st.session_state.authenticated:
    st.sidebar.header("Authentication")
    auth_choice = st.sidebar.radio("Select Option", ["Login", "Register"])
    if auth_choice == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if validate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.success("Logged in!")
            else:
                st.error("Invalid credentials. Please try again.")
    else:
        new_username = st.sidebar.text_input("New Username")
        new_password = st.sidebar.text_input("New Password", type="password")
        confirm_password = st.sidebar.text_input("Confirm Password", type="password")
        if st.sidebar.button("Register"):
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif register_user(new_username, new_password):
                st.session_state.authenticated = True
                st.session_state.current_user = new_username
                st.success("Registration successful, you are now logged in!")
            else:
                st.error("Username already exists!")
    st.stop()

#####################
# PDF SCRAPING FUNCTION (for PDF links)
#####################
def scrape_pdf(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file_stream = io.BytesIO(response.content)
            reader = PyPDF2.PdfReader(file_stream)
            text_content = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            return "\n".join(text_content)
        return ""
    except Exception as e:
        st.error(f"PDF scraping error: {e}")
        return ""

#####################
# GLOBAL LAWS DATABASE (Simulated)
#####################
ALL_LAWS = {
    "legal": [
        {
            "title": "Freedom of Speech",
            "details": (
                "Freedom of Speech is the right to articulate one's opinions without fear of retaliation. "
                "Subject to limitations such as defamation and incitement laws."
            ),
        },
        {
            "title": "Right to Privacy",
            "details": (
                "The right to privacy protects individuals against unlawful searches and surveillance, "
                "and is supported by data protection regulations like GDPR."
            ),
        },
        {
            "title": "Right to Fair Trial",
            "details": (
                "A fair trial involves due process, the right to counsel, and the presumption of innocence."
            ),
        },
        {
            "title": "Ownership of Property",
            "details": (
                "Ownership rights include possession, use, and transfer of property, subject to zoning laws and eminent domain."
            ),
        },
        {
            "title": "Business Contracts",
            "details": (
                "Contracts are legally binding agreements requiring offer, acceptance, and consideration. Breaches can lead to damages."
            ),
        },
        {
            "title": "Marriage and Divorce Laws",
            "details": (
                "These laws govern marriage rights and divorce proceedings, including custody and support."
            ),
        },
        {
            "title": "Tax Compliance",
            "details": (
                "Tax compliance involves proper filing and payment of taxes. Non‑compliance can lead to fines or criminal charges."
            ),
        },
        {
            "title": "Intellectual Property Rights",
            "details": (
                "IP laws protect patents, copyrights, trademarks, and trade secrets. Enforcement varies by jurisdiction."
            )
        }
    ],
    "illegal": [
        {
            "title": "Theft and Robbery",
            "details": (
                "Theft is taking property without permission, while robbery involves force. Penalties vary with the offense."
            ),
        },
        {
            "title": "Hacking Without Consent",
            "details": (
                "Unauthorized access to computer systems is illegal and may result in fines or imprisonment."
            ),
        },
        {
            "title": "Drug Trafficking",
            "details": (
                "Drug trafficking involves the illegal distribution of controlled substances with severe penalties."
            ),
        },
        {
            "title": "Violent Crimes",
            "details": (
                "Violent crimes such as assault and murder carry harsh penalties and long-term imprisonment."
            ),
        },
        {
            "title": "Bribery and Corruption",
            "details": (
                "Bribery and corruption involve illicit payments to influence actions, which are illegal."
            ),
        },
        {
            "title": "Cybercrime",
            "details": (
                "Cybercrimes include fraud, phishing, and identity theft, with specialized laws addressing these offenses."
            ),
        },
        {
            "title": "Human Trafficking",
            "details": (
                "Human trafficking is the exploitation of people for labor or sexual purposes, carrying strict penalties."
            ),
        },
        {
            "title": "Tax Evasion",
            "details": (
                "Tax evasion is the illegal avoidance of tax payments through unreported income or false deductions."
            )
        }
    ]
}

#####################
# LOCAL LAWS DATABASE (Simulated)
#####################
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
for country in COUNTRIES:
    file_path = DATA_DIR / f"laws_{country.lower()}.json"
    if not file_path.exists():
        sample_laws = [
            {
                "title": "Sample Legal Law",
                "text": (
                    "This sample legal law grants individuals rights in accordance with constitutional protections."
                ),
                "type": "Legal",
                "enforcement_agency": "Sample Agency"
            },
            {
                "title": "Sample Illegal Act",
                "text": (
                    "This sample illegal act is prohibited unless an exemption is granted by authority."
                ),
                "type": "Illegal",
                "enforcement_agency": "Law Enforcement"
            }
        ]
        with open(file_path, "w") as f:
            json.dump(sample_laws, f)

#####################
# LEGAL KNOWLEDGE BASE CLASS
#####################
class LegalKnowledgeBase:
    def __init__(self, country):
        self.country = country
        self.laws = self._load_laws()
    
    def _load_laws(self):
        try:
            with open(DATA_DIR / f"laws_{self.country.lower()}.json") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def get_relevant_laws(self, keywords):
        return [law for law in self.laws if any(kw.lower() in law["text"].lower() for kw in keywords)]

#####################
# WEB SEARCH FUNCTIONS
#####################
def duckduckgo_search(query):
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        response = requests.get(url)
        results = []
        if response.status_code == 200:
            data = response.json()
            related = data.get("RelatedTopics", [])
            for item in related:
                if "Text" in item:
                    title = item.get("Text", "")
                    link = item.get("FirstURL", "")
                    snippet = item.get("Text", "")
                    results.append({"title": title, "link": link, "snippet": snippet})
                elif "Name" in item and "Topics" in item:
                    for sub in item["Topics"]:
                        sub_title = sub.get("Text", "")
                        sub_link = sub.get("FirstURL", "")
                        sub_snippet = sub.get("Text", "")
                        results.append({"title": sub_title, "link": sub_link, "snippet": sub_snippet})
        return results
    except Exception as e:
        st.error(f"Web search error: {str(e)}")
        return []

def scrape_page(url, max_paragraphs=2):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            paragraphs = soup.find_all("p")
            text_content = [p.get_text().strip() for p in paragraphs[:max_paragraphs] if p.get_text().strip()]
            return "\n".join(text_content)
        return ""
    except:
        return ""

def comprehensive_web_research(query, max_results=5):
    search_results = duckduckgo_search(query)
    limited_results = search_results[:max_results]
    for item in limited_results:
        link = item.get("link", "")
        if link:
            if link.lower().endswith(".pdf"):
                scraped = scrape_pdf(link)
            else:
                scraped = scrape_page(link)
            item["scraped_text"] = scraped
        else:
            item["scraped_text"] = ""
    return limited_results

#####################
# LOOPHOLE FINDER
#####################
def find_potential_loopholes(text, window=30):
    keywords = ["unless", "except", "exempt", "provided that", "exception", "exemption", "conditional", "if "]
    text_lower = text.lower()
    results = []
    for kw in keywords:
        start = 0
        while True:
            idx = text_lower.find(kw, start)
            if idx == -1:
                break
            snippet_start = max(0, idx - window)
            snippet_end = min(len(text), idx + len(kw) + window)
            snippet = text[snippet_start:snippet_end].strip()
            snippet = snippet.replace(text[idx:idx+len(kw)], f"**{text[idx:idx+len(kw)]}**")
            results.append(snippet)
            start = idx + len(kw)
    return results

#####################
# LEGAL ADVISOR CLASS
#####################
class LegalAdvisor:
    def __init__(self, country):
        self.kb = LegalKnowledgeBase(country)
    
    def analyze(self, text):
        doc = nlp(text)
        keywords = [token.lemma_ for token in doc if token.pos_ in ["NOUN", "VERB"]]
        local_laws = self.kb.get_relevant_laws(keywords)
        global_laws = []
        for category, law_list in ALL_LAWS.items():
            for law_item in law_list:
                title = law_item["title"]
                details = law_item["details"]
                if any(kw.lower() in title.lower() for kw in keywords) or any(kw.lower() in details.lower() for kw in keywords):
                    law_dict = {
                        "title": title,
                        "text": details,
                        "type": category.capitalize(),
                        "enforcement_agency": "N/A (Global Database)"
                    }
                    global_laws.append(law_dict)
        combined_results = []
        for law in local_laws:
            combined_results.append({
                "title": law["title"],
                "text": law["text"],
                "type": law["type"],
                "enforcement_agency": law["enforcement_agency"]
            })
        combined_results.extend(global_laws)
        for law in combined_results:
            law["loopholes"] = find_potential_loopholes(law["text"])
        web_results = comprehensive_web_research(text, max_results=5)
        save_query(st.session_state.current_user, text)
        return combined_results, web_results

#####################
# VOICE & TTS FUNCTIONS
#####################
def text_to_speech(text):
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            temp_path = tf.name
            engine.save_to_file(text, temp_path)
            engine.runAndWait()
            time.sleep(0.5)
            with open(temp_path, "rb") as f:
                audio_bytes = f.read()
            return audio_bytes
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def speech_to_text():
    with sr.Microphone() as source:
        try:
            st.session_state.listening = True
            audio = r.listen(source, timeout=7)
            return r.recognize_google(audio)
        except sr.WaitTimeoutError:
            st.error("Listening timed out - please try again")
            return ""
        finally:
            st.session_state.listening = False

#####################
# TAX OPTIMIZER CLASS
#####################
class TaxOptimizer:
    def __init__(self, income, expenses, deductions):
        self.income = income
        self.expenses = expenses
        self.deductions = deductions
    
    def calculate(self):
        taxable = self.income - self.deductions
        # Adjusted 'charity' logic so it doesn't exceed 500
        allocations = {
            "retirement": min(6000, self.income * 0.1),
            "charity": min(500, self.income * 0.1) 
        }
        return max(0, taxable), allocations

#####################
# PDF GENERATION FUNCTION (Using fpdf)
#####################
def generate_pdf(report_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in report_text.split("\n"):
        pdf.cell(200, 10, txt=line, ln=True)
    pdf_file = "analysis_report.pdf"
    pdf.output(pdf_file)
    return pdf_file

#####################
# SIDEBAR & MAIN TABS
#####################
with st.sidebar:
    st.image("D:\AI lawyer\DALL·E 2025-02-14 02.55.41 - A professional and minimalistic logo for a legal research AI application. The design should feature a stylized balance scale, symbolizing justice, int.webp", width=120)
    st.session_state.country = st.selectbox("🌍 Select Jurisdiction", COUNTRIES, index=0)
    if st.button("🔍 New Research Case"):
        st.success("New research case initiated!")
    with st.expander("Query History"):
        history = get_query_history(st.session_state.current_user)
        if history:
            for idx, query in enumerate(history, start=1):
                st.write(f"{idx}. {query}")
        else:
            st.write("No queries yet.")
    with st.expander("Full Laws Database"):
        st.markdown("**Legal Laws:**")
        for law_dict in ALL_LAWS["legal"]:
            st.write(f"- {law_dict['title']}")
        st.markdown("**Illegal Activities:**")
        for law_dict in ALL_LAWS["illegal"]:
            st.write(f"- {law_dict['title']}")

tabs = st.tabs(["Legal Analysis", "Voice Input", "Tax Optimization", "Legal Chatbot"])

###############
# TAB 1: LEGAL ANALYSIS
###############
with tabs[0]:
    st.header("🔍 Legal Case Analysis")
    case_text = st.text_area("Enter Case Details:", height=100)
    link_input = st.text_input("Enter additional URL(s) (comma separated)", value="")
    if st.button("Analyze Case") and case_text:
        with st.spinner("Analyzing..."):
            combined_text = case_text
            if link_input:
                urls = [url.strip() for url in link_input.split(",") if url.strip()]
                for url in urls:
                    if url.lower().endswith(".pdf"):
                        scraped_content = scrape_pdf(url)
                    else:
                        scraped_content = scrape_page(url)
                    if scraped_content:
                        combined_text += "\n" + scraped_content
            advisor = LegalAdvisor(st.session_state.country)
            all_laws_found, web_results = advisor.analyze(combined_text)
            report = ""
            st.subheader("Legal Analysis Report")
            if all_laws_found:
                for law in all_laws_found:
                    block = f"""
Title: {law['title']}
Type: {law['type']}
Enforcement Agency: {law['enforcement_agency']}
Details: {law['text']}
"""
                    st.markdown(f"""
<div style='padding:10px;border-radius:5px;background:#1e1e1e;margin:5px'>
    <h4 style='color:#2d4059'>{law['title']}</h4>
    <p style='color:#ffffff'>{law['text']}</p>
    <p style='color:#ff4500'><strong>Type:</strong> {law['type']}</p>
    <p style='color:#ffcc00'><strong>Enforcement Agency:</strong> {law['enforcement_agency']}</p>
</div>
""", unsafe_allow_html=True)
                    report += block + "\n"
                    if law.get("loopholes"):
                        st.write("**Potential Loopholes / Exceptions Found:**")
                        for snippet in law["loopholes"]:
                            st.markdown(f"- {snippet}")
                            report += f"Loophole: {snippet}\n"
                        st.write("---")
            else:
                st.warning("No relevant laws found.")

            st.subheader("Comprehensive Web Research")
            if web_results:
                for i, item in enumerate(web_results, start=1):
                    title = item.get("title", "No Title")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    scraped_text = item.get("scraped_text", "")
                    st.markdown(f"**Result #{i}:** [{title}]({link})")
                    if snippet.strip():
                        st.write(f"**Snippet:** {snippet}")
                    if scraped_text.strip():
                        st.write("**Scraped Content:**")
                        st.write(scraped_text)
                    st.write("---")
                    report += f"Web Result #{i}: {title}\nSnippet: {snippet}\nScraped: {scraped_text}\n---\n"
            else:
                st.write("No additional web results found.")

            if st.download_button("Download Analysis Report (TXT)", report, "analysis_report.txt", "text/plain"):
                st.success("Report downloaded!")
            pdf_file = generate_pdf(report)
            with open(pdf_file, "rb") as f:
                st.download_button("Download Analysis Report (PDF)", f, pdf_file, "application/pdf")

            law_types = [law["type"] for law in all_laws_found] if all_laws_found else []
            if law_types:
                df = pd.DataFrame(law_types, columns=["Type"])
                st.bar_chart(df["Type"].value_counts())
            else:
                st.write("No law types to display in chart.")

###############
# TAB 2: VOICE INPUT
###############
with tabs[1]:
    st.header("🎤 Voice Input")
    if st.button("Start Listening 🎙️"):
        voice_text = speech_to_text()
        if voice_text:
            st.success("Recognized: " + voice_text)
            st.session_state.voice_input = voice_text
    recognized = st.text_area("Recognized Text:", value=st.session_state.get("voice_input", ""), height=70, disabled=True)
    if recognized:
        if st.button("Analyze Voice Query"):
            with st.spinner("Analyzing voice query..."):
                advisor = LegalAdvisor(st.session_state.country)
                all_laws_found, web_results = advisor.analyze(recognized)
                st.subheader("Voice Query Analysis Report")
                if all_laws_found:
                    for law in all_laws_found:
                        st.markdown(f"""
<div style='padding:10px;border-radius:5px;background:#1e1e1e;margin:5px'>
    <h4 style='color:#2d4059'>{law['title']}</h4>
    <p style='color:#ffffff'>{law['text']}</p>
    <p style='color:#ff4500'><strong>Type:</strong> {law['type']}</p>
    <p style='color:#ffcc00'><strong>Enforcement Agency:</strong> {law['enforcement_agency']}</p>
</div>
""", unsafe_allow_html=True)
                        if law.get("loopholes"):
                            st.write("**Potential Loopholes / Exceptions Found:**")
                            for snippet in law["loopholes"]:
                                st.markdown(f"- {snippet}")
                            st.write("---")
                else:
                    st.warning("No relevant laws found.")

                st.subheader("Additional Web Research")
                if web_results:
                    for i, item in enumerate(web_results, start=1):
                        title = item.get("title", "No Title")
                        link = item.get("link", "")
                        snippet = item.get("snippet", "")
                        scraped_text = item.get("scraped_text", "")
                        st.markdown(f"**Result #{i}:** [{title}]({link})")
                        if snippet.strip():
                            st.write(f"**Snippet:** {snippet}")
                        if scraped_text.strip():
                            st.write("**Scraped Content:**")
                            st.write(scraped_text)
                        st.write("---")
                else:
                    st.write("No additional web results found.")

###############
# TAB 3: TAX OPTIMIZATION
###############
with tabs[2]:
    st.header("💰 Tax Optimization Suite")
    with st.form("tax_form"):
        st.subheader("Case Financials")
        income = st.number_input("Annual Income ($)", min_value=0, value=100000)
        expenses = st.number_input("Expenses ($)", min_value=0, value=30000)
        deductions = st.number_input("Deductions ($)", min_value=0, value=15000)
        submitted = st.form_submit_button("Calculate Tax Savings")
        if submitted:
            optimizer = TaxOptimizer(income, expenses, deductions)
            taxable, allocations = optimizer.calculate()
            st.metric("Taxable Income", f"${taxable:,.2f}")
            st.write("**Recommended Allocations:**")
            for k, v in allocations.items():
                st.progress(v/10000, text=f"{k.title()}: ${v:,.2f}")
            audio_bytes = text_to_speech(f"Optimization complete with total savings of ${sum(allocations.values()):,.2f}")
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")

###############
# TAB 4: LEGAL CHATBOT
###############
with tabs[3]:
    st.header("💬 Legal Chatbot")
    st.markdown("Ask a legal question below and get a simulated answer.")
    user_question = st.text_input("Your Question:")
    if st.button("Get Answer"):
        if "contract" in user_question.lower():
            answer = "Contracts require offer, acceptance, and consideration. Always review key terms carefully."
        elif "privacy" in user_question.lower():
            answer = "Privacy laws protect you from unlawful searches and require data protection measures."
        elif "trial" in user_question.lower():
            answer = "A fair trial ensures due process, the right to counsel, and an impartial jury."
        else:
            answer = "This is a complex legal question. Please consult a qualified attorney for detailed advice."
        st.markdown(f"**Chatbot Answer:** {answer}")
