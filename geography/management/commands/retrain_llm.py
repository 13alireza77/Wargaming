from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import json
import requests
import logging
from pathlib import Path
from geography.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retrain the LLM model with updated geographical data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='llama3.2:3b',
            help='Ollama model name to use (default: llama3.2:3b)'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='http://localhost:11434',
            help='Ollama base URL (default: http://localhost:11434)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retraining even if model is already available'
        )

    def handle(self, *args, **options):
        model_name = options['model']
        base_url = options['base_url']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'Starting LLM retraining process for model: {model_name}')
        )

        # Check if Ollama is running
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                raise CommandError(f"Ollama is not responding at {base_url}")
        except requests.exceptions.ConnectionError:
            raise CommandError(f"Could not connect to Ollama at {base_url}. Please ensure Ollama is running.")

        # Check if model already exists
        llm_service = LLMService(model_name=model_name, base_url=base_url)
        if llm_service.check_model_availability() and not force:
            self.stdout.write(
                self.style.WARNING(f'Model {model_name} is already available. Use --force to retrain.')
            )
            return

        # Load geographical data for training context
        data_path = Path(__file__).parent.parent.parent / "data" / "middle_east_geography.json"
        if not data_path.exists():
            raise CommandError(f"Geography data file not found at {data_path}")

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                geography_data = json.load(f)
        except json.JSONDecodeError:
            raise CommandError(f"Invalid JSON in geography data file at {data_path}")

        self.stdout.write('Loading geographical data...')

        # Create training prompt with geographical data
        training_prompt = self._create_training_prompt(geography_data)

        # Pull the model if it doesn't exist
        if not llm_service.check_model_availability():
            self.stdout.write(f'Pulling model {model_name}...')
            try:
                pull_response = requests.post(
                    f"{base_url}/api/pull",
                    json={"name": model_name},
                    timeout=300  # 5 minutes timeout for model download
                )
                if pull_response.status_code != 200:
                    raise CommandError(f"Failed to pull model {model_name}")
                self.stdout.write(self.style.SUCCESS(f'Model {model_name} pulled successfully'))
            except Exception as e:
                raise CommandError(f"Error pulling model: {str(e)}")

        # Create a custom model with geographical training data
        custom_model_name = f"{model_name}-geography"
        self.stdout.write(f'Creating custom model: {custom_model_name}...')

        try:
            # Create a Modelfile for fine-tuning with geographical data
            modelfile_content = self._create_modelfile(model_name, training_prompt, geography_data)

            # Save the Modelfile to a temporary file
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(mode='w', suffix='.modelfile', delete=False) as f:
                f.write(modelfile_content)
                modelfile_path = f.name

            try:
                # Create the custom model using Ollama CLI
                import subprocess
                result = subprocess.run(
                    ['ollama', 'create', custom_model_name, '-f', modelfile_path],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode == 0:
                    self.stdout.write(self.style.SUCCESS(f'Custom model {custom_model_name} created successfully'))

                    # Update the LLM service to use the custom model
                    llm_service.model_name = custom_model_name

                    # Test the custom model with geographical data
                    self.stdout.write('Testing custom model with geographical data...')
                    test_result = llm_service.analyze_geography(
                        "What are the key terrain features of Syria and how do they affect military operations?"
                    )

                    if test_result['success']:
                        self.stdout.write(
                            self.style.SUCCESS('Model training and testing completed successfully!')
                        )
                        self.stdout.write(f"Custom model: {custom_model_name}")
                        self.stdout.write(f"Test analysis: {test_result['analysis'][:200]}...")
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Model testing failed: {test_result.get("error", "Unknown error")}')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Could not create custom model: {result.stderr}. Using base model for testing.')
                    )
                    # Fallback to testing the base model
                    test_result = llm_service.analyze_geography(
                        "What are the key terrain features of Syria and how do they affect military operations?"
                    )

                    if test_result['success']:
                        self.stdout.write(
                            self.style.SUCCESS('Base model testing completed successfully!')
                        )
                        self.stdout.write(f"Test analysis: {test_result['analysis'][:200]}...")
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Model testing failed: {test_result.get("error", "Unknown error")}')
                        )
            finally:
                # Clean up temporary file
                if os.path.exists(modelfile_path):
                    os.unlink(modelfile_path)

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error creating custom model: {str(e)}. Using base model.')
            )
            # Fallback to testing the base model
            test_result = llm_service.analyze_geography(
                "What are the key terrain features of Syria and how do they affect military operations?"
            )

            if test_result['success']:
                self.stdout.write(
                    self.style.SUCCESS('Base model testing completed successfully!')
                )
                self.stdout.write(f"Test analysis: {test_result['analysis'][:200]}...")
            else:
                self.stdout.write(
                    self.style.ERROR(f'Model testing failed: {test_result.get("error", "Unknown error")}')
                )

    def _create_training_prompt(self, geography_data):
        """Create a concise training prompt with geographical data"""
        regions = geography_data.get('regions', {})
        weather_patterns = geography_data.get('weather_patterns', {})
        strategic_chokepoints = geography_data.get('strategic_chokepoints', {})

        prompt = "You are a military geography expert specializing in Middle Eastern terrain analysis. Analyze geographical data and provide strategic insights. Be brief and focused.\n\n"
        prompt += "Available regions: "

        region_names = []
        for region_key, region_data in regions.items():
            name = region_data.get('name', region_key)
            region_names.append(name)
        
        prompt += ", ".join(region_names)
        prompt += "\n\nFocus on: terrain impact, weather effects, strategic advantages, military considerations."

        return prompt

    def _create_modelfile(self, base_model, training_prompt, geography_data):
        """Create a Modelfile for fine-tuning with geographical data"""

        # Create a concise system prompt with geographical data
        enhanced_prompt = self._create_enhanced_system_prompt(training_prompt, geography_data)

        modelfile = f"""FROM {base_model}

# Optimized system prompt for fast responses
SYSTEM \"\"\"
{enhanced_prompt}
\"\"\"

# Parameters optimized for speed and efficiency
PARAMETER temperature 0.3
PARAMETER top_p 0.7
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 1024
PARAMETER num_predict 500
"""
        return modelfile

    def _create_enhanced_system_prompt(self, base_prompt, geography_data):
        """Create a concise enhanced system prompt with geographical data"""
        
        # Extract key geographical information in a compact format
        regions_summary = []
        for region_key, region_data in geography_data.get('regions', {}).items():
            region_name = region_data.get('name', region_key.title())
            terrain = region_data.get('terrain', {})
            weather = region_data.get('weather', {})
            
            terrain_desc = terrain.get('description', 'Unknown')
            climate = weather.get('climate', 'Unknown')
            
            regions_summary.append(f"{region_name}: {terrain_desc} ({climate})")
        
        enhanced_prompt = f"""{base_prompt}

GEOGRAPHY DATA: {', '.join(regions_summary[:5])}

Provide brief, focused analysis of terrain and strategic considerations."""
        
        return enhanced_prompt
