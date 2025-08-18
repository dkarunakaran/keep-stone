"""
Test configuration with environment-specific settings
"""

# Test environment configuration
TEST_DATABASE_URI = 'sqlite:///:memory:'
TEST_SECRET_KEY = 'test-secret-key-for-testing-only'
TEST_WTF_CSRF_ENABLED = False

# Test data paths
TEST_CONFIG_FILE = 'test_config.yaml'
TEST_DB_PATH = '/tmp/test_keepstone.db'
TEST_UPLOAD_PATH = '/tmp/test_uploads'
TEST_BACKUP_PATH = '/tmp/test_backups'

# Test configuration data
TEST_CONFIG = {
    'maintainer': 'Test Suite',
    'debug': True,
    'sql_alchemy': {
        'loc': {
            'value': '/tmp',
            'edit': False
        },
        'db': {
            'value': 'test.db',
            'edit': True
        }
    },
    'type': ['Token', 'Test', 'Debug'],
    'general': {
        'default_type': {
            'value': 'Token',
            'edit': True
        }
    },
    'trim': {
        'name': {
            'value': 10,
            'edit': True
        },
        'content': {
            'value': 50,
            'edit': True
        },
        'extra': {
            'value': 5,
            'edit': True
        }
    },
    'email': {
        'smtp_server': {
            'value': 'test.smtp.com',
            'edit': False
        },
        'smtp_port': {
            'value': 25,
            'edit': True
        },
        'notification_days': {
            'value': 5,
            'edit': True
        },
        'max_notifications': {
            'value': 2,
            'edit': True
        },
        'notification_interval': {
            'value': 12,
            'edit': True
        },
        'timezone': {
            'value': 'UTC',
            'edit': True
        }
    },
    'storage': {
        'image_path': {
            'value': 'test_uploads',
            'edit': False
        },
        'allowed_extensions': {
            'value': ['jpg', 'png', 'txt'],
            'edit': True
        },
        'max_file_size': {
            'value': 512000,
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
            'value': 1,
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
            'value': 'monday',
            'edit': True
        }
    }
}

# Test artifacts data
TEST_ARTIFACTS = [
    {
        'name': 'Test Token 1',
        'content': 'This is a test token for unit testing',
        'type_name': 'Token',
        'project_name': 'Default'
    },
    {
        'name': 'Test Debug Info',
        'content': 'Debug information for testing purposes',
        'type_name': 'Debug',
        'project_name': 'Test Project'
    },
    {
        'name': 'Sample Artifact',
        'content': 'Sample content with multiple lines\nLine 2\nLine 3',
        'type_name': 'Test',
        'project_name': 'Default'
    }
]

# Test projects data
TEST_PROJECTS = [
    {
        'name': 'Default',
        'description': 'Default project for testing',
        'is_default': True
    },
    {
        'name': 'Test Project',
        'description': 'Project created for testing purposes',
        'is_default': False
    },
    {
        'name': 'Sample Project',
        'description': 'Another test project',
        'is_default': False
    }
]

# Test types data
TEST_TYPES = [
    {'name': 'Token'},
    {'name': 'Test'},
    {'name': 'Debug'},
    {'name': 'Sample'}
]

# Expected editable config keys
EXPECTED_EDITABLE_KEYS = [
    'sql_alchemy.db',
    'general.default_type',
    'trim.name',
    'trim.content', 
    'trim.extra',
    'email.smtp_port',
    'email.notification_days',
    'email.max_notifications',
    'email.notification_interval',
    'email.timezone',
    'storage.allowed_extensions',
    'storage.max_file_size',
    'storage.cleanup_threshold_hours',
    'backup.enabled',
    'backup.keep_backups',
    'backup.backup_database',
    'backup.backup_images',
    'backup.backup_day'
]

# Expected non-editable config keys
EXPECTED_NON_EDITABLE_KEYS = [
    'sql_alchemy.loc',
    'email.smtp_server',
    'storage.image_path',
    'backup.backup_path'
]

# Test file content for image uploads
TEST_IMAGE_DATA = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'

# Test form data
TEST_FORM_DATA = {
    'add_artifact': {
        'name': 'Test Artifact',
        'content': 'Test content for artifact',
        'type_id': '1',
        'project_id': '1'
    },
    'add_project': {
        'name': 'New Test Project',
        'description': 'Description for new project'
    },
    'settings_update': {
        'general.default_type': 'Token',
        'trim.name': '20',
        'email.smtp_port': '587',
        'backup.enabled': 'true'
    }
}

# Mock response templates
MOCK_RESPONSES = {
    'index': {
        'status_code': 200,
        'content': 'KeepStone Dashboard'
    },
    'settings': {
        'status_code': 200,
        'content': 'Settings Configuration'
    },
    'projects': {
        'status_code': 200,
        'content': 'Project Management'
    },
    'add_artifact': {
        'status_code': 200,
        'content': 'Add New Artifact'
    }
}
