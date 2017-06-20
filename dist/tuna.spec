# -*- mode: python -*-

block_cipher = None


a = Analysis(
  ['../src/tuna.py'],
  pathex=[],
  binaries=[],
  datas=[],
  hiddenimports=[
    # http://pyexcel-io.readthedocs.io/en/latest/pyinstaller.html
    'pyexcel.plugins',
    'pyexcel.plugins.parsers',
    'pyexcel.plugins.parsers.excel',
    'pyexcel.plugins.renderers',
    'pyexcel.plugins.sources',
    'pyexcel.plugins.sources.file_input',
    'pyexcel_io',
    'pyexcel_io.database',
    'pyexcel_io.readers.csvr',
    'pyexcel_io.readers.csvz',
    'pyexcel_io.readers.tsv',
    'pyexcel_io.readers.tsvz',
    'pyexcel_io.writers.csvw',
    'pyexcel_io.readers.csvz',
    'pyexcel_io.readers.tsv',
    'pyexcel_io.readers.tsvz',
    'pyexcel_xls',
    'pyexcel_xls.xlsr',
    'pyexcel_odsr',
    'pyexcel_odsr.odsr'
  ],
  hookspath=[],
  runtime_hooks=[],
  excludes=[],
  win_no_prefer_redirects=False,
  win_private_assemblies=False,
  cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
  pyz,
  a.scripts,
  exclude_binaries=True,
  name='Tuna',
  debug=False,
  strip=False,
  upx=True,
  console=False
)

coll = COLLECT(
  exe,
  a.binaries,
  a.zipfiles,
  a.datas,
  strip=False,
  upx=True,
  name='Tuna'
)

app = BUNDLE(
  coll,
  name='Tuna.app',
  icon=None,
  bundle_identifier=None
)
