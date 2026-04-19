<div align="center">
  <img src="https://img.shields.io/badge/CodeSentinel-AI-7C3AED?style=for-the-badge" alt="CodeSentinel AI">
  <h1>🛡️ CodeSentinel AI: The Ultimate Explanation Guide</h1>
  <p><strong>Autonomous Multi-Agent Code Review & Verification Pipeline</strong></p>
</div>

---

Welcome! If you are reading this, you probably need to explain this project to a reviewer, an interviewer, or a professor. **This document is written specifically for you.** It assumes you know nothing and explains every single detail, technology, and design choice so you can answer any question confidently.

---

## 📖 1. What exactly is this project? (The Elevator Pitch)

Imagine having a Senior Developer, a Security Expert, and a QA Tester sitting inside your computer. When you give them a folder of code, they don't just point out mistakes—they actually discuss how to fix them, rewrite the code for you, and run tests to make sure their fixes didn't break anything else.

**CodeSentinel AI** is a web application that implements an **Autonomous Agentic Workflow**. Instead of just chatting with an AI like ChatGPT, this system sets up four distinct AI "Agents" that communicate with each other to automatically analyze, plan, fix, and verify software bugs without human intervention.

---

## 🛠️ 2. Technologies & Libraries Used

If a reviewer asks: *"Tell me about your tech stack and why you chose these specific libraries?"* — Here is your cheat sheet.

### **The Backend Engine (Python)**
*   **FastAPI:** The core web framework. Chosen because it natively supports asynchronous programming (`async/await`) and is extremely fast.
*   **Uvicorn:** The ASGI server that runs the FastAPI application.
*   **WebSockets (built into FastAPI):** Used to create a real-time, two-way connection between the server and the browser. This is how the frontend dashboard shows the "Live Agent Activity" without you needing to refresh the page.
*   **Pydantic:** Used for strict data validation. It ensures that when agents generate JSON plans, the data exactly matches the structure we need (e.g., ensuring an Issue always has a `severity` and `line_number`).

