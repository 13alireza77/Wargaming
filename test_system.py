#!/usr/bin/env python3
"""
Test script for the War Game Simulation System
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/geography"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed")
            print(f"   LLM Available: {data.get('llm_available')}")
            print(f"   Model: {data.get('model_name')}")
            print(f"   Regions: {data.get('available_regions')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_get_regions():
    """Test getting available regions"""
    print("\nTesting get regions...")
    try:
        response = requests.get(f"{BASE_URL}/api/regions/")
        if response.status_code == 200:
            data = response.json()
            regions = data.get('regions', [])
            print(f"✅ Get regions passed: {len(regions)} regions found")
            print(f"   Regions: {', '.join(regions[:5])}{'...' if len(regions) > 5 else ''}")
            return regions
        else:
            print(f"❌ Get regions failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Get regions error: {e}")
        return []

def test_get_region_data(region):
    """Test getting data for a specific region"""
    print(f"\nTesting get region data for {region}...")
    try:
        response = requests.get(f"{BASE_URL}/api/regions/{region}/")
        if response.status_code == 200:
            data = response.json()
            region_data = data.get('data', {})
            print(f"✅ Get region data passed for {region}")
            print(f"   Name: {region_data.get('name')}")
            print(f"   Terrain: {region_data.get('terrain', {}).get('primary', 'Unknown')}")
            return True
        else:
            print(f"❌ Get region data failed for {region}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get region data error for {region}: {e}")
        return False

def test_analyze_geography(query, region=None):
    """Test geographical analysis"""
    print(f"\nTesting geographical analysis...")
    print(f"   Query: {query}")
    if region:
        print(f"   Region: {region}")
    
    try:
        payload = {"query": query}
        if region:
            payload["region"] = region
            
        response = requests.post(
            f"{BASE_URL}/api/analyze/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                analysis = data.get('analysis', '')
                print(f"✅ Analysis successful")
                print(f"   Analysis preview: {analysis[:200]}...")
                return True
            else:
                print(f"❌ Analysis failed: {data.get('error')}")
                return False
        else:
            print(f"❌ Analysis request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting War Game Simulation System Tests")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ System health check failed. Please ensure:")
        print("   1. Django server is running (python manage.py runserver)")
        print("   2. Ollama is running (ollama serve)")
        print("   3. Model is installed (ollama pull llama3.2:3b)")
        return
    
    # Test 2: Get regions
    regions = test_get_regions()
    if not regions:
        print("\n❌ Failed to get regions")
        return
    
    # Test 3: Get region data
    if regions:
        test_get_region_data(regions[0])
    
    # Test 4: Analyze geography (general)
    test_analyze_geography(
        "What are the key terrain features that affect military operations in the Middle East?"
    )
    
    # Test 5: Analyze geography (specific region)
    if regions:
        test_analyze_geography(
            "How does the terrain affect defensive operations?",
            regions[0]
        )
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n🎯 Example API Usage:")
    print(f"   Health Check: GET {BASE_URL}/api/health/")
    print(f"   Get Regions: GET {BASE_URL}/api/regions/")
    print(f"   Get Region Data: GET {BASE_URL}/api/regions/syria/")
    print(f"   Analyze: POST {BASE_URL}/api/analyze/")
    print("\n📖 See README.md for detailed usage instructions")

if __name__ == "__main__":
    main()
