import os
import appdirs
import json
import umsgpack



class ConfigFileManagerBase:
  version = 1

  def load(self, filename):
    if not os.path.exists(filename):
      return None

    if filename.endswith('.json'):
      mode, func = 'r', json.load
    elif filename.endswith('.msgpack'):
      mode, func = 'rb', umsgpack.unpack
    else:
      raise RuntimeError('Unsupported filename extension - "%s"' % filename)

    with open(filename, mode) as f:
      obj = func(f)
      if 'version' not in obj:
        obj['version'] = 1
      return self.convertVersion(obj, obj['version'])

  def save(self, obj, filename):
    if filename.endswith('.json'):
      mode, func = 'w', json.dump
    elif filename.endswith('.msgpack'):
      mode, func = 'wb', umsgpack.pack
    else:
      raise RuntimeError('Unsupported filename extension - "%s"' % filename)

    dirpath = os.path.dirname(filename)
    if not os.path.exists(dirpath):
      os.makedirs(dirpath)

    obj['version'] = self.version
    with open(filename, mode) as f:
      func(obj, f)



class ConfigFileManager(ConfigFileManagerBase):
  def __init__(self):
    self.configdir = appdirs.user_config_dir('tuna')
    self.filename  = os.path.join(self.configdir, 'tuna.conf.msgpack')

  def load(self):
    return super().load(self.filename)

  def save(self, obj):
    super().save(obj, self.filename)

  @classmethod
  def convertVersion(cls, obj, version):
    from sessionfilemanager import SessionFileManager
    if 'session' in obj:
      obj['session'] = SessionFileManager.convertVersion(obj['session'], version)
    return obj
