# 🏛️ Architecture & System Design# 🏛️ Architecture & System Design



This document provides a high-level overview of the CodeSentinel AI architecture. Use this as a guide to explain the system's data flow, concurrency models, and agentic loop.This document provides a high-level overview of the CodeSentinel AI architecture. Use this as a guide to explain the system's data flow, concurrency models, and agentic loop.



## 📊 1. System Architecture Diagram## 📊 1. System Architecture Diagram



```mermaid```mermaid

flowchart TBgraph TD

    %% Define Styles    %% Define Styles

    classDef frontend fill:#1e1e2f,stroke:#4a4a6a,stroke-width:2px,color:#fff,rx:5px,ry:5px    classDef client fill:#2d3748,stroke:#a0aec0,stroke-width:2px,color:#fff

    classDef backend fill:#25254b,stroke:#5c5c8a,stroke-width:2px,color:#fff,rx:5px,ry:5px    classDef api fill:#2c5282,stroke:#63b3ed,stroke-width:2px,color:#fff

    classDef agent fill:#3d2b56,stroke:#7b5aab,stroke-width:2px,color:#fff,rx:5px,ry:5px    classDef core fill:#2b6cb0,stroke:#90cdf4,stroke-width:2px,color:#fff

    classDef tool fill:#1b4332,stroke:#48bb78,stroke-width:2px,color:#fff,rx:5px,ry:5px    classDef agent fill:#553c9a,stroke:#b794f4,stroke-width:2px,color:#fff

    classDef external fill:#4a154b,stroke:#d53f8c,stroke-width:2px,color:#fff,rx:5px,ry:5px    classDef tool fill:#276749,stroke:#68d391,stroke-width:2px,color:#fff

    classDef default fill:#2d3748,stroke:#718096,stroke-width:1px,color:#fff    classDef llm fill:#702459,stroke:#d6bcfa,stroke-width:2px,color:#fff



    subgraph Client ["🖥️ Web Client (Frontend)"]    %% Client Layer

        direction TB    Client[��️ Glassmorphism Dashboard<br>HTML / CSS / JS]:::client

        UI["Glassmorphism Dashboard<br/>(HTML, CSS, Vanilla JS)"]:::frontend

    end    %% API Layer

    subgraph FastAPI Backend

    subgraph Server ["⚡ Server Layer (FastAPI)"]        API[⚡ FastAPI Server]:::api

        direction TB        WS[🔌 WebSocket Manager]:::api

        REST["REST API Endpoints"]:::backend        

        WS["WebSocket Manager<br/>(Live Event Stream)"]:::backend        %% Core Orchestration

        Orchestrator["🧠 Pipeline Orchestrator<br/>(State & Retry Logic)"]:::backend        Orchestrator[🧠 Orchestrator<br>State & Retry Logic]:::core

    end        

        %% Agent Ecosystem

    subgraph Agents ["🤖 Autonomous Multi-Agent Pipeline"]        subgraph Multi-Agent Pipeline

        direction LR            A1[🔍 Analyzer Agent]:::agent

        A1["🔍 Analyzer<br/>(Scans codebase)"]:::agent            A2[📋 Planner Agent]:::agent

        A2["📋 Planner<br/>(Creates FixPlan)"]:::agent            A3[🔧 Fixer Agent]:::agent

        A3["🔧 Fixer<br/>(Applies code changes)"]:::agent            A4[✅ Verifier Agent]:::agent

        A4["✅ Verifier<br/>(Runs tests)"]:::agent        end

                

        A1 -->|Raw Issues| A2        %% Deterministic Tools

        A2 -->|Fix Plan| A3        subgraph Static Analysis Tools

        A3 -->|Modified Files| A4            T1[AST Parser]:::tool

        A4 -.->|Test Traceback<br/>(Self-Healing Loop)| A3            T2[Pylint]:::tool

    end            T3[Bandit]:::tool

            T4[Radon / Pytest]:::tool

    subgraph Tools ["🛠️ Deterministic Static Analysis Tools"]        end

        direction TB    end

        AST["Python AST<br/>(Syntax & Structure)"]:::tool

        Pylint["Pylint<br/>(Style & Practices)"]:::tool    %% External Infrastructure

        Bandit["Bandit<br/>(Security Vulnerabilities)"]:::tool    LLM[🤖 Local LLM<br>Ollama / LLaMA 3]:::llm

        Pytest["Pytest<br/>(Regression Tests)"]:::tool    Repo[📁 Git Repo / Sandbox]:::tool

    end

    %% Connections

    subgraph Infrastructure ["🌍 External Infrastructure"]    Client <-->|REST / API| API

        direction TB    Client <-->|Live Events| WS

        LLM["Local LLM API<br/>(Ollama / LLaMA 3)"]:::external    API -->|Triggers| Orchestrator

        FileSystem["/tmp Sandbox<br/>(Cloned Git Repository)"]:::external    Orchestrator -.->|Streams Events| WS

    end    

    Orchestrator -->|1. Setup| Repo

    %% Wiring it all together    Orchestrator -->|2. Invoke| A1

    UI <-->|HTTP POST / GET| REST    A1 -->|3. Handoff| A2

    UI <-->|ws:// Events| WS    A2 -->|4. Handoff| A3

    REST -->|Triggers Pipeline| Orchestrator    A3 -->|5. Handoff| A4

    Orchestrator -.->|Dispatches Live Logs| WS    A4 -.->|Test Failed? Retry| A3

    

    Orchestrator -->|1. Git Clone| FileSystem    %% Tool Usage

    Orchestrator -->|2. Start Pipeline| A1    A1 -->|Scan| T1 & T2 & T3 & T4

        A4 -->|Test| T4

    A1 -->|Executes tools| AST & Pylint & Bandit

    A4 -->|Executes tests| Pytest    %% LLM Usage

        A1 & A2 & A3 & A4 <-->|HTTP POST| LLM

    AST & Pylint & Bandit --> FileSystem```

    Pytest --> FileSystem

    A3 -->|Writes Patches| FileSystem## 🔄 2. Data Flow & Execution Walkthrough

    

    A1 & A2 & A3 & A4 <-->|POST Prompt Requests| LLMWhen you explain the architecture in a video or interview, follow this 5-step flow:

```

