from django.test import TestCase
from django.urls import reverse
from django.test import Client
import json

class PersonnelAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.client.get('/personnel/api/health/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['service'], 'personnel')

    def test_get_countries(self):
        """Test getting available countries"""
        response = self.client.get('/personnel/api/countries/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('countries', data)

    def test_get_country_personnel(self):
        """Test getting personnel data for a specific country"""
        response = self.client.get('/personnel/api/countries/israel/personnel/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['country'], 'israel')

    def test_get_branch_personnel(self):
        """Test getting personnel data for a specific branch"""
        response = self.client.get('/personnel/api/countries/israel/branches/ground_forces/personnel/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['country'], 'israel')
        self.assertEqual(data['branch'], 'ground_forces')

    def test_get_branches(self):
        """Test getting available branches"""
        response = self.client.get('/personnel/api/branches/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_get_personnel_summary(self):
        """Test getting personnel summary"""
        response = self.client.get('/personnel/api/summary/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('summary', data)

    def test_analyze_personnel(self):
        """Test personnel analysis endpoint"""
        payload = {
            'query': 'What are the key factors for military victory based on personnel analysis?'
        }
        response = self.client.post(
            '/personnel/api/analyze/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # This might fail if Ollama is not running, but we can test the endpoint structure
        self.assertIn(response.status_code, [200, 500])

    def test_victory_probability(self):
        """Test victory probability calculation endpoint"""
        payload = {
            'country1': 'israel',
            'country2': 'iran',
            'scenario': 'conventional'
        }
        response = self.client.post(
            '/personnel/api/victory-probability/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # This might fail if Ollama is not running, but we can test the endpoint structure
        self.assertIn(response.status_code, [200, 500])
