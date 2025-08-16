import json
from sqlalchemy.orm import sessionmaker
from models.base import engine
from models.project_config import ProjectConfig
from models.project import Project
from utils.config_utils import load_config_from_yaml, flatten_dict, generate_config_description, generate_config_title

Session = sessionmaker(bind=engine)

def get_project_level_config_keys():
    """Get list of configuration keys that should be managed at project level"""
    yaml_config = load_config_from_yaml()
    flat_config = flatten_dict(yaml_config)
    
    project_level_keys = []
    for key, value, is_editable in flat_config:
        # Check if this config has project_settings: True
        if isinstance(value, dict) and value.get('project_settings', False):
            project_level_keys.append(key)
        elif key in yaml_config and isinstance(yaml_config[key], dict) and yaml_config[key].get('project_settings', False):
            project_level_keys.append(key)
    
    return project_level_keys

def initialize_project_configs(project_id):
    """Initialize project configurations with default values"""
    session = Session()
    try:
        project = session.query(Project).get(project_id)
        if not project:
            return False
        
        # Get project-level config keys
        project_keys = get_project_level_config_keys()
        yaml_config = load_config_from_yaml()
        
        for key in project_keys:
            # Check if config already exists for this project
            existing = session.query(ProjectConfig).filter_by(
                project_id=project_id,
                key=key
            ).first()
            
            if not existing:
                # Get default value from YAML
                default_value = None
                if '.' in key:
                    # Nested key like 'general.other_setting'
                    parts = key.split('.')
                    value = yaml_config
                    for part in parts:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            value = None
                            break
                    if isinstance(value, dict) and 'value' in value:
                        default_value = value['value']
                else:
                    # Top-level key like 'type'
                    if key in yaml_config and isinstance(yaml_config[key], dict) and 'value' in yaml_config[key]:
                        default_value = yaml_config[key]['value']
                
                if default_value is not None:
                    config_item = ProjectConfig(
                        project_id=project_id,
                        key=key,
                        value=json.dumps(default_value) if isinstance(default_value, (list, dict)) else str(default_value),
                        description=generate_config_description(key)
                    )
                    session.add(config_item)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing project configs: {e}")
        return False
    finally:
        session.close()

def get_project_config(project_id, key, default=None):
    """Get a specific configuration value for a project"""
    session = Session()
    try:
        config = session.query(ProjectConfig).filter_by(
            project_id=project_id,
            key=key
        ).first()
        
        if config:
            return config.get_parsed_value()
        return default
        
    except Exception as e:
        print(f"Error getting project config: {e}")
        return default
    finally:
        session.close()

def update_project_config(project_id, key, value):
    """Update a project configuration value"""
    session = Session()
    try:
        config = session.query(ProjectConfig).filter_by(
            project_id=project_id,
            key=key
        ).first()
        
        if config:
            config.set_value(value)
        else:
            # Create new config item
            config = ProjectConfig(
                project_id=project_id,
                key=key,
                description=generate_config_description(key)
            )
            config.set_value(value)
            session.add(config)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error updating project config: {e}")
        return False
    finally:
        session.close()

def get_project_configs_for_settings(project_id):
    """Get all project configurations for settings page display"""
    session = Session()
    try:
        configs = session.query(ProjectConfig).filter_by(project_id=project_id).order_by(ProjectConfig.key).all()
        
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
            
            # Add title and parsed value
            config_dict = {
                'key': config.key,
                'value': config.value,
                'description': config.description,
                'title': generate_config_title(config.key),
                'section': section,
                'editable': True  # All project configs are editable
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
                    # Get options from the project's type configuration
                    type_config = session.query(ProjectConfig).filter_by(
                        project_id=project_id, 
                        key='type'
                    ).first()
                    if type_config:
                        try:
                            type_options = json.loads(type_config.value)
                            config_dict['options'] = type_options if isinstance(type_options, list) else ['Token', 'Troubleshoot', 'Information', 'Other']
                        except (json.JSONDecodeError, TypeError):
                            config_dict['options'] = ['Token', 'Troubleshoot', 'Information', 'Other']
                    else:
                        config_dict['options'] = ['Token', 'Troubleshoot', 'Information', 'Other']
                elif config.value.lower() in ('true', 'false'):
                    config_dict['input_type'] = 'boolean'
                else:
                    config_dict['input_type'] = 'text'
            
            grouped_configs[section].append(config_dict)
        
        return grouped_configs
        
    except Exception as e:
        print(f"Error getting project configs for settings: {e}")
        return {}
    finally:
        session.close()
