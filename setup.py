from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'includes': ['pyperclip'],
    'packages': [],
    'iconfile': 'icon.icns',  # optional: replace with your icon or remove this line
    'plist': {
        'CFBundleName': 'Clipboard Sync',
        'CFBundleDisplayName': 'Clipboard Sync',
        'CFBundleIdentifier': 'com.muffafa.clipboardsync',
        'CFBundleVersion': '0.1',
        'CFBundleShortVersionString': '0.1',
    },
}

setup(
    app=APP,
    name='Clipboard Sync',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
