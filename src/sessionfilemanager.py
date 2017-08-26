import umsgpack

from configfilemanager import ConfigFileManagerBase



class SessionFileManager(ConfigFileManagerBase):
  @classmethod
  def convertVersion(cls, obj, version):
    return obj
