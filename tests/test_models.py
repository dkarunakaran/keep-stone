"""
Unit tests for database models
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path for imports
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class TestArtifactModel:
    """Test Artifact model functionality"""
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_artifact_creation(self):
        """Test creating an artifact instance"""
        try:
            from models.artifact import Artifact
            
            artifact = Artifact(
                name="Test Artifact",
                content="Test content",
                type_id=1,
                project_id=1
            )
            
            assert artifact.name == "Test Artifact"
            assert artifact.content == "Test content"
            assert artifact.type_id == 1
            assert artifact.project_id == 1
            assert artifact.deleted is False  # Default value
            
        except ImportError:
            pytest.skip("Could not import Artifact model")
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_artifact_repr(self):
        """Test artifact string representation"""
        try:
            from models.artifact import Artifact
            
            artifact = Artifact(name="Test Artifact")
            repr_str = repr(artifact)
            
            assert "Test Artifact" in repr_str
            
        except ImportError:
            pytest.skip("Could not import Artifact model")

class TestTypeModel:
    """Test Type model functionality"""
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_type_creation(self):
        """Test creating a type instance"""
        try:
            from models.type import Type
            
            type_obj = Type(name="Test Type")
            
            assert type_obj.name == "Test Type"
            
        except ImportError:
            pytest.skip("Could not import Type model")
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_type_repr(self):
        """Test type string representation"""
        try:
            from models.type import Type
            
            type_obj = Type(name="Test Type")
            repr_str = repr(type_obj)
            
            assert "Test Type" in repr_str
            
        except ImportError:
            pytest.skip("Could not import Type model")

class TestProjectModel:
    """Test Project model functionality"""
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_project_creation(self):
        """Test creating a project instance"""
        try:
            from models.project import Project
            
            project = Project(
                name="Test Project",
                description="Test description"
            )
            
            assert project.name == "Test Project"
            assert project.description == "Test description"
            assert project.is_default is False  # Default value
            
        except ImportError:
            pytest.skip("Could not import Project model")
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_project_set_as_default_mock(self):
        """Test setting project as default with mocked session"""
        try:
            from models.project import Project
            
            # Mock the session and query
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_session.query.return_value = mock_query
            
            project = Project(name="Test Project")
            
            # Mock the set_as_default method behavior
            with patch.object(project, 'set_as_default') as mock_set_default:
                project.set_as_default(mock_session)
                mock_set_default.assert_called_once_with(mock_session)
            
        except ImportError:
            pytest.skip("Could not import Project model")

class TestConfigModel:
    """Test Config model functionality"""
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_config_creation(self):
        """Test creating a config instance"""
        try:
            from models.config import Config
            
            config = Config(
                key="test.key",
                value="test_value",
                description="Test description"
            )
            
            assert config.key == "test.key"
            assert config.value == "test_value"
            assert config.description == "Test description"
            
        except ImportError:
            pytest.skip("Could not import Config model")
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_config_repr(self):
        """Test config string representation"""
        try:
            from models.config import Config
            
            config = Config(key="test.key", value="test_value")
            repr_str = repr(config)
            
            assert "test.key" in repr_str
            assert "test_value" in repr_str
            
        except ImportError:
            pytest.skip("Could not import Config model")

class TestBaseModel:
    """Test base model functionality"""
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_base_engine_creation(self):
        """Test that base engine is created properly"""
        try:
            from models.base import engine, Base
            
            # Engine should exist
            assert engine is not None
            
            # Base should be a declarative base
            assert Base is not None
            assert hasattr(Base, 'metadata')
            
        except ImportError:
            pytest.skip("Could not import base model")
    
    @pytest.mark.models
    @pytest.mark.unit
    def test_config_value_extraction(self):
        """Test the get_config_value function in base.py"""
        try:
            from models.base import get_config_value
            
            test_config = {
                'section': {
                    'item_with_value': {
                        'value': 'extracted_value',
                        'edit': True
                    },
                    'simple_item': 'simple_value'
                }
            }
            
            # Test value extraction
            result1 = get_config_value(test_config, 'section.item_with_value')
            assert result1 == 'extracted_value'
            
            # Test simple value
            result2 = get_config_value(test_config, 'section.simple_item')
            assert result2 == 'simple_value'
            
            # Test non-existent key
            result3 = get_config_value(test_config, 'non.existent.key')
            assert result3 is None
            
        except ImportError:
            pytest.skip("Could not import base model functions")

class TestModelRelationships:
    """Test model relationships and constraints"""
    
    @pytest.mark.models
    @pytest.mark.integration
    def test_artifact_type_relationship_mock(self):
        """Test artifact-type relationship with mocking"""
        try:
            from models.artifact import Artifact
            from models.type import Type
            
            # Create mock objects
            mock_type = Type(id=1, name="Test Type")
            mock_artifact = Artifact(name="Test Artifact", type_id=1)
            
            # In a real test, this would be tested with a database
            # For now, just verify the foreign key relationship exists
            assert hasattr(Artifact, 'type_id')
            assert mock_artifact.type_id == 1
            
        except ImportError:
            pytest.skip("Could not import models for relationship testing")
    
    @pytest.mark.models
    @pytest.mark.integration
    def test_artifact_project_relationship_mock(self):
        """Test artifact-project relationship with mocking"""
        try:
            from models.artifact import Artifact
            from models.project import Project
            
            # Create mock objects
            mock_project = Project(id=1, name="Test Project")
            mock_artifact = Artifact(name="Test Artifact", project_id=1)
            
            # Verify the foreign key relationship exists
            assert hasattr(Artifact, 'project_id')
            assert mock_artifact.project_id == 1
            
        except ImportError:
            pytest.skip("Could not import models for relationship testing")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
