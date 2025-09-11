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
        return """Military personnel expert. Analyze troop capabilities and provide strategic insights. Be brief and focused."""

    def _create_user_prompt(self, query: str, personnel_data: Dict[str, Any] = None, country: str = None) -> str:
        """Create the user prompt with personnel context"""
        if personnel_data and country:
            context = f"{country}: {personnel_data.get('total_personnel', 'Unknown')} total, {personnel_data.get('active_duty', 'Unknown')} active. {query}"
        else:
            context = query
        
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
            # Check if this is a simple query that can be answered quickly
            if self._is_simple_query(query):
                return self._get_quick_response(query, country, branch)
            
            # Get personnel data if specified
            personnel_data = None
            if country and country.lower() in self.personnel_data.get('personnel_data', {}).get('countries', {}):
                personnel_data = self.personnel_data['personnel_data']['countries'][country.lower()]
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, personnel_data, country)
            
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
            
            # Make the request with reduced timeout
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

    def _is_simple_query(self, query: str) -> bool:
        """Check if this is a simple query that can be answered quickly"""
        simple_keywords = ['personnel', 'troops', 'military', 'forces', 'victory probability', 'compare']
        return any(keyword in query.lower() for keyword in simple_keywords)

    def _get_quick_response(self, query: str, country: str = None, branch: str = None) -> Dict[str, Any]:
        """Provide a quick response for simple queries"""
        query_lower = query.lower()
        
        if country and country.lower() in self.personnel_data.get('personnel_data', {}).get('countries', {}):
            country_data = self.personnel_data['personnel_data']['countries'][country.lower()]
            
            # Extract key information
            total = country_data.get('total_personnel', 'Unknown')
            active = country_data.get('active_duty', 'Unknown')
            reserves = country_data.get('reserves', 'Unknown')
            branches = list(country_data.get('branches', {}).keys())
            
            analysis = f"Quick Personnel Analysis:\n\n{country}:\n"
            analysis += f"- Total Personnel: {total}\n"
            analysis += f"- Active Duty: {active}\n"
            analysis += f"- Reserves: {reserves}\n"
            analysis += f"- Military Branches: {', '.join(branches[:3])}\n"
            analysis += "\nNote: This is a simplified analysis. For detailed assessment, use LLM analysis."
            
            return {
                "success": True,
                "analysis": analysis,
                "country": country,
                "query": query
            }
        
        # Default quick response
        return {
            "success": True,
            "analysis": "Quick analysis: Based on available personnel data, this requires detailed LLM analysis. For faster response, try a more specific query.",
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
            
            # Create a focused comparison prompt
            system_prompt = self._create_system_prompt()
            user_prompt = f"Compare {country1} vs {country2} personnel for {scenario} conflict. Focus on key factors and victory probability."
            
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
                    "max_tokens": 400,
                    "num_predict": 400,
                    "num_ctx": 1024
                }
            }
            
            # Make the request with reduced timeout
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=25)
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
            # Fallback to quick analysis
            return self._quick_victory_analysis(country1, country2, scenario)
        except Exception as e:
            logger.error(f"Error calculating victory probability: {e}")
            # Fallback to quick analysis
            return self._quick_victory_analysis(country1, country2, scenario)

    def _quick_victory_analysis(self, country1: str, country2: str, scenario: str) -> Dict[str, Any]:
        """Provide a quick victory analysis based on personnel data"""
        countries_data = self.personnel_data.get('personnel_data', {}).get('countries', {})
        
        country1_data = countries_data[country1.lower()]
        country2_data = countries_data[country2.lower()]
        
        # Simple analysis based on personnel numbers
        total1 = country1_data.get('total_personnel', 0)
        total2 = country2_data.get('total_personnel', 0)
        
        if isinstance(total1, str):
            total1 = 0
        if isinstance(total2, str):
            total2 = 0
        
        if total1 > total2:
            winner = country1
            confidence = "High"
            reason = f"{country1} has more personnel ({total1:,} vs {total2:,})"
        elif total2 > total1:
            winner = country2
            confidence = "High"
            reason = f"{country2} has more personnel ({total2:,} vs {total1:,})"
        else:
            winner = "Tie"
            confidence = "Medium"
            reason = f"Both countries have similar personnel numbers ({total1:,} each)"
        
        analysis = f"Quick Victory Analysis:\n\n{country1} vs {country2}:\n- Winner: {winner}\n- Confidence: {confidence}\n- Reason: {reason}\n\nNote: This is a simplified analysis. For detailed assessment, use LLM analysis."
        
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
