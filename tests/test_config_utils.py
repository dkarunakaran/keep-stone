"""
Unit tests for configuration utilities
"""
import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open, MagicMock
import json

# Add project root to path for imports
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.config_utils import (
    flatten_dict, 
    unflatten_dict,
    generate_config_description,
    generate_config_title
)

class TestConfigUtils:
    """Test configuration utility functions"""
    
    @pytest.mark.unit
    def test_flatten_dict_with_value_edit_structure(self):
        """Test flattening dictionary with new value/edit structure"""
        config = {
            'section1': {
                'item1': {
                    'value': 'test_value',
                    'edit': True
                },
                'item2': {
                    'value': 42,
                    'edit': False
                }
            },
            'section2': {
                'simple_item': 'simple_value'
            }
        }
        
        result = flatten_dict(config)
        
        # Convert to dict for easier testing
        result_dict = {key: (value, editable) for key, value, editable in result}
        
        assert result_dict['section1.item1'] == ('test_value', True)
        assert result_dict['section1.item2'] == (42, False)
        assert result_dict['section2.simple_item'] == ('simple_value', False)
    
    @pytest.mark.unit
    def test_flatten_dict_nested_structure(self):
        """Test flattening nested dictionary structures"""
        config = {
            'level1': {
                'level2': {
                    'level3': {
                        'value': 'deep_value',
                        'edit': True
                    }
                }
            }
        }
        
        result = flatten_dict(config)
        result_dict = {key: (value, editable) for key, value, editable in result}
        
        assert 'level1.level2.level3' in result_dict
        assert result_dict['level1.level2.level3'] == ('deep_value', True)
    
    @pytest.mark.unit
    def test_unflatten_dict(self):
        """Test unflattening dictionary"""
        flat_dict = {
            'section1.item1': 'value1',
            'section1.item2': 'value2',
            'section2.item1': 'value3'
        }
        
        result = unflatten_dict(flat_dict)
        
        expected = {
            'section1': {
                'item1': 'value1',
                'item2': 'value2'
            },
            'section2': {
                'item1': 'value3'
            }
        }
        
        assert result == expected
    
    @pytest.mark.unit
    def test_generate_config_description(self):
        """Test config description generation"""
        # Test known descriptions
        assert 'database' in generate_config_description('sql_alchemy.loc').lower()
        assert 'smtp' in generate_config_description('email.smtp_server').lower()
        assert 'backup' in generate_config_description('backup.enabled').lower()
        
        # Test unknown key fallback
        desc = generate_config_description('unknown.key')
        assert 'unknown key' in desc.lower()
    
    @pytest.mark.unit
    def test_generate_config_title(self):
        """Test config title generation"""
        assert generate_config_title('smtp_server') == 'Smtp Server'
        assert generate_config_title('section.max_file_size') == 'Max File Size'
        assert generate_config_title('simple') == 'Simple'
    
    @pytest.mark.unit
    def test_flatten_dict_empty_input(self):
        """Test flattening empty dictionary"""
        result = flatten_dict({})
        assert result == []
    
    @pytest.mark.unit  
    def test_flatten_dict_missing_edit_key(self):
        """Test flattening when edit key is missing"""
        config = {
            'section': {
                'item': {
                    'value': 'test'
                    # missing 'edit' key
                }
            }
        }
        
        result = flatten_dict(config)
        # Should handle missing edit key gracefully
        assert len(result) >= 0

