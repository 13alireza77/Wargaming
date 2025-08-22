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
                        "What are the key factors that determine victory probability in modern warfare?"
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
                        "What are the key factors that determine victory probability in modern warfare?"
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
                "What are the key factors that determine victory probability in modern warfare?"
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
        """Create a comprehensive training prompt with weapons data"""
        categories = weapons_data.get('weapon_categories', {})
        
        prompt = "You are a military weapons and equipment expert specializing in Middle Eastern military capabilities analysis.\n\n"
        prompt += "Available weapon categories and their key characteristics:\n"
        
        for category_key, category_data in categories.items():
            name = category_data.get('name', category_key)
            description = category_data.get('description', 'Unknown')
            prompt += f"- {name}: {description}\n"
            
            # Add weapon types within each category
            types = category_data.get('types', {})
            for weapon_type, weapon_data in types.items():
                weapon_name = weapon_data.get('name', weapon_type)
                effectiveness = weapon_data.get('effectiveness', 'Unknown')
                range_info = weapon_data.get('range', 'Unknown')
                prompt += f"  * {weapon_name}: {effectiveness} effectiveness, {range_info} range\n"
        
        prompt += "\nWhen analyzing military scenarios, consider:\n"
        prompt += "1. Weapon effectiveness and capabilities\n"
        prompt += "2. Strategic advantages and disadvantages\n"
        prompt += "3. Impact on victory probability\n"
        prompt += "4. Logistics and maintenance requirements\n"
        prompt += "5. Tactical and operational considerations\n"
        
        return prompt

    def _create_modelfile(self, base_model, training_prompt, weapons_data):
        """Create a Modelfile for fine-tuning with weapons data"""
        
        # Create a comprehensive system prompt with weapons data
        enhanced_prompt = self._create_enhanced_system_prompt(training_prompt, weapons_data)
        
        modelfile = f"""FROM {base_model}

# Enhanced system prompt with weapons data
SYSTEM \"\"\"
{enhanced_prompt}
\"\"\"

# Parameters optimized for weapons analysis
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
"""
        return modelfile

    def _create_enhanced_system_prompt(self, base_prompt, weapons_data):
        """Create an enhanced system prompt with weapons data embedded"""
        
        # Extract key weapons information
        categories_info = []
        for category_key, category_data in weapons_data.get('weapon_categories', {}).items():
            category_name = category_data.get('name', category_key.title())
            description = category_data.get('description', 'Unknown')
            
            category_info = f"""
{category_name}:
- Description: {description}
- Weapon Types:"""
            
            types = category_data.get('types', {})
            for weapon_type, weapon_data in types.items():
                weapon_name = weapon_data.get('name', weapon_type.title())
                effectiveness = weapon_data.get('effectiveness', 'Unknown')
                range_info = weapon_data.get('range', 'Unknown')
                cost = weapon_data.get('cost', 'Unknown')
                
                category_info += f"""
  * {weapon_name}: {effectiveness} effectiveness, {range_info} range, {cost} cost"""
                
                # Add country information
                countries = weapon_data.get('countries', {})
                if countries:
                    country_list = []
                    for country, data in countries.items():
                        quantity = data.get('quantity', 'Unknown')
                        country_list.append(f"{country} ({quantity})")
                    category_info += f"\n    Countries: {', '.join(country_list)}"
            
            categories_info.append(category_info)
        
        enhanced_prompt = f"""{base_prompt}

DETAILED WEAPONS DATA:

WEAPON CATEGORIES:
{chr(10).join(categories_info)}

When analyzing military scenarios, always reference this specific weapons data and provide detailed, data-driven insights based on weapon capabilities, effectiveness, and strategic considerations for each category."""
        
        return enhanced_prompt
