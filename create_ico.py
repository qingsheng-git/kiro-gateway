"""
Create Windows ICO file from PNG icons.

This script converts the PNG tray icons to ICO format for use with
the Windows executable.
"""

from PIL import Image
from pathlib import Path

def create_ico_from_png(png_path: Path, ico_path: Path, sizes=None):
    """
    Convert PNG to ICO with multiple sizes.
    
    Args:
        png_path: Path to source PNG file
        ico_path: Path to output ICO file
        sizes: List of sizes to include (default: [16, 32, 48, 256])
    """
    if sizes is None:
        sizes = [16, 32, 48, 256]
    
    # Load the PNG image
    img = Image.open(png_path)
    
    # Create images at different sizes
    icon_images = []
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Save as ICO
    icon_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in icon_images]
    )
    
    print(f"✓ Created {ico_path} with sizes: {sizes}")

def main():
    """Create ICO files from PNG icons."""
    assets_dir = Path('assets')
    
    # Create main application icon
    create_ico_from_png(
        assets_dir / 'tray_icon.png',
        assets_dir / 'tray_icon.ico'
    )
    
    # Create warning icon
    create_ico_from_png(
        assets_dir / 'tray_icon_warning.png',
        assets_dir / 'tray_icon_warning.ico'
    )
    
    # Create error icon
    create_ico_from_png(
        assets_dir / 'tray_icon_error.png',
        assets_dir / 'tray_icon_error.ico'
    )
    
    print("\n✓ All ICO files created successfully!")
    print("\nYou can now uncomment the icon line in kiro_gateway.spec:")
    print("  icon='assets/tray_icon.ico',")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure Pillow is installed: pip install Pillow")
