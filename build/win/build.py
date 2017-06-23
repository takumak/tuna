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
    'pyinstaller'
  ], check=True)


import shutil
for name in 'build', 'dist':
  if os.path.exists(name):
    shutil.rmtree(name)

import subprocess
subprocess.run(['venv/Scripts/pyinstaller.exe', '../tuna.spec'], check=True)
os.makedirs('../../dist')
os.rename('dist/Tuna.exe', '../../dist/Tuna.exe')