### **The AI Brain**
*   **Ollama (Local LLM):** Used to run the AI locally (like Meta's LLaMA 3) completely for free.
*   *Note on API*: The code utilizes `urllib` to make HTTP POST requests directly to the Ollama server dynamically.

### **The Deterministic Code Tools (The "Anti-Hallucination" Stack)**
AI is known to hallucinate (make things up). To stop this, our `AnalyzerAgent` uses hardcore, traditional Python tools *before* it talks to the AI.
*   **`ast` (Abstract Syntax Tree - built into Python):** Reads Python code and breaks it down into a tree structure to find deep structural bugs.
*   **`pylint`:** Scans code for bad coding styles, missing docstrings, and standard errors.
*   **`bandit`:** A security linter designed to find common security vulnerabilities in Python code (e.g., hardcoded passwords, `eval()` injections).
*   **`radon`:** Computes metrics like Cyclomatic Complexity (measuring if a function has too many `if/else` loops and is too complicated to read).
*   **`pytest`:** Used by the Verifier Agent to run regression tests automatically on the modified code.

### **Utilities**
*   **`GitPython`:** Allows the backend to safely run `git clone` to pull down external repositories from GitHub straight into temporary folders.
*   **`python-dotenv`:** Loads configuration variables from the `.env` file securely.

### **The Frontend (UI/UX)**
*   **Vanilla HTML, CSS, JavaScript:** No heavy React or Vue. It uses a modern "Glassmorphism" design with CSS Grid/Flexbox and native JavaScript WebSocket API to listen to server events.

---

## 🤖 3. How the Pipeline Works (Step-by-Step)

When you click "Launch Code Review", here is exactly what happens under the hood:

### 1. The Orchestrator (`orchestrator.py`)
This is the "Manager". It creates a temporary `/tmp` sandbox folder (so your real code isn't destroyed) and then calls the agents one by one.

### 2. Stage 1: The Analyzer Agent 🔍
*   **What it does:** Scans the code to find bugs.
*   **How it does it:** Instead of just asking the AI to guess where bugs are, it runs `CodeParser`, `Pylint`, `Bandit`, and `Radon` in the background using `asyncio.to_thread` (so it doesn't freeze the server). It gathers all these hardcore metrics and *then* asks the LLM to write nice, human-readable descriptions of the bugs.

### 3. Stage 2: The Planner Agent 📋
*   **What it does:** Decides the order of operations.
*   **How it does it:** Takes the huge list of issues from the Analyzer and uses the LLM to generate a JSON `FixPlan`. It prioritizes critical security bugs first, and ignores minor formatting issues to save time.

### 4. Stage 3: The Fixer Agent 🔧
*   **What it does:** Actually rewrites the code.
*   **How it does it:** Reads the files, looks at the `FixPlan`, and uses the LLM to generate replacement code blocks. It writes the patched code directly back to the disk.

### 5. Stage 4: The Verifier Agent ✅
*   **What it does:** Makes sure the Fixer didn't break the application.
*   **How it does it:** It runs `pytest` and `ast.parse` syntax checks.
*   **⭐ THE GENIUS PART (The Self-Healing Loop):** If the tests FAIL, the Orchestrator catches the error traceback, feeds it back to the Fixer Agent, and says *"You made a mistake, try again!"* It will retry up to 3 times automatically.

---

## 📂 4. Project Directory Structure

```text
├── backend/
│   ├── main.py            # The FastAPI server entry point. Handles web requests/WebSockets.
│   ├── orchestrator.py    # The core logic loop that passes data between agents.
│   ├── config.py          # Loads environment variables (like API keys or local LLM setup).
│   ├── models.py          # Pydantic classes defining strict data shapes (Issue, FixPlan).
│   ├── agents/            # Contains the 4 unique AI agent bots.
│   └── tools/             # Wrappers around traditional tools (Bandit, Pylint, AST).
├── frontend/              # The Dashboard UI files (HTML, CSS, JS).
├── sample_projects/       # Code intentionally filled with bugs to demo the AI's power.
└── requirements.txt       # The list of Python libraries needed to run the app.
```

---

## 🎤 5. Cheat Sheet: How to Answer Interview Questions

**Q: Explain the bug I showed you earlier: Why didn't the UI show missing imports or bare exceptions when I had a syntax error?**
> A: "Because our pipeline relies on deterministic Abstract Syntax Trees (AST) and Python parsing tools first, to avoid LLM hallucinations. If the code has a critical compiler syntax error (like a missing colon), Python cannot construct the tree at all. The tools exit early properly, reporting a `SyntaxError`. The agentic workflow is actually designed to fix the syntax error first, and once it compiles on a retry loop, the analyzer will detect the deeper logical bugs."

**Q: How did you handle performance when parsing huge repositories? Wouldn't the server freeze?**
> A: "Yes, heavy IO/CPU-bound tasks (like `git clone`, `ast.parse`, and running `pylint`) normally block Python's main event loop, causing WebSockets to disconnect. I solved this by wrapping all tool executions inside `asyncio.to_thread()`, which offloads the synchronous workload to a background worker thread. This keeps the FastAPI event loop unblocked and the UI perfectly responsive."

**Q: Why use external tools like Bandit or Radon instead of just asking the AI to find bugs?**
> A: "Large Language Models inherently hallucinate and are non-deterministic. If you ask an LLM to find bugs, it will guess. By using deterministic static analysis tools to find the exact line numbers and severity first, and *only* using the LLM for reasoning and refactoring, I dramatically increased the accuracy and safety of the system."

**Q: What is the "ReAct" pattern in your architecture?**
> A: "ReAct stands for Reasoning and Acting. In my `BaseAgent` class, agents don't just output text. They take in context, 'Reason' about it (e.g., planning the fix), and 'Act' using tools (e.g., executing code rewrites or running tests). The orchestrator manages this loop."

---

## 🚀 6. Setup & Installation 

1. **Clone the project:**
   ```bash
   git clone <your-repo-link>
   cd CodeSentinelAI
   ```
2. **Install requirements:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Run Ollama (for the local AI engine):**
   *(In a separate terminal)*
   ```bash
   ollama run llama3
   ```
4. **Start the backend:**
   ```bash
   python -m uvicorn backend.main:app --port 8000 --reload
   ```
5. **Open Browser:** Navigate to `http://localhost:8000`.
