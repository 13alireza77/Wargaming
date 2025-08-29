import json
import requests
import logging
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retrain the LLM model with military personnel data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='llama3.2:3b',
            help='Base model to use for training (default: llama3.2:3b)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retrain even if model already exists'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            default='http://localhost:11434',
            help='Ollama base URL (default: http://localhost:11434)'
        )

    def handle(self, *args, **options):
        model_name = options['model']
        force = options['force']
        base_url = options['base_url']

        # Create the new model name
        new_model_name = f"{model_name}-personnel"

        self.stdout.write(
            self.style.SUCCESS(f'Starting personnel LLM retraining...')
        )

        try:
            # Check if model already exists
            if not force:
                existing_models = self._get_existing_models(base_url)
                if new_model_name in existing_models:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Model {new_model_name} already exists. Use --force to retrain.'
                        )
                    )
                    return

            # Load personnel data
            personnel_data = self._load_personnel_data()
            if not personnel_data:
                raise CommandError('Failed to load personnel data')

            # Create training data
            training_data = self._create_training_data(personnel_data)

            # Create the model
            success = self._create_model(base_url, model_name, new_model_name, training_data)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created personnel-trained model: {new_model_name}'
                    )
                )

                # Test the model
                self._test_model(base_url, new_model_name)
            else:
                raise CommandError('Failed to create personnel-trained model')

        except Exception as e:
            logger.error(f'Error during personnel LLM retraining: {e}')
            raise CommandError(f'Personnel LLM retraining failed: {str(e)}')

    def _get_existing_models(self, base_url: str) -> list:
        """Get list of existing models"""
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            response.raise_for_status()
            models_data = response.json()
            return [model['name'] for model in models_data.get('models', [])]
        except Exception as e:
            logger.warning(f"Could not get existing models: {e}")
            return []

    def _load_personnel_data(self) -> dict:
        """Load the personnel dataset"""
        data_path = Path(__file__).parent.parent.parent / "data" / "middle_east_personnel.json"
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load personnel data: {e}")
            return {}

    def _create_training_data(self, personnel_data: dict) -> str:
        """Create training data from personnel dataset"""
        training_content = """You are a military personnel and human resources expert specializing in Middle Eastern military capabilities analysis.

Your expertise includes:
- Military personnel analysis and assessment
- Troop effectiveness evaluation
- Victory probability calculations based on personnel factors
- Strategic military planning considering human resources
- Training and experience analysis
- Military branch capabilities assessment

Available military branches: Ground Forces, Air Force, Navy, Special Forces, Revolutionary Guards (Iran)

Key personnel factors for victory probability:
1. Total personnel numbers and active duty strength
2. Reserve forces availability and mobilization capability
3. Officer-to-enlisted ratio and leadership quality
4. Special forces capabilities and training
5. Branch-specific expertise and equipment proficiency
6. Combat experience and training levels
7. Morale and motivation factors
8. Logistics and support personnel ratios

When analyzing military personnel data, consider:
- Personnel numbers and their impact on combat effectiveness
- Quality of leadership and command structure
- Specialized unit capabilities
- Training and experience levels
- Reserve force mobilization potential
- Branch-specific advantages and limitations
- Strategic depth and sustainability

Provide detailed analysis including:
1. Personnel effectiveness assessment and capabilities
2. Strategic advantages and disadvantages based on troop numbers and quality
3. Impact on victory probability considering personnel factors
4. Training and experience considerations
5. Tactical and operational recommendations based on personnel analysis

Base your analysis on the provided personnel data and military considerations.

"""

        # Add personnel data to training content
        training_content += f"\nPersonnel Data:\n{json.dumps(personnel_data, indent=2)}"

        return training_content

    def _create_model(self, base_url: str, base_model: str, new_model: str, training_data: str) -> bool:
        """Create the new model with personnel training data"""
        try:
            # Create Modelfile content
            modelfile_content = f"""FROM {base_model}

# Set system prompt for personnel analysis
SYSTEM {json.dumps(training_data)}

# Set parameters for better personnel analysis
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER max_tokens 2500
"""

            # Create the model
            payload = {
                "name": new_model,
                "modelfile": modelfile_content
            }

            response = requests.post(f"{base_url}/api/create", json=payload, timeout=300)
            response.raise_for_status()

            return True

        except Exception as e:
            logger.error(f"Failed to create model: {e}")
            return False

    def _test_model(self, base_url: str, model_name: str):
        """Test the newly created model"""
        try:
            test_prompt = "What are the key factors that determine victory probability in military conflicts based on personnel analysis?"

            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": test_prompt}
                ],
                "stream": False
            }

            response = requests.post(f"{base_url}/api/chat", json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            analysis = result.get('message', {}).get('content', '')

            if analysis and len(analysis) > 100:
                self.stdout.write(
                    self.style.SUCCESS('Model test successful - personnel analysis working correctly')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('Model test completed but response seems short')
                )

        except Exception as e:
            logger.warning(f"Model test failed: {e}")
            self.stdout.write(
                self.style.WARNING(f'Model test failed: {str(e)}')
            )
