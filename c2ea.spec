# -*- mode: python -*-

block_cipher = None


a = Analysis(['c2ea.py'],
             pathex=['C:\\Users\\bovie_000\\Dropbox\\Unified FE Hacking\\Circles\\NMM 2 CSV'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='c2ea',
          debug=False,
          strip=False,
          upx=True,
          console=True , icon='icon.ico')
