#!/usr/bin/env python3
"""
Automated Insulin Dose Recommendation System
============================================

This application provides insulin dose recommendations based on:
- Previous insulin doses and GRBS values
- Insulin route (IV/SC)
- Patient conditions (CKD, dual inotropes)
- Diet orders

Author: Automated Insulin Advisory System
"""

import csv
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from flask_oauthlib.client import OAuth
from functools import wraps
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('insulin_recommendations.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# OAuth configuration
oauth = OAuth(app)

# Initialize OAuth only if credentials are provided
google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

if google_client_id and google_client_secret and google_client_id != 'your-google-client-id-here':
    google = oauth.remote_app(
        'google',
        consumer_key=google_client_id,
        consumer_secret=google_client_secret,
        request_token_params={
            'scope': 'email'
        },
        base_url='https://www.googleapis.com/oauth2/v1/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
    )
else:
    google = None
    logger.warning("OAuth credentials not configured. Authentication will be disabled.")

class InsulinRecommendationEngine:
    """Main engine for insulin dose calculations"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.InsulinRecommendationEngine")
        
        # Load algorithm configurations from CSV
        self.iv_algorithm = {}
        self.basal_bolus_algorithm = {}
        self._load_algorithm_config()
    
    def _load_algorithm_config(self):
        """Load algorithm configurations from CSV file"""
        csv_file = 'algorithm_config.csv'
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    algorithm = row['algorithm']
                    level = int(row['level'])
                    grbs_range_str = row['grbs_range']
                    dose = float(row['dose'])
                    
                    if algorithm == 'IV':
                        # Parse GRBS range (e.g., "<110", "110-129", ">400")
                        if '<' in grbs_range_str:
                            grbs_max = int(grbs_range_str.replace('<', '').strip())
                            grbs_min = 0
                        elif '>' in grbs_range_str:
                            grbs_min = int(grbs_range_str.replace('>', '').strip())
                            grbs_max = 1000
                        else:
                            parts = grbs_range_str.split('-')
                            grbs_min = int(parts[0])
                            grbs_max = int(parts[1])
                        
                        # Store as dictionary with GRBS range as key (2D table)
                        if level not in self.iv_algorithm:
                            self.iv_algorithm[level] = {}
                        
                        grbs_key = (grbs_min, grbs_max)
                        self.iv_algorithm[level][grbs_key] = dose
                                
                    elif algorithm == 'Basal':
                        # Parse GRBS range (e.g., "<150", "151-200", ">400")
                        if '<' in grbs_range_str:
                            grbs_max = int(grbs_range_str.replace('<', '').strip())
                            grbs_min = 0
                        elif '>' in grbs_range_str:
                            grbs_min = int(grbs_range_str.replace('>', '').strip())
                            grbs_max = 1000
                        else:
                            parts = grbs_range_str.split('-')
                            grbs_min = int(parts[0])
                            grbs_max = int(parts[1])
                        
                        # Store as dictionary with GRBS range as key
                        if level not in self.basal_bolus_algorithm:
                            self.basal_bolus_algorithm[level] = {}
                        
                        grbs_key = (grbs_min, grbs_max)
                        self.basal_bolus_algorithm[level][grbs_key] = int(dose)
            
            self.logger.info(f"Loaded algorithm configurations from {csv_file}")
            
        except FileNotFoundError:
            self.logger.error(f"CSV file {csv_file} not found. Using default values.")
            # Fallback to defaults if CSV not found
            self._load_default_config()
        except Exception as e:
            self.logger.error(f"Error loading algorithm config: {e}. Using default values.")
            self._load_default_config()
    
    def _load_default_config(self):
        """Load default algorithm configurations"""
        # IV Insulin Infusion Algorithm Table
        self.iv_algorithm = {
            1: {"grbs_range": (0, 110), "insulin_rate": 0, "action": "Turn off insulin"},
            2: {"grbs_range": (111, 150), "insulin_rate": 1.0, "action": "Maintain current rate"},
            3: {"grbs_range": (151, 200), "insulin_rate": 2.0, "action": "Increase rate"},
            4: {"grbs_range": (201, 250), "insulin_rate": 3.0, "action": "Increase rate"},
            5: {"grbs_range": (251, 300), "insulin_rate": 4.0, "action": "Increase rate"},
            6: {"grbs_range": (301, 350), "insulin_rate": 5.0, "action": "Increase rate"},
            7: {"grbs_range": (351, 400), "insulin_rate": 6.0, "action": "Increase rate"},
            8: {"grbs_range": (401, 450), "insulin_rate": 7.0, "action": "Increase rate"},
            9: {"grbs_range": (451, 500), "insulin_rate": 8.0, "action": "Increase rate"},
            10: {"grbs_range": (501, 1000), "insulin_rate": 10.0, "action": "Maximum rate"}
        }
        
        # Basal Bolus Algorithm Table
        self.basal_bolus_algorithm = {
            1: {"grbs_range": (0, 140), "insulin_dose": 0, "action": "No insulin"},
            2: {"grbs_range": (141, 180), "insulin_dose": 2, "action": "Low dose"},
            3: {"grbs_range": (181, 220), "insulin_dose": 4, "action": "Medium dose"},
            4: {"grbs_range": (221, 260), "insulin_dose": 6, "action": "High dose"},
            5: {"grbs_range": (261, 300), "insulin_dose": 8, "action": "Very high dose"},
            6: {"grbs_range": (301, 350), "insulin_dose": 16, "action": "Maximum dose"},
            7: {"grbs_range": (351, 1000), "insulin_dose": 12, "action": "Critical dose"}
        }
    
    def validate_input(self, data: Dict) -> Tuple[bool, str]:
        """Validate input data structure and values - only GRBS1 is mandatory"""
        # Only GRBS1 is required
        if "GRBS1" not in data:
            return False, "Missing required field: GRBS1 (latest GRBS value)"
        
        # Try to validate GRBS1 is numeric
        try:
            float(data["GRBS1"])
        except (ValueError, TypeError):
            return False, f"Invalid GRBS1 value: {data['GRBS1']}"
        
        # Set defaults for missing fields (except GRBS1 which is already validated)
        defaults = {
            "GRBS2": 0, "GRBS3": 0, "GRBS4": 0, "GRBS5": 0,
            "Insulin1": 0, "Insulin2": 0, "Insulin3": 0, "Insulin4": 0,
            "CKD": False, "Dual inotropes": False, "route": "sc", "diet_order": "others"
        }
        
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        # Validate GRBS values (should be numeric, allow missing)
        grbs_fields = ["GRBS1", "GRBS2", "GRBS3", "GRBS4", "GRBS5"]
        for field in grbs_fields:
            try:
                float(data[field])
            except (ValueError, TypeError):
                data[field] = 0  # Default to 0 if invalid
        
        # Validate insulin values (should be numeric, allow missing)
        insulin_fields = ["Insulin1", "Insulin2", "Insulin3", "Insulin4"]
        for field in insulin_fields:
            try:
                float(data[field])
            except (ValueError, TypeError):
                data[field] = 0  # Default to 0 if invalid
        
        # Validate boolean fields
        if not isinstance(data["CKD"], bool):
            data["CKD"] = False
        if not isinstance(data["Dual inotropes"], bool):
            data["Dual inotropes"] = False
        
        # Validate route
        if data["route"] not in ["iv", "sc"]:
            data["route"] = "sc"  # Default to SC
        
        # Validate diet order
        if data["diet_order"] not in ["NPO", "others"]:
            data["diet_order"] = "others"  # Default to others
        
        return True, "Valid input"
    
    def determine_algorithm_type(self, data: Dict) -> str:
        """Determine which algorithm to use based on input conditions"""
        route = data["route"]
        dual_inotropes = data["Dual inotropes"]
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        
        self.logger.info("\n🔍 STEP 2: Algorithm Selection")
        self.logger.info(f"  Current Route: {route}")
        self.logger.info(f"  Dual Inotropes: {dual_inotropes}")
        self.logger.info(f"  GRBS Values: {grbs_values}")
        
        # Priority 1: If Dual Inotropes is True, ALWAYS use IV algorithm
        if dual_inotropes:
            self.logger.info("  → Condition: Dual Inotropes = True")
            self.logger.info("  ✓ Decision: Use IV algorithm (Dual Inotropes requirement)")
            return "iv"
        
        # Priority 2: Check SC route conditions
        if route == "sc":
            # Use IV ONLY if two or more of the latest GRBS values are more than 350
            high_grbs_count = sum(1 for grbs in grbs_values if grbs > 350)
            
            self.logger.info(f"  → High GRBS (>350) count: {high_grbs_count}")
            self.logger.info(f"  → GRBS values: {grbs_values}")
            
            if high_grbs_count >= 2:
                self.logger.info(f"  → Condition: {high_grbs_count} GRBS values > 350")
                self.logger.info("  ✓ Decision: Use IV algorithm (2+ high GRBS values)")
                return "iv"
            else:
                self.logger.info("  ✓ Decision: Use Basal Bolus algorithm (SC route without 2+ high GRBS)")
        elif route == "iv":
            # Use IV if not all GRBS1-4 are in 150-180 range
            grbs_1_4 = grbs_values[:4]
            if not all(150 <= val <= 180 for val in grbs_1_4):
                self.logger.info(f"  → Condition: GRBS1-4 not all in 150-180 range")
                self.logger.info(f"  → GRBS1-4: {grbs_1_4}")
                self.logger.info("  ✓ Decision: Continue with IV algorithm")
                return "iv"
            else:
                self.logger.info(f"  → Condition: GRBS1-4 all in 150-180 range")
                self.logger.info(f"  → GRBS1-4: {grbs_1_4}")
                self.logger.info("  ✓ Decision: Switch to Basal Bolus (GRBS controlled)")
        
        # Default to basal bolus
        self.logger.info("  ✓ Final Decision: Basal Bolus algorithm")
        return "basal_bolus"
    
    def calculate_iv_insulin_dose(self, data: Dict) -> Dict:
        """Calculate insulin dose using IV infusion algorithm"""
        self.logger.info("\n💉 STEP 3: IV Infusion Algorithm")
        
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        insulin_values = [data[f"Insulin{i}"] for i in range(1, 5)]
        
        # Count valid (non-zero) GRBS readings
        valid_grbs = [g for g in grbs_values if g > 0]
        grbs_count = len(valid_grbs)
        
        current_grbs = grbs_values[0] if grbs_values[0] > 0 else (valid_grbs[0] if valid_grbs else 0)
        
        self.logger.info(f"  Current GRBS: {current_grbs}")
        self.logger.info(f"  Number of GRBS readings: {grbs_count}")
        self.logger.info(f"  Previous Insulin doses: {insulin_values}")
        
        has_previous_insulin = any(ins > 0 for ins in insulin_values)
        
        # If 0 or 1 GRBS readings AND no previous insulin, default to Level 2
        # But if previous insulin exists, try to match it regardless of GRBS count
        if grbs_count <= 1 and not has_previous_insulin:
            self.logger.info("  → 0 or 1 GRBS readings detected")
            self.logger.info("  → Defaulting to Level 2")
            level = 2
            apply_transition_rules = False
        elif not has_previous_insulin:
            # No previous insulin - always start at level 2 and stay there (no transition rules)
            self.logger.info("  → No previous insulin doses detected")
            self.logger.info("  → Starting at level 2 (no transition rules applied)")
            level = 2
            apply_transition_rules = False
        else:
            # Previous insulin given - for Dual Inotropes, always start at Level 2
            # For others, determine level from most recent insulin dose or GRBS
            dual_inotropes = data.get("Dual inotropes", False)
            
            if dual_inotropes:
                # Dual Inotropes: always start at Level 2 conservatively
                self.logger.info("  → Dual Inotropes selected: starting at Level 2")
                level = 2
                apply_transition_rules = False
            else:
                # Regular case: find level from previous dose using CSV lookup
                most_recent_insulin = insulin_values[0]  # Insulin1
                
                # Find which level corresponds to this insulin rate for the current GRBS
                level = 2  # Default
                best_match_level = 2
                min_diff = float('inf')
                
                self.logger.info(f"  → Previous insulin rate: {most_recent_insulin} IU/hr")
                self.logger.info(f"  → Current GRBS: {current_grbs}")
                
                # Look through all levels to find which one gives a dose closest to previous dose
                for level_num, grbs_table in self.iv_algorithm.items():
                    # Get the dose for this level and current GRBS
                    dose_for_level = self._find_iv_rate_for_level_and_grbs(level_num, current_grbs)
                    diff = abs(dose_for_level - most_recent_insulin)
                    
                    if diff < min_diff:
                        min_diff = diff
                        best_match_level = level_num
                
                level = best_match_level
                dose_at_level = self._find_iv_rate_for_level_and_grbs(level, current_grbs)
                self.logger.info(f"  → Matched to Level {level} (gives {dose_at_level} IU/hr, previous was {most_recent_insulin} IU/hr)")
                
                self.logger.info(f"  → Starting from previous level: {level}")
                self.logger.info("  → Applying transition rules based on GRBS trends")
                apply_transition_rules = True
        
        # Apply transition rules only if there was previous insulin
        if apply_transition_rules:
            old_level = level
            level = self._apply_iv_transition_rules(level, grbs_values)
            if level > 5:
                level = 5  # IV only has levels 1-5
            if level != old_level:
                self.logger.info(f"  → Level adjusted from {old_level} to {level}")
        else:
            self.logger.info(f"  → Staying at level {level}")
        
        # Find the rate for this level and GRBS range
        insulin_rate = self._find_iv_rate_for_level_and_grbs(level, current_grbs)
        action = self._get_iv_action(insulin_rate)
        
        self.logger.info(f"  ✓ Final Level: {level}")
        self.logger.info(f"  ✓ Insulin Rate: {insulin_rate} IU/hr")
        self.logger.info(f"  ✓ Action: {action}")
        
        # Calculate next GRBS check time
        next_check_hours = self._calculate_next_check_time(data, "iv")
        self.logger.info(f"  ✓ Next GRBS Check: {next_check_hours} hours")
        
        return {
            "Suggested_insulin_dose": insulin_rate,
            "Suggested_route": "iv",
            "next_grbs_after": next_check_hours,
            "algorithm_used": "IV Infusion",
            "level": level,
            "action": action,
            "unit": "IU/hr"
        }
    
    def calculate_basal_bolus_dose(self, data: Dict) -> Dict:
        """Calculate insulin dose using basal bolus algorithm"""
        self.logger.info("\n💉 STEP 3: Basal Bolus Algorithm")
        
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        
        # Count valid (non-zero) GRBS readings
        valid_grbs = [g for g in grbs_values if g > 0]
        grbs_count = len(valid_grbs)
        
        current_grbs = grbs_values[0]  # Most recent GRBS
        
        self.logger.info(f"  Current GRBS: {current_grbs}")
        self.logger.info(f"  Number of GRBS readings: {grbs_count}")
        
        # Check for previous insulin doses
        insulin_values = [data[f"Insulin{i}"] for i in range(1, 5)]
        has_previous_insulin = any(ins > 0 for ins in insulin_values)
        
        # If 0 or 1 GRBS readings, default to Level 2
        if grbs_count <= 1:
            self.logger.info("  → 0 or 1 GRBS readings detected")
            self.logger.info("  → Defaulting to Level 2")
            level = 2
            apply_transition_rules = False
        elif not has_previous_insulin:
            # No previous insulin - start at level 2
            self.logger.info("  → No previous insulin doses detected")
            self.logger.info("  → Starting at level 2")
            level = 2
            apply_transition_rules = False
        else:
            # Previous insulin given - determine level from previous dose
            most_recent_insulin = insulin_values[0]  # Insulin1
            
            # Find which level corresponds to this insulin dose for the current GRBS
            level = 2  # Default
            best_match_level = 2
            min_diff = float('inf')
            
            self.logger.info(f"  → Previous insulin dose: {most_recent_insulin} IU")
            self.logger.info(f"  → Current GRBS: {current_grbs}")
            
            # Look through all levels to find which one gives a dose closest to previous dose
            for level_num, grbs_table in self.basal_bolus_algorithm.items():
                # Get the dose for this level and current GRBS
                dose_for_level = self._find_basal_dose_for_level_and_grbs(level_num, current_grbs)
                diff = abs(dose_for_level - most_recent_insulin)
                
                if diff < min_diff:
                    min_diff = diff
                    best_match_level = level_num
            
            level = best_match_level
            dose_at_level = self._find_basal_dose_for_level_and_grbs(level, current_grbs)
            self.logger.info(f"  → Matched to Level {level} (gives {dose_at_level} IU, previous was {most_recent_insulin} IU)")
            
            self.logger.info(f"  → Starting from previous level: {level}")
            
            # Apply transition rules
            old_level = level
            level = self._apply_basal_bolus_transition_rules(level, grbs_values)
            if level != old_level:
                self.logger.info(f"  → Level adjusted from {old_level} to {level}")
            apply_transition_rules = True
        
        # Find the dose for this level and GRBS range
        insulin_dose = self._find_basal_dose_for_level_and_grbs(level, current_grbs)
        action = self._get_basal_action(level, insulin_dose)
        
        self.logger.info(f"  ✓ Final Level: {level}")
        self.logger.info(f"  ✓ Insulin Dose: {insulin_dose} IU")
        self.logger.info(f"  ✓ Action: {action}")
        
        # Calculate next GRBS check time
        next_check_hours = self._calculate_next_check_time(data, "sc")
        self.logger.info(f"  ✓ Next GRBS Check: {next_check_hours} hours")
        
        return {
            "Suggested_insulin_dose": insulin_dose,
            "Suggested_route": "subcutaneous",
            "next_grbs_after": next_check_hours,
            "algorithm_used": "Basal Bolus",
            "level": level,
            "action": action,
            "unit": "IU"
        }
    
    def _find_basal_dose_for_level_and_grbs(self, level: int, current_grbs: float) -> int:
        """Find the insulin dose for a given level and GRBS value"""
        if level not in self.basal_bolus_algorithm:
            return 2  # Default dose
        
        grbs_table = self.basal_bolus_algorithm[level]
        
        # Find the GRBS range that current_grbs falls into
        for (grbs_min, grbs_max), dose in grbs_table.items():
            if grbs_min <= current_grbs <= grbs_max:
                return dose
        
        # If no exact match, return first available dose as default
        if grbs_table:
            return list(grbs_table.values())[0]
        return 2
    
    def _get_basal_action(self, level: int, dose: int) -> str:
        """Get action description based on level and dose"""
        if dose == 0:
            return "No insulin"
        elif dose <= 2:
            return "Low dose"
        elif dose <= 6:
            return "Medium dose"
        elif dose <= 12:
            return "High dose"
        elif dose <= 20:
            return "Very high dose"
        else:
            return "Critical dose"
    
    def _find_iv_rate_for_level_and_grbs(self, level: int, current_grbs: float) -> float:
        """Find the insulin rate for a given level and GRBS value"""
        if level not in self.iv_algorithm:
            return 1.0  # Default rate
        
        grbs_table = self.iv_algorithm[level]
        
        # Find the GRBS range that current_grbs falls into
        for (grbs_min, grbs_max), rate in grbs_table.items():
            if grbs_min <= current_grbs <= grbs_max:
                return rate
        
        # If no exact match, return first available rate as default
        if grbs_table:
            return list(grbs_table.values())[0]
        return 1.0
    
    def _get_iv_action(self, rate: float) -> str:
        """Get action description based on insulin rate"""
        if rate == 0:
            return "Turn off insulin"
        elif rate <= 1:
            return "Maintain current rate"
        elif rate >= 40:
            return "Maximum rate"
        else:
            return "Increase rate"
    
    def _apply_iv_transition_rules(self, current_level: int, grbs_values: List[float]) -> int:
        """Apply IV algorithm transition rules"""
        if len(grbs_values) < 2:
            return current_level
        
        current_grbs = grbs_values[0]
        previous_grbs = grbs_values[1]
        
        # Moving UP: Blood glucose > 150 AND (increased OR decreased 0-60)
        if current_grbs > 150:
            if current_grbs > previous_grbs or (previous_grbs - current_grbs) <= 60:
                new_level = min(current_level + 1, 5)  # IV only has levels 1-5
                self.logger.info(f"IV Algorithm: Moving UP from level {current_level} to {new_level}")
                return new_level
        
        # Moving DOWN: Blood glucose < 110
        if current_grbs < 110:
            new_level = max(current_level - 1, 1)
            self.logger.info(f"IV Algorithm: Moving DOWN from level {current_level} to {new_level}")
            return new_level
        
        # Maintain: Blood glucose 110-150 OR decreased by 61+ mg/dL
        if 110 <= current_grbs <= 150 or (previous_grbs - current_grbs) >= 61:
            self.logger.info(f"IV Algorithm: MAINTAINING level {current_level}")
            return current_level
        
        return current_level
    
    def _apply_basal_bolus_transition_rules(self, current_level: int, grbs_values: List[float]) -> int:
        """Apply basal bolus algorithm transition rules
        
        Target range: 140-180 mg/dl
        
        Move UP: Two or more readings above 180 mg/dl
        Move DOWN: Any one reading less than 140 mg/dl
        """
        if len(grbs_values) < 2:
            return current_level
        
        # Count readings
        readings_above_180 = sum(1 for grbs in grbs_values if grbs > 180)
        readings_below_140 = sum(1 for grbs in grbs_values if grbs > 0 and grbs < 140)
        
        self.logger.info(f"  → Readings above 180 (>180): {readings_above_180}")
        self.logger.info(f"  → Readings below 140 (<140): {readings_below_140}")
        
        # Move UP: Two or more readings above 180
        if readings_above_180 >= 2:
            new_level = min(current_level + 1, 7)
            self.logger.info(f"Basal Bolus: Moving UP from level {current_level} to {new_level} (2+ readings > 180)")
            return new_level
        
        # Move DOWN: Any reading less than 140
        if readings_below_140 >= 1:
            new_level = max(current_level - 1, 1)
            self.logger.info(f"Basal Bolus: Moving DOWN from level {current_level} to {new_level} (1+ readings < 140)")
            return new_level
        
        # Maintain current level
        self.logger.info(f"Basal Bolus: MAINTAINING level {current_level}")
        return current_level
    
    def _calculate_next_check_time(self, data: Dict, route: str) -> int:
        """Calculate next GRBS check time in hours"""
        diet_order = data["diet_order"]
        
        if route == "iv":
            # For IV route: Hourly, or 2nd hourly if GRBS1-4 are 140-180
            grbs_values = [data[f"GRBS{i}"] for i in range(1, 5)]
            if all(140 <= val <= 180 for val in grbs_values):
                return 2
            return 1
        else:  # SC route
            if diet_order == "NPO":
                return 4  # 4th hourly for fasting patients
            else:
                return 6  # 6-8th hourly for others (using 6 as default)
    
    def recommend_insulin_dose(self, data: Dict) -> Dict:
        """Main method to recommend insulin dose"""
        self.logger.info("Starting insulin dose recommendation process")
        self.logger.info(f"Input data: {json.dumps(data, indent=2)}")
        
        # Validate input
        is_valid, error_msg = self.validate_input(data)
        if not is_valid:
            self.logger.error(f"Input validation failed: {error_msg}")
            return {"error": f"Invalid input: {error_msg}"}
        
        # Determine algorithm type
        algorithm_type = self.determine_algorithm_type(data)
        self.logger.info(f"Selected algorithm: {algorithm_type}")
        
        # Calculate dose based on algorithm
        if algorithm_type == "iv":
            result = self.calculate_iv_insulin_dose(data)
        else:
            result = self.calculate_basal_bolus_dose(data)
        
        self.logger.info(f"Recommendation result: {json.dumps(result, indent=2)}")
        return result

# Initialize the recommendation engine
engine = InsulinRecommendationEngine()

def require_auth(f):
    """Decorator to require Gmail authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if google is None:
            # OAuth not configured, allow access for demo purposes
            logger.info("OAuth not configured, allowing access for demo")
            return f(*args, **kwargs)
        if 'google_token' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    """Initiate Gmail OAuth login"""
    if google is None:
        return 'OAuth not configured. Please set up Google OAuth credentials in .env file.'
    return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/login/authorized')
def authorized():
    """Handle OAuth callback"""
    if google is None:
        return 'OAuth not configured. Please set up Google OAuth credentials in .env file.'
    
    resp = google.authorized_response()
    if resp is None or resp.get('access_token') is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    
    session['google_token'] = (resp['access_token'], '')
    user_info = google.get('userinfo')
    
    # Check if email is from @cloudphysician.net domain
    email = user_info.data.get('email', '')
    if not email.endswith('@cloudphysician.net'):
        session.pop('google_token', None)
        return f'Access denied: Email {email} is not authorized. Only @cloudphysician.net emails are allowed.'
    
    logger.info(f"User authenticated: {email}")
    return redirect(url_for('index'))

if google is not None:
    @google.tokengetter
    def get_google_oauth_token():
        """Get OAuth token from session"""
        return session.get('google_token')

@app.route('/')
@require_auth
def index():
    """Main page with web interface"""
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
@require_auth
def recommend():
    """Main API endpoint for insulin dose recommendations"""
    logger.info("=" * 80)
    logger.info("NEW RECOMMENDATION REQUEST RECEIVED")
    logger.info("=" * 80)
    
    try:
        data = request.get_json()
        if not data:
            logger.error("Request rejected: No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
        
        logger.info("\n📋 INPUT DATA:")
        logger.info(f"  GRBS Values: [{data.get('GRBS1')}, {data.get('GRBS2')}, {data.get('GRBS3')}, {data.get('GRBS4')}, {data.get('GRBS5')}]")
        logger.info(f"  Insulin Doses: [{data.get('Insulin1')}, {data.get('Insulin2')}, {data.get('Insulin3')}, {data.get('Insulin4')}]")
        logger.info(f"  Route: {data.get('route')}")
        logger.info(f"  Diet Order: {data.get('diet_order')}")
        logger.info(f"  CKD: {data.get('CKD')}")
        logger.info(f"  Dual Inotropes: {data.get('Dual inotropes')}")
        
        logger.info("\n🔍 STEP 1: Input Validation")
        result = engine.recommend_insulin_dose(data)
        
        if "error" in result:
            logger.error(f"✗ Validation Failed: {result['error']}")
            return jsonify(result), 400
        
        logger.info("✓ Input validation passed")
        logger.info(f"\n✅ FINAL RECOMMENDATION:")
        logger.info(f"  Algorithm: {result.get('algorithm_used')}")
        logger.info(f"  Level: {result.get('level')}")
        logger.info(f"  Insulin Dose: {result.get('Suggested_insulin_dose')}")
        logger.info(f"  Route: {result.get('Suggested_route')}")
        logger.info(f"  Next Check: {result.get('next_grbs_after')} hours")
        logger.info(f"  Action: {result.get('action')}")
        logger.info("=" * 80)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"✗ Error in recommendation endpoint: {str(e)}")
        logger.error("=" * 80)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('google_token', None)
    return 'Logged out successfully. <a href="/">Login again</a>'

if __name__ == '__main__':
    logger.info("Starting Automated Insulin Dose Recommendation System")
    app.run(debug=True, host='0.0.0.0', port=5000)
