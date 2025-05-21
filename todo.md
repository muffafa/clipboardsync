# Todo List

- Add versioning system
- Fix when other disconnected status not updated in our ui
- Write a readme.md

## Macos

```pyinstaller --noconfirm --onefile --windowed main.py```

or

```bash
mkdir clipboard.iconset
sips -z 16 16     clipboard_icon.png --out clipboard.iconset/icon_16x16.png
sips -z 32 32     clipboard_icon.png --out clipboard.iconset/icon_16x16@2x.png
sips -z 32 32     clipboard_icon.png --out clipboard.iconset/icon_32x32.png
sips -z 64 64     clipboard_icon.png --out clipboard.iconset/icon_32x32@2x.png
sips -z 128 128   clipboard_icon.png --out clipboard.iconset/icon_128x128.png
sips -z 256 256   clipboard_icon.png --out clipboard.iconset/icon_128x128@2x.png
sips -z 256 256   clipboard_icon.png --out clipboard.iconset/icon_256x256.png
sips -z 512 512   clipboard_icon.png --out clipboard.iconset/icon_256x256@2x.png
sips -z 512 512   clipboard_icon.png --out clipboard.iconset/icon_512x512.png
cp clipboard_icon.png clipboard.iconset/icon_512x512@2x.png
```

```iconutil -c icns clipboard.iconset -o icon.icns```

```python setup.py py2app```

```mv "/Users/muffafa/Desktop/clipboardsync/dist/Clipboard Sync.app" /Applications/```

## Ubuntu

[Desktop Entry]
Version=1.0
Name=Clipboard Sync
Comment=Clipboard synchronization tool
Exec=Exec=/home/muffafa/projects/clipboardsync/venv/bin/python /home/muffafa/projects/clipboardsync/main.py
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;Network;
StartupNotify=true

```chmod +x ~/.local/share/applications/clipboardsync.desktop```
