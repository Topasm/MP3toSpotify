import os
import sys
from tinytag import TinyTag

def scan_dir(directory):
    print(f"Scanning: {directory}")
    supported_exts = ('.mp3', '.m4a', '.flac', '.wav', '.ogg')
    found = []
    
    if not os.path.exists(directory):
        print(f"[ERROR] Directory not found: {directory}")
        return

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_exts):
                path = os.path.join(root, file)
                try:
                    tag = TinyTag.get(path)
                    print(f"[FOUND] {file}")
                    print(f"  -> Title: {tag.title}")
                    print(f"  -> Artist: {tag.artist}")
                    found.append(file)
                except Exception as e:
                    print(f"[ERROR] {file}: {e}")

    print(f"\nTotal found: {len(found)}")

if __name__ == "__main__":
    # Force UTF-8 for Windows console
    sys.stdout.reconfigure(encoding='utf-8')
    
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = input("Enter directory to scan: ").strip()
        
    scan_dir(target_dir)
