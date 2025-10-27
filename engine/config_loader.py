"""
Configuration Loader - Handles loading algorithm configurations from CSV
"""
import csv
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def load_algorithm_config(csv_file: str = 'algorithm_config.csv') -> tuple:
    """
    Load algorithm configurations from CSV file
    
    Returns:
        tuple: (iv_algorithm, basal_bolus_algorithm)
    """
    iv_algorithm = {}
    basal_bolus_algorithm = {}
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                algorithm = row['algorithm']
                level = int(row['level'])
                grbs_range_str = row['grbs_range']
                dose = float(row['dose'])
                
                # Parse GRBS range
                grbs_min, grbs_max = parse_grbs_range(grbs_range_str)
                grbs_key = (grbs_min, grbs_max)
                
                if algorithm == 'IV':
                    if level not in iv_algorithm:
                        iv_algorithm[level] = {}
                    iv_algorithm[level][grbs_key] = dose
                            
                elif algorithm == 'Basal':
                    if level not in basal_bolus_algorithm:
                        basal_bolus_algorithm[level] = {}
                    basal_bolus_algorithm[level][grbs_key] = int(dose)
        
        logger.info(f"Loaded algorithm configurations from {csv_file}")
        
    except FileNotFoundError:
        logger.error(f"CSV file {csv_file} not found. Using default values.")
        return get_default_config()
    except Exception as e:
        logger.error(f"Error loading algorithm config: {e}. Using default values.")
        return get_default_config()
    
    return iv_algorithm, basal_bolus_algorithm


def parse_grbs_range(grbs_range_str: str) -> tuple:
    """
    Parse GRBS range string into (min, max) tuple
    
    Examples: "<110", "110-129", ">400"
    """
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
    
    return grbs_min, grbs_max


def get_default_config() -> tuple:
    """
    Get default algorithm configurations
    
    Returns:
        tuple: (iv_algorithm, basal_bolus_algorithm)
    """
    iv_algorithm = {
        1: {(0, 110): 0},
        2: {(111, 150): 1.0},
        3: {(151, 200): 2.0},
        4: {(201, 250): 3.0},
        5: {(251, 300): 4.0},
    }
    
    basal_bolus_algorithm = {
        1: {(0, 140): 0},
        2: {(141, 180): 2},
        3: {(181, 220): 4},
        4: {(221, 260): 6},
        5: {(261, 300): 8},
        6: {(301, 350): 16},
        7: {(351, 1000): 12}
    }
    
    return iv_algorithm, basal_bolus_algorithm

