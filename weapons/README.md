# Weapons Analysis App

The Weapons Analysis app provides comprehensive military equipment and weapons data analysis for Middle Eastern armed forces. It manages detailed information about various weapon categories, their capabilities, and effectiveness assessments.

## 🎯 Purpose

This app analyzes military weapons and equipment including:
- Individual weapons (assault rifles, sniper rifles, etc.)
- Armored vehicles (tanks, APCs, IFVs)
- Artillery systems (howitzers, rocket launchers)
- Air defense systems (SAMs, anti-aircraft guns)
- Naval vessels (frigates, corvettes, patrol boats)
- Aircraft (fighters, helicopters, transport)

## 📊 Data Coverage

The app covers weapons data for 10 Middle Eastern countries across multiple categories:

- **Individual Weapons**: Assault rifles, sniper rifles, machine guns
- **Armored Vehicles**: Main battle tanks, APCs, IFVs
- **Artillery**: Howitzers, rocket launchers, mortars
- **Air Defense**: Surface-to-air missiles, anti-aircraft systems
- **Naval Vessels**: Frigates, corvettes, patrol boats
- **Aircraft**: Fighter jets, attack helicopters, transport aircraft

## 🏗️ Architecture

```
weapons/
├── data/
│   └── middle_east_weapons.json      # Weapons dataset
├── services/
│   └── weapons_service.py           # Data management service
├── management/
│   └── commands/
│       └── retrain_weapons_llm.py   # Model retraining command
├── views.py                         # API endpoints
└── urls.py                          # URL routing
```

## 🔗 API Endpoints

### Analyze Weapons
**POST** `/weapons/api/analyze/`

Analyze weapons data and get military insights.

**Request Body:**
```json
{
    "query": "Compare tank capabilities in the region",
    "weapon_category": "armored_vehicles",  // optional
    "country": "israel"                     // optional
}
```

**Response:**
```json
{
    "success": true,
    "analysis": "Based on the weapons data analysis...",
    "weapon_category": "armored_vehicles",
    "country": "Israel",
    "query": "Compare tank capabilities in the region"
}
```

### Get Weapon Categories
**GET** `/weapons/api/categories/`

Get list of all available weapon categories.

**Response:**
```json
{
    "success": true,
    "categories": ["individual_weapons", "armored_vehicles", "artillery", "air_defense", "naval_vessels", "aircraft"]
}
```

### Get Category Data
**GET** `/weapons/api/categories/{category}/`

Get detailed data for a specific weapon category.

**Response:**
```json
{
    "success": true,
    "category": "individual_weapons",
    "data": {
        "name": "Individual Weapons",
        "description": "Personal firearms and portable weapons",
        "types": {
            "assault_rifles": {...},
            "sniper_rifles": {...}
        }
    }
}
```

### Health Check
**GET** `/weapons/api/health/`

Check system status and LLM availability.

**Response:**
```json
{
    "success": true,
    "llm_available": true,
    "model_name": "llama3.2:3b",
    "available_categories": 6
}
```

## 📋 Data Structure

### Weapon Category Format
Each category contains:

#### Category Information
```json
{
    "name": "Individual Weapons",
    "description": "Personal firearms and portable weapons for individual use.",
    "types": {
        "assault_rifles": {
            "name": "Assault Rifles",
            "description": "Automatic rifles for infantry",
            "effectiveness": "high",
            "range": "medium",
            "accuracy": "high",
            "mobility": "high",
            "logistics": "moderate",
            "cost": "moderate"
        }
    }
}
```

#### Weapon Specifications
```json
{
    "models": {
        "ak_47": {
            "caliber": "7.62mm",
            "capacity": 30,
            "range": "400m",
            "fire_rate": "600rpm"
        },
        "m16": {
            "caliber": "5.56mm",
            "capacity": 30,
            "range": "550m",
            "fire_rate": "700rpm"
        }
    }
}
```

