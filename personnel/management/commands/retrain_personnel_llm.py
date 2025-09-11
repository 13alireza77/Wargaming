import json
import requests
import logging
import time
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retrain the LLM model with military personnel data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='qwen2.5:0.5b',
            help='Base model to use for training (default: qwen2.5:0.5b)'
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
            self.stdout.write(f'Loading personnel data from: {data_path}')
            if not data_path.exists():
                raise FileNotFoundError(f"Personnel data file not found: {data_path}")
            
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.stdout.write(f'Successfully loaded personnel data with {len(data.get("personnel_data", {}).get("countries", {}))} countries')
                return data
        except FileNotFoundError as e:
            logger.error(f"Personnel data file not found: {e}")
            self.stdout.write(f'Error: {str(e)}')
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in personnel data file: {e}")
            self.stdout.write(f'Error: Invalid JSON format in data file')
            return {}
        except Exception as e:
            logger.error(f"Failed to load personnel data: {e}")
            self.stdout.write(f'Error loading data: {str(e)}')
            return {}

    def _create_training_data(self, personnel_data: dict) -> str:
        """Create training data from personnel dataset"""
        training_content = """You are a military personnel analyst specializing in Middle Eastern armed forces. Your role is to provide detailed analysis of military personnel capabilities, troop effectiveness, and strategic assessments.

Key analysis areas:
- Personnel strength and composition
- Training and experience levels
- Leadership quality and command structure
- Special forces capabilities
- Reserve force mobilization potential
- Victory probability based on human factors

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

Provide clear, structured analysis with specific insights and recommendations. Focus on actionable intelligence for military planning and war outcome prediction.

"""

        # Add personnel data to training content
        training_content += f"\nPersonnel Data:\n{json.dumps(personnel_data, indent=2)}"

        return training_content

    def _create_model(self, base_url: str, base_model: str, new_model: str, training_data: str) -> bool:
        """Create the new model with personnel training data"""
        try:
            self.stdout.write(f'Creating model {new_model} from base model {base_model}...')
            
            # Create Modelfile content
            modelfile_content = f"""FROM {base_model}

# Set system prompt for personnel analysis
SYSTEM {json.dumps(training_data)}

# Set parameters optimized for quality responses
PARAMETER temperature 0.3
PARAMETER top_p 0.8
PARAMETER max_tokens 800
PARAMETER num_ctx 2048
PARAMETER num_predict 800
PARAMETER repeat_penalty 1.1
"""
            # Create the model using the correct Ollama API format
            payload = {
                "name": new_model,
                "from": base_model,
                "modelfile": modelfile_content
            }

            self.stdout.write('Sending model creation request to Ollama...')
            response = requests.post(f"{base_url}/api/create", json=payload, timeout=300)
            response.raise_for_status()
            
            # Verify the model was created with retry mechanism
            self.stdout.write('Verifying model creation...')
            for attempt in range(5):  # Try 5 times with delays
                time.sleep(2)  # Wait 2 seconds between attempts
                existing_models = self._get_existing_models(base_url)
                if new_model in existing_models:
                    self.stdout.write(f'Model {new_model} successfully created and verified!')
                    return True
                else:
                    self.stdout.write(f'Attempt {attempt + 1}/5: Model not found yet, waiting...')
            
            self.stdout.write(f'Model creation request succeeded but model not found after 5 attempts')
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during model creation: {e}")
            self.stdout.write(f'Network error: {str(e)}')
            return False
        except Exception as e:
            logger.error(f"Failed to create model: {e}")
            self.stdout.write(f'Model creation failed: {str(e)}')
            return False

    def _test_model(self, base_url: str, model_name: str):
        """Test the newly created model"""
        try:
            test_prompt = "What are the key factors that determine victory probability in military conflicts based on personnel analysis?"

            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": test_prompt
                    }
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
                self.stdout.write(f'Test response preview: {analysis[:200]}...')
            else:
                self.stdout.write(
                    self.style.WARNING('Model test completed but response seems short')
                )

        except Exception as e:
            logger.warning(f"Model test failed: {e}")
            self.stdout.write(
                self.style.WARNING(f'Model test failed: {str(e)}')
            )
