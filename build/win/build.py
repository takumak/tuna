import sys, os, platform, re
from glob import glob
from distutils.version import StrictVersion

x64 = platform.architecture()[0] == '64bit'

if not os.path.exists('venv'):
  if x64:
    suffix = 'win_amd64'
  else:
    suffix = 'win32'

  ver = sys.version_info
  ver = '%d%d' % (ver.major, ver.minor)
  np_p = 'numpy-*-cp%s-cp%sm-%s.whl' % (ver, ver, suffix)
  sp_p = 'scipy-*-cp%s-cp%sm-%s.whl' % (ver, ver, suffix)
  np = list(sorted(glob(np_p), key=StrictVersion))
  sp = list(sorted(glob(sp_p), key=StrictVersion))

  depends = re.split(r'[\s]+', open('../../depends.txt').read().strip())

  if not (len(np) > 0 and len(sp) > 0):
    print('''
Download following 2 files:
  * %s
  * %s
from:
  http://www.lfd.uci.edu/~gohlke/pythonlibs/
and place these files into:
  %s
'''.strip() % (np_p, sp_p, os.path.dirname(os.path.realpath(os.curdir))))
    sys.exit(0)

  np = np[-1]
  sp = sp[-1]

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
