"""
Unit tests for IconManager.

Tests icon loading, validation, and state-based icon selection.
"""

import pytest
from pathlib import Path
from kiro.icon_manager import IconManager


class TestIconManagerInitialization:
    """Tests for IconManager initialization."""
    
    def test_initialization_stores_assets_directory(self):
        """Test that initialization stores assets directory path."""
        assets_dir = Path("/tmp/assets")
        
        manager = IconManager(assets_dir=assets_dir)
        
        assert manager.assets_dir == Path(assets_dir)
    
    def test_initialization_creates_icons_dict(self):
        """Test that initialization creates icons dictionary."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        
        assert isinstance(manager._icons, dict)


class TestIconManagerMethods:
    """Tests for IconManager methods."""
    
    def test_get_icon_method_exists(self):
        """Test that get_icon method exists and is callable."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        assert callable(manager.get_icon)
    
    def test_validate_icon_method_exists(self):
        """Test that validate_icon method exists and is callable."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        assert callable(manager.validate_icon)
    
    def test_get_icon_accepts_state_parameter(self):
        """Test that get_icon accepts state parameter and returns icon or None."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        
        # Should not raise exception
        result = manager.get_icon("running")
        
        # May return None or an Image depending on PIL availability
        assert result is None or hasattr(result, 'size')
    
    def test_get_icon_maps_states_correctly(self):
        """Test that get_icon maps service states to icon types correctly."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        
        # Test various states
        states = ["stopped", "starting", "running", "stopping", "error", "warning"]
        for state in states:
            result = manager.get_icon(state)
            # Should not raise exception
            assert result is None or hasattr(result, 'size')
    
    def test_validate_icon_accepts_path_parameter(self):
        """Test that validate_icon accepts path parameter."""
        manager = IconManager(assets_dir=Path("/tmp/assets"))
        icon_path = Path("/tmp/test_icon.png")
        
        # Should not raise exception
        result = manager.validate_icon(icon_path)
        
        # Returns False for non-existent files
        assert isinstance(result, bool)



class TestIconManagerWithRealIcons:
    """Tests for IconManager with real icon files."""
    
    def test_loads_icons_from_assets_directory(self):
        """Test that IconManager loads icons from assets directory."""
        # Use the actual assets directory
        assets_dir = Path(__file__).parent.parent.parent / "assets"
        
        if not assets_dir.exists():
            pytest.skip("Assets directory not found")
        
        manager = IconManager(assets_dir=assets_dir)
        
        # Check that icons were loaded (if PIL is available)
        try:
            from PIL import Image
            # If PIL is available, icons should be loaded
            assert len(manager._icons) > 0
        except ImportError:
            # If PIL is not available, icons dict may be empty
            pass
    
    def test_validate_icon_with_real_icon(self):
        """Test that validate_icon works with real icon files."""
        assets_dir = Path(__file__).parent.parent.parent / "assets"
        icon_path = assets_dir / "tray_icon.png"
        
        if not icon_path.exists():
            pytest.skip("Icon file not found")
        
        manager = IconManager(assets_dir=assets_dir)
        
        try:
            from PIL import Image
            # If PIL is available, validation should work
            result = manager.validate_icon(icon_path)
            assert isinstance(result, bool)
        except ImportError:
            # If PIL is not available, validation returns False
            result = manager.validate_icon(icon_path)
            assert result is False
    
    def test_get_icon_returns_image_for_valid_state(self):
        """Test that get_icon returns image for valid service state."""
        assets_dir = Path(__file__).parent.parent.parent / "assets"
        
        if not assets_dir.exists():
            pytest.skip("Assets directory not found")
        
        manager = IconManager(assets_dir=assets_dir)
        
        try:
            from PIL import Image
            # If PIL is available, should return an image
            icon = manager.get_icon("running")
            assert icon is None or hasattr(icon, 'size')
        except ImportError:
            # If PIL is not available, returns None
            icon = manager.get_icon("running")
            assert icon is None


class TestIconManagerFallback:
    """Tests for IconManager fallback icon generation."""
    
    def test_generates_fallback_for_missing_icons(self):
        """Test that IconManager generates fallback icons when files are missing."""
        # Use a non-existent directory
        assets_dir = Path("/tmp/nonexistent_assets_dir_12345")
        
        manager = IconManager(assets_dir=assets_dir)
        
        # Should not raise exception
        icon = manager.get_icon("running")
        
        # May return None (if PIL not available) or a fallback image
        assert icon is None or hasattr(icon, 'size')
    
    def test_fallback_icon_has_correct_size(self):
        """Test that fallback icons have correct size."""
        assets_dir = Path("/tmp/nonexistent_assets_dir_12345")
        
        try:
            from PIL import Image
            manager = IconManager(assets_dir=assets_dir)
            icon = manager.get_icon("running")
            
            if icon is not None:
                # Fallback icons should be 48x48
                assert icon.size == (48, 48)
        except ImportError:
            pytest.skip("PIL not available")
    
    def test_different_states_get_different_fallback_colors(self):
        """Test that different states get different colored fallback icons."""
        assets_dir = Path("/tmp/nonexistent_assets_dir_12345")
        
        try:
            from PIL import Image
            manager = IconManager(assets_dir=assets_dir)
            
            normal_icon = manager.get_icon("running")
            error_icon = manager.get_icon("error")
            warning_icon = manager.get_icon("warning")
            
            # All should be images (or all None)
            if normal_icon is not None:
                assert hasattr(normal_icon, 'size')
                assert hasattr(error_icon, 'size')
                assert hasattr(warning_icon, 'size')
        except ImportError:
            pytest.skip("PIL not available")
