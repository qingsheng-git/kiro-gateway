"""
Icon Manager for system tray icon assets.

This module manages tray icon assets for different service states,
validates icon format and dimensions, and provides fallback icons.
"""

from pathlib import Path
from typing import Optional, Dict
from loguru import logger

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not available - icon management disabled")


class IconManager:
    """
    Manages tray icon assets and states.
    
    Loads icon files for different service states (normal, warning, error),
    validates icon format and dimensions, and provides PIL Image objects for pystray.
    """
    
    def __init__(self, assets_dir: Path):
        """
        Initialize icon manager with assets directory.
        
        Args:
            assets_dir: Path to directory containing icon files
        """
        self.assets_dir = Path(assets_dir)
        self._icons: Dict[str, Optional[Image.Image]] = {}
        self._load_icons()
        logger.info(f"IconManager initialized with assets_dir: {assets_dir}")
    
    def _load_icons(self) -> None:
        """Load all icon files from assets directory."""
        if not PIL_AVAILABLE:
            logger.warning("Pillow not available - cannot load icons")
            return
        
        icon_files = {
            "normal": "tray_icon.png",
            "warning": "tray_icon_warning.png",
            "error": "tray_icon_error.png"
        }
        
        for state, filename in icon_files.items():
            icon_path = self.assets_dir / filename
            if icon_path.exists():
                try:
                    if self.validate_icon(icon_path):
                        self._icons[state] = Image.open(icon_path)
                        logger.info(f"Loaded icon for state '{state}': {filename}")
                    else:
                        logger.warning(f"Icon validation failed for '{state}': {filename}")
                        self._icons[state] = self._generate_fallback_icon(state)
                except Exception as e:
                    logger.error(f"Failed to load icon '{filename}': {e}")
                    self._icons[state] = self._generate_fallback_icon(state)
            else:
                logger.warning(f"Icon file not found: {icon_path}, using fallback")
                self._icons[state] = self._generate_fallback_icon(state)
    
    def get_icon(self, state: str) -> Optional[Image.Image]:
        """
        Get icon for given service state.
        
        Args:
            state: Service state name (e.g., "stopped", "running", "error", "warning")
        
        Returns:
            PIL Image object for the icon, or None if not available
        """
        if not PIL_AVAILABLE:
            logger.debug("Pillow not available - cannot get icon")
            return None
        
        # Map service states to icon types
        state_mapping = {
            "stopped": "normal",
            "starting": "normal",
            "running": "normal",
            "stopping": "normal",
            "error": "error",
            "warning": "warning"
        }
        
        icon_type = state_mapping.get(state.lower(), "normal")
        icon = self._icons.get(icon_type)
        
        if icon is None:
            logger.warning(f"No icon available for state '{state}', generating fallback")
            icon = self._generate_fallback_icon(icon_type)
            self._icons[icon_type] = icon
        
        logger.debug(f"Retrieved icon for state: {state} (type: {icon_type})")
        return icon
    
    def validate_icon(self, icon_path: Path) -> bool:
        """
        Validate icon format and dimensions.
        
        Args:
            icon_path: Path to icon file
        
        Returns:
            True if valid, False otherwise
        """
        if not PIL_AVAILABLE:
            logger.debug("Pillow not available - cannot validate icon")
            return False
        
        try:
            with Image.open(icon_path) as img:
                # Check format (PNG or ICO)
                if img.format not in ['PNG', 'ICO']:
                    logger.warning(f"Invalid icon format: {img.format} (expected PNG or ICO)")
                    return False
                
                # Check minimum dimensions (16x16)
                width, height = img.size
                if width < 16 or height < 16:
                    logger.warning(f"Icon too small: {width}x{height} (minimum 16x16)")
                    return False
                
                logger.debug(f"Icon validation passed: {icon_path} ({width}x{height}, {img.format})")
                return True
        except Exception as e:
            logger.error(f"Icon validation failed for {icon_path}: {e}")
            return False

    def _generate_fallback_icon(self, icon_type: str) -> Optional[Image.Image]:
        """
        Generate a simple colored square as fallback icon.
        
        Args:
            icon_type: Type of icon ("normal", "warning", "error")
        
        Returns:
            PIL Image object with colored square, or None if PIL not available
        """
        if not PIL_AVAILABLE:
            return None
        
        # Define colors for different states
        colors = {
            "normal": (0, 120, 212),    # Blue
            "warning": (255, 185, 0),   # Orange/Yellow
            "error": (232, 17, 35)      # Red
        }
        
        color = colors.get(icon_type, colors["normal"])
        
        # Create a 48x48 colored square
        size = 48
        img = Image.new('RGB', (size, size), color)
        
        logger.debug(f"Generated fallback icon for type '{icon_type}' with color {color}")
        return img
