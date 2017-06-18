from datetime import datetime

_app = None
_log = []

def log(text, role='message'):
  if not isinstance(text, str):
    text = repr(text)

  time = datetime.now().strftime('%m/%d %H:%M:%S')
  text = '[%s] %s' % (time, text)
  print(text)

  global _app
  if _app:
    _app.window.log_(text, role)
  else:
    _log.append((text, role))

def set_app(app):
  global _app
  _app = app
  for t, r in _log:
    _app.window.log_(t, r)
  _log.clear()
