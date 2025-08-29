# Geography Analysis App

The Geography Analysis app provides comprehensive terrain and strategic analysis for military operations in the Middle East region. It uses local LLMs to analyze geographical data and provide military insights.

## 🎯 Purpose

This app analyzes geographical features that impact military operations, including:
- Terrain characteristics and difficulty ratings
- Weather patterns and their impact on operations
- Strategic features (ports, airports, mountain passes)
- Military considerations for offensive and defensive operations

## 📊 Data Coverage

The app covers 10 Middle Eastern countries with detailed geographical data:

- **Syria**: Desert terrain with mountain ranges and coastal plains
- **Iraq**: Desert plains with marshlands and northern mountains
- **Iran**: Mountainous terrain with central plateau
- **Israel**: Diverse terrain including coastal plains and mountains
- **Lebanon**: Mountainous with coastal strip
- **Jordan**: Desert plateau with mountain ranges
- **Saudi Arabia**: Extensive desert with mountain ranges
- **Yemen**: Mountainous terrain with coastal plains
- **Egypt**: Desert with Nile Valley and Sinai Peninsula
- **Turkey**: Diverse terrain including mountains and coastal areas

## 🏗️ Architecture

```
geography/
├── data/
│   └── middle_east_geography.json    # Geographical dataset
├── services/
│   └── llm_service.py               # LLM integration service
├── management/
│   └── commands/
│       └── retrain_llm.py           # Model retraining command
├── views.py                         # API endpoints
└── urls.py                          # URL routing
```

## 🔗 API Endpoints

### Analyze Geography
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

### Get Available Regions
**GET** `/geography/api/regions/`

Get list of all available regions.

**Response:**
```json
{
    "success": true,
    "regions": ["syria", "iraq", "iran", "israel", "lebanon", "jordan", "saudi_arabia", "yemen", "egypt", "turkey"]
}
```

### Get Region Data
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

### Health Check
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

## 📋 Data Structure

### Region Data Format
Each region contains:

#### Terrain Information
```json
{
    "primary": "desert",
    "secondary": ["mountains", "coastal_plains"],
    "elevation": {
        "min": 0,
        "max": 2814,
        "average": 514
    },
    "difficulty": "moderate",
    "description": "Mostly desert with mountain ranges in the west"
}
```

#### Weather Data
```json
{
    "climate": "mediterranean",
    "temperature": {
        "summer": {"min": 20, "max": 40},
        "winter": {"min": 5, "max": 15}
    },
    "precipitation": {
        "annual": "low",
        "season": "winter",
        "mm_per_year": 252
    },
    "visibility_impact": "moderate",
    "mobility_impact": "high"
}
```

#### Strategic Features
```json
{
    "ports": ["Latakia", "Tartus"],
    "airports": ["Damascus", "Aleppo", "Latakia"],
    "mountain_passes": ["Golan Heights"],
    "rivers": ["Euphrates", "Orontes"],
    "oil_fields": ["Deir ez-Zor", "Homs"],
    "urban_centers": ["Damascus", "Aleppo", "Homs", "Hama"]
}
```

#### Military Considerations
```json
{
    "terrain_advantages": ["mountainous_west", "desert_cover"],
    "terrain_disadvantages": ["limited_water", "extreme_heat"],
    "logistics_challenges": ["water_supply", "fuel_consumption"],
    "defensive_positions": ["Golan Heights", "coastal_mountains"],
    "offensive_routes": ["Euphrates Valley", "coastal_highway"]
}
```

## 🎮 Usage Examples

### Terrain Analysis
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the mountainous terrain of Iran affect offensive military operations?",
    "region": "iran"
  }'
```

### Weather Impact Assessment
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the weather challenges for military operations in Saudi Arabia during summer?",
    "region": "saudi_arabia"
  }'
```

### Strategic Assessment
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the strategic advantages and disadvantages of defending the Golan Heights?",
    "region": "syria"
  }'
```

### Logistics Planning
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main logistics challenges for military operations in Yemen?",
    "region": "yemen"
  }'
```

## 🔧 Management Commands

### Retrain LLM Model
```bash
# Retrain with default model
python manage.py retrain_llm

# Retrain with specific model
python manage.py retrain_llm --model llama3.2:7b

# Force retrain even if model exists
python manage.py retrain_llm --force
```

## 🛠️ Customization

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

## 🔍 Troubleshooting

### LLM Model Issues
```bash
# Check if Ollama is running
ollama list

# Pull the required model
ollama pull llama3.2:3b

# Restart Ollama
ollama serve
```

### Data File Issues
- Ensure `geography/data/middle_east_geography.json` exists
- Check JSON syntax validity
- Verify file permissions

### API Errors
- Check Django server logs
- Verify Ollama is running on `http://localhost:11434`
- Ensure the geographical data file is properly formatted

## 📈 Performance Considerations

- **Model Size**: Llama 3.2 3B is optimized for M1 Pro performance
- **Response Time**: Typical response time is 5-15 seconds
- **Memory Usage**: Model requires ~4GB RAM
- **Concurrent Requests**: Limit to 2-3 simultaneous requests for optimal performance

## 🔮 Future Enhancements

- Real-time weather data integration
- Satellite imagery analysis
- 3D terrain visualization
- Historical weather pattern analysis
- Advanced terrain difficulty algorithms
- Integration with GIS systems
