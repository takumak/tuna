import sys, os, platform, re
from glob import glob

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
  np = glob(np_p)
  sp = glob(sp_p)

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

  np = np[0]
  sp = sp[0]

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
