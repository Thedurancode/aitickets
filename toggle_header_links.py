"""Toggle header links visibility in the event pages."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings

def toggle_header_links():
    """Toggle the SHOW_HEADER_LINKS setting in .env file."""
    import os
    from pathlib import Path

    # Get current ENV file
    env_file = Path(f".env.{os.getenv('ENV', 'development')}")

    if not env_file.exists():
        print(f"❌ Error: {env_file} not found")
        return

    # Read current content
    with open(env_file, 'r') as f:
        lines = f.readlines()

    # Find and update SHOW_HEADER_LINKS
    found = False
    with open(env_file, 'w') as f:
        for line in lines:
            if line.strip().startswith('SHOW_HEADER_LINKS='):
                current_value = line.split('=')[1].strip().lower()
                new_value = 'false' if current_value == 'true' else 'true'
                f.write(f'SHOW_HEADER_LINKS={new_value}\n')
                found = True
                print(f"✅ Toggled SHOW_HEADER_LINKS: {current_value} → {new_value}")
            else:
                f.write(line)

    if not found:
        # Add it if not found
        with open(env_file, 'a') as f:
            f.write('\nSHOW_HEADER_LINKS=true\n')
        print("✅ Added SHOW_HEADER_LINKS=true to .env file")

    print(f"\n📝 Updated file: {env_file}")
    print("🔄 Restart the server to apply changes")

if __name__ == '__main__':
    toggle_header_links()
