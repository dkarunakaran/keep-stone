"""
Test configuration and fixtures for KeepStone application
"""
import os
import tempfile
import pytest
from unittest.mock import patch
import yaml

# Set test environment
os.environ['TESTING'] = 'True'
os.environ['FLASK_ENV'] = 'testing'

@pytest.fixture(scope="session")
def test_config():
    """Create test configuration"""
    return {
        'maintainer': 'Test User',
        'debug': True,
        'sql_alchemy': {
            'loc': {
                'value': '/tmp/test_db',
                'edit': False
            },
            'db': {
                'value': 'test.db',
                'edit': True
            }
        },
        'type': ['Token', 'Troubleshoot', 'Information', 'Other'],
        'general': {
            'default_type': {
                'value': 'Token',
                'edit': True
            }
        },
        'trim': {
            'name': {
                'value': 15,
                'edit': True
            },
            'content': {
                'value': 100,
                'edit': True
            },
            'extra': {
                'value': 7,
                'edit': True
            }
        },
        'email': {
            'smtp_server': {
                'value': 'smtp.test.com',
                'edit': False
            },
            'smtp_port': {
                'value': 587,
                'edit': True
            },
            'notification_days': {
                'value': 10,
                'edit': True
            },
            'max_notifications': {
                'value': 3,
                'edit': True
            },
            'notification_interval': {
                'value': 24,
                'edit': True
            },
            'timezone': {
                'value': 'UTC',
                'edit': True
            }
        },
        'storage': {
            'image_path': {
                'value': 'test/uploads',
                'edit': False
            },
            'allowed_extensions': {
                'value': ['jpg', 'png'],
                'edit': True
            },
            'max_file_size': {
                'value': 1048576,
                'edit': True
            },
            'cleanup_threshold_hours': {
                'value': 1,
                'edit': True
            }
        },
        'backup': {
            'enabled': {
                'value': False,
                'edit': True
            },
            'backup_path': {
                'value': '/tmp/test_backups',
                'edit': False
            },
            'keep_backups': {
                'value': 2,
                'edit': True
            },
            'backup_database': {
                'value': True,
                'edit': True
            },
            'backup_images': {
                'value': False,
                'edit': True
            },
            'backup_day': {
                'value': 'sunday',
                'edit': True
            }
        }
    }

@pytest.fixture(scope="session")
def temp_config_file(test_config):
    """Create temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture(scope="function")
def mock_config_file(temp_config_file):
    """Mock the config file path for tests"""
    with patch('utils.config_utils.load_config_from_yaml') as mock_load:
        with open(temp_config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        mock_load.return_value = config_data
        yield mock_load

@pytest.fixture(scope="session")
def app():
    """Create test Flask application"""
    # Import here to avoid circular imports
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Mock the config file loading before importing the app
    with patch('models.base.open', create=True) as mock_open:
        # Create a mock config that returns test values
        mock_config_content = """
maintainer: Test User
debug: True
sql_alchemy:
  loc: 
    value: '/tmp/test_db'
    edit: False
  db: 
    value: 'test.db'
    edit: True
type: 
  - 'Token'
  - 'Test'
"""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_config_content
        
        try:
            from app import app as flask_app
            
            # Configure for testing
            flask_app.config.update({
                'TESTING': True,
                'WTF_CSRF_ENABLED': False,
                'SECRET_KEY': 'test-secret-key',
                'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            })
            
            yield flask_app
            
        except ImportError as e:
            pytest.skip(f"Could not import app: {e}")

@pytest.fixture(scope="function")
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope="function") 
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
