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
    
    def __init__(self, model_name: str = "llama3.2:3b-weapons", base_url: str = "http://localhost:11434"):
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
        return """Military weapons expert. Analyze weapons and provide victory probability insights. Be brief and focused."""

    def _create_user_prompt(self, query: str, weapon_data: Dict[str, Any] = None, country: str = None) -> str:
        """Create the user prompt with weapons context"""
        if weapon_data and country:
            context = f"{country}: {weapon_data.get('name', 'Unknown')} ({weapon_data.get('effectiveness', 'Unknown')}). {query}"
        else:
            context = query
        
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
            # Check if this is a simple query that can be answered quickly
            if self._is_simple_query(query):
                return self._get_quick_response(query, weapon_category, country)
            
            # Get weapon data if specified
            weapon_data = None
            if weapon_category and weapon_category.lower() in self.weapons_data.get('weapon_categories', {}):
                weapon_data = self.weapons_data['weapon_categories'][weapon_category.lower()]
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, weapon_data, country)
            
            # Prepare the request to Ollama with optimized parameters
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.7,
                    "max_tokens": 500,
                    "num_predict": 500,
                    "num_ctx": 1024
                }
            }
            
            # Make request to Ollama with reduced timeout
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
    
    def _is_simple_query(self, query: str) -> bool:
        """Check if this is a simple query that can be answered quickly"""
        simple_keywords = ['victory probability', 'compare', 'vs', 'versus', 'conflict']
        return any(keyword in query.lower() for keyword in simple_keywords)
    
    def _get_quick_response(self, query: str, weapon_category: str = None, country: str = None) -> Dict[str, Any]:
        """Provide a quick response for simple queries without using LLM"""
        query_lower = query.lower()
        
        if 'victory probability' in query_lower or 'compare' in query_lower:
            # Extract countries from query
            countries = self._extract_countries_from_query(query)
            if len(countries) >= 2:
                return self._quick_victory_analysis(countries[0], countries[1])
        
        # Default quick response
        return {
            "success": True,
            "analysis": "Quick analysis: Based on available weapons data, this requires detailed LLM analysis. For faster response, try a more specific query.",
            "query": query
        }
    
    def _extract_countries_from_query(self, query: str) -> List[str]:
        """Extract country names from query"""
        # Simple country extraction - in production you'd want a more sophisticated approach
        countries = []
        query_lower = query.lower()
        
        # Common Middle East countries
        middle_east_countries = ['israel', 'syria', 'iran', 'iraq', 'turkey', 'saudi arabia', 'uae', 'egypt', 'jordan', 'lebanon']
        
        for country in middle_east_countries:
            if country in query_lower:
                countries.append(country.title())
        
        return countries
    
    def _quick_victory_analysis(self, country1: str, country2: str) -> Dict[str, Any]:
        """Provide a quick victory analysis based on weapons data"""
        weapons1 = self.get_country_weapons(country1)
        weapons2 = self.get_country_weapons(country2)
        
        # Simple analysis based on weapon categories
        categories1 = len(weapons1.keys())
        categories2 = len(weapons2.keys())
        
        if categories1 > categories2:
            winner = country1
            confidence = "High"
            reason = f"{country1} has more weapon categories ({categories1} vs {categories2})"
        elif categories2 > categories1:
            winner = country2
            confidence = "High"
            reason = f"{country2} has more weapon categories ({categories2} vs {categories1})"
        else:
            winner = "Tie"
            confidence = "Medium"
            reason = f"Both countries have similar weapon diversity ({categories1} categories each)"
        
        analysis = f"Quick Victory Analysis:\n\n{country1} vs {country2}:\n- Winner: {winner}\n- Confidence: {confidence}\n- Reason: {reason}\n\nNote: This is a simplified analysis. For detailed assessment, use LLM analysis."
        
        return {
            "success": True,
            "analysis": analysis,
            "country1": country1,
            "country2": country2,
            "weapons1": weapons1,
            "weapons2": weapons2,
            "query": f"Compare {country1} vs {country2}"
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
            
            # Create a focused analysis query
            query = f"Compare {country1} vs {country2} in {scenario} conflict. Focus on key weapons and victory probability."
            
            # Use custom model with optimized settings for faster response
            system_prompt = "Military weapons expert. Analyze weapons and provide victory probability insights. Be brief and focused."
            user_prompt = f"Victory probability analysis: {query}"
            
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.7,
                    "max_tokens": 400,
                    "num_predict": 400,
                    "num_ctx": 1024
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=25
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('message', {}).get('content', '')
                
                return {
                    "success": True,
                    "country1": country1,
                    "country2": country2,
                    "scenario": scenario,
                    "analysis": analysis,
                    "weapons1": weapons1,
                    "weapons2": weapons2
                }
            else:
                # Fallback to quick analysis if model fails
                return self._quick_victory_analysis(country1, country2)
                
        except Exception as e:
            logger.error(f"Error calculating victory probability: {str(e)}")
            # Fallback to quick analysis if model fails
            return self._quick_victory_analysis(country1, country2)
    
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
