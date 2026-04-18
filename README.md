# 🧠 Multi-Agent AI Research Assistant

An AI-powered research tool that generates structured, citation-backed reports using a multi-agent pipeline.

---

## 🚀 Live Demo

🔗 [Demo](https://multi-agent-research-system-hemam.streamlit.app/)

---

## 📌 Overview

This project simulates a **multi-agent research system** where different AI agents collaborate to produce high-quality research reports from real-time web data.

This system follows a structured pipeline:

* Planner → breaks topic into sub-questions
* Researcher → fetches real-time data
* Writer → generates structured report
* Critic → refines output for clarity

---

## ✨ Features

* 🧠 Multi-agent architecture (Planner, Researcher, Writer, Critic)
* 🔄 LangGraph-based workflow orchestration
* 🌐 Real-time web search using Tavily API
* 🤖 LLM-powered generation using Google Gemini API
* 📚 Inline citations + source references
* 🎛 Depth mode (Basic vs Advanced)
* ⚡ Caching for faster responses
* 📄 PDF export functionality
* 🌐 Interactive UI built with Streamlit

---

## 🛠 Tech Stack

* Python
* LangGraph
* Google Gemini API
* Tavily API
* Streamlit
* ReportLab

---

## 🧩 Architecture

<img width="1212" height="302" alt="Screenshot 2026-04-15 at 11 38 34 PM" src="https://github.com/user-attachments/assets/82ef90ef-a4dd-4e08-a2e5-5fa5f2cda763" />

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/ai-research-agent.git
cd ai-research-agent
```

---

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 3. Add environment variables

Create a `.env` file:

```env
GEMINI_API_KEY=your_key
TAVILY_API_KEY=your_key
```

---

### 4. Run the app

```bash
streamlit run streamlit_app.py
```

---

## 📸 Screenshots

<img width="1200" height="700" alt="Screenshot 2026-04-15 at 11 04 13 PM" src="https://github.com/user-attachments/assets/5da3a973-8977-4026-8610-93c8e8bb03f9" />
<img width="1200" height="700" alt="Screenshot 2026-04-15 at 11 04 36 PM" src="https://github.com/user-attachments/assets/fa4acde6-b683-491f-b4f9-e1230bba8e2e" />


---

## 🎯 Key Highlights

* Designed a modular multi-agent pipeline
* Integrated real-time data retrieval to reduce hallucinations
* Implemented caching and depth control for optimized performance
* Built a production-like UI with export and citation features

---

## ⚠️ Limitations

* Depends on external API rate limits
* LLM output quality may vary
* Demo version includes usage constraints

---

## 🚀 Future Improvements

* Add user authentication
* Store past research history
* Improve citation accuracy
* Add multi-document input support

---

## 👤 Author

Hemam Pandey
GitHub: https://github.com/hemampandey

---