#### Country Distribution
```json
{
    "countries": {
        "syria": {
            "quantity": "extensive",
            "primary_models": ["ak_47", "ak_74"]
        },
        "israel": {
            "quantity": "extensive",
            "primary_models": ["m4_carbine", "tavor"]
        }
    }
}
```

### Weapon Categories

#### Individual Weapons
- **Assault Rifles**: AK-47, M16, M4 Carbine, G3, Tavor
- **Sniper Rifles**: Dragunov, M24, Barret M82
- **Machine Guns**: PKM, M249, M60
- **Submachine Guns**: MP5, Uzi, PPSh-41

#### Armored Vehicles
- **Main Battle Tanks**: T-72, M1A1 Abrams, Merkava, Leopard 2
- **APCs**: BTR-80, M113, Namer
- **IFVs**: BMP-2, Bradley, Namer IFV

#### Artillery
- **Howitzers**: M109, D-30, M198
- **Rocket Launchers**: BM-21, M270 MLRS
- **Mortars**: 120mm, 81mm, 60mm

#### Air Defense
- **SAMs**: S-300, Patriot, Iron Dome
- **Anti-Aircraft Guns**: ZSU-23-4, M163 VADS

#### Naval Vessels
- **Frigates**: Oliver Hazard Perry, MEKO 200
- **Corvettes**: Sa'ar 5, Type 056
- **Patrol Boats**: Various coastal defense vessels

#### Aircraft
- **Fighters**: F-16, F-15, MiG-29, Su-27
- **Attack Helicopters**: AH-64 Apache, Mi-24 Hind
- **Transport**: C-130, Il-76, CH-47

## 🎮 Usage Examples

### Weapons Analysis
```bash
curl -X POST http://localhost:8000/weapons/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare tank capabilities in the region",
    "weapon_category": "armored_vehicles"
  }'
```

### Category-Specific Analysis
```bash
curl -X POST http://localhost:8000/weapons/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main air defense systems in Israel?",
    "weapon_category": "air_defense",
    "country": "israel"
  }'
```

### Get Weapon Categories
```bash
curl http://localhost:8000/weapons/api/categories/
```

### Get Category Data
```bash
curl http://localhost:8000/weapons/api/categories/individual_weapons/
```

## 🔧 Management Commands

### Retrain Weapons LLM Model
```bash
# Retrain with default model
python manage.py retrain_weapons_llm

# Retrain with specific model
python manage.py retrain_weapons_llm --model llama3.2:7b

# Force retrain even if model exists
python manage.py retrain_weapons_llm --force
```

## 🛠️ Customization

### Adding New Weapon Categories
1. Edit `weapons/data/middle_east_weapons.json`
2. Add new category data following the existing structure
3. Restart the Django server

### Adding New Weapons
1. Add weapon data to the appropriate category
2. Include specifications and country distribution
3. Update effectiveness ratings and capabilities

### Modifying Weapon Data
1. Edit the JSON file directly
2. The changes take effect immediately
3. Ensure data consistency across categories

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
- Ensure `weapons/data/middle_east_weapons.json` exists
- Check JSON syntax validity
- Verify file permissions

### API Errors
- Check Django server logs
- Verify Ollama is running on `http://localhost:11434`
- Ensure the weapons data file is properly formatted

## 📈 Performance Considerations

- **Model Size**: Llama 3.2 3B is optimized for M1 Pro performance
- **Response Time**: 5-15 seconds for LLM analysis
- **Memory Usage**: Model requires ~4GB RAM
- **Concurrent Requests**: Limit to 2-3 simultaneous requests for optimal performance

## 🔮 Future Enhancements

- Real-time weapons tracking
- Integration with procurement systems
- Historical weapons data analysis
- Weapons effectiveness modeling
- Advanced comparison algorithms
- Integration with logistics systems
- Weapons maintenance tracking
- Training simulation integration
