from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import json
import requests
import logging
from pathlib import Path
from weapons.services.weapons_service import WeaponsService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Retrain the LLM model with updated weapons data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='qwen2.5:0.5b',
            help='Ollama model name to use (default: qwen2.5:0.5b)'
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
            self.style.SUCCESS(f'Starting weapons LLM retraining process for model: {model_name}')
        )

        # Check if Ollama is running
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            if response.status_code != 200:
                raise CommandError(f"Ollama is not responding at {base_url}")
        except requests.exceptions.ConnectionError:
            raise CommandError(f"Could not connect to Ollama at {base_url}. Please ensure Ollama is running.")

        # Check if model already exists
        weapons_service = WeaponsService(model_name=model_name, base_url=base_url)
        if weapons_service.check_model_availability() and not force:
            self.stdout.write(
                self.style.WARNING(f'Model {model_name} is already available. Use --force to retrain.')
            )
            return

        # Load weapons data for training context
        data_path = Path(__file__).parent.parent.parent / "data" / "middle_east_weapons.json"
        if not data_path.exists():
            raise CommandError(f"Weapons data file not found at {data_path}")

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                weapons_data = json.load(f)
        except json.JSONDecodeError:
            raise CommandError(f"Invalid JSON in weapons data file at {data_path}")

        self.stdout.write('Loading weapons data...')

        # Create training prompt with weapons data
        training_prompt = self._create_training_prompt(weapons_data)

        # Create a custom model with weapons training data
        custom_model_name = f"{model_name}-weapons"
        self.stdout.write(f'Creating custom weapons model: {custom_model_name}...')

        try:
            # Create a Modelfile for fine-tuning with weapons data
            modelfile_content = self._create_modelfile(model_name, training_prompt, weapons_data)

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
                    self.stdout.write(self.style.SUCCESS(f'Custom weapons model {custom_model_name} created successfully'))

                    # Update the weapons service to use the custom model
                    weapons_service.model_name = custom_model_name

                    # Test the custom model with weapons data
                    self.stdout.write('Testing custom weapons model...')
                    test_result = weapons_service.analyze_weapons(
                        "What are key factors for victory probability?"
                    )

                    if test_result['success']:
                        self.stdout.write(
                            self.style.SUCCESS('Weapons model training and testing completed successfully!')
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
                            f'Could not create custom weapons model: {result.stderr}. Using base model for testing.')
                    )
                    # Fallback to testing the base model
                    test_result = weapons_service.analyze_weapons(
                        "What are key factors for victory probability?"
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
                self.style.WARNING(f'Error creating custom weapons model: {str(e)}. Using base model.')
            )
            # Fallback to testing the base model
            test_result = weapons_service.analyze_weapons(
                "What are key factors for victory probability?"
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

    def _create_training_prompt(self, weapons_data):
        """Create a concise training prompt with weapons data"""
        categories = weapons_data.get('weapon_categories', {})
        
        prompt = "You are a military weapons and capabilities analyst specializing in Middle Eastern defense systems and military technology. Your role is to provide detailed analysis of weapons systems, military capabilities, and strategic assessments.\n\n"
        prompt += "Weapon categories: "
        
        category_names = []
        for category_key, category_data in categories.items():
            name = category_data.get('name', category_key)
            category_names.append(name)
        
        prompt += ", ".join(category_names)
        prompt += "\n\nKey analysis areas:\n- Weapons system effectiveness and capabilities\n- Military technology advantages and disadvantages\n- Defense system analysis and vulnerabilities\n- Strategic weapons capabilities assessment\n- Victory probability based on military technology\n- Comparative analysis of military equipment\n\nProvide clear, structured analysis with specific technical insights and strategic recommendations. Focus on actionable intelligence for military planning and war outcome prediction."
        
        return prompt

    def _create_modelfile(self, base_model, training_prompt, weapons_data):
        """Create a Modelfile for fine-tuning with weapons data"""
        
        # Create a concise system prompt with weapons data
        enhanced_prompt = self._create_enhanced_system_prompt(training_prompt, weapons_data)
        
        modelfile = f"""FROM {base_model}

# Optimized system prompt for fast responses
SYSTEM \"\"\"
{enhanced_prompt}
\"\"\"

# Parameters optimized for quality responses
PARAMETER temperature 0.3
PARAMETER top_p 0.8
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 2048
PARAMETER num_predict 800
"""
        return modelfile

    def _create_enhanced_system_prompt(self, base_prompt, weapons_data):
        """Create a concise enhanced system prompt with weapons data"""
        
        # Extract key weapons information in a very compact format
        categories_summary = []
        for category_key, category_data in weapons_data.get('weapon_categories', {}).items():
            category_name = category_data.get('name', category_key.title())
            types = category_data.get('types', {})
            
            # Get just the first weapon type for each category
            if types:
                first_weapon = list(types.keys())[0]
                weapon_data = types[first_weapon]
                weapon_name = weapon_data.get('name', first_weapon.title())
                effectiveness = weapon_data.get('effectiveness', 'Unknown')
                categories_summary.append(f"{category_name}: {weapon_name}({effectiveness})")
        
        enhanced_prompt = f"""{base_prompt}

WEAPONS DATA: {', '.join(categories_summary[:5])}

Provide technical analysis of military capabilities and defense systems. Focus on capabilities assessment and strategic analysis."""
        
        return enhanced_prompt
