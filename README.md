# War Gaming Simulation System

A Django-based war game system that uses a single local LLM to analyze military data for the Middle East. The chat LLM is trained on geography, personnel, and weapons data and provides victory possibilities, reasons, strategy advice, and wargaming recommendations.

## 🎯 Overview

- **Chat**: One UI and one API; one Ollama model (`wargaming:unified`) trained on all data.
- **Data** (used only for training the chat LLM):
  - **Geography**: Terrain, weather, strategic features (`geography/data/`)
  - **Personnel**: Military personnel and structure (`personnel/data/`)
  - **Weapons**: Equipment and effectiveness (`weapons/data/`)

## 🏗️ Architecture

```
war_game/                 # Django project
├── orchestrator/         # Chat UI, API, unified LLM service
├── geography/data/       # Geography JSON (training data)
├── personnel/data/       # Personnel JSON (training data)
├── weapons/data/         # Weapons JSON (training data)
└── manage.py
```

## 🚀 Features

- **Unified Wargaming LLM**: Single Ollama model trained on geography, personnel, and weapons data; sub-60s responses
- **Single Chat UI & API**: `/chat/` and `/orchestrator/api/chat/`
- **Local LLM**: Ollama (default base `qwen2.5:1.5b`)
- **Output**: Victory possibilities, reasons, strategy advice, wargaming recommendations

## 📋 Prerequisites

- Python 3.8+
- Django 5.2.5
- Ollama (local LLM)

## 🛠️ Installation

### 1. Clone and setup
```bash
git clone <repository-url>
cd Wargaming
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Ollama and start the server
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

The base model (`qwen2.5:1.5b` by default) is pulled automatically by the
training command in step 3 if it isn't already present.

### 3. Train the chat LLM (uses geography, personnel, weapons data)
```bash
python manage.py migrate
python manage.py retrain_wargaming_llm
```

### 4. Run server
```bash
python manage.py runserver
```

## 🔗 API

- **Chat UI**: `GET /chat/` or `GET /orchestrator/`
- **Chat API**: `POST /chat/api/chat/` or `POST /orchestrator/api/chat/`
  - Body: `{"message": "Your question", "conversation_id": "optional-uuid"}`
  - Response: `{"success", "reply", "sources", "conversation_id"}`

### Example
```bash
curl -X POST http://localhost:8000/orchestrator/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare Syria and Israel for a conventional conflict"}'
```

## ✅ Testing

With the server running (`runserver`), Ollama running (`ollama serve`), and the
unified model built (`retrain_wargaming_llm`), run the end-to-end chat test:

```bash
python test_system.py
```

It sends several questions to the chat API and prints the model's replies, so you
can confirm responses are varied and question-specific.

## 🔧 Management Commands

```bash
# Create/update the unified chat model (reads geography/data, personnel/data, weapons/data)
python manage.py retrain_wargaming_llm

# Options: --model qwen2.5:1.5b --base-url http://localhost:11434 --force
```

## 🛡️ Data (for training only)

Data lives in project folders and is read by `retrain_wargaming_llm` and the chat service:

- **geography/data/middle_east_geography.json** – Terrain, weather, strategic features
- **personnel/data/middle_east_personnel.json** – Personnel, branches, reserves
- **weapons/data/middle_east_weapons.json** – Weapon categories and capabilities

Regions covered: Syria, Iraq, Iran, Israel, Lebanon, Jordan, Saudi Arabia, Yemen, Egypt, Turkey.

## 🔍 Troubleshooting

- Start Ollama: `ollama serve`
- List models: `ollama list`
- Ensure data files exist under `geography/data/`, `personnel/data/`, `weapons/data/`

## 📄 License

For educational and research purposes.
