import umsgpack

from configfilemanager import ConfigFileManagerBase



class SessionFileManager(ConfigFileManagerBase):
  version = 1

  @classmethod
  def convertVersion(cls, obj):
    return obj
