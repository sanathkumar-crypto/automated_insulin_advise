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

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from flask import Flask, request, jsonify, session, redirect, url_for
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

app = Flask(__name__)
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
        
        # IV Insulin Infusion Algorithm Table (Level 2 as starting point)
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
        
        # Basal Bolus Algorithm Table (Level 2 as starting point)
        self.basal_bolus_algorithm = {
            1: {"grbs_range": (0, 140), "insulin_dose": 0, "action": "No insulin"},
            2: {"grbs_range": (141, 180), "insulin_dose": 2, "action": "Low dose"},
            3: {"grbs_range": (181, 220), "insulin_dose": 4, "action": "Medium dose"},
            4: {"grbs_range": (221, 260), "insulin_dose": 6, "action": "High dose"},
            5: {"grbs_range": (261, 300), "insulin_dose": 8, "action": "Very high dose"},
            6: {"grbs_range": (301, 350), "insulin_dose": 10, "action": "Maximum dose"},
            7: {"grbs_range": (351, 1000), "insulin_dose": 12, "action": "Critical dose"}
        }
    
    def validate_input(self, data: Dict) -> Tuple[bool, str]:
        """Validate input data structure and values"""
        required_fields = [
            "GRBS1", "GRBS2", "GRBS3", "GRBS4", "GRBS5",
            "Insulin1", "Insulin2", "Insulin3", "Insulin4", "Insulin5",
            "CKD", "Dual inotropes", "route", "diet_order"
        ]
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate GRBS values (should be numeric)
        grbs_fields = ["GRBS1", "GRBS2", "GRBS3", "GRBS4", "GRBS5"]
        for field in grbs_fields:
            try:
                float(data[field])
            except (ValueError, TypeError):
                return False, f"Invalid GRBS value for {field}: {data[field]}"
        
        # Validate insulin values
        insulin_fields = ["Insulin1", "Insulin2", "Insulin3", "Insulin4", "Insulin5"]
        for field in insulin_fields:
            try:
                float(data[field])
            except (ValueError, TypeError):
                return False, f"Invalid insulin value for {field}: {data[field]}"
        
        # Validate boolean fields
        if not isinstance(data["CKD"], bool):
            return False, "CKD must be boolean"
        if not isinstance(data["Dual inotropes"], bool):
            return False, "Dual inotropes must be boolean"
        
        # Validate route
        if data["route"] not in ["iv", "sc"]:
            return False, "Route must be 'iv' or 'sc'"
        
        # Validate diet order
        if data["diet_order"] not in ["NPO", "others"]:
            return False, "Diet order must be 'NPO' or 'others'"
        
        return True, "Valid input"
    
    def determine_algorithm_type(self, data: Dict) -> str:
        """Determine which algorithm to use based on input conditions"""
        route = data["route"]
        dual_inotropes = data["Dual inotropes"]
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        
        self.logger.info(f"Determining algorithm type for route: {route}, dual_inotropes: {dual_inotropes}")
        self.logger.info(f"GRBS values: {grbs_values}")
        
        # Check conditions for IV algorithm
        if route == "sc":
            # Use IV if dual_inotropes is False OR GRBS1 and GRBS2 > 350
            if not dual_inotropes or (grbs_values[0] > 350 and grbs_values[1] > 350):
                self.logger.info("Using IV algorithm: SC route with dual_inotropes=False or high GRBS")
                return "iv"
        elif route == "iv":
            # Use IV if not all GRBS1-4 are in 150-180 range
            grbs_1_4 = grbs_values[:4]
            if not all(150 <= val <= 180 for val in grbs_1_4):
                self.logger.info("Using IV algorithm: IV route with GRBS1-4 not in 150-180 range")
                return "iv"
        
        # Default to basal bolus
        self.logger.info("Using Basal Bolus algorithm")
        return "basal_bolus"
    
    def calculate_iv_insulin_dose(self, data: Dict) -> Dict:
        """Calculate insulin dose using IV infusion algorithm"""
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        current_grbs = grbs_values[0]  # Most recent GRBS
        
        self.logger.info(f"Calculating IV insulin dose for current GRBS: {current_grbs}")
        
        # Find appropriate level based on current GRBS
        level = 2  # Start with level 2
        for level_num, config in self.iv_algorithm.items():
            min_val, max_val = config["grbs_range"]
            if min_val <= current_grbs <= max_val:
                level = level_num
                break
        
        # Apply transition rules
        level = self._apply_iv_transition_rules(level, grbs_values)
        
        insulin_rate = self.iv_algorithm[level]["insulin_rate"]
        action = self.iv_algorithm[level]["action"]
        
        self.logger.info(f"IV Algorithm - Level {level}: GRBS={current_grbs}, Rate={insulin_rate} IU/hr, Action={action}")
        
        # Calculate next GRBS check time
        next_check_hours = self._calculate_next_check_time(data, "iv")
        
        return {
            "Suggested_insulin_dose": insulin_rate,
            "Suggested_route": "iv",
            "next_grbs_after": next_check_hours,
            "algorithm_used": "IV Infusion",
            "level": level,
            "action": action
        }
    
    def calculate_basal_bolus_dose(self, data: Dict) -> Dict:
        """Calculate insulin dose using basal bolus algorithm"""
        grbs_values = [data[f"GRBS{i}"] for i in range(1, 6)]
        current_grbs = grbs_values[0]  # Most recent GRBS
        
        self.logger.info(f"Calculating Basal Bolus dose for current GRBS: {current_grbs}")
        
        # Find appropriate level based on current GRBS
        level = 2  # Start with level 2
        for level_num, config in self.basal_bolus_algorithm.items():
            min_val, max_val = config["grbs_range"]
            if min_val <= current_grbs <= max_val:
                level = level_num
                break
        
        # Apply transition rules
        level = self._apply_basal_bolus_transition_rules(level, grbs_values)
        
        insulin_dose = self.basal_bolus_algorithm[level]["insulin_dose"]
        action = self.basal_bolus_algorithm[level]["action"]
        
        self.logger.info(f"Basal Bolus Algorithm - Level {level}: GRBS={current_grbs}, Dose={insulin_dose} IU, Action={action}")
        
        # Calculate next GRBS check time
        next_check_hours = self._calculate_next_check_time(data, "sc")
        
        return {
            "Suggested_insulin_dose": insulin_dose,
            "Suggested_route": "subcutaneous",
            "next_grbs_after": next_check_hours,
            "algorithm_used": "Basal Bolus",
            "level": level,
            "action": action
        }
    
    def _apply_iv_transition_rules(self, current_level: int, grbs_values: List[float]) -> int:
        """Apply IV algorithm transition rules"""
        if len(grbs_values) < 2:
            return current_level
        
        current_grbs = grbs_values[0]
        previous_grbs = grbs_values[1]
        
        # Moving UP: Blood glucose > 150 AND (increased OR decreased 0-60)
        if current_grbs > 150:
            if current_grbs > previous_grbs or (previous_grbs - current_grbs) <= 60:
                new_level = min(current_level + 1, 10)
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
        """Apply basal bolus algorithm transition rules"""
        if len(grbs_values) < 2:
            return current_level
        
        # Count readings above 180 (move up)
        readings_above_180 = sum(1 for grbs in grbs_values[:2] if grbs > 180)
        if readings_above_180 >= 2:
            new_level = min(current_level + 1, 7)
            self.logger.info(f"Basal Bolus: Moving UP from level {current_level} to {new_level} (2+ readings > 180)")
            return new_level
        
        # Check for any reading below 140 (move down)
        if any(grbs < 140 for grbs in grbs_values[:1]):
            new_level = max(current_level - 1, 1)
            self.logger.info(f"Basal Bolus: Moving DOWN from level {current_level} to {new_level} (reading < 140)")
            return new_level
        
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
    """Main page with API documentation"""
    return """
    <h1>Automated Insulin Dose Recommendation System</h1>
    <h2>API Endpoints:</h2>
    <ul>
        <li><strong>POST /recommend</strong> - Get insulin dose recommendation</li>
        <li><strong>GET /logout</strong> - Logout</li>
    </ul>
    <h2>Input Format:</h2>
    <pre>
{
    "GRBS1": 180,
    "GRBS2": 200,
    "GRBS3": 190,
    "GRBS4": 185,
    "GRBS5": 175,
    "Insulin1": 2,
    "Insulin2": 3,
    "Insulin3": 2.5,
    "Insulin4": 2,
    "Insulin5": 1.5,
    "CKD": false,
    "Dual inotropes": false,
    "route": "sc",
    "diet_order": "NPO"
}
    </pre>
    <h2>Output Format:</h2>
    <pre>
{
    "Suggested_insulin_dose": 4,
    "Suggested_route": "subcutaneous",
    "next_grbs_after": 4,
    "algorithm_used": "Basal Bolus",
    "level": 3,
    "action": "Medium dose"
}
    </pre>
    <p><a href="/logout">Logout</a></p>
    """

@app.route('/recommend', methods=['POST'])
@require_auth
def recommend():
    """Main API endpoint for insulin dose recommendations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        logger.info(f"Received recommendation request: {json.dumps(data, indent=2)}")
        
        result = engine.recommend_insulin_dose(data)
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in recommendation endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('google_token', None)
    return 'Logged out successfully. <a href="/">Login again</a>'

if __name__ == '__main__':
    logger.info("Starting Automated Insulin Dose Recommendation System")
    app.run(debug=True, host='0.0.0.0', port=5000)
