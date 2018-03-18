## How to run Tuna from source code

### Windows

### Mac / Linux

```bash
$ git clone https://github.com/pyenv/pyenv.git ~/.pyenv
$ echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
$ echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
$ echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile
```

```bash
$ git clone https://github.com/takumak/tuna.git
$ cd tuna
$ ./tools/make_virtualenv.bash
$ ./tools/run_in_virtualenv.bash
```
