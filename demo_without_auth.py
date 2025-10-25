#!/usr/bin/env python3
"""
Demo script for Insulin Recommendation System (without OAuth)
============================================================

This script demonstrates the insulin recommendation functionality
without requiring OAuth authentication. It directly uses the
InsulinRecommendationEngine class.

Usage:
    python demo_without_auth.py
"""

import json
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the engine directly
from app import InsulinRecommendationEngine

def demo_scenarios():
    """Run demonstration scenarios"""
    print("🏥 Automated Insulin Dose Recommendation System - Demo")
    print("=" * 60)
    
    # Initialize the recommendation engine
    engine = InsulinRecommendationEngine()
    
    # Demo scenarios
    scenarios = [
        {
            "name": "High GRBS - IV Route Required",
            "data": {
                "GRBS1": 400, "GRBS2": 380, "GRBS3": 360, "GRBS4": 340, "GRBS5": 320,
                "Insulin1": 0, "Insulin2": 0, "Insulin3": 0, "Insulin4": 0, "Insulin5": 0,
                "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
            }
        },
        {
            "name": "SC Route with High GRBS - Should Switch to IV",
            "data": {
                "GRBS1": 380, "GRBS2": 400, "GRBS3": 350, "GRBS4": 320, "GRBS5": 300,
                "Insulin1": 2, "Insulin2": 3, "Insulin3": 2, "Insulin4": 1, "Insulin5": 0,
                "CKD": False, "Dual inotropes": False, "route": "sc", "diet_order": "NPO"
            }
        },
        {
            "name": "Normal SC Route - Basal Bolus",
            "data": {
                "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
                "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1, "Insulin5": 0,
                "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
            }
        },
        {
            "name": "Low GRBS - No Insulin Required",
            "data": {
                "GRBS1": 120, "GRBS2": 130, "GRBS3": 125, "GRBS4": 135, "GRBS5": 140,
                "Insulin1": 0, "Insulin2": 0, "Insulin3": 0, "Insulin4": 0, "Insulin5": 0,
                "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
            }
        },
        {
            "name": "IV Route with GRBS in Target Range - Basal Bolus",
            "data": {
                "GRBS1": 170, "GRBS2": 160, "GRBS3": 155, "GRBS4": 150, "GRBS5": 145,
                "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1, "Insulin5": 0,
                "CKD": True, "Dual inotropes": True, "route": "iv", "diet_order": "NPO"
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['name']}")
        print("-" * 50)
        
        # Show input data
        print("Input Data:")
        print(json.dumps(scenario['data'], indent=2))
        
        # Get recommendation
        print("\nProcessing...")
        result = engine.recommend_insulin_dose(scenario['data'])
        
        # Show result
        print("\nRecommendation:")
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("✅ Success!")
            print(f"   Algorithm: {result.get('algorithm_used', 'Unknown')}")
            print(f"   Level: {result.get('level', 'Unknown')}")
            print(f"   Suggested Dose: {result.get('Suggested_insulin_dose', 'Unknown')} {result.get('Suggested_route', 'Unknown')}")
            print(f"   Next Check: {result.get('next_grbs_after', 'Unknown')} hours")
            print(f"   Action: {result.get('action', 'Unknown')}")
        
        print("\n" + "=" * 60)

def interactive_demo():
    """Interactive demo where user can input their own data"""
    print("\n🎯 Interactive Demo")
    print("=" * 30)
    print("Enter patient data (press Enter for default values):")
    
    engine = InsulinRecommendationEngine()
    
    # Get user input
    data = {}
    
    # GRBS values
    for i in range(1, 6):
        value = input(f"GRBS{i} (mg/dL): ").strip()
        data[f"GRBS{i}"] = float(value) if value else 150 + i * 10
    
    # Insulin values
    for i in range(1, 6):
        value = input(f"Insulin{i} (IU): ").strip()
        data[f"Insulin{i}"] = float(value) if value else 0
    
    # Boolean values
    ckd = input("CKD (True/False): ").strip().lower()
    data["CKD"] = ckd == "true" if ckd else False
    
    dual_inotropes = input("Dual inotropes (True/False): ").strip().lower()
    data["Dual inotropes"] = dual_inotropes == "true" if dual_inotropes else False
    
    # Route
    route = input("Route (iv/sc): ").strip().lower()
    data["route"] = route if route in ["iv", "sc"] else "sc"
    
    # Diet order
    diet = input("Diet order (NPO/others): ").strip()
    data["diet_order"] = diet if diet in ["NPO", "others"] else "others"
    
    print("\nProcessing your data...")
    print("Input:", json.dumps(data, indent=2))
    
    result = engine.recommend_insulin_dose(data)
    
    print("\nRecommendation:")
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Success!")
        print(json.dumps(result, indent=2))

def main():
    """Main demo function"""
    print("Choose demo mode:")
    print("1. Run predefined scenarios")
    print("2. Interactive demo")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        demo_scenarios()
    elif choice == "2":
        interactive_demo()
    elif choice == "3":
        demo_scenarios()
        interactive_demo()
    else:
        print("Invalid choice. Running predefined scenarios...")
        demo_scenarios()
    
    print("\n🎉 Demo completed!")
    print("\nTo run the full Flask application with OAuth:")
    print("1. Update .env file with your Google OAuth credentials")
    print("2. Run: ./run_app.sh")
    print("3. Open: http://localhost:5000")

if __name__ == "__main__":
    main()

