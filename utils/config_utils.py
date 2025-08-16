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
    """Flatten nested dictionary, handling new structure with value/edit properties"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            # Check if this is a config item with value/edit structure
            if 'value' in v and 'edit' in v:
                # This is a config item with individual edit flag
                edit_flag = v.get('edit', False)
                value = v.get('value')
                items.append((new_key, value, edit_flag))
            else:
                # Regular nested dict - recurse
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
        
        # General settings
        'default_type': 'Default artifact type to pre-select when creating new artifacts',
        
        # Types
        'type': 'Available artifact types (comma-separated list)',
        
        # Backup settings
        'backup.enabled': 'Enable or disable automatic weekly backups',
        'backup.backup_path': 'Directory path where backup files are stored',
        'backup.keep_backups': 'Number of backup files to retain (older files are deleted)',
        'backup.backup_database': 'Include SQLite database in backups',
        'backup.backup_images': 'Include uploaded images in backups (can be large)',
        'backup.backup_day': 'Day of the week when automatic backups are performed',
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
        # Load from YAML and get all editable configs
        yaml_config = load_config_from_yaml()
        flat_config = flatten_dict(yaml_config)
        
        # Get existing config keys from database
        existing_configs = session.query(Config.key).all()
        existing_keys = {config.key for config in existing_configs}
        
        added_count = 0
        for key, value, is_editable in flat_config:
            # Only add to database if it's editable and not already exists
            if is_editable and key not in existing_keys:
                config_item = Config(
                    key=key,
                    value=json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                    description=generate_config_description(key)
                )
                session.add(config_item)
                added_count += 1
        
        if added_count > 0:
            session.commit()
            print(f"Config table updated: added {added_count} new editable config items")
        else:
            print("Config table is up to date - no new items to add")
        
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
        
        # Remove edit flags and extract values from result
        def clean_edit_flags(d):
            if isinstance(d, dict):
                cleaned = {}
                for k, v in d.items():
                    if isinstance(v, dict) and 'value' in v and 'edit' in v:
                        # Extract just the value from value/edit structure
                        cleaned[k] = v['value']
                    elif k not in ['edit']:  # Skip old-style edit flags
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
                    if isinstance(v, dict) and 'value' in v and 'edit' in v:
                        # Extract just the value from value/edit structure
                        cleaned[k] = v['value']
                    elif k not in ['edit']:  # Skip old-style edit flags
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
        
        # Filter out project-related config items (these should not appear in system settings UI)
        # Get project-level config keys to exclude from system settings
        yaml_config = load_config_from_yaml()
        flat_config = flatten_dict(yaml_config)
        
        project_level_keys = set()
        for key, value, is_editable in flat_config:
            # Check if this config has project_settings: True
            if isinstance(value, dict) and value.get('project_settings', False):
                project_level_keys.add(key)
            elif key in yaml_config and isinstance(yaml_config[key], dict) and yaml_config[key].get('project_settings', False):
                project_level_keys.add(key)
        
        # Also exclude other system keys
        excluded_keys = {'ui.default_project_id'}.union(project_level_keys)
        configs = [config for config in configs if config.key not in excluded_keys]
        
        # Load YAML config to check editability
        yaml_config = load_config_from_yaml()
        flat_config = flatten_dict(yaml_config)
        
        # Create a map of config keys to their editability
        editability_map = {}
        for key, value, is_editable in flat_config:
            editability_map[key] = is_editable
        
        # Group configs by section
        grouped_configs = {}
        for config in configs:
            if config.key == 'type':
                section = 'type'  # Special section for artifact types
            elif config.key == 'default_type':
                section = 'type'  # Group with artifact types
            elif '.' in config.key:
                section = config.key.split('.')[0]
            else:
                section = 'general'
                
            if section not in grouped_configs:
                grouped_configs[section] = []
            
            # Check if this config item should be editable
            is_editable = editability_map.get(config.key, True)  # Default to editable if not found
            
            # Add title and parsed value
            config_dict = {
                'key': config.key,
                'value': config.value,
                'description': config.description,
                'title': generate_config_title(config.key),
                'section': section,
                'editable': is_editable  # Add editability flag
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
                if config.key == 'default_type':
                    config_dict['input_type'] = 'select'
                    # Get options from the type configuration
                    type_config = session.query(Config).filter_by(key='type').first()
                    if type_config:
                        try:
                            type_options = json.loads(type_config.value)
                            config_dict['options'] = type_options if isinstance(type_options, list) else ['Token', 'Troubleshoot', 'Information', 'Other']
                        except (json.JSONDecodeError, TypeError):
                            config_dict['options'] = ['Token', 'Troubleshoot', 'Information', 'Other']
                    else:
                        config_dict['options'] = ['Token', 'Troubleshoot', 'Information', 'Other']
                elif config.key == 'backup.backup_day':
                    config_dict['input_type'] = 'select'
                    config_dict['options'] = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                elif config.key.endswith(('_port', '_size', '_days', '_hours', '_notifications', '_interval', '_backups')):
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
        'general': 'General Settings',
        'backup': 'Backup & Recovery Settings',
        'type': 'Artifact Types'
    }
    return section_titles.get(section, section.replace('_', ' ').title())

def get_section_icon(section):
    """Get Font Awesome icon for config sections"""
    section_icons = {
        'storage': 'fas fa-hard-drive',
        'sql_alchemy': 'fas fa-database',
        'trim': 'fas fa-eye',
        'email': 'fas fa-envelope',
        'general': 'fas fa-cog',
        'backup': 'fas fa-shield-alt',
        'type': 'fas fa-shapes'
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