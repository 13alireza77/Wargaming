# Geography Analysis App

The Geography Analysis app provides comprehensive terrain and strategic analysis for military operations in the Middle East region. It uses local LLMs to analyze geographical data and provide military insights focused on war conditions and battle outcomes.

## 🎯 Purpose

This app analyzes geographical features that impact military operations and war outcomes, including:
- **War Condition Analysis**: Terrain advantages for attack/defense operations
- **Strategic Positioning**: Key locations that control the battlefield
- **Logistical Challenges**: Supply lines, water sources, and infrastructure
- **Weather Impact**: How climate affects military operations
- **War Outcome Prediction**: Which side has geographical advantages for victory
- **Battle Scenario Analysis**: Comparative analysis between regions for war planning

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

### Analyze Geography (War Conditions)
**POST** `/geography/api/analyze/`

Analyze geographical data and get military insights focused on war conditions and battle outcomes.

**Request Body:**
```json
{
    "query": "What are the war conditions in Syria and how do they affect battle outcomes?",
    "region": "syria"  // optional
}
```

**Response:**
```json
{
    "success": true,
    "analysis": "WAR CONDITIONS ANALYSIS - Syria:\n\nTERRAIN ASSESSMENT:\n- Primary terrain: desert\n- Difficulty level: moderate\n- Key advantages: mountainous_west, desert_cover\n- Major challenges: limited_water, extreme_heat\n\nSTRATEGIC EVALUATION:\n- Defensive positions: Golan Heights, coastal_mountains\n- Offensive routes: Euphrates Valley, coastal_highway\n\nWAR OUTCOME PREDICTION:\nBased on terrain analysis, this region shows moderate conditions for military operations...",
    "region": "Syria",
    "query": "What are the war conditions in Syria and how do they affect battle outcomes?",
    "analysis_type": "war_conditions",
    "model_used": "llama3.2:3b-geography",
    "response_time": "< 10 seconds",
    "strategic_summary": {
        "terrain_difficulty": "moderate",
        "key_advantages": ["mountainous_west", "desert_cover"],
        "major_challenges": ["limited_water", "extreme_heat"]
    }
}
```

### Analyze War Conditions (Region Comparison)
**POST** `/geography/api/war-conditions/`

Compare two regions for war scenario analysis and predict battle outcomes.

**Request Body:**
```json
{
    "attacker_region": "syria",
    "defender_region": "israel",
    "scenario": "Desert warfare scenario"  // optional
}
```

**Response:**
```json
{
    "success": true,
    "analysis": "WAR SCENARIO ANALYSIS:\n\nATTACKER: Syria\n- Terrain: Mostly desert with mountain ranges in the west\n- Advantages: mountainous_west, desert_cover\n- Challenges: limited_water, extreme_heat\n\nDEFENDER: Israel\n- Terrain: Narrow coastal plain with central mountains\n- Advantages: narrow_front, technological_edge\n- Challenges: lack_of_depth, vulnerable_borders\n\nWAR OUTCOME PREDICTION:\nBased on geographical analysis...",
    "war_scenario": {
        "attacker": "syria",
        "defender": "israel",
        "scenario": "Desert warfare scenario"
    },
    "analysis_type": "war_conditions_comparison",
    "model_used": "llama3.2:3b-geography",
    "response_time": "< 10 seconds"
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
    "model_name": "llama3.2:3b-geography",
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

## 🎮 Usage Examples & Testing

### 1. Health Check
Test if the service is running and LLM is available:
```bash
curl -X GET http://localhost:8000/geography/api/health/ \
  -H "Content-Type: application/json"
```

### 2. War Conditions Analysis
Analyze war conditions for a specific region:
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the war conditions in Syria and how do they affect battle outcomes?",
    "region": "syria"
  }'
```

### 3. War Scenario Comparison
Compare two regions for war scenario analysis:
```bash
curl -X POST http://localhost:8000/geography/api/war-conditions/ \
  -H "Content-Type: application/json" \
  -d '{
    "attacker_region": "iran",
    "defender_region": "iraq",
    "scenario": "Mountain vs Desert warfare"
  }'
```

### 4. Terrain Analysis for War Planning
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the mountainous terrain of Iran affect offensive military operations?",
    "region": "iran"
  }'
