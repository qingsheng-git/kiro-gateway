"""
Script to generate tray icon assets.

This script creates the required icon files for the system tray:
- tray_icon.png (normal state - blue)
- tray_icon_warning.png (warning state - orange/yellow)
- tray_icon_error.png (error state - red)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def create_icon(output_path: Path, color: tuple, size: int = 48) -> None:
    """
    Create a simple icon with a colored circle and 'K' letter.
    
    Args:
        output_path: Path to save the icon
        color: RGB color tuple
        size: Icon size in pixels (default: 48)
    """
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw colored circle
    margin = 2
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline=(255, 255, 255, 255),
        width=2
    )
    
    # Draw 'K' letter in white
    try:
        # Try to use a system font
        font_size = int(size * 0.6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    text = "K"
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the icon
    img.save(output_path, 'PNG')
    print(f"Created icon: {output_path}")

def main():
    """Generate all required icon assets."""
    # Get assets directory
    assets_dir = Path(__file__).parent.parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Define icon colors
    icons = {
        "tray_icon.png": (0, 120, 212),        # Blue (normal)
        "tray_icon_warning.png": (255, 185, 0), # Orange/Yellow (warning)
        "tray_icon_error.png": (232, 17, 35)    # Red (error)
    }
    
    # Create icons in multiple sizes
    sizes = [16, 32, 48]
    
    for filename, color in icons.items():
        # Create the main 48x48 icon
        output_path = assets_dir / filename
        create_icon(output_path, color, size=48)
        
        # Also create smaller versions for reference
        for size in [16, 32]:
            size_filename = filename.replace('.png', f'_{size}.png')
            size_output_path = assets_dir / size_filename
            create_icon(size_output_path, color, size=size)
    
    print(f"\nAll icons created successfully in: {assets_dir}")
    print("\nMain icons (48x48):")
    print("  - tray_icon.png (normal state)")
    print("  - tray_icon_warning.png (warning state)")
    print("  - tray_icon_error.png (error state)")

if __name__ == "__main__":
    main()
