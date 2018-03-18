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

  missing = []
  whls = []
  for name in 'numpy', 'scipy', 'PyOpenGL', 'PyOpenGL_accelerate':
    pat = '%s-*-cp%s-cp%sm-%s.whl' % (name, ver, ver, suffix)
    lst = glob(pat)
    if len(lst) == 0:
      missing.append(pat)
    else:
      whls.append(lst[0])

  if len(missing) > 0:
    print('''
Download following file(s):
%s
from:
  http://www.lfd.uci.edu/~gohlke/pythonlibs/
and place these files into:
  %s
'''.strip() % ('\n'.join(['  * %s' % p for p in missing]),
               os.path.dirname(os.path.realpath(os.curdir))))
    sys.exit(0)

  depends = re.split(r'[\s]+', open('../../depends.txt').read().strip())

  import pip
  pip.main(['install', 'virtualenv'])

  import virtualenv
  sys.argv = ['virtualenv', 'venv']
  virtualenv.main()

  import subprocess
  subprocess.run(['venv/Scripts/pip.exe', 'install'] + whls, check=True)
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
