# -*- mode: python -*-

block_cipher = None


a = Analysis(['../../src/tuna.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=['pyexcel-io', 'pyexcel-xls', 'pyexcel-odsr'],
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
          exclude_binaries=True,
          name='tuna',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='tuna')
app = BUNDLE(coll,
             name='tuna.app',
             icon=None,
             bundle_identifier=None)
