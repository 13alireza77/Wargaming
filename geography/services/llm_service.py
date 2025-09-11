import json
import requests
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for interacting with local LLM via Ollama for geographical analysis
    """

    def __init__(self, model_name: str = "qwen2.5:0.5b-geography", base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.geography_data = self._load_geography_data()
        self.model_name = model_name

    def _load_geography_data(self) -> Dict[str, Any]:
        """Load the Middle East geography dataset"""
        data_path = Path(__file__).parent.parent / "data" / "middle_east_geography.json"
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Geography data file not found at {data_path}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in geography data file at {data_path}")
            return {}

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM focused on geographical analysis"""
        return """You are a military geography expert specializing in Middle Eastern terrain analysis and strategic positioning. Your role is to provide detailed analysis of geographical factors affecting military operations and war outcomes.

Key analysis areas:
- Terrain advantages and disadvantages for military operations
- Weather impact on combat effectiveness
- Strategic positioning and defensive capabilities
- Logistical challenges and supply line vulnerabilities
- Key battle-winning geographical factors
- Victory probability based on terrain control

Provide clear, structured analysis with specific geographical insights and strategic recommendations. Focus on actionable intelligence for military planning and war outcome prediction."""

    def _create_user_prompt(self, query: str, region_data: Dict[str, Any] = None) -> str:
        """Create the user prompt with comprehensive geographical and military context"""
        if region_data:
            # Build comprehensive military context
            terrain = region_data.get('terrain', {})
            weather = region_data.get('weather', {})
            military = region_data.get('military_considerations', {})
            strategic = region_data.get('strategic_features', {})
            
            context = f"""REGION: {region_data.get('name', 'Unknown')}
Terrain: {terrain.get('primary', 'Unknown')} - {terrain.get('description', 'Unknown')}
Climate: {weather.get('climate', 'Unknown')}
Advantages: {', '.join(military.get('terrain_advantages', [])[:3])}
Challenges: {', '.join(military.get('terrain_disadvantages', [])[:3])}
Defensive: {', '.join(military.get('defensive_positions', [])[:2])}
Offensive: {', '.join(military.get('offensive_routes', [])[:2])}

QUERY: {query}

Analyze war conditions and predict outcome."""
        else:
            context = f"""
QUERY: {query}

Analyze the geographical factors for war conditions and strategic military decision-making. Consider terrain, weather, infrastructure, and strategic positioning for battle outcomes."""
        
        return context

    def analyze_geography(self, query: str, region: str = None) -> Dict[str, Any]:
        """
        Analyze geographical data for war conditions using LLM
        
        Args:
            query: The geographical analysis question focused on war conditions
            region: Specific region to focus on (optional)
            
        Returns:
            Dictionary containing war condition analysis results
        """
        try:
            # Get region data if specified
            region_data = None
            if region and region.lower() in self.geography_data.get('regions', {}):
                region_data = self.geography_data['regions'][region.lower()]

            # Create optimized prompts for war analysis
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, region_data)

            # Prepare the request to Ollama with optimized parameters for quality responses
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Balanced for quality responses
                    "top_p": 0.8,        # Good balance for quality
                    "max_tokens": 600,   # Optimized length for analysis
                    "num_predict": 600,  # Optimized length for analysis
                    "num_ctx": 1536,     # Sufficient context for analysis
                    "repeat_penalty": 1.1,
                    "stop": ["END_ANALYSIS", "---END---"]
                }
            }

            # Make request to Ollama with reasonable timeout
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60  # 60 seconds for quality responses
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get('message', {}).get('content', '').strip()
                
                # Return only essential information
                war_analysis = {
                    "success": True,
                    "analysis": analysis,
                    "region": region_data.get('name') if region_data else None,
                    "model_used": self.model_name
                }
                
                return war_analysis
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"LLM API error: {response.status_code} - {response.text}",
                    "analysis": None
                }

        except requests.exceptions.Timeout:
            logger.error("LLM request timed out")
            return {
                "success": False,
                "error": "LLM request timed out. Please try again or check model availability.",
                "analysis": None
            }
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama. Make sure Ollama is running.")
            return {
                "success": False,
                "error": "LLM service unavailable. Please start Ollama and ensure the model is available.",
                "analysis": None
            }
        except Exception as e:
            logger.error(f"Error in war condition analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}",
                "analysis": None
            }



    def get_available_regions(self) -> List[str]:
        """Get list of available regions"""
        return list(self.geography_data.get('regions', {}).keys())

    def get_region_data(self, region: str) -> Dict[str, Any]:
        """Get data for a specific region"""
        return self.geography_data.get('regions', {}).get(region.lower(), {})

    def analyze_war_conditions(self, attacker_region: str, defender_region: str, scenario: str = None) -> Dict[str, Any]:
        """
        Analyze war conditions between two regions for strategic decision making
        
        Args:
            attacker_region: Region launching the attack
            defender_region: Region being defended
            scenario: Optional specific war scenario description
            
        Returns:
            Dictionary containing war condition analysis and outcome prediction
        """
        try:
            # Get data for both regions
            attacker_data = self.geography_data.get('regions', {}).get(attacker_region.lower())
            defender_data = self.geography_data.get('regions', {}).get(defender_region.lower())
            
            if not attacker_data or not defender_data:
                return {
                    "success": False,
                    "error": f"Region data not found for {attacker_region} or {defender_region}",
                    "analysis_type": "war_conditions"
                }
            
            # Create specialized war analysis prompt
            war_prompt = f"""
WAR SCENARIO ANALYSIS:

ATTACKER: {attacker_data.get('name', attacker_region)}
- Terrain: {attacker_data.get('terrain', {}).get('description', 'Unknown')}
- Advantages: {', '.join(attacker_data.get('military_considerations', {}).get('terrain_advantages', []))}
- Challenges: {', '.join(attacker_data.get('military_considerations', {}).get('terrain_disadvantages', []))}
- Offensive Routes: {', '.join(attacker_data.get('military_considerations', {}).get('offensive_routes', []))}

DEFENDER: {defender_data.get('name', defender_region)}
- Terrain: {defender_data.get('terrain', {}).get('description', 'Unknown')}
- Advantages: {', '.join(defender_data.get('military_considerations', {}).get('terrain_advantages', []))}
- Challenges: {', '.join(defender_data.get('military_considerations', {}).get('terrain_disadvantages', []))}
- Defensive Positions: {', '.join(defender_data.get('military_considerations', {}).get('defensive_positions', []))}

SCENARIO: {scenario or 'General war conditions analysis'}

Analyze the war conditions and predict the likely outcome. Consider:
1. Terrain advantages for each side
2. Strategic positioning and defensive capabilities
3. Logistical challenges and supply lines
4. Weather impact on operations
5. Key battle-winning factors
6. Predicted war outcome and reasoning

Provide a concise military assessment for strategic decision-making."""
            
            # Use the main analysis method with the war-specific prompt
            result = self.analyze_geography(war_prompt)
            
            if result.get('success'):
                result['attacker'] = attacker_region
                result['defender'] = defender_region
            
            return result
            
        except Exception as e:
            logger.error(f"Error in war conditions analysis: {str(e)}")
            return {
                "success": False,
                "error": f"War analysis failed: {str(e)}",
                "analysis": None
            }

    def check_model_availability(self) -> bool:
        """Check if the specified model is available in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name') == self.model_name for model in models)
            return False
        except:
            return False
