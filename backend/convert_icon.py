from PIL import Image
import os
import sys

# Convert PNG to ICO
png_path = r"c:/Users/dhkdw/Desktop/new/MP3toSpotify/electron/assets/icon.png"
ico_path = r"c:/Users/dhkdw/Desktop/new/MP3toSpotify/electron/assets/icon.ico"

try:
    img = Image.open(png_path)
    # Resize and create multiresolution ICO
    # Typically 256, 128, 64, 48, 32, 16
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Successfully converted {png_path} to {ico_path}")
except Exception as e:
    print(f"Error converting icon: {e}")
    sys.exit(1)
