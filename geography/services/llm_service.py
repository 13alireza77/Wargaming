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

    def __init__(self, model_name: str = "llama3.2:3b-geography", base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.geography_data = self._load_geography_data()
        self.model_name = model_name
        self.fallback_model = "llama3.2:3b"  # Faster base model as fallback

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
        """Create the system prompt for the LLM focused on war conditions and strategic analysis"""
        return """Military geography expert. Analyze war conditions and predict outcomes. Focus on:
- Terrain advantages for attack/defense
- Strategic positions and chokepoints  
- Logistics challenges and supply lines
- Weather impact on operations
- War outcome prediction

Provide concise military intelligence for decision-making."""

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

            # Prepare the request to Ollama with optimized parameters for speed
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Very low temperature for focused responses
                    "top_p": 0.5,        # Reduced for faster generation
                    "max_tokens": 300,   # Further reduced for faster response
                    "num_predict": 300,  # Further reduced for faster response
                    "num_ctx": 1536,     # Reduced context for speed
                    "repeat_penalty": 1.05,
                    "stop": ["\n\n", "---", "##", "Analysis:", "Conclusion:"]  # More stop tokens
                }
            }

            # Make request to Ollama with strict timeout for 10-second requirement
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=3  # 3 seconds to ensure total response under 10 seconds
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result.get('message', {}).get('content', '').strip()
                
                # Add war condition metadata
                war_analysis = {
                    "success": True,
                    "analysis": analysis,
                    "region": region_data.get('name') if region_data else None,
                    "query": query,
                    "analysis_type": "war_conditions",
                    "model_used": self.model_name,
                    "response_time": "< 10 seconds"
                }
                
                # Add strategic summary if region data available
                if region_data:
                    war_analysis["strategic_summary"] = {
                        "terrain_difficulty": region_data.get('terrain', {}).get('difficulty', 'unknown'),
                        "key_advantages": region_data.get('military_considerations', {}).get('terrain_advantages', [])[:3],
                        "major_challenges": region_data.get('military_considerations', {}).get('terrain_disadvantages', [])[:3]
                    }
                
                return war_analysis
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "query": query,
                    "analysis_type": "war_conditions"
                }

        except requests.exceptions.Timeout:
            logger.warning("Primary model timed out, trying fallback model")
            return self._try_fallback_model(query, region_data)
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama. Make sure Ollama is running.")
            return {
                "success": False,
                "error": "Ollama not running. Please start Ollama and ensure the model is available.",
                "query": query,
                "analysis_type": "war_conditions"
            }
        except Exception as e:
            logger.error(f"Error in war condition analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis error: {str(e)}",
                "query": query,
                "analysis_type": "war_conditions"
            }

    def _try_fallback_model(self, query: str, region_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Try the fallback model with even more aggressive parameters"""
        try:
            # Create simplified prompts for fallback
            system_prompt = "Military expert. Analyze war conditions briefly."
            
            if region_data:
                user_prompt = f"Region: {region_data.get('name')}. Terrain: {region_data.get('terrain', {}).get('primary', 'Unknown')}. Query: {query}. Analyze war conditions."
            else:
                user_prompt = f"Query: {query}. Analyze war conditions briefly."
            
            # Very aggressive parameters for speed
            payload = {
                "model": self.fallback_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.4,
                    "max_tokens": 200,
                    "num_predict": 200,
                    "num_ctx": 1024,
                    "stop": ["\n\n", "---", "##"]
                }
            }
            
            # Very short timeout for fallback
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=2
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('message', {}).get('content', '').strip()
                
                return {
                    "success": True,
                    "analysis": f"[Fallback Model] {analysis}",
                    "region": region_data.get('name') if region_data else None,
                    "query": query,
                    "analysis_type": "war_conditions",
                    "model_used": self.fallback_model,
                    "response_time": "< 10 seconds (fallback)"
                }
            else:
                return {
                    "success": False,
                    "error": f"Fallback model failed: {response.status_code}",
                    "query": query,
                    "analysis_type": "war_conditions"
                }
                
        except Exception as e:
            logger.error(f"Fallback model also failed: {str(e)}")
            # Return a mock response for testing when models are too slow
            return self._get_mock_response(query, region_data)

    def _get_mock_response(self, query: str, region_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Provide a mock response when LLM models are unavailable or too slow"""
        if region_data:
            terrain = region_data.get('terrain', {})
            military = region_data.get('military_considerations', {})
            
            analysis = f"""WAR CONDITIONS ANALYSIS - {region_data.get('name', 'Region')}:

TERRAIN ASSESSMENT:
- Primary terrain: {terrain.get('primary', 'Unknown')}
- Difficulty level: {terrain.get('difficulty', 'Unknown')}
- Key advantages: {', '.join(military.get('terrain_advantages', [])[:3])}
- Major challenges: {', '.join(military.get('terrain_disadvantages', [])[:3])}

STRATEGIC EVALUATION:
- Defensive positions: {', '.join(military.get('defensive_positions', [])[:2])}
- Offensive routes: {', '.join(military.get('offensive_routes', [])[:2])}

WAR OUTCOME PREDICTION:
Based on terrain analysis, this region shows {'favorable' if terrain.get('difficulty') == 'moderate' else 'challenging'} conditions for military operations. The geographical factors suggest {'defensive' if 'mountainous' in str(military.get('terrain_advantages', [])) else 'offensive'} advantages.

NOTE: This is a mock analysis. For real-time LLM analysis, ensure Ollama models are properly loaded and responding within timeout limits."""
        else:
            analysis = f"""WAR CONDITIONS ANALYSIS:

Based on the query: "{query}"

This analysis requires specific geographical data to provide accurate war condition assessment. The system is designed to analyze terrain advantages, strategic positioning, logistical challenges, and weather impact on military operations.

For detailed analysis, please specify a region or ensure the LLM models are properly configured and responding within the required time limits.

NOTE: This is a mock response. The actual LLM analysis provides more detailed strategic intelligence."""
        
        return {
            "success": True,
            "analysis": analysis,
            "region": region_data.get('name') if region_data else None,
            "query": query,
            "analysis_type": "war_conditions",
            "model_used": "mock_response",
            "response_time": "< 1 second (mock)",
            "note": "Mock response - LLM models unavailable or too slow"
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
                result['war_scenario'] = {
                    'attacker': attacker_region,
                    'defender': defender_region,
                    'scenario': scenario
                }
                result['analysis_type'] = 'war_conditions_comparison'
            
            return result
            
        except Exception as e:
            logger.error(f"Error in war conditions analysis: {str(e)}")
            return {
                "success": False,
                "error": f"War analysis error: {str(e)}",
                "analysis_type": "war_conditions_comparison"
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
