from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import os
import yaml

with open("/app/config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)

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

engine = create_engine(f"sqlite:///{os.path.join(db_loc, db_name)}") 
Base = declarative_base() 