### Step 1: The Request (Frontend ➔ FastAPI)

## 🔄 2. Data Flow & Execution WalkthroughThe user submits a GitHub URL or a Local Path via the UI. **FastAPI** establishes a **WebSocket** connection immediately so the frontend can listen to live updates.



When you explain the architecture in a video or interview, follow this 5-step flow:### Step 2: The Sandbox (Orchestrator)

The **Orchestrator** intercepts the request and uses `GitTools` to clone the target repository into an isolated `/tmp` workspace. This ensures the user's original codebase is never permanently corrupted by AI changes.

### Step 1: The Request (Frontend ➔ FastAPI)

The user submits a GitHub URL or a Local Path via the UI. **FastAPI** establishes a **WebSocket** connection immediately so the frontend can listen to live updates.### Step 3: Analysis (Anti-Hallucination)

The Orchestrator wakes up the **Analyzer Agent**. 

### Step 2: The Sandbox (Orchestrator)* **The Magic:** To prevent the LLM from hallucinating bugs, the Analyzer offloads the file reading to *deterministic Python tools* (`ast`, `pylint`, `bandit`). 

The **Orchestrator** intercepts the request and uses `GitTools` to clone the target repository into an isolated `/tmp` workspace. This ensures the user's original codebase is never permanently corrupted by AI changes.* Because these tools are CPU-bound and slow on large repos, they are pushed to a background thread using `asyncio.to_thread()`, keeping the FastAPI WebSocket alive and responsive.

* Once the tools return hard data (exact line numbers and severities), the Analyzer pings the **Local LLM (Ollama)** to write human-readable descriptions of the issues.

### Step 3: Analysis (Anti-Hallucination)

The Orchestrator wakes up the **Analyzer Agent**. ### Step 4: The ReAct Handoffs (Planner ➔ Fixer)

* **The Magic:** To prevent the LLM from hallucinating bugs, the Analyzer offloads the file reading to *deterministic Python tools* (`ast`, `pylint`, `bandit`). * **Planner Agent:** Takes the JSON list of issues, sends it to the LLM, and generates a strict, prioritized `FixPlan` (focusing on Critical/High bugs first).

* Because these tools are CPU-bound and slow on large repos, they are pushed to a background thread using `asyncio.to_thread()`, keeping the FastAPI WebSocket alive and responsive.* **Fixer Agent:** Reads the `FixPlan`, reads the specific files needing repairs, and uses the LLM to generate patched code, replacing the bad code on the disk in the temporary sandbox.

* Once the tools return hard data (exact line numbers and severities), the Analyzer pings the **Local LLM (Ollama)** to write human-readable descriptions of the issues.

### Step 5: The Self-Healing Loop (Verifier)

### Step 4: The ReAct Handoffs (Planner ➔ Fixer)* **Verifier Agent:** Runs `pytest` and `ast` syntax checks against the patched code. 

* **Planner Agent:** Takes the JSON list of issues, sends it to the LLM, and generates a strict, prioritized `FixPlan` (focusing on Critical/High bugs first).* **The Retry Loop:** If the test fails or throws a Python syntax error, the Orchestrator catches the traceback, sends it back to the Fixer Agent, and triggers a retry loop (`attempt < MAX_RETRIES`). The AI essentially debugs its own code before the user ever sees it.

* **Fixer Agent:** Reads the `FixPlan`, reads the specific files needing repairs, and uses the LLM to generate patched code, replacing the bad code on the disk in the temporary sandbox.* Once verified, the final payload—issues, fix plans, code diffs, and execution traces—is served back to the Frontend.



### Step 5: The Self-Healing Loop (Verifier)## 🧠 3. Core Principles

* **Verifier Agent:** Runs `pytest` and `ast` syntax checks against the patched code. * **Separation of Concerns:** Using specialized agents makes prompting the LLM much cheaper and more accurate than asking one giant AI to do everything at once.

* **The Retry Loop:** If the test fails or throws a Python syntax error, the Orchestrator catches the traceback, sends it back to the Fixer Agent, and triggers a retry loop (`attempt < MAX_RETRIES`). The AI essentially debugs its own code before the user ever sees it.* **Deterministic Boundaries:** Using real tools (`pylint`, `ast`) restricts the AI from guessing.

* Once verified, the final payload—issues, fix plans, code diffs, and execution traces—is served back to the Frontend.* **Non-blocking IO:** FastAPI event loops handle networking while `asyncio.to_thread` handles the heavy code parsing.


## 🧠 3. Core Principles
* **Separation of Concerns:** Using specialized agents makes prompting the LLM much cheaper and more accurate than asking one giant AI to do everything at once.
* **Deterministic Boundaries:** Using real tools (`pylint`, `ast`) restricts the AI from guessing.
* **Non-blocking IO:** FastAPI event loops handle networking while `asyncio.to_thread` handles the heavy code parsing.