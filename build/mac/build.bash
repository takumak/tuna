#!/bin/bash

set -xe

if python -c "import sys,sysconfig;sys.exit(sysconfig.get_config_vars('Py_ENABLE_SHARED')[0])"; then
  set +x
  echo '####################################################################'
  echo 'Your python seems to be compiled without --enable-shared'
  echo 'try following command:'
  echo '  env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -f 3.5.5'
  exit 1
fi

ROOT=$(dirname $(realpath $0))/../..
SPEC=$ROOT/build/tuna.spec
OUTDIR=$ROOT/dist

rm -rf venv build dist Tuna.app $OUTDIR/Tuna.app.zip
$ROOT/tools/make_virtualenv.bash

source venv/bin/activate
pip install pyinstaller
pyinstaller $SPEC
deactivate

mv dist/Tuna.app .
mkdir -p $OUTDIR
zip -r $OUTDIR/Tuna.app.zip Tuna.app
rm -rf venv build dist
