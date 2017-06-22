#!/bin/bash

set -xe

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
