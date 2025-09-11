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
    
    def __init__(self, model_name: str = "qwen2.5:0.5b-personnel", base_url: str = "http://localhost:11434"):
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
        return """You are a military personnel analyst specializing in Middle Eastern armed forces. Your role is to provide detailed analysis of military personnel capabilities, troop effectiveness, and strategic assessments.

Key analysis areas:
- Personnel strength and composition
- Training and experience levels
- Leadership quality and command structure
- Special forces capabilities
- Reserve force mobilization potential
- Victory probability based on human factors

Provide clear, structured analysis with specific insights and recommendations. Focus on actionable intelligence for military planning."""

    def _create_user_prompt(self, query: str, personnel_data: Dict[str, Any] = None, country: str = None) -> str:
        """Create the user prompt with personnel context"""
        if personnel_data and country:
            context = f"{country}: {personnel_data.get('total_personnel', 'Unknown')} total, {personnel_data.get('active_duty', 'Unknown')} active. {query}"
        else:
            context = query
        
        return context

    def _build_analysis_context(self, query: str, personnel_data: Dict[str, Any] = None, country: str = None, branch: str = None) -> Dict[str, Any]:
        """Build comprehensive context for LLM analysis"""
        context = {
            "query": query,
            "country": country,
            "branch": branch,
            "personnel_data": personnel_data
        }
        
        if personnel_data:
            context["summary"] = {
                "total_personnel": personnel_data.get('total_personnel'),
                "active_duty": personnel_data.get('active_duty'),
                "reserves": personnel_data.get('reserves'),
                "branches": list(personnel_data.get('branches', {}).keys())
            }
            
            if branch and branch.lower() in personnel_data.get('branches', {}):
                branch_data = personnel_data['branches'][branch.lower()]
                context["branch_summary"] = {
                    "personnel": branch_data.get('personnel'),
                    "ranks": branch_data.get('ranks', {}),
                    "special_units": branch_data.get('special_units', {})
                }
        
        return context

    def _create_enhanced_user_prompt(self, query: str, context_data: Dict[str, Any], country: str = None, branch: str = None) -> str:
        """Create enhanced user prompt with comprehensive context"""
        prompt_parts = []
        
        # Add query
        prompt_parts.append(f"Query: {query}")
        
        # Add country context
        if country and context_data.get("summary"):
            summary = context_data["summary"]
            prompt_parts.append(f"\nCountry: {country}")
            prompt_parts.append(f"- Total Personnel: {summary.get('total_personnel', 'Unknown')}")
            prompt_parts.append(f"- Active Duty: {summary.get('active_duty', 'Unknown')}")
            prompt_parts.append(f"- Reserves: {summary.get('reserves', 'Unknown')}")
            prompt_parts.append(f"- Branches: {', '.join(summary.get('branches', []))}")
        
        # Add branch context
        if branch and context_data.get("branch_summary"):
            branch_summary = context_data["branch_summary"]
            prompt_parts.append(f"\nBranch: {branch}")
            prompt_parts.append(f"- Personnel: {branch_summary.get('personnel', 'Unknown')}")
            if branch_summary.get('special_units'):
                units = list(branch_summary['special_units'].keys())
                prompt_parts.append(f"- Special Units: {', '.join(units[:3])}")
        
        # Add analysis focus
        prompt_parts.append(f"\nProvide a focused military analysis considering war conditions and strategic factors.")
        
        return "\n".join(prompt_parts)

    def _create_victory_system_prompt(self) -> str:
        """Create specialized system prompt for victory probability analysis"""
        return """You are a military strategist specializing in personnel-based victory probability analysis. Your expertise includes:

- Comparative analysis of military personnel strengths
- Assessment of troop quality and training levels
- Evaluation of leadership and command effectiveness
- Analysis of special forces capabilities
- Reserve force mobilization potential
- Strategic advantages based on human resources

Provide detailed victory probability assessments with specific reasoning, key factors, and strategic recommendations. Structure your analysis clearly with numbered points and clear conclusions."""

    def _build_victory_comparison_context(self, country1: str, country2: str, country1_data: Dict[str, Any], country2_data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        """Build comprehensive context for victory comparison analysis"""
        return {
            "country1": {
                "name": country1,
                "total_personnel": country1_data.get('total_personnel'),
                "active_duty": country1_data.get('active_duty'),
                "reserves": country1_data.get('reserves'),
                "branches": country1_data.get('branches', {}),
                "branch_summary": self._summarize_branches(country1_data.get('branches', {}))
            },
            "country2": {
                "name": country2,
                "total_personnel": country2_data.get('total_personnel'),
                "active_duty": country2_data.get('active_duty'),
                "reserves": country2_data.get('reserves'),
                "branches": country2_data.get('branches', {}),
                "branch_summary": self._summarize_branches(country2_data.get('branches', {}))
            },
            "scenario": scenario
        }

    def _summarize_branches(self, branches: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize branch information for comparison"""
        summary = {}
        for branch_name, branch_data in branches.items():
            summary[branch_name] = {
                "personnel": branch_data.get('personnel'),
                "special_units": list(branch_data.get('special_units', {}).keys())[:3],
                "officer_ranks": len(branch_data.get('ranks', {}).get('officers', {})),
                "enlisted_ranks": len(branch_data.get('ranks', {}).get('enlisted', {}))
            }
        return summary

    def _create_victory_user_prompt(self, comparison_context: Dict[str, Any], scenario: str) -> str:
        """Create comprehensive user prompt for victory analysis"""
        country1 = comparison_context["country1"]
        country2 = comparison_context["country2"]
        
        prompt = f"""VICTORY PROBABILITY ANALYSIS

Scenario: {scenario} conflict

COUNTRY 1: {country1['name']}
- Total Personnel: {country1['total_personnel']:,}
- Active Duty: {country1['active_duty']:,}
- Reserves: {country1['reserves']:,}
- Military Branches: {len(country1['branches'])}

COUNTRY 2: {country2['name']}
- Total Personnel: {country2['total_personnel']:,}
- Active Duty: {country2['active_duty']:,}
- Reserves: {country2['reserves']:,}
- Military Branches: {len(country2['branches'])}

ANALYSIS REQUIRED:
1. Personnel strength comparison
2. Training and experience assessment
3. Leadership quality evaluation
4. Special forces capabilities
5. Reserve mobilization potential
6. Victory probability percentage
7. Key strategic factors
8. Recommendations

Provide detailed analysis with specific insights and clear conclusions."""
        
        return prompt

    def analyze_personnel(self, query: str, country: str = None, branch: str = None) -> Dict[str, Any]:
        """
        Analyze personnel data based on the query using LLM model
        
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
            
            # Create comprehensive context for the LLM
            context_data = self._build_analysis_context(query, personnel_data, country, branch)
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_enhanced_user_prompt(query, context_data, country, branch)
            
            # Prepare the request to Ollama with optimized parameters for quality responses
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "max_tokens": 600,
                    "num_predict": 600,
                    "num_ctx": 1536,
                    "repeat_penalty": 1.1,
                    "stop": ["END_ANALYSIS", "---END---"]
                }
            }
            
            # Make the request with reasonable timeout
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            analysis = result.get('message', {}).get('content', 'No analysis available')
            
            return {
                "success": True,
                "analysis": analysis,
                "country": country,
                "model_used": self.model_name
            }
            
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return {
                "success": False,
                "error": "LLM request timed out. Please try again or check model availability.",
                "analysis": None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return {
                "success": False,
                "error": f"LLM service unavailable: {str(e)}",
                "analysis": None
            }
        except Exception as e:
            logger.error(f"Error analyzing personnel: {e}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "analysis": None
            }


    def calculate_victory_probability(self, country1: str, country2: str, scenario: str = "conventional") -> Dict[str, Any]:
        """
        Calculate victory probability based on personnel comparison using LLM model
        
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
            
            # Create comprehensive comparison context
            comparison_context = self._build_victory_comparison_context(country1, country2, country1_data, country2_data, scenario)
            
            # Create enhanced prompts for victory analysis
            system_prompt = self._create_victory_system_prompt()
            user_prompt = self._create_victory_user_prompt(comparison_context, scenario)
            
            # Prepare the request to Ollama with optimized parameters for quality responses
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "max_tokens": 600,
                    "num_predict": 600,
                    "num_ctx": 1536,
                    "repeat_penalty": 1.1,
                    "stop": ["END_ANALYSIS", "---END---"]
                }
            }
            
            # Make the request with reasonable timeout
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            analysis = result.get('message', {}).get('content', 'No analysis available')
            
            return {
                "success": True,
                "analysis": analysis,
                "country1": country1,
                "country2": country2,
                "model_used": self.model_name
            }
            
        except requests.exceptions.Timeout:
            logger.error("Victory probability request timed out")
            return {
                "success": False,
                "error": "LLM request timed out. Please try again or check model availability.",
                "analysis": None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return {
                "success": False,
                "error": f"LLM service unavailable: {str(e)}",
                "analysis": None
            }
        except Exception as e:
            logger.error(f"Error calculating victory probability: {e}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "analysis": None
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
