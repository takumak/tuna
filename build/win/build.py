import sys, os, platform, re

x64 = platform.architecture()[0] == '64bit'

if not os.path.exists('venv'):
  if x64:
    np = 'numpy-1.13.3+mkl-cp35-cp35m-win_amd64.whl'
    sp = 'scipy-1.0.0-cp35-cp35m-win_amd64.whl'
  else:
    np = 'numpy-1.13.3+mkl-cp35-cp35m-win32.whl'
    sp = 'scipy-1.0.0-cp35-cp35m-win32.whl'

  depends = re.split(r'[\s]+', open('../../depends.txt').read().strip())

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
  subprocess.run(['venv/Scripts/pip.exe', 'install', 'pyinstaller'] + depends, check=True)


import shutil
for name in 'build', 'dist':
  if os.path.exists(name):
    shutil.rmtree(name)

import subprocess
subprocess.run(['venv/Scripts/pyinstaller.exe', '../tuna.spec'], check=True)
if not os.path.exists('../../dist'):
  os.makedirs('../../dist')
if os.path.exists('../../dist/Tuna.exe'):
  os.remove('../../dist/Tuna.exe')
os.rename('dist/Tuna.exe', '../../dist/Tuna.exe')
