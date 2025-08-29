import json
import requests
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class PersonnelService:
    """
    Service for analyzing military personnel data
    """
    
    def __init__(self, model_name: str = "llama3.2:3b-personnel", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.personnel_data = self._load_personnel_data()
        
    def _load_personnel_data(self) -> Dict[str, Any]:
        """Load the Middle East personnel dataset"""
        data_path = Path(__file__).parent.parent / "data" / "middle_east_personnel.json"
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Personnel data file not found at {data_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in personnel data file at {data_path}")
            return {}
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for personnel analysis"""
        return """You are a military personnel and human resources expert specializing in Middle Eastern military capabilities analysis. 
Your task is to analyze military personnel data and provide strategic military insights about troop effectiveness and victory probability.

Available military branches: Ground Forces, Air Force, Navy, Special Forces, Revolutionary Guards (Iran)

For each analysis, provide:
1. Personnel effectiveness assessment and capabilities
2. Strategic advantages and disadvantages based on troop numbers and quality
3. Impact on victory probability considering personnel factors
4. Training and experience considerations
5. Tactical and operational recommendations based on personnel analysis

Base your analysis on the provided personnel data and military considerations."""

    def _create_user_prompt(self, query: str, personnel_data: Dict[str, Any] = None, country: str = None) -> str:
        """Create the user prompt with personnel context"""
        if personnel_data and country:
            context = f"""
Country: {country}
Total Personnel: {personnel_data.get('total_personnel', 'Unknown')}
Active Duty: {personnel_data.get('active_duty', 'Unknown')}
Reserves: {personnel_data.get('reserves', 'Unknown')}

Available branches: {', '.join(personnel_data.get('branches', {}).keys())}

Query: {query}
"""
        else:
            context = f"""
Available personnel data for Middle East countries including ground forces, air force, navy, special forces, and various military branches.

Query: {query}
"""
        
        return context

    def analyze_personnel(self, query: str, country: str = None, branch: str = None) -> Dict[str, Any]:
        """
        Analyze personnel data based on the query
        
        Args:
            query: The personnel analysis question
            country: Specific country to focus on (optional)
            branch: Specific military branch to focus on (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Get personnel data if specified
            personnel_data = None
            if country and country.lower() in self.personnel_data.get('personnel_data', {}).get('countries', {}):
                personnel_data = self.personnel_data['personnel_data']['countries'][country.lower()]
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, personnel_data, country)
            
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
            
            # Make the request
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            analysis = result.get('message', {}).get('content', 'No analysis available')
            
            return {
                "success": True,
                "analysis": analysis,
                "country": country,
                "branch": branch,
                "query": query
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return {
                "success": False,
                "error": f"Failed to communicate with LLM service: {str(e)}",
                "query": query
            }
        except Exception as e:
            logger.error(f"Error analyzing personnel: {e}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "query": query
            }

    def calculate_victory_probability(self, country1: str, country2: str, scenario: str = "conventional") -> Dict[str, Any]:
        """
        Calculate victory probability based on personnel comparison
        
        Args:
            country1: First country in the conflict
            country2: Second country in the conflict
            scenario: Type of conflict scenario
            
        Returns:
            Dictionary containing victory probability analysis
        """
        try:
            # Get personnel data for both countries
            countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
            
            if country1.lower() not in countries_data or country2.lower() not in countries_data:
                return {
                    "success": False,
                    "error": f"Personnel data not available for one or both countries: {country1}, {country2}"
                }
            
            country1_data = countries_data[country1.lower()]
            country2_data = countries_data[country2.lower()]
            
            # Create comparison prompt
            system_prompt = self._create_system_prompt()
            user_prompt = f"""
Compare the military personnel capabilities between {country1} and {country2} for a {scenario} conflict scenario.

{country1} Personnel Data:
- Total Personnel: {country1_data.get('total_personnel', 'Unknown')}
- Active Duty: {country1_data.get('active_duty', 'Unknown')}
- Reserves: {country1_data.get('reserves', 'Unknown')}
- Branches: {', '.join(country1_data.get('branches', {}).keys())}

{country2} Personnel Data:
- Total Personnel: {country2_data.get('total_personnel', 'Unknown')}
- Active Duty: {country2_data.get('active_duty', 'Unknown')}
- Reserves: {country2_data.get('reserves', 'Unknown')}
- Branches: {', '.join(country2_data.get('branches', {}).keys())}

Provide a detailed analysis including:
1. Personnel strength comparison
2. Strategic advantages for each side
3. Victory probability percentages with reasoning
4. Key factors affecting the outcome
5. Tactical recommendations for each side
"""
            
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
                    "max_tokens": 2500
                }
            }
            
            # Make the request
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            analysis = result.get('message', {}).get('content', 'No analysis available')
            
            return {
                "success": True,
                "analysis": analysis,
                "country1": country1,
                "country2": country2,
                "scenario": scenario,
                "country1_data": {
                    "total_personnel": country1_data.get('total_personnel'),
                    "active_duty": country1_data.get('active_duty'),
                    "reserves": country1_data.get('reserves')
                },
                "country2_data": {
                    "total_personnel": country2_data.get('total_personnel'),
                    "active_duty": country2_data.get('active_duty'),
                    "reserves": country2_data.get('reserves')
                }
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return {
                "success": False,
                "error": f"Failed to communicate with LLM service: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error calculating victory probability: {e}")
            return {
                "success": False,
                "error": f"Victory probability calculation failed: {str(e)}"
            }

    def get_country_personnel(self, country: str) -> Dict[str, Any]:
        """
        Get personnel data for a specific country
        
        Args:
            country: Country name
            
        Returns:
            Dictionary containing country personnel data
        """
        try:
            countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
            
            if country.lower() not in countries_data:
                return {
                    "success": False,
                    "error": f"Personnel data not available for country: {country}"
                }
            
            country_data = countries_data[country.lower()]
            
            return {
                "success": True,
                "country": country,
                "data": country_data
            }
            
        except Exception as e:
            logger.error(f"Error getting country personnel: {e}")
            return {
                "success": False,
                "error": f"Failed to get country personnel data: {str(e)}"
            }

    def get_branch_personnel(self, country: str, branch: str) -> Dict[str, Any]:
        """
        Get personnel data for a specific branch of a country
        
        Args:
            country: Country name
            branch: Military branch name
            
        Returns:
            Dictionary containing branch personnel data
        """
        try:
            countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
            
            if country.lower() not in countries_data:
                return {
                    "success": False,
                    "error": f"Personnel data not available for country: {country}"
                }
            
            country_data = countries_data[country.lower()]
            branches = country_data.get('branches', {})
            
            if branch.lower() not in branches:
                return {
                    "success": False,
                    "error": f"Branch data not available for {country}: {branch}"
                }
            
            branch_data = branches[branch.lower()]
            
            return {
                "success": True,
                "country": country,
                "branch": branch,
                "data": branch_data
            }
            
        except Exception as e:
            logger.error(f"Error getting branch personnel: {e}")
            return {
                "success": False,
                "error": f"Failed to get branch personnel data: {str(e)}"
            }

    def get_available_countries(self) -> List[str]:
        """Get list of available countries in the dataset"""
        try:
            countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
            return list(countries_data.keys())
        except Exception as e:
            logger.error(f"Error getting available countries: {e}")
            return []

    def get_available_branches(self, country: str = None) -> Dict[str, Any]:
        """Get available branches for a country or all countries"""
        try:
            countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
            
            if country:
                if country.lower() not in countries_data:
                    return {
                        "success": False,
                        "error": f"Country not found: {country}"
                    }
                
                branches = countries_data[country.lower()].get('branches', {})
                return {
                    "success": True,
                    "country": country,
                    "branches": list(branches.keys())
                }
            else:
                # Return branches for all countries
                all_branches = {}
                for country_name, country_data in countries_data.items():
                    all_branches[country_name] = list(country_data.get('branches', {}).keys())
                
                return {
                    "success": True,
                    "branches": all_branches
                }
                
        except Exception as e:
            logger.error(f"Error getting available branches: {e}")
            return {
                "success": False,
                "error": f"Failed to get available branches: {str(e)}"
            }
