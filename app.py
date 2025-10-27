#!/usr/bin/env python3
"""
Automated Insulin Dose Recommendation System - API Server
==========================================================

Flask API server for insulin dose recommendations.

Author: Automated Insulin Advisory System
"""

import logging
from flask import Flask, request, jsonify

from engine import InsulinRecommendationEngine

# Configure logging - console only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize recommendation engine
engine = InsulinRecommendationEngine()


@app.route('/')
def index():
    """API health check endpoint"""
    return jsonify({
        "status": "running",
        "service": "Automated Insulin Dose Recommendation System",
        "version": "1.2.0",
        "endpoints": {
            "/": "Health check",
            "/recommend": "POST - Get insulin dose recommendation"
        }
    })


@app.route('/recommend', methods=['POST'])
def recommend():
    """Main API endpoint for insulin dose recommendations"""
    logger.info("=" * 80)
    logger.info("NEW RECOMMENDATION REQUEST RECEIVED")
    logger.info("=" * 80)
    
    try:
        # Get and validate JSON data
        data = request.get_json()
        if not data:
            logger.error("Request rejected: No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Log input data
        _log_input_data(data)
        
        # Get recommendation
        logger.info("\n🔍 STEP 1: Input Validation")
        result = engine.recommend_insulin_dose(data)
        
        # Handle errors
        if "error" in result:
            logger.error(f"✗ Validation Failed: {result['error']}")
            return jsonify(result), 400
        
        # Log and return successful result
        _log_recommendation_result(result)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"✗ Error in recommendation endpoint: {str(e)}")
        logger.error("=" * 80)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


def _log_input_data(data: dict) -> None:
    """Helper function to log input data"""
    logger.info("\n📋 INPUT DATA:")
    
    # Log GRBS values
    if 'GRBS' in data and isinstance(data.get('GRBS'), list):
        logger.info(f"  GRBS Values: {data.get('GRBS')}")
    else:
        grbs_list = [data.get(f'GRBS{i}') for i in range(1, 6)]
        logger.info(f"  GRBS Values: {grbs_list}")
    
    # Log Insulin values
    if 'Insulin' in data and isinstance(data.get('Insulin'), list):
        logger.info(f"  Insulin Doses: {data.get('Insulin')}")
    else:
        insulin_list = [data.get(f'Insulin{i}') for i in range(1, 5)]
        logger.info(f"  Insulin Doses: {insulin_list}")
    
    # Log other parameters
    logger.info(f"  Route: {data.get('route')}")
    logger.info(f"  Diet Order: {data.get('diet_order')}")
    logger.info(f"  CKD: {data.get('CKD')}")
    logger.info(f"  Dual Inotropes: {data.get('Dual inotropes')}")


def _log_recommendation_result(result: dict) -> None:
    """Helper function to log recommendation result"""
    logger.info("✓ Input validation passed")
    logger.info(f"\n✅ FINAL RECOMMENDATION:")
    logger.info(f"  Algorithm: {result.get('algorithm_used')}")
    logger.info(f"  Level: {result.get('level')}")
    logger.info(f"  Insulin Dose: {result.get('Suggested_insulin_dose')} {result.get('unit')}")
    logger.info(f"  Route: {result.get('Suggested_route')}")
    logger.info(f"  Next Check: {result.get('next_grbs_after')} hours")
    logger.info(f"  Action: {result.get('action')}")
    logger.info("=" * 80)


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Starting Automated Insulin Dose Recommendation System on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
