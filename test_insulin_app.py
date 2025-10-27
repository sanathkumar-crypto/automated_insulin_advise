#!/usr/bin/env python3
"""
Test Script for Automated Insulin Dose Recommendation System
===========================================================

This script tests the insulin recommendation system with various scenarios
and provides detailed logging of the decision-making process.

Usage:
    python test_insulin_app.py

Author: Automated Insulin Advisory System
"""

import json
import logging
import requests
import time
from typing import Dict, List
import sys

# Configure logging - console only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InsulinTestSuite:
    """Comprehensive test suite for insulin recommendation system"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.test_results = []
        self.logger = logging.getLogger(f"{__name__}.InsulinTestSuite")
        
    def log_test_scenario(self, scenario_name: str, input_data: Dict, expected_route: str = None):
        """Log test scenario details"""
        self.logger.info("=" * 80)
        self.logger.info(f"TEST SCENARIO: {scenario_name}")
        self.logger.info("=" * 80)
        self.logger.info(f"Input Data: {json.dumps(input_data, indent=2)}")
        if expected_route:
            self.logger.info(f"Expected Route: {expected_route}")
        self.logger.info("-" * 80)
    
    def make_recommendation_request(self, data: Dict) -> Dict:
        """Make API request to get insulin recommendation"""
        try:
            response = requests.post(
                f"{self.base_url}/recommend",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API Error {response.status_code}: {response.text}")
                return {"error": f"API Error {response.status_code}: {response.text}"}
        
        except requests.exceptions.ConnectionError:
            self.logger.error("Connection Error: Make sure the Flask app is running on localhost:5001")
            return {"error": "Connection Error: Flask app not running"}
        except Exception as e:
            self.logger.error(f"Request Error: {str(e)}")
            return {"error": f"Request Error: {str(e)}"}
    
    def analyze_recommendation(self, result: Dict, scenario_name: str):
        """Analyze and log recommendation results"""
        self.logger.info("RECOMMENDATION RESULT:")
        self.logger.info("-" * 40)
        
        if "error" in result:
            self.logger.error(f"ERROR: {result['error']}")
            return False
        
        # Log detailed results
        self.logger.info(f"Algorithm Used: {result.get('algorithm_used', 'Unknown')}")
        self.logger.info(f"Level: {result.get('level', 'Unknown')}")
        self.logger.info(f"Suggested Insulin Dose: {result.get('Suggested_insulin_dose', 'Unknown')}")
        self.logger.info(f"Suggested Route: {result.get('Suggested_route', 'Unknown')}")
        self.logger.info(f"Next GRBS Check: {result.get('next_grbs_after', 'Unknown')} hours")
        self.logger.info(f"Action: {result.get('action', 'Unknown')}")
        
        # Store test result
        self.test_results.append({
            "scenario": scenario_name,
            "result": result,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return True
    
    def test_iv_algorithm_scenarios(self):
        """Test IV insulin infusion algorithm scenarios"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TESTING IV INSULIN INFUSION ALGORITHM")
        self.logger.info("="*100)
        
        # Test Case 1: High GRBS requiring IV
        test_data = {
            "GRBS1": 400, "GRBS2": 380, "GRBS3": 360, "GRBS4": 340, "GRBS5": 320,
            "Insulin1": 0, "Insulin2": 0, "Insulin3": 0, "Insulin4": 0,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("High GRBS - IV Route", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "High GRBS - IV Route")
        
        # Test Case 2: SC route with 2+ high GRBS (should switch to IV)
        test_data = {
            "GRBS1": 400, "GRBS2": 420, "GRBS3": 350, "GRBS4": 320, "GRBS5": 300,
            "Insulin1": 2, "Insulin2": 3, "Insulin3": 2, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "NPO"
        }
        self.log_test_scenario("SC Route with 2+ High GRBS - Should Switch to IV", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "SC Route with 2+ High GRBS - Should Switch to IV")
        
        # Test Case 3: SC route WITHOUT 2+ high GRBS (should stay SC)
        test_data = {
            "GRBS1": 200, "GRBS2": 180, "GRBS3": 160, "GRBS4": 140, "GRBS5": 120,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": False, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("SC Route WITHOUT 2+ High GRBS - Should Stay SC", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "SC Route WITHOUT 2+ High GRBS - Should Stay SC")
        
        # Test Case 4: IV route with GRBS not in 150-180 range
        test_data = {
            "GRBS1": 250, "GRBS2": 230, "GRBS3": 210, "GRBS4": 190, "GRBS5": 170,
            "Insulin1": 3, "Insulin2": 3, "Insulin3": 2, "Insulin4": 2,
            "CKD": True, "Dual inotropes": True, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Route with GRBS not in 150-180 range", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Route with GRBS not in 150-180 range")
    
    def test_basal_bolus_scenarios(self):
        """Test basal bolus algorithm scenarios"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TESTING BASAL BOLUS ALGORITHM")
        self.logger.info("="*100)
        
        # Test Case 1: Normal SC route scenario
        test_data = {
            "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("Normal SC Route - Basal Bolus", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Normal SC Route - Basal Bolus")
        
        # Test Case 2: IV route with GRBS in 150-180 range (should use basal bolus)
        test_data = {
            "GRBS1": 170, "GRBS2": 160, "GRBS3": 155, "GRBS4": 150, "GRBS5": 145,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": True, "Dual inotropes": True, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Route with GRBS in 150-180 range - Should Use Basal Bolus", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Route with GRBS in 150-180 range - Should Use Basal Bolus")
        
        # Test Case 3: High GRBS requiring higher dose
        test_data = {
            "GRBS1": 300, "GRBS2": 280, "GRBS3": 260, "GRBS4": 240, "GRBS5": 220,
            "Insulin1": 6, "Insulin2": 5, "Insulin3": 4, "Insulin4": 3,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "NPO"
        }
        self.log_test_scenario("High GRBS - Basal Bolus High Dose", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "High GRBS - Basal Bolus High Dose")
        
        # Test Case 4: Low GRBS requiring no insulin
        test_data = {
            "GRBS1": 120, "GRBS2": 130, "GRBS3": 125, "GRBS4": 135, "GRBS5": 140,
            "Insulin1": 0, "Insulin2": 0, "Insulin3": 0, "Insulin4": 0,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("Low GRBS - No Insulin Required", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Low GRBS - No Insulin Required")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TESTING EDGE CASES AND ERROR CONDITIONS")
        self.logger.info("="*100)
        
        # Test Case 1: Invalid input data
        test_data = {
            "GRBS1": "invalid",  # Invalid GRBS value
            "GRBS2": 200, "GRBS3": 180, "GRBS4": 160, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("Invalid GRBS Value", test_data)
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Invalid GRBS Value")
        
        # Test Case 2: Missing required field
        test_data = {
            "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc"
            # Missing "diet_order" field
        }
        self.log_test_scenario("Missing Required Field", test_data)
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Missing Required Field")
        
        # Test Case 3: Invalid route
        test_data = {
            "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "invalid", "diet_order": "others"
        }
        self.log_test_scenario("Invalid Route", test_data)
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Invalid Route")
        
        # Test Case 4: Extreme GRBS values
        test_data = {
            "GRBS1": 1000, "GRBS2": 950, "GRBS3": 900, "GRBS4": 850, "GRBS5": 800,
            "Insulin1": 8, "Insulin2": 7, "Insulin3": 6, "Insulin4": 5,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("Extreme High GRBS Values", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Extreme High GRBS Values")
    
    def test_algorithm_transitions(self):
        """Test algorithm level transitions"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TESTING ALGORITHM LEVEL TRANSITIONS")
        self.logger.info("="*100)
        
        # Test Case 1: IV Algorithm - Moving up levels
        test_data = {
            "GRBS1": 300, "GRBS2": 280, "GRBS3": 260, "GRBS4": 240, "GRBS5": 220,
            "Insulin1": 4, "Insulin2": 3, "Insulin3": 2, "Insulin4": 1,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Algorithm - Moving Up Levels", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Algorithm - Moving Up Levels")
        
        # Test Case 2: IV Algorithm - Moving down levels
        test_data = {
            "GRBS1": 100, "GRBS2": 120, "GRBS3": 140, "GRBS4": 160, "GRBS5": 180,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Algorithm - Moving Down Levels", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Algorithm - Moving Down Levels")
        
        # Test Case 3: Basal Bolus - Moving up levels (2+ readings > 180)
        test_data = {
            "GRBS1": 200, "GRBS2": 190, "GRBS3": 180, "GRBS4": 170, "GRBS5": 160,
            "Insulin1": 4, "Insulin2": 3, "Insulin3": 2, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("Basal Bolus - Moving Up Levels", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Basal Bolus - Moving Up Levels")
        
        # Test Case 4: Basal Bolus - Moving down levels (reading < 140)
        test_data = {
            "GRBS1": 130, "GRBS2": 150, "GRBS3": 160, "GRBS4": 170, "GRBS5": 180,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("Basal Bolus - Moving Down Levels", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "Basal Bolus - Moving Down Levels")
    
    def test_timing_scenarios(self):
        """Test next GRBS check timing scenarios"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TESTING NEXT GRBS CHECK TIMING")
        self.logger.info("="*100)
        
        # Test Case 1: IV route - hourly check
        test_data = {
            "GRBS1": 250, "GRBS2": 230, "GRBS3": 210, "GRBS4": 190, "GRBS5": 170,
            "Insulin1": 3, "Insulin2": 2, "Insulin3": 1, "Insulin4": 0,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Route - Hourly Check", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Route - Hourly Check")
        
        # Test Case 2: IV route - 2nd hourly check (GRBS1-4 in 140-180)
        test_data = {
            "GRBS1": 170, "GRBS2": 160, "GRBS3": 150, "GRBS4": 140, "GRBS5": 130,
            "Insulin1": 2, "Insulin2": 1, "Insulin3": 0, "Insulin4": 0,
            "CKD": False, "Dual inotropes": False, "route": "iv", "diet_order": "NPO"
        }
        self.log_test_scenario("IV Route - 2nd Hourly Check", test_data, "iv")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "IV Route - 2nd Hourly Check")
        
        # Test Case 3: SC route - NPO (4th hourly)
        test_data = {
            "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "NPO"
        }
        self.log_test_scenario("SC Route - NPO (4th Hourly)", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "SC Route - NPO (4th Hourly)")
        
        # Test Case 4: SC route - Others (6th hourly)
        test_data = {
            "GRBS1": 180, "GRBS2": 170, "GRBS3": 160, "GRBS4": 150, "GRBS5": 140,
            "Insulin1": 2, "Insulin2": 2, "Insulin3": 1, "Insulin4": 1,
            "CKD": False, "Dual inotropes": True, "route": "sc", "diet_order": "others"
        }
        self.log_test_scenario("SC Route - Others (6th Hourly)", test_data, "subcutaneous")
        result = self.make_recommendation_request(test_data)
        self.analyze_recommendation(result, "SC Route - Others (6th Hourly)")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        self.logger.info("\n" + "="*100)
        self.logger.info("TEST EXECUTION SUMMARY")
        self.logger.info("="*100)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if "error" not in result["result"])
        failed_tests = total_tests - successful_tests
        
        self.logger.info(f"Total Tests Executed: {total_tests}")
        self.logger.info(f"Successful Tests: {successful_tests}")
        self.logger.info(f"Failed Tests: {failed_tests}")
        self.logger.info(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # Log algorithm usage statistics
        algorithm_usage = {}
        for result in self.test_results:
            if "error" not in result["result"]:
                algo = result["result"].get("algorithm_used", "Unknown")
                algorithm_usage[algo] = algorithm_usage.get(algo, 0) + 1
        
        self.logger.info("\nAlgorithm Usage Statistics:")
        for algo, count in algorithm_usage.items():
            self.logger.info(f"  {algo}: {count} tests")
    
    def run_all_tests(self):
        """Run all test scenarios"""
        self.logger.info("Starting Comprehensive Insulin Recommendation Test Suite")
        self.logger.info(f"Target URL: {self.base_url}")
        self.logger.info(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Run all test categories
            self.test_iv_algorithm_scenarios()
            self.test_basal_bolus_scenarios()
            self.test_edge_cases()
            self.test_algorithm_transitions()
            self.test_timing_scenarios()
            
            # Generate final report
            self.generate_test_report()
            
            self.logger.info(f"\nTest suite completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            self.logger.error(f"Test suite failed with error: {str(e)}")
            sys.exit(1)

def main():
    """Main function to run the test suite"""
    print("Automated Insulin Dose Recommendation System - Test Suite")
    print("=" * 60)
    print("This test suite will test various scenarios for insulin dose recommendations.")
    print("Make sure the Flask application is running on localhost:5001")
    print("=" * 60)
    
    # Check if Flask app is running
    try:
        response = requests.get("http://localhost:5001", timeout=5)
        print("✓ Flask application is running")
    except requests.exceptions.ConnectionError:
        print("✗ Flask application is not running!")
        print("Please start the Flask app first:")
        print("  python app.py")
        sys.exit(1)
    
    # Run test suite
    test_suite = InsulinTestSuite()
    test_suite.run_all_tests()
    
    print("\nTest execution completed!")

if __name__ == "__main__":
    main()