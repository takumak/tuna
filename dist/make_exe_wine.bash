#!/bin/bash

set -xe

WINETRICKS_URL=https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
test ! -f winetricks && curl -LO $WINETRICKS_URL

export WINEPREFIX=$(pwd)/wine
# export WINEARCH=win32

bash winetricks -q dotnet46 || :

PYTHON_EXE_URL=https://www.python.org/ftp/python/3.6.1/python-3.6.1-amd64.exe
PYTHON_EXE=${PYTHON_EXE_URL##*/}
PYTHON_NAME=${PYTHON_EXE%-*}

test ! -f $PYTHON_EXE && curl -LO $PYTHON_EXE_URL
wine $PYTHON_EXE /quiet InstallAllUsers=1 TargetDir=c:/$PYTHON_NAME
