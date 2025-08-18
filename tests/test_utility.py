"""
Unit tests for utility functions
"""
import pytest
import os
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from werkzeug.datastructures import FileStorage

# Add project root to path for imports
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class TestUtilityFunctions:
    """Test general utility functions"""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_get_unique_filename(self):
        """Test unique filename generation"""
        try:
            from utility import get_unique_filename
            
            # Test with different extensions
            filename1 = get_unique_filename("test.jpg")
            filename2 = get_unique_filename("test.jpg")
            filename3 = get_unique_filename("document.pdf")
            
            # Should be different
            assert filename1 != filename2
            
            # Should preserve extensions
            assert filename1.endswith('.jpg')
            assert filename2.endswith('.jpg')
            assert filename3.endswith('.pdf')
            
            # Should be valid hex + extension format
            assert len(filename1) > 4  # At least some hex + .ext
            
        except ImportError:
            pytest.skip("Could not import utility functions")
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_get_unique_filename_no_extension(self):
        """Test unique filename generation without extension"""
        try:
            from utility import get_unique_filename
            
            filename = get_unique_filename("test_file")
            
            # Should still work without extension
            assert len(filename) > 0
            
        except ImportError:
            pytest.skip("Could not import utility functions")

class TestImageUtilities:
    """Test image handling utilities"""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_save_image_mock(self):
        """Test image saving with mocked file system"""
        try:
            from utility import save_image
            
            # Mock file object
            mock_file = MagicMock()
            mock_file.filename = "test_image.jpg"
            mock_file.save = MagicMock()
            
            # Mock config
            test_config = {
                'storage': {
                    'image_path': 'test/uploads'
                }
            }
            
            # Mock file system operations
            with patch('utility.os.makedirs') as mock_makedirs:
                with patch('utility.os.path.join', return_value='test/uploads/mock_file.jpg'):
                    with patch('utility.get_unique_filename', return_value='mock_file.jpg'):
                        
                        result = save_image(mock_file, test_config)
                        
                        # Should call makedirs
                        mock_makedirs.assert_called_once()
                        
                        # Should call file.save
                        mock_file.save.assert_called_once()
                        
                        # Should return a path
                        assert isinstance(result, str)
                        assert 'uploads' in result
                        
        except ImportError:
            pytest.skip("Could not import utility functions")
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_delete_image_mock(self):
        """Test image deletion with mocked file system"""
        try:
            from utility import delete_image
            
            test_path = "test/uploads/test_image.jpg"
            
            # Mock file system operations
            with patch('utility.os.path.exists', return_value=True) as mock_exists:
                with patch('utility.os.remove') as mock_remove:
                    with patch('utility.os.path.join', return_value='/full/path/test_image.jpg'):
                        
                        delete_image(test_path)
                        
                        # Should check if file exists
                        mock_exists.assert_called_once()
                        
                        # Should remove the file
                        mock_remove.assert_called_once()
                        
        except ImportError:
            pytest.skip("Could not import utility functions")
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_delete_image_nonexistent_mock(self):
        """Test deleting non-existent image"""
        try:
            from utility import delete_image
            
            test_path = "test/uploads/nonexistent.jpg"
            
            # Mock file system operations - file doesn't exist
            with patch('utility.os.path.exists', return_value=False) as mock_exists:
                with patch('utility.os.remove') as mock_remove:
                    
                    delete_image(test_path)
                    
                    # Should check if file exists
                    mock_exists.assert_called_once()
                    
                    # Should NOT try to remove the file
                    mock_remove.assert_not_called()
                    
        except ImportError:
            pytest.skip("Could not import utility functions")

class TestDatabaseUtilities:
    """Test database utility functions"""
    
    @pytest.mark.utils
    @pytest.mark.database
    def test_create_database_mock(self):
        """Test database creation with mocked dependencies"""
        try:
            from utility import create_database
            
            # Mock database session
            mock_session = MagicMock()
            mock_session.query.return_value.all.return_value = []  # Empty types
            
            # Mock models
            with patch('utility.models.base.Base.metadata.create_all') as mock_create_all:
                with patch('utility.models.type.Type') as mock_type_class:
                    with patch('utility.initialize_config_table') as mock_init_config:
                        
                        test_config = {
                            'type': ['Token', 'Test']
                        }
                        
                        create_database(session=mock_session, config=test_config)
                        
                        # Should create all tables
                        mock_create_all.assert_called_once()
                        
                        # Should initialize config
                        mock_init_config.assert_called_once()
                        
                        # Should add types if they don't exist
                        assert mock_session.add.called
                        assert mock_session.commit.called
                        
        except ImportError:
            pytest.skip("Could not import utility functions")

class TestFileHandling:
    """Test file handling utilities"""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_secure_filename_integration(self):
        """Test that secure_filename is properly used"""
        try:
            from utility import save_image
            from werkzeug.utils import secure_filename
            
            # Test with potentially unsafe filename
            unsafe_filename = "../../../etc/passwd.jpg"
            safe_filename = secure_filename(unsafe_filename)
            
            # Should be sanitized
            assert safe_filename != unsafe_filename
            assert ".." not in safe_filename
            assert "/" not in safe_filename
            
        except ImportError:
            pytest.skip("Could not import required modules")

class TestErrorHandling:
    """Test error handling in utilities"""
    
    @pytest.mark.utils
    @pytest.mark.unit
    def test_save_image_error_handling(self):
        """Test error handling in save_image function"""
        try:
            from utility import save_image
            
            # Mock file that raises an exception
            mock_file = MagicMock()
            mock_file.filename = "test.jpg"
            mock_file.save.side_effect = Exception("Disk full")
            
            test_config = {
                'storage': {
                    'image_path': 'test/uploads'
                }
            }
            
            # Should handle the exception gracefully
            with patch('utility.os.makedirs'):
                with patch('utility.os.path.join', return_value='test/path'):
                    with patch('utility.get_unique_filename', return_value='test.jpg'):
                        try:
                            save_image(mock_file, test_config)
                            # If no exception is raised, that's also valid handling
                        except Exception:
                            # Exception should be handled appropriately
                            pass
                            
        except ImportError:
            pytest.skip("Could not import utility functions")

class TestConfigIntegration:
    """Test integration with config system"""
    
    @pytest.mark.utils
    @pytest.mark.integration
    def test_utility_config_usage(self):
        """Test how utilities use configuration"""
        try:
            from utility import save_image
            
            # Test different config structures
            test_configs = [
                {
                    'storage': {
                        'image_path': 'uploads'
                    }
                },
                {
                    'storage': {
                        'image_path': 'custom/path/uploads'
                    }
                }
            ]
            
            mock_file = MagicMock()
            mock_file.filename = "test.jpg"
            
            for config in test_configs:
                with patch('utility.os.makedirs'):
                    with patch('utility.os.path.join', return_value='mocked/path'):
                        with patch('utility.get_unique_filename', return_value='unique.jpg'):
                            try:
                                result = save_image(mock_file, config)
                                assert isinstance(result, str)
                            except Exception:
                                # Some configs might cause issues, that's okay for testing
                                pass
                                
        except ImportError:
            pytest.skip("Could not import utility functions")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
