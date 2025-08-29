# Personnel Management App

The Personnel Management app provides comprehensive military personnel data and organizational structure analysis for Middle Eastern armed forces. It manages detailed information about active duty personnel, reserves, ranks, and special units.

## 🎯 Purpose

This app manages military personnel data including:
- Active duty and reserve personnel counts
- Military rank structures and hierarchies
- Branch-specific personnel (Ground Forces, Air Force, Navy)
- Special units and their capabilities
- Organizational structure analysis

## 📊 Data Coverage

The app covers military personnel data for 10 Middle Eastern countries:

- **Israel**: 169,500 active duty, 465,000 reserves
- **Iran**: 610,000 active duty, 350,000 reserves
- **Turkey**: 355,000 active duty, 380,000 reserves
- **Egypt**: 438,500 active duty, 479,000 reserves
- **Saudi Arabia**: 227,000 active duty, 25,000 reserves
- **Syria**: 142,500 active duty, 80,000 reserves
- **Iraq**: 193,000 active duty, 145,000 reserves
- **Jordan**: 100,500 active duty, 65,000 reserves
- **Lebanon**: 60,000 active duty, 20,000 reserves
- **Yemen**: 66,000 active duty, 40,000 reserves

## 🏗️ Architecture

```
personnel/
├── data/
│   └── middle_east_personnel.json    # Personnel dataset
├── services/
│   └── personnel_service.py         # Data management service
├── management/
│   └── commands/
│       └── retrain_personnel_llm.py # Model retraining command
├── views.py                         # API endpoints
└── urls.py                          # URL routing
```

## 🔗 API Endpoints

### Health Check
**GET** `/personnel/api/health/`

Check system status and data availability.

**Response:**
```json
{
    "status": "healthy",
    "service": "personnel",
    "available_countries": 10,
    "message": "Personnel service is operational"
}
```

### Get Available Countries
**GET** `/personnel/api/countries/`

Get list of all available countries.

**Response:**
```json
{
    "success": true,
    "countries": ["israel", "iran", "turkey", "egypt", "saudi_arabia", "syria", "iraq", "jordan", "lebanon", "yemen"],
    "count": 10
}
```

### Get Country Personnel
**GET** `/personnel/api/countries/{country}/`

Get comprehensive personnel data for a specific country.

**Response:**
```json
{
    "success": true,
    "country": "israel",
    "data": {
        "name": "Israel",
        "total_personnel": 169500,
        "active_duty": 169500,
        "reserves": 465000,
        "branches": {
            "ground_forces": {...},
            "air_force": {...},
            "navy": {...}
        }
    }
}
```

### Get Available Branches
**GET** `/personnel/api/countries/{country}/branches/`

Get available military branches for a country.

**Response:**
```json
{
    "success": true,
    "country": "israel",
    "branches": ["ground_forces", "air_force", "navy"]
}
```

### Get Branch Personnel
**GET** `/personnel/api/countries/{country}/branches/{branch}/`

Get detailed personnel data for a specific branch.

**Response:**
```json
{
    "success": true,
    "country": "israel",
    "branch": "ground_forces",
    "data": {
        "name": "Israeli Ground Forces",
        "personnel": 133000,
        "ranks": {...},
        "special_units": {...}
    }
}
```

## 📋 Data Structure

### Country Personnel Format
Each country contains:

#### Basic Information
```json
{
    "name": "Israel",
    "total_personnel": 169500,
    "active_duty": 169500,
    "reserves": 465000
}
```

#### Branch Structure
```json
{
    "ground_forces": {
        "name": "Israeli Ground Forces",
        "personnel": 133000,
        "ranks": {
            "officers": {
                "general": {
                    "quantity": 15,
                    "roles": ["Chief of Staff", "Deputy Chief of Staff"]
                },
                "colonel": {
                    "quantity": 150,
                    "roles": ["Brigade Commanders", "Division Chiefs of Staff"]
                }
            },
            "enlisted": {
                "sergeant_major": {
                    "quantity": 2000,
                    "roles": ["Senior NCOs", "Training Instructors"]
                }
            }
        },
        "special_units": {
            "paratroopers": {
                "quantity": 5000,
                "roles": ["Airborne Operations", "Special Missions"]
            }
        }
    }
}
```

### Rank Structure
Each branch includes detailed rank information:

#### Officer Ranks
- **General**: Senior leadership positions
- **Colonel**: Brigade and division commanders
- **Lieutenant Colonel**: Battalion and regiment commanders
- **Major**: Company commanders and staff officers
- **Captain**: Platoon leaders and staff officers
- **Lieutenant**: Platoon leaders and section leaders

#### Enlisted Ranks
- **Sergeant Major**: Senior NCOs and training instructors
- **Master Sergeant**: Platoon sergeants and section leaders
- **Sergeant**: Squad leaders and team leaders
- **Corporal**: Team leaders and specialists
- **Private**: Infantry and support personnel

## 🎮 Usage Examples

### Get Country Overview
```bash
curl http://localhost:8000/personnel/api/countries/israel/
```

### Get Branch Information
```bash
curl http://localhost:8000/personnel/api/countries/israel/branches/ground_forces/
```

### Get Available Countries
```bash
curl http://localhost:8000/personnel/api/countries/
```

### Get Country Branches
```bash
curl http://localhost:8000/personnel/api/countries/iran/branches/
```

## 🔧 Management Commands

### Retrain Personnel LLM Model
```bash
# Retrain with default model
python manage.py retrain_personnel_llm

# Retrain with specific model
python manage.py retrain_personnel_llm --model llama3.2:7b

# Force retrain even if model exists
python manage.py retrain_personnel_llm --force
```

## 🛠️ Customization

### Adding New Countries
1. Edit `personnel/data/middle_east_personnel.json`
2. Add new country data following the existing structure
3. Restart the Django server

### Modifying Personnel Data
1. Edit the JSON file directly
2. The changes take effect immediately
3. Ensure data consistency across branches and ranks

### Adding New Branches
1. Add branch data to the country structure
2. Include rank hierarchy and special units
3. Update personnel counts accordingly

## 🔍 Troubleshooting

### Data File Issues
- Ensure `personnel/data/middle_east_personnel.json` exists
- Check JSON syntax validity
- Verify file permissions

### API Errors
- Check Django server logs
- Verify the personnel data file is properly formatted
- Ensure country and branch names match exactly

### Data Consistency
- Verify total personnel equals sum of branch personnel
- Check that rank quantities are reasonable
- Ensure special unit personnel is included in branch totals

## 📈 Performance Considerations

- **Response Time**: < 1 second for data queries
- **Memory Usage**: Minimal (JSON data loaded on demand)
- **Concurrent Requests**: No limitations for read operations
- **Data Size**: ~1.2MB JSON file

## 🔮 Future Enhancements

- Personnel training and qualification tracking
- Historical personnel data analysis
- Integration with recruitment systems
- Personnel deployment tracking
- Advanced organizational analysis
- Personnel effectiveness metrics
- Integration with HR systems
