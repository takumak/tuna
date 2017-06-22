import sys, os

if not os.path.exists('venv'):
  np = 'numpy-1.13.0+mkl-cp35-cp35m-win_amd64.whl'
  sp = 'scipy-0.19.1-cp35-cp35m-win_amd64.whl'

  if not (os.path.exists(np) and os.path.exists(sp)):
    print('''
Download following 2 files:
  * %s
  * %s
from:
  http://www.lfd.uci.edu/~gohlke/pythonlibs/
and place these files into:
  %s
'''.strip() % (np, sp, os.path.dirname(os.path.realpath(os.curdir))))
    sys.exit(0)


  import pip
  pip.main(['install', 'virtualenv'])

  import virtualenv
  sys.argv = ['virtualenv', 'venv']
  virtualenv.main()

  import subprocess
  subprocess.run(['venv/Scripts/pip.exe', 'install', np], check=True)
  subprocess.run(['venv/Scripts/pip.exe', 'install', sp], check=True)
  subprocess.run([
    'venv/Scripts/pip.exe', 'install',
    'pyqt5', 'pyqtgraph',
    'pyexcel', 'pyexcel-io', 'pyexcel-xls', 'pyexcel-odsr',
    'cx_Freeze'
  ], check=True)


print('Go into virtualenv')
__file__ = 'venv/Scripts/activate_this.py'
exec(open('venv/Scripts/activate_this.py').read())

import glob
from cx_Freeze import setup, Executable

# https://stackoverflow.com/questions/32432887/cx-freeze-importerror-no-module-named-scipy
# https://bitbucket.org/anthony_tuininga/cx_freeze/issues/43/import-errors-when-using-cx_freeze-with
from cx_Freeze.finder import ModuleFinder
modname_map = {
  'scipy.lib': 'scipy._lib',
}
IncludePackage = ModuleFinder.IncludePackage
ModuleFinder.IncludePackage = lambda s, n: IncludePackage(s, modname_map.get(n, n))

build_exe_options = {
  'include_files': glob.glob('../../src/*.py'),
  'packages': [
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',
    'scipy.sparse.csgraph._validation',
    'scipy.spatial.ckdtree',
    'pyqtgraph',
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
    'pyexcel_odsr.odsr',
    'lxml._elementpath' # required by pyexcel_odsr
  ]
}

base = None
if sys.platform == 'win32':
  base = 'Win32GUI'

sys.argv = ['build.py', 'build_exe']
setup(
  name = 'Tuna',
  options = {'build_exe': build_exe_options},
  executables = [Executable('../../src/tuna.py', base='Win32GUI')]
)

for fn in glob.glob('build/*/scipy/spatial/cKDTree.*'):
  dirname = os.path.dirname(fn)
  newname = os.path.basename(fn).lower()
  print('Rename file: %s => %s' % (fn, newname))
  os.rename(fn, os.path.join(dirname, newname))

import zipfile
with zipfile.ZipFile('tuna.zip', 'w', zipfile.ZIP_DEFLATED) as f:
  for dirpath, dirnames, filenames in os.walk(glob.glob('build/*/')[0]):
    for fn in filenames:
      path = os.path.join(dirpath, fn)
      print()