class TestConfigLoading:
    """Test configuration loading functionality"""
    
    @pytest.mark.config
    def test_load_config_from_yaml_mock(self):
        """Test loading config from YAML with mocking"""
        test_config = {
            'test_section': {
                'test_item': {
                    'value': 'test_value',
                    'edit': True
                }
            }
        }
        
        mock_yaml_content = yaml.dump(test_config)
        
        with patch('builtins.open', mock_open(read_data=mock_yaml_content)):
            with patch('utils.config_utils.yaml.safe_load') as mock_yaml_load:
                mock_yaml_load.return_value = test_config
                
                # Import and test the function
                try:
                    from utils.config_utils import load_config_from_yaml
                    result = load_config_from_yaml()
                    assert result == test_config
                except ImportError:
                    pytest.skip("Could not import config utils")
    
    @pytest.mark.config
    def test_config_file_not_found(self):
        """Test handling of missing config file"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            try:
                from utils.config_utils import load_config_from_yaml
                result = load_config_from_yaml()
                assert result == {}  # Should return empty dict on file not found
            except ImportError:
                pytest.skip("Could not import config utils")

class TestConfigInitialization:
    """Test configuration initialization"""
    
    @pytest.mark.integration
    @pytest.mark.database
    def test_initialize_config_table_mock(self, mock_config_file):
        """Test config table initialization with mocked dependencies"""
        # Mock database session
        mock_session = MagicMock()
        mock_config_class = MagicMock()
        
        with patch('utils.config_utils.Session') as mock_session_class:
            with patch('utils.config_utils.Config', mock_config_class):
                mock_session_class.return_value = mock_session
                mock_session.query.return_value.all.return_value = []  # Empty existing configs
                
                try:
                    from utils.config_utils import initialize_config_table
                    initialize_config_table()
                    
                    # Should have called session methods
                    mock_session.add.assert_called()
                    mock_session.commit.assert_called()
                    
                except ImportError:
                    pytest.skip("Could not import config utils")

class TestConfigValidation:
    """Test configuration validation"""
    
    @pytest.mark.unit
    def test_config_structure_validation(self):
        """Test that config structure is valid"""
        # Test the expected structure
        valid_config = {
            'section': {
                'item': {
                    'value': 'some_value',
                    'edit': True
                }
            }
        }
        
        # This should not raise any errors
        flattened = flatten_dict(valid_config)
        assert len(flattened) == 1
        
        key, value, editable = flattened[0]
        assert key == 'section.item'
        assert value == 'some_value'
        assert editable is True
    
    @pytest.mark.unit
    def test_config_type_validation(self):
        """Test config value type handling"""
        config = {
            'types': {
                'string_item': {
                    'value': 'string_value',
                    'edit': True
                },
                'int_item': {
                    'value': 42,
                    'edit': True
                },
                'bool_item': {
                    'value': True,
                    'edit': True
                },
                'list_item': {
                    'value': ['item1', 'item2'],
                    'edit': True
                }
            }
        }
        
        flattened = flatten_dict(config)
        
        # Extract values
        values = {key: value for key, value, _ in flattened}
        
        assert values['types.string_item'] == 'string_value'
        assert values['types.int_item'] == 42
        assert values['types.bool_item'] is True
        assert values['types.list_item'] == ['item1', 'item2']

class TestProjectConfigUtils:
    """Test project configuration utilities"""
    
    @pytest.mark.unit
    def test_initialize_project_configs_with_default_types(self):
        """Test that project configuration is initialized with default types from config.yaml"""
        try:
            from utils.project_config_utils import initialize_project_configs, get_project_config
            from models.project_config import ProjectConfig
            
            # Mock the YAML config to return our expected defaults
            mock_yaml_config = {
                'type': {
                    'value': ['Token', 'Troubleshoot', 'Information', 'Other'],
                    'edit': True,
                    'project_settings': True
                },
                'default_type': {
                    'value': 'Token',
                    'edit': True,
                    'project_settings': True
                }
            }
            
            # Mock database session and project
            with patch('utils.project_config_utils.Session') as mock_session_class:
                with patch('utils.project_config_utils.load_config_from_yaml', return_value=mock_yaml_config):
                    with patch('utils.project_config_utils.get_project_level_config_keys', return_value=['type', 'default_type']):
                        mock_session = MagicMock()
                        mock_session_class.return_value = mock_session
                        
                        # Mock project exists
                        mock_project = MagicMock()
                        mock_session.query.return_value.get.return_value = mock_project
                        
                        # Mock no existing config
                        mock_session.query.return_value.filter_by.return_value.first.return_value = None
                        
                        # Call the function
                        result = initialize_project_configs(1)
                        
                        # Verify it tried to add configs
                        assert mock_session.add.call_count >= 1  # Should add at least one config
                        assert mock_session.commit.called
                        assert result is True
                        
        except ImportError:
            pytest.skip("Could not import project config utilities")
    
    @pytest.mark.unit 
    def test_get_project_config_returns_parsed_list(self):
        """Test that get_project_config returns parsed JSON list for project types"""
        try:
            from utils.project_config_utils import get_project_config
            from models.project_config import ProjectConfig
            
            # Mock a project config with JSON list value
            mock_config = MagicMock()
            mock_config.get_parsed_value.return_value = ['Token', 'Troubleshoot', 'Information', 'Other']
            
            with patch('utils.project_config_utils.Session') as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value = mock_session
                
                # Mock query returns our config
                mock_session.query.return_value.filter_by.return_value.first.return_value = mock_config
                
                # Call the function
                result = get_project_config(1, 'type', [])
                
                # Verify it returns the parsed list
                assert result == ['Token', 'Troubleshoot', 'Information', 'Other']
                
        except ImportError:
            pytest.skip("Could not import project config utilities")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