```

### 5. Weather Impact on War Conditions
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the weather challenges for military operations in Saudi Arabia during summer?",
    "region": "saudi_arabia"
  }'
```

### 6. Strategic Position Analysis
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the strategic advantages and disadvantages of defending the Golan Heights?",
    "region": "syria"
  }'
```

### 7. Logistics Challenges for War
```bash
curl -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main logistics challenges for military operations in Yemen?",
    "region": "yemen"
  }'
```

### 8. Get Available Regions
```bash
curl -X GET http://localhost:8000/geography/api/regions/ \
  -H "Content-Type: application/json"
```

### 9. Get Specific Region Data
```bash
curl -X GET http://localhost:8000/geography/api/regions/israel/ \
  -H "Content-Type: application/json"
```

### 10. Complex War Scenario Analysis
```bash
curl -X POST http://localhost:8000/geography/api/war-conditions/ \
  -H "Content-Type: application/json" \
  -d '{
    "attacker_region": "turkey",
    "defender_region": "syria",
    "scenario": "Mountain warfare with winter conditions"
  }'
```

## 🧪 Testing Script

Create a test script to verify all endpoints:

```bash
#!/bin/bash
echo "Testing Geography Service API Endpoints..."

echo "1. Health Check:"
curl -s -X GET http://localhost:8000/geography/api/health/ | jq '.'

echo -e "\n2. Available Regions:"
curl -s -X GET http://localhost:8000/geography/api/regions/ | jq '.'

echo -e "\n3. War Conditions Analysis:"
curl -s -X POST http://localhost:8000/geography/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze war conditions in Israel", "region": "israel"}' | jq '.'

echo -e "\n4. War Scenario Comparison:"
curl -s -X POST http://localhost:8000/geography/api/war-conditions/ \
  -H "Content-Type: application/json" \
  -d '{"attacker_region": "egypt", "defender_region": "israel", "scenario": "Desert warfare"}' | jq '.'

echo -e "\n5. Region Data:"
curl -s -X GET http://localhost:8000/geography/api/regions/iran/ | jq '.'

echo -e "\nTesting completed!"
```

### Quick Test Script
Run the comprehensive test script to verify all endpoints:

```bash
# Make the script executable (if not already)
chmod +x test_geography_api.sh

# Run the test script
./test_geography_api.sh
```

This script will test all 10 endpoints and provide a comprehensive overview of the service functionality.

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

- **Model Size**: Llama 3.2 3B Geography is optimized for war condition analysis
- **Response Time**: Optimized to stay under 10 seconds with fallback mechanisms
- **Memory Usage**: Model requires ~4GB RAM
- **Concurrent Requests**: Limit to 2-3 simultaneous requests for optimal performance
- **Fallback Strategy**: Primary model → Fallback model → Mock response (always succeeds)
- **Timeout Management**: 3-second timeout for primary model, 2-second for fallback
- **War Analysis Focus**: Specialized prompts for faster, more focused military intelligence

## ⚔️ War Analysis Features

### Enhanced Military Intelligence
- **Terrain Advantages**: Analysis of how geography favors defensive or offensive operations
- **Strategic Positions**: Identification of key locations that control the battlefield
- **Logistical Challenges**: Assessment of supply lines, water sources, and infrastructure
- **Weather Impact**: Evaluation of how climate affects military operations
- **War Outcome Prediction**: Prediction of which side has geographical advantages for victory

### Battle Scenario Analysis
- **Region Comparison**: Side-by-side analysis of two regions for war planning
- **Scenario-Specific Analysis**: Custom war scenarios with specific conditions
- **Strategic Recommendations**: Actionable military intelligence for decision-making
- **Risk Assessment**: Evaluation of geographical risks and opportunities

### Response Optimization
- **Fast Response Times**: Guaranteed response under 10 seconds
- **Fallback Mechanisms**: Multiple layers of reliability (Primary → Fallback → Mock)
- **Specialized Prompts**: Military-focused prompts for accurate war analysis
- **Structured Output**: Consistent format for integration with decision-making systems

## 🔮 Future Enhancements

- Real-time weather data integration
- Satellite imagery analysis
- 3D terrain visualization
- Historical weather pattern analysis
- Advanced terrain difficulty algorithms
- Integration with GIS systems
- Multi-region battle simulations
- Historical war outcome analysis
- Advanced logistics optimization
