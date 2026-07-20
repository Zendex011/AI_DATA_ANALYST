<div align="center">

# AI Data Analyst

### AI-Powered Conversational Data Analysis Platform

Transform CSV files and SQL databases into actionable insights using Natural Language.

Built with **FastAPI**, **LangGraph**, **Google Gemini**, **React**, and **SQLAlchemy**.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange)
![Gemini](https://img.shields.io/badge/Google-Gemini-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

# Overview

AI Data Analyst is an intelligent analytics platform that enables users to interact with structured datasets using natural language instead of writing SQL queries or Python scripts.

The system combines **Large Language Models**, **agentic workflows**, and **data processing pipelines** to automatically understand user intent, generate executable code, retrieve insights from structured data, and visualize the results.

Whether the data is stored inside a CSV file or a relational database, the platform converts conversational requests into meaningful analytical outputs.

Instead of asking:

> "Write an SQL query to calculate monthly sales."

Users simply ask:

> "Show me monthly sales for the last year."

The platform handles the complete reasoning and execution pipeline automatically.

---

# Why AI Data Analyst?

Traditional analytics tools require users to possess SQL knowledge, programming skills, or experience with BI dashboards.

AI Data Analyst removes this barrier by enabling conversational interaction with data while maintaining complete transparency through generated SQL queries, Python code, execution results, and visualizations.

The platform is designed to bridge the gap between business users and technical data analysis.

---

# Features

## Conversational Analytics

- Query datasets using natural language
- AI-generated responses with explanations
- Conversational follow-up questions
- Automatic reasoning using LangGraph

---

## CSV Analysis

- Upload CSV datasets
- Automatic schema detection
- Data profiling
- Pandas-powered analysis
- AI-generated Python code
- Statistical summaries

---

## SQL Database Analysis

- Connect external databases
- Automatic schema inspection
- AI-generated SQL
- SQL validation
- Secure execution
- Query history

---

## Visualization

Generate charts automatically whenever appropriate.

Supported visualizations include:

- Bar Charts
- Line Charts
- Scatter Plots
- Histograms
- Pie Charts
- Box Plots

---

## Agentic Workflow

Instead of sending every request directly to an LLM, the system follows an intelligent multi-step workflow.

- Intent Analysis
- Route Selection
- Code Generation
- SQL Generation
- Validation
- Execution
- Visualization
- Response Formatting

---

## History

Maintain previous conversations and analytical sessions.

- CSV history
- Database history
- Previous generated code
- Previous SQL queries

---

## Modular Backend

Designed using independent components.

- LLM Service
- SQL Executor
- Code Executor
- Chart Generator
- Schema Inspector
- Validation Layer

---

# System Architecture

```text
                        User
                          │
                          ▼
                 Natural Language Query
                          │
                          ▼
                  FastAPI REST API
                          │
                          ▼
                 LangGraph Orchestrator
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
    CSV Workflow                    SQL Workflow
          │                               │
          ▼                               ▼
 Python Code Generator           SQL Query Generator
          │                               │
          ▼                               ▼
 Code Validation                SQL Validation
          │                               │
          ▼                               ▼
 Code Execution                 SQL Execution
          │                               │
          └───────────────┬───────────────┘
                          ▼
                 Chart Generation
                          ▼
               AI Generated Response
                          ▼
                       Frontend
```

---

# AI Workflow

The application uses an agentic pipeline powered by LangGraph.

### Step 1

Receive user question.

↓

### Step 2

Determine whether the request requires

- CSV analysis
- Database analysis

↓

### Step 3

Generate executable Python code or SQL query.

↓

### Step 4

Validate generated output.

↓

### Step 5

Execute inside the appropriate execution engine.

↓

### Step 6

Generate charts when applicable.

↓

### Step 7

Format response for the user.

---

# Core Components

## LangGraph Orchestrator

Responsible for coordinating the complete AI workflow.

Responsibilities include:

- Intent detection
- Workflow routing
- Context management
- Agent coordination

---

## LLM Service

Responsible for

- Prompt engineering
- Response generation
- SQL generation
- Python generation

Powered by Google Gemini.

---

## Code Executor

Executes AI-generated Python code in an isolated execution environment with timeout protection.

Responsible for

- Pandas operations
- Statistical analysis
- Data aggregation
- Result extraction

---

## SQL Executor

Responsible for

- Database connectivity
- Query execution
- Result formatting

Supports SQLAlchemy-compatible databases.

---

## Schema Inspector

Automatically discovers

- Tables
- Columns
- Relationships
- Data types

This information is provided to the LLM for accurate SQL generation.

---

## Chart Generator

Automatically creates visualizations whenever the analytical result benefits from graphical representation.

---

# Supported Data Sources

The platform currently supports

- CSV Files
- SQLite
- PostgreSQL

Architecture is extensible for

- MySQL
- Microsoft SQL Server
- MariaDB
- Oracle
- Any SQLAlchemy-supported database

---

# Security

The application includes multiple safety mechanisms before execution.

- SQL validation
- Query sanitization
- Execution timeout
- Read-only analytical queries
- Request validation
- Schema-aware prompting
- Controlled code execution

---

# Technology Stack

## Frontend

- React
- Vite
- JavaScript
- Tailwind CSS

---

## Backend

- FastAPI
- LangGraph
- Google Gemini
- SQLAlchemy
- Pandas
- Pydantic

---

## Databases

- SQLite
- PostgreSQL

---

## AI

- Google Gemini
- LangGraph
- Prompt Engineering
- Agentic Workflows

---

## Visualization

- Matplotlib
- Plotly

---

# API Modules

The backend exposes dedicated APIs for

- Authentication
- CSV Upload
- CSV Analysis
- Database Connection
- SQL Analysis
- History
- File Management
- Visualization
- Health Monitoring

---

# Example Workflow

```text
Upload CSV
      │
      ▼

"What are the top 10 selling products?"

      │

      ▼

AI generates Python

      │

      ▼

Execute Pandas

      │

      ▼

Generate Bar Chart

      │

      ▼

Return Insights
```

---

# Key Highlights

- Natural Language to SQL
- Natural Language to Pandas
- LangGraph Agent Architecture
- Modular FastAPI Backend
- Database Schema Discovery
- AI Generated Visualizations
- Query History
- Multi-source Data Analysis
- Extensible Architecture
- Production-ready Design

---

# Future Roadmap

- User-managed API Keys
- Multi-Agent Collaboration
- PDF Report Generation
- Scheduled Analytics
- Dashboard Builder
- Streaming Responses
- Role-Based Access Control
- Data Cleaning Assistant
- RAG-powered Knowledge Base
- Multi-file Analysis
- Business KPI Monitoring
- Cloud Deployment

---

# Design Principles

This project is built around four core principles.

- Transparency over black-box AI
- Modular architecture
- Production-oriented backend design
- Extensible agent workflows

Every AI-generated response can be traced back to the generated SQL query or Python code, allowing users to understand how conclusions were reached.

---

<img width="1917" height="1097" alt="Screenshot 2026-07-19 215937" src="https://github.com/user-attachments/assets/85ba1934-631a-4b94-94c9-02c4404bd436" />
<img width="1917" height="1082" alt="Screenshot 2026-07-19 220333" src="https://github.com/user-attachments/assets/14963deb-e23c-44fa-aa5d-96df6738665d" />
<img width="1917" height="1086" alt="Screenshot 2026-07-19 220204" src="https://github.com/user-attachments/assets/4da1dde0-91c1-4706-adb0-4eb8ba5be707" />
<img width="1917" height="1092" alt="Screenshot 2026-07-19 220048" src="https://github.com/user-attachments/assets/64b43fa1-b085-4bad-9577-95adb0647610" />
<img width="1917" height="1132" alt="Screenshot 2026-07-19 220019" src="https://github.com/user-attachments/assets/f981e3bc-bff4-4ee4-89ae-a80a4939d40b" />



# Contributing

Contributions are welcome.

Ideas for improvements include

- Additional database connectors
- New visualization types
- Advanced agent workflows
- Better prompt optimization
- Cloud integrations
- Enterprise authentication

---

# License

This project is licensed under the MIT License.

---

<div align="center">

### Built to simplify data analysis through AI.

⭐ If you found this project useful, consider giving it a star.

</div>
