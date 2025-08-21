"""
Tool utilities for managing project tools
"""

from models.base import engine
from models.project_config import ProjectConfig
from models.tool import Tool
from sqlalchemy.orm import sessionmaker
from utils.config_utils import load_config_from_yaml

Session = sessionmaker(bind=engine)

def initialize_tools_table():
    """Initialize the tools table from config.yaml if it's empty"""
    session = Session()
    try:
        # Check if tools table is empty
        existing_tools = session.query(Tool).count()
        if existing_tools > 0:
            return True  # Already initialized
        
        # Load config from YAML
        yaml_config = load_config_from_yaml()
        tools_config = yaml_config.get('tools', {})
        
        # Add tools to the tools table
        for tool_key, tool_data in tools_config.items():
            # Skip the project_settings flag
            if tool_key == 'project_settings':
                continue
                
            if isinstance(tool_data, dict):
                # Create tool entry
                description = 'Conversion tool'
                if isinstance(tool_data, dict) and 'description' in tool_data:
                    description = tool_data['description']
                
                tool = Tool(
                    name=tool_key,
                    display_name=get_tool_display_name(tool_key),
                    description=description,
                    icon=get_tool_icon(tool_key),
                    url=f'/tools/{tool_key}',
                    enabled=True  # All tools are available by default
                )
                session.add(tool)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing tools table: {e}")
        return False
    finally:
        session.close()

def get_available_tools():
    """Get all available tools from the tools table"""
    session = Session()
    try:
        # Ensure tools table is initialized
        initialize_tools_table()
        
        tools = session.query(Tool).filter(Tool.enabled == True).all()
        return [{
            'name': tool.name,
            'display_name': tool.display_name,
            'description': tool.description,
            'icon': tool.icon,
            'url': tool.url
        } for tool in tools]
        
    except Exception as e:
        print(f"Error getting available tools: {e}")
        return []
    finally:
        session.close()

def initialize_project_tools(project_id):
    """Initialize project tools from tools table if they don't exist in project_config"""
    session = Session()
    try:
        # Ensure tools table is initialized
        initialize_tools_table()
        
        # Get all available tools from tools table
        available_tools = session.query(Tool).filter(Tool.enabled == True).all()
        
        # Check existing tool configs for this project
        existing_configs = session.query(ProjectConfig).filter(
            ProjectConfig.project_id == project_id,
            ProjectConfig.key.like('tools.%')
        ).all()
        
        existing_keys = {config.key for config in existing_configs}
        
        # Add missing tool configs from tools table (disabled by default)
        for tool in available_tools:
            db_key = f'tools.{tool.name}'
            
            if db_key not in existing_keys:
                new_config = ProjectConfig(
                    project_id=project_id,
                    key=db_key,
                    value='false',  # Disabled by default
                    description=f'Enable {tool.display_name} tool'
                )
                session.add(new_config)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error initializing project tools: {e}")
        return False
    finally:
        session.close()

def get_enabled_tools(project_id):
    """Get list of enabled tools for a project"""
    session = Session()
    try:
        enabled_tools = []
        
        # Get all available tools from tools table
        available_tools = session.query(Tool).filter(Tool.enabled == True).all()
        
        # Get project-specific tool configurations
        tool_configs = session.query(ProjectConfig).filter(
            ProjectConfig.project_id == project_id,
            ProjectConfig.key.like('tools.%')
        ).all()
        
        # Create a map of enabled tools for this project
        enabled_map = {}
        for config in tool_configs:
            tool_name = config.key.replace('tools.', '')
            enabled_map[tool_name] = config.value and config.value.lower() == 'true'
        
        # Return only tools that are both available and enabled for this project
        for tool in available_tools:
            if enabled_map.get(tool.name, False):
                enabled_tools.append({
                    'name': tool.name,
                    'display_name': tool.display_name,
                    'icon': tool.icon,
                    'url': tool.url
                })
        
        return enabled_tools
        
    except Exception as e:
        print(f"Error getting enabled tools: {e}")
        return []
    finally:
        session.close()

def get_tool_display_name(tool_name):
    """Get display name for a tool"""
    tool_names = {
        'json_to_csv': 'JSON to CSV',
        'csv_to_json': 'CSV to JSON'
    }
    return tool_names.get(tool_name, tool_name.replace('_', ' ').title())

def get_tool_icon(tool_name):
    """Get icon for a tool"""
    tool_icons = {
        'json_to_csv': 'fas fa-file-code',
        'csv_to_json': 'fas fa-file-csv'
    }
    return tool_icons.get(tool_name, 'fas fa-tools')

def save_project_tools(project_id, selected_tools):
    """Save selected tools for a project"""
    session = Session()
    try:
        # First, ensure tools are initialized
        initialize_project_tools(project_id)
        
        # Get all existing tool configs
        existing_configs = session.query(ProjectConfig).filter(
            ProjectConfig.project_id == project_id,
            ProjectConfig.key.like('tools.%')
        ).all()
        
        # Create a map of existing configs
        config_map = {config.key: config for config in existing_configs}
        
        # Get available tools from config.yaml
        yaml_config = load_config_from_yaml()
        tools_config = yaml_config.get('tools', {})
        available_tools = [key for key in tools_config.keys() if key != 'project_settings']
        
        for tool_name in available_tools:
            key = f'tools.{tool_name}'
            is_selected = tool_name in selected_tools
            
            if key in config_map:
                # Update existing config
                config_map[key].value = 'true' if is_selected else 'false'
            else:
                # Create new config (shouldn't happen after initialization, but just in case)
                new_config = ProjectConfig(
                    project_id=project_id,
                    key=key,
                    value='true' if is_selected else 'false',
                    description=f'Enable {tool_name.replace("_", " ").title()} tool'
                )
                session.add(new_config)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"Error saving project tools: {e}")
        return False
    finally:
        session.close()

def get_project_tools_for_settings(project_id):
    """Get all tools with their current enabled/disabled status for project settings"""
    session = Session()
    try:
        # Ensure tools are initialized for this project
        initialize_project_tools(project_id)
        
        # Get all available tools
        available_tools = session.query(Tool).filter(Tool.enabled == True).all()
        
        # Get current project tool configurations
        tool_configs = session.query(ProjectConfig).filter(
            ProjectConfig.project_id == project_id,
            ProjectConfig.key.like('tools.%')
        ).all()
        
        # Create a map of current settings
        settings_map = {}
        for config in tool_configs:
            tool_name = config.key.replace('tools.', '')
            settings_map[tool_name] = {
                'enabled': config.value and config.value.lower() == 'true',
                'config': config
            }
        
        # Build the result
        tools_for_settings = []
        for tool in available_tools:
            tool_setting = settings_map.get(tool.name, {'enabled': False, 'config': None})
            tools_for_settings.append({
                'name': tool.name,
                'display_name': tool.display_name,
                'description': tool.description,
                'enabled': tool_setting['enabled'],
                'key': f'tools.{tool.name}'
            })
        
        return tools_for_settings
        
    except Exception as e:
        print(f"Error getting project tools for settings: {e}")
        return []
    finally:
        session.close()
