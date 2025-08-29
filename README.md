# War Gaming Simulation System

A comprehensive Django-based war game simulation system that uses local LLMs to analyze military data for the Middle East region. The system provides detailed analysis of geography, personnel, and weapons to support military planning and strategic decision-making.

## 🎯 Overview

This system consists of three main components:
- **Geography Analysis**: Terrain, weather, and strategic features analysis
- **Personnel Management**: Military personnel data and organizational structure
- **Weapons Analysis**: Equipment capabilities and effectiveness assessment

## 🏗️ Architecture

```
war_game/                 # Main Django project
├── geography/           # Geography analysis app
├── personnel/           # Personnel management app
├── weapons/            # Weapons analysis app
└── manage.py           # Django management
```

## 🚀 Features

- **Local LLM Integration**: Uses Ollama with Llama 3.2 3B for local processing
- **Comprehensive Data**: Detailed datasets covering 10+ Middle Eastern countries
- **RESTful APIs**: Clean API endpoints for each component
- **Military Intelligence**: Strategic analysis and tactical recommendations
- **Modular Design**: Independent apps for different military aspects

## 📋 Prerequisites

- Python 3.8+
- Django 5.2.5
- Ollama (for local LLM)
- Mac M1 Pro (optimized for Apple Silicon)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Wargaming
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Ollama
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 5. Download the LLM Model
```bash
ollama pull llama3.2:3b
```

### 6. Run Django Migrations
```bash
python manage.py migrate
```

### 7. Start the Development Server
```bash
python manage.py runserver
```

## 📚 Documentation

Each app has its own detailed documentation:

- [Geography App README](geography/README.md) - Terrain and strategic analysis
- [Personnel App README](personnel/README.md) - Military personnel management
- [Weapons App README](weapons/README.md) - Equipment and weapons analysis

## 🔗 API Endpoints

### Geography Analysis
- `POST /geography/api/analyze/` - Analyze geographical data
- `GET /geography/api/regions/` - Get available regions
- `GET /geography/api/regions/{region}/` - Get region data
- `GET /geography/api/health/` - Health check

### Personnel Management
- `GET /personnel/api/health/` - Health check
- `GET /personnel/api/countries/` - Get available countries
- `GET /personnel/api/countries/{country}/` - Get country personnel
- `GET /personnel/api/countries/{country}/branches/` - Get branches
- `GET /personnel/api/countries/{country}/branches/{branch}/` - Get branch personnel

### Weapons Analysis
- `POST /weapons/api/analyze/` - Analyze weapons data
- `GET /weapons/api/categories/` - Get weapon categories
- `GET /weapons/api/categories/{category}/` - Get category data
- `GET /weapons/api/health/` - Health check

## 🎮 Usage Examples

### Geography Analysis
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key terrain features of Syria?",
    "region": "syria"
  }'
```

### Personnel Query
```bash
curl http://localhost:8000/personnel/api/countries/israel/
```

### Weapons Analysis
```bash
curl -X POST http://localhost:8000/weapons/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare tank capabilities in the region",
    "weapon_category": "armored_vehicles"
  }'
```

## 🔧 Management Commands

### Retrain LLM Models
```bash
# Geography model
python manage.py retrain_llm

# Personnel model
python manage.py retrain_personnel_llm

# Weapons model
python manage.py retrain_weapons_llm
```

## 🗺️ Supported Regions

The system covers military data for:
- Syria, Iraq, Iran, Israel, Lebanon
- Jordan, Saudi Arabia, Yemen, Egypt, Turkey

## 🛡️ Data Sources

- **Geography**: Terrain, weather, strategic features, military considerations
- **Personnel**: Active duty, reserves, ranks, special units, branches
- **Weapons**: Individual weapons, armored vehicles, artillery, air defense, naval vessels

## 🔍 Troubleshooting

### Ollama Issues
```bash
# Start Ollama
ollama serve

# Check model availability
ollama list
```

### API Errors
- Check Django server logs
- Verify Ollama is running on `http://localhost:11434`
- Ensure data files exist in respective app directories

## 📈 Performance

- **Response Time**: 5-15 seconds for LLM analysis
- **Memory Usage**: ~4GB RAM for LLM model
- **Concurrent Requests**: 2-3 simultaneous requests recommended

## 🔮 Future Enhancements

- Real-time weather integration
- Advanced battle simulation algorithms
- Multi-region conflict scenarios
- Historical battle data integration
- Machine learning model improvements

## 📄 License

This project is for educational and research purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review individual app READMEs
3. Open an issue on the repository
