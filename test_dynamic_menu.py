"""
Test script to verify dynamic menu updates work correctly.
"""
import sys
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stdout, level="DEBUG")

try:
    import pystray
    from pystray import MenuItem as Item
    from PIL import Image
    
    # Create a simple test icon
    img = Image.new('RGB', (64, 64), color='blue')
    
    # State variable
    service_running = False
    
    def toggle_service(icon, item):
        global service_running
        service_running = not service_running
        logger.info(f"Service toggled: running={service_running}")
        icon.update_menu()
    
    def get_status_text(item):
        return f"Status: {'Running' if service_running else 'Stopped'}"
    
    def can_start(item):
        return not service_running
    
    def can_stop(item):
        return service_running
    
    # Create menu with dynamic properties
    menu = pystray.Menu(
        Item(get_status_text, lambda: None, enabled=False, default=True),
        Item("Start Service", toggle_service, enabled=can_start),
        Item("Stop Service", toggle_service, enabled=can_stop),
        Item("Exit", lambda icon, item: icon.stop())
    )
    
    # Create icon
    icon = pystray.Icon("test", img, "Test Dynamic Menu", menu=menu)
    
    logger.success("✓ Dynamic menu test setup complete!")
    logger.info("Please test the menu:")
    logger.info("1. Right-click the tray icon")
    logger.info("2. Click 'Start Service' - it should become disabled")
    logger.info("3. 'Stop Service' should become enabled")
    logger.info("4. Click 'Stop Service' - states should reverse")
    logger.info("5. Click 'Exit' when done")
    
    # Run the icon (this will block)
    icon.run()
    
    logger.success("✓ Test completed successfully!")
    
except ImportError as e:
    logger.error(f"pystray not available: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Test failed: {e}")
    sys.exit(1)
