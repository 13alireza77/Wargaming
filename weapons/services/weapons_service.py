import json
import requests
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class WeaponsService:
    """
    Service for analyzing weapons and military equipment data
    """
    
    def __init__(self, model_name: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.weapons_data = self._load_weapons_data()
        
    def _load_weapons_data(self) -> Dict[str, Any]:
        """Load the Middle East weapons dataset"""
        data_path = Path(__file__).parent.parent / "data" / "middle_east_weapons.json"
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Weapons data file not found at {data_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in weapons data file at {data_path}")
            return {}
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for weapons analysis"""
        return """You are a military weapons and equipment expert specializing in Middle Eastern military capabilities analysis. 
Your task is to analyze weapons data and provide strategic military insights about weapon effectiveness and victory probability.

Available weapon categories: Individual Weapons, Collective Weapons, Cold Weapons, Robotics/AI Weapons, Conventional Weapon Systems, Unconventional Weapons, Chemical Weapons, Biological Weapons, Nuclear Weapons, Toxic Weapons

For each analysis, provide:
1. Weapon effectiveness assessment and capabilities
2. Strategic advantages and disadvantages
3. Impact on victory probability
4. Logistics and maintenance considerations
5. Tactical and operational recommendations

Base your analysis on the provided weapons data and military considerations."""

    def _create_user_prompt(self, query: str, weapon_data: Dict[str, Any] = None, country: str = None) -> str:
        """Create the user prompt with weapons context"""
        if weapon_data and country:
            context = f"""
Weapon Category: {weapon_data.get('name', 'Unknown')}
Country: {country}
Weapon Type: {weapon_data.get('description', 'Unknown')}
Effectiveness: {weapon_data.get('effectiveness', 'Unknown')}
Range: {weapon_data.get('range', 'Unknown')}

Query: {query}
"""
        else:
            context = f"""
Available weapons data for Middle East countries including individual weapons, collective weapons, and various weapon categories.

Query: {query}
"""
        
        return context

    def analyze_weapons(self, query: str, weapon_category: str = None, country: str = None) -> Dict[str, Any]:
        """
        Analyze weapons data based on the query
        
        Args:
            query: The weapons analysis question
            weapon_category: Specific weapon category to focus on (optional)
            country: Specific country to focus on (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Get weapon data if specified
            weapon_data = None
            if weapon_category and weapon_category.lower() in self.weapons_data.get('weapon_categories', {}):
                weapon_data = self.weapons_data['weapon_categories'][weapon_category.lower()]
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, weapon_data, country)
            
            # Prepare the request to Ollama
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            }
            
            # Make request to Ollama
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('message', {}).get('content', '')
                
                return {
                    "success": True,
                    "analysis": analysis,
                    "weapon_category": weapon_data.get('name') if weapon_data else None,
                    "country": country,
                    "query": query
                }
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "query": query
                }
                
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama. Make sure Ollama is running.")
            return {
                "success": False,
                "error": "Ollama not running. Please start Ollama and ensure the model is available.",
                "query": query
            }
        except Exception as e:
            logger.error(f"Error in weapons analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis error: {str(e)}",
                "query": query
            }
    
    def get_available_weapon_categories(self) -> List[str]:
        """Get list of available weapon categories"""
        return list(self.weapons_data.get('weapon_categories', {}).keys())
    
    def get_weapon_category_data(self, category: str) -> Dict[str, Any]:
        """Get data for a specific weapon category"""
        return self.weapons_data.get('weapon_categories', {}).get(category.lower(), {})
    
    def get_country_weapons(self, country: str) -> Dict[str, Any]:
        """Get all weapons data for a specific country"""
        country_weapons = {}
        categories = self.weapons_data.get('weapon_categories', {})
        
        for category_name, category_data in categories.items():
            types = category_data.get('types', {})
            for weapon_type, weapon_data in types.items():
                countries = weapon_data.get('countries', {})
                if country.lower() in countries:
                    if category_name not in country_weapons:
                        country_weapons[category_name] = {}
                    country_weapons[category_name][weapon_type] = weapon_data
        
        return country_weapons
    
    def calculate_victory_probability(self, country1: str, country2: str, scenario: str = "conventional") -> Dict[str, Any]:
        """
        Calculate victory probability between two countries based on their weapons
        
        Args:
            country1: First country
            country2: Second country
            scenario: Type of conflict scenario
            
        Returns:
            Dictionary with victory probability analysis
        """
        try:
            # Get weapons data for both countries
            weapons1 = self.get_country_weapons(country1)
            weapons2 = self.get_country_weapons(country2)
            
            # Create analysis query
            query = f"Compare the military capabilities of {country1} and {country2} in a {scenario} conflict scenario. Analyze their weapons and calculate the probability of victory for each side."
            
            # Perform analysis
            result = self.analyze_weapons(query)
            
            if result['success']:
                return {
                    "success": True,
                    "country1": country1,
                    "country2": country2,
                    "scenario": scenario,
                    "analysis": result['analysis'],
                    "weapons1": weapons1,
                    "weapons2": weapons2
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error calculating victory probability: {str(e)}")
            return {
                "success": False,
                "error": f"Calculation error: {str(e)}"
            }
    
    def check_model_availability(self) -> bool:
        """Check if the specified model is available in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name') == self.model_name for model in models)
            return False
        except:
            return False
