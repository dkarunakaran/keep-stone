import yaml
import json
from sqlalchemy.orm import sessionmaker
from models.base import engine
from models.config import Config

Session = sessionmaker(bind=engine)

def load_config_from_yaml():
    """Load initial config from YAML file"""
    try:
        with open("/app/config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

def flatten_dict(d, parent_key='', sep='.'):
    """Flatten nested dictionary, keeping track of edit flags"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            # Check if this dict has an 'edit' key
            if 'edit' in v:
                # This is a config section with edit flag
                edit_flag = v.get('edit', False)
                for sub_k, sub_v in v.items():
                    if sub_k != 'edit':  # Skip the edit flag itself
                        sub_key = f"{new_key}{sep}{sub_k}"
                        items.append((sub_key, sub_v, edit_flag))
            else:
                # Regular nested dict
                items.extend(flatten_dict(v, new_key, sep=sep))
        else:
            # Simple value at root level - no edit flag means not editable
            items.append((new_key, v, False))
    return items

def unflatten_dict(d, sep='.'):
    """Unflatten dictionary back to nested structure"""
    result = {}
    for key, value in d.items():
        keys = key.split(sep)
        current = result
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    return result

def generate_config_description(key):
    """Generate human-readable description for config keys"""
    descriptions = {
        # Storage
        'storage.image_path': 'Directory path where uploaded images are stored',
        'storage.allowed_extensions': 'Allowed file extensions for image uploads',
        'storage.max_file_size': 'Maximum file size for uploads (in bytes)',
        'storage.cleanup_threshold_hours': 'Hours after which unused files are cleaned up',
        
        # Database
        'sql_alchemy.loc': 'Database directory location',
        'sql_alchemy.db': 'Database filename',
        
        # Display/Trim settings
        'trim.name': 'Maximum characters for artifact name display',
        'trim.content': 'Maximum characters for content preview',
        'trim.extra': 'Extra characters allowed for display',
        
        # Email settings
        'email.smtp_server': 'SMTP server hostname for email',
        'email.smtp_port': 'SMTP server port number',
        'email.notification_days': 'Days before expiry to send notifications',
        'email.max_notifications': 'Maximum number of notifications per token',
        'email.notification_interval': 'Hours between notification attempts',
        'email.timezone': 'Timezone for date calculations',
    }
    
    return descriptions.get(key, f'Configuration setting for {key.replace(".", " ").title()}')

def generate_config_title(key):
    """Generate human-readable title for config keys"""
    if '.' in key:
        section, field = key.rsplit('.', 1)
        return field.replace('_', ' ').title()
    else:
        return key.replace('_', ' ').title()

def initialize_config_table():
    """Initialize config table with editable data from YAML file"""
    session = Session()
    try:
        # Check if config table has any data
        existing_configs = session.query(Config).count()
        
        if existing_configs == 0:
            # Load from YAML and populate database
            yaml_config = load_config_from_yaml()
            flat_config = flatten_dict(yaml_config)
            
            for key, value, is_editable in flat_config:
                # Only add to database if it's editable
                if is_editable:
                    config_item = Config(
                        key=key,
                        value=json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                        description=generate_config_description(key)
                    )
                    session.add(config_item)
            
            session.commit()
            print(f"Config table initialized with {session.query(Config).count()} editable items")
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing config table: {e}")
    finally:
        session.close()

def load_config():
    """Load configuration from database and YAML, merging both"""
    yaml_config = load_config_from_yaml()
    
    session = Session()
    try:
        # Get editable configs from database
        db_configs = session.query(Config).all()
        db_flat_config = {}
        
        for config in db_configs:
            try:
                # Try to parse as JSON first (for lists/dicts)
                value = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as string
                value = config.value
                # Convert string numbers to appropriate types
                if isinstance(value, str):
                    if value.isdigit():
                        value = int(value)
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
            
            db_flat_config[config.key] = value
        
        # Start with YAML config as base
        result_config = yaml_config.copy()
        
        # Remove edit flags from result
        def clean_edit_flags(d):
            if isinstance(d, dict):
                cleaned = {}
                for k, v in d.items():
                    if k != 'edit':
                        cleaned[k] = clean_edit_flags(v)
                return cleaned
            return d
        
        result_config = clean_edit_flags(result_config)
        
        # Override with database values for editable configs
        db_nested = unflatten_dict(db_flat_config)
        
        # Merge database config into result
        def merge_configs(base, override):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_configs(base[key], value)
                else:
                    base[key] = value
        
        merge_configs(result_config, db_nested)
        
        return result_config
        
    except Exception as e:
        print(f"Error loading config from database: {e}")
        # Fallback to YAML if database fails - clean edit flags
        def clean_edit_flags(d):
            if isinstance(d, dict):
                cleaned = {}
                for k, v in d.items():
                    if k != 'edit':
                        cleaned[k] = clean_edit_flags(v)
                return cleaned
            return d
        return clean_edit_flags(yaml_config)
    finally:
        session.close()

def update_config(key, value):
    """Update a single config value"""
    session = Session()
    try:
        config = session.query(Config).filter(Config.key == key).first()
        if config:
            config.value = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error updating config: {e}")
        return False
    finally:
        session.close()

def get_config_for_settings():
    """Get all editable config items for settings page display"""
    session = Session()
    try:
        configs = session.query(Config).order_by(Config.key).all()
        
        # Group configs by section
        grouped_configs = {}
        for config in configs:
            if '.' in config.key:
                section = config.key.split('.')[0]
            else:
                section = 'general'
                
            if section not in grouped_configs:
                grouped_configs[section] = []
            
            # Add title and parsed value
            config_dict = {
                'key': config.key,
                'value': config.value,
                'description': config.description,
                'title': generate_config_title(config.key),
                'section': section
            }
            
            # Parse value for display
            try:
                parsed_value = json.loads(config.value)
                if isinstance(parsed_value, list):
                    config_dict['display_value'] = ', '.join(map(str, parsed_value))
                    config_dict['input_type'] = 'text'
                else:
                    config_dict['display_value'] = str(parsed_value)
                    config_dict['input_type'] = 'text'
            except (json.JSONDecodeError, TypeError):
                config_dict['display_value'] = config.value
                # Determine input type based on key and value
                if config.key.endswith(('_port', '_size', '_days', '_hours', '_notifications', '_interval')):
                    config_dict['input_type'] = 'number'
                elif config.value.lower() in ('true', 'false'):
                    config_dict['input_type'] = 'boolean'
                else:
                    config_dict['input_type'] = 'text'
            
            grouped_configs[section].append(config_dict)
        
        return grouped_configs
        
    except Exception as e:
        print(f"Error getting config for settings: {e}")
        return {}
    finally:
        session.close()

def get_section_title(section):
    """Get human-readable title for config sections"""
    section_titles = {
        'storage': 'File Storage Settings',
        'sql_alchemy': 'Database Settings', 
        'trim': 'Display & Formatting',
        'email': 'Email & Notifications',
        'general': 'General Settings'
    }
    return section_titles.get(section, section.replace('_', ' ').title())

def get_section_icon(section):
    """Get Font Awesome icon for config sections"""
    section_icons = {
        'storage': 'fas fa-hard-drive',
        'sql_alchemy': 'fas fa-database',
        'trim': 'fas fa-eye',
        'email': 'fas fa-envelope',
        'general': 'fas fa-cog'
    }
    return section_icons.get(section, 'fas fa-cog')

def reset_config_to_defaults():
    """Reset config table to default values from YAML"""
    session = Session()
    try:
        # Delete all existing configs
        session.query(Config).delete()
        
        # Reinitialize from YAML
        yaml_config = load_config_from_yaml()
        flat_config = flatten_dict(yaml_config)
        
        for key, value, is_editable in flat_config:
            if is_editable:
                config_item = Config(
                    key=key,
                    value=json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                    description=generate_config_description(key)
                )
                session.add(config_item)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error resetting config to defaults: {e}")
        return False
    finally:
        session.close()