from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import os
import yaml

# Find config file - support both Docker (/app) and local development
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATHS = [
    "/app/config.yaml",  # Docker path
    os.path.join(PROJECT_ROOT, "config.yaml"),  # Local development
]

cfg = None
for config_path in CONFIG_PATHS:
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        break

if cfg is None:
    raise FileNotFoundError(f"config.yaml not found in: {CONFIG_PATHS}")

def get_config_value(config_dict, key_path):
    """Extract value from new config structure with value/edit properties"""
    keys = key_path.split('.')
    current = config_dict

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None

    # If the final value is a dict with 'value' key, extract the value
    if isinstance(current, dict) and 'value' in current:
        return current['value']

    return current

# Extract database configuration values
db_loc = get_config_value(cfg, 'sql_alchemy.loc')
db_name = get_config_value(cfg, 'sql_alchemy.db')

# Adjust path for local development if Docker path doesn't exist
db_path = os.path.join(db_loc, db_name)
if db_loc == "/app/db" and not os.path.exists(db_path):
    local_db_path = os.path.join(PROJECT_ROOT, "db", db_name)
    if os.path.exists(local_db_path):
        db_path = local_db_path

engine = create_engine(f"sqlite:///{db_path}")
Base = declarative_base() 