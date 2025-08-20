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
    
    def __init__(self, model_name: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.geography_data = self._load_geography_data()
        
        # Try to use the geography-trained model if available, otherwise use the base model
        geography_model = f"{model_name}-geography"
        if self._check_model_exists(geography_model):
            self.model_name = geography_model
        else:
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
        """Create the system prompt for the LLM"""
        return """You are a military geography expert specializing in Middle Eastern terrain analysis. 
Your task is to analyze geographical data and provide strategic military insights.

Available regions: Syria, Iraq, Iran, Israel, Lebanon, Jordan, Saudi Arabia, Yemen, Egypt, Turkey

For each analysis, provide:
1. Terrain assessment and its impact on military operations
2. Weather considerations and seasonal effects
3. Strategic advantages and disadvantages
4. Logistics challenges and recommendations
5. Defensive and offensive considerations

Base your analysis on the provided geographical data and military considerations."""

    def _create_user_prompt(self, query: str, region_data: Dict[str, Any] = None) -> str:
        """Create the user prompt with geographical context"""
        if region_data:
            context = f"""
Region: {region_data.get('name', 'Unknown')}
Terrain: {region_data.get('terrain', {}).get('description', 'Unknown')}
Climate: {region_data.get('weather', {}).get('climate', 'Unknown')}
Strategic Features: {', '.join(region_data.get('strategic_features', {}).get('urban_centers', []))}
Military Considerations: {', '.join(region_data.get('military_considerations', {}).get('terrain_advantages', []))}

Query: {query}
"""
        else:
            context = f"""
Available geographical data for Middle East regions including terrain, weather, strategic features, and military considerations.

Query: {query}
"""
        
        return context

    def analyze_geography(self, query: str, region: str = None) -> Dict[str, Any]:
        """
        Analyze geographical data based on the query
        
        Args:
            query: The geographical analysis question
            region: Specific region to focus on (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Get region data if specified
            region_data = None
            if region and region.lower() in self.geography_data.get('regions', {}):
                region_data = self.geography_data['regions'][region.lower()]
            
            # Create prompts
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(query, region_data)
            
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
                    "region": region_data.get('name') if region_data else None,
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
            logger.error(f"Error in geographical analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis error: {str(e)}",
                "query": query
            }
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions"""
        return list(self.geography_data.get('regions', {}).keys())
    
    def get_region_data(self, region: str) -> Dict[str, Any]:
        """Get data for a specific region"""
        return self.geography_data.get('regions', {}).get(region.lower(), {})
    
    def _check_model_exists(self, model_name: str) -> bool:
        """Check if a specific model exists in Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(model.get('name') == model_name for model in models)
            return False
        except:
            return False

    def check_model_availability(self) -> bool:
        """Check if the specified model is available in Ollama"""
        return self._check_model_exists(self.model_name)
