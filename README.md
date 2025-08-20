# War Game Simulation System - Phase 1: Geographical Analysis

A Django-based war game simulation system that uses local LLMs to analyze geographical data and provide military insights for the Middle East region.

## Features

- **Comprehensive Middle East Geography Dataset**: Detailed JSON dataset covering terrain, weather, strategic features, and military considerations for 10 Middle Eastern countries
- **Local LLM Integration**: Uses Ollama with Llama 3.2 3B model for local processing (no cloud dependencies)
- **RESTful API**: Clean API endpoints for geographical analysis
- **Military Intelligence**: Provides terrain assessment, weather impact, strategic advantages/disadvantages, and tactical recommendations
- **Easy Data Management**: JSON-based dataset that's easy to edit and update

## Supported Regions

- Syria
- Iraq
- Iran
- Israel
- Lebanon
- Jordan
- Saudi Arabia
- Yemen
- Egypt
- Turkey

## Prerequisites

- Python 3.8+
- Django 5.2.5
- Ollama (for local LLM)
- Mac M1 Pro (optimized for Apple Silicon)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd war_gaming
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
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh
```

### 5. Download the LLM Model
```bash
# Pull the Llama 3.2 3B model
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

## Usage

### API Endpoints

#### 1. Analyze Geography
**POST** `/geography/api/analyze/`

Analyze geographical data and get military insights.

**Request Body:**
```json
{
    "query": "What are the key terrain features of Syria and how do they affect military operations?",
    "region": "syria"  // optional
}
```

**Response:**
```json
{
    "success": true,
    "analysis": "Based on the geographical data for Syria...",
    "region": "Syria",
    "query": "What are the key terrain features of Syria and how do they affect military operations?"
}
```

#### 2. Get Available Regions
**GET** `/geography/api/regions/`

Get list of all available regions.

**Response:**
```json
{
    "success": true,
    "regions": ["syria", "iraq", "iran", "israel", "lebanon", "jordan", "saudi_arabia", "yemen", "egypt", "turkey"]
}
```

#### 3. Get Region Data
**GET** `/geography/api/regions/{region}/`

Get detailed data for a specific region.

**Response:**
```json
{
    "success": true,
    "region": "syria",
    "data": {
        "name": "Syria",
        "terrain": {...},
        "weather": {...},
        "strategic_features": {...},
        "military_considerations": {...}
    }
}
```

#### 4. Health Check
**GET** `/geography/api/health/`

Check system status and LLM availability.

**Response:**
```json
{
    "success": true,
    "llm_available": true,
    "model_name": "llama3.2:3b",
    "available_regions": 10
}
```

### Management Commands

#### Retrain LLM Model
```bash
# Retrain with default model
python manage.py retrain_llm

# Retrain with specific model
python manage.py retrain_llm --model llama3.2:7b

# Force retrain even if model exists
python manage.py retrain_llm --force
```

## Example Queries

### Terrain Analysis
```json
{
    "query": "How does the mountainous terrain of Iran affect offensive military operations?",
    "region": "iran"
}
```

### Weather Impact
```json
{
    "query": "What are the weather challenges for military operations in Saudi Arabia during summer?",
    "region": "saudi_arabia"
}
```

### Strategic Assessment
```json
{
    "query": "What are the strategic advantages and disadvantages of defending the Golan Heights?",
    "region": "syria"
}
```

### Logistics Planning
```json
{
    "query": "What are the main logistics challenges for military operations in Yemen?",
    "region": "yemen"
}
```

## Data Structure

The geographical dataset (`geography/data/middle_east_geography.json`) contains:

### Region Data
- **Terrain**: Primary/secondary terrain types, elevation data, difficulty rating
- **Weather**: Climate type, temperature ranges, precipitation, visibility/mobility impact
- **Strategic Features**: Ports, airports, mountain passes, rivers, oil fields, urban centers
- **Military Considerations**: Terrain advantages/disadvantages, logistics challenges, defensive/offensive positions

### Weather Patterns
- Sandstorms, dust storms, winter snow, monsoon rains
- Frequency and impact on military operations

### Strategic Chokepoints
- Suez Canal, Strait of Hormuz, Bab el-Mandeb, Golan Heights
- Strategic importance and control implications

### Infrastructure
- Major highways, railway networks, airports
- Vulnerability assessments

## Customization

### Adding New Regions
1. Edit `geography/data/middle_east_geography.json`
2. Add new region data following the existing structure
3. Restart the Django server

### Modifying LLM Model
1. Change the model in `geography/services/llm_service.py`
2. Update the `model_name` parameter in the `LLMService` class
3. Run `python manage.py retrain_llm --model your_model_name`

### Updating Geographical Data
1. Edit the JSON file directly
2. The changes take effect immediately (no retraining required)
3. For major changes, consider retraining the model

## Troubleshooting

### Ollama Not Running
```bash
# Start Ollama
ollama serve

# Check if model is available
ollama list
```

### Model Not Found
```bash
# Pull the required model
ollama pull llama3.2:3b

# Or use a different model
python manage.py retrain_llm --model llama3.2:7b
```

### API Errors
- Check Django server logs
- Verify Ollama is running on `http://localhost:11434`
- Ensure the geographical data file exists

## Performance Considerations

- **Model Size**: Llama 3.2 3B is optimized for M1 Pro performance
- **Response Time**: Typical response time is 5-15 seconds
- **Memory Usage**: Model requires ~4GB RAM
- **Concurrent Requests**: Limit to 2-3 simultaneous requests for optimal performance

## Future Enhancements (Phase 2+)

- Weapons and equipment data
- Army composition and capabilities
- Historical battle data
- Real-time weather integration
- Advanced battle simulation algorithms
- Multi-region conflict scenarios

## License

This project is for educational and research purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Django and Ollama documentation
3. Open an issue on the repository
