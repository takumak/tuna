import os
from PyQt5.QtWidgets import \
  QDialog, QPushButton, QCheckBox, QLabel, QFileDialog

from commonwidgets import VBoxLayout, HBoxLayout



class FileDialog(QFileDialog):
  params = {
    'file_import':     ('Import file',  QFileDialog.AcceptOpen, QFileDialog.ExistingFiles, 'Any files (*)', None),
    'session_open':    ('Open session', QFileDialog.AcceptOpen, QFileDialog.ExistingFiles, 'Session files (*.json)', None),
    'session_save':    ('Save session', QFileDialog.AcceptSave, QFileDialog.AnyFile,       'Session files (*.json)', 'json'),
    'iad_export_xlsx': ('Export xlsx',  QFileDialog.AcceptSave, QFileDialog.AnyFile,       'Excel files (*.xlsx)', 'xlsx')
  }
  state = None
  states = {}

  def __init__(self, name):
    super().__init__()
    title, acceptmode, filemode, namefilter, suffix = self.params[name]
    self.name = name
    self.setWindowTitle(title)
    self.setAcceptMode(acceptmode)
    self.setFileMode(filemode)
    self.setNameFilter(namefilter)
    if suffix: self.setDefaultSuffix(suffix)

  def exec_(self):
    cls = self.__class__
    if self.name in cls.states:
      if cls.state: self.restoreState(cls.state)
      st = cls.states[self.name]
      if 'dir' in st: self.setDirectory(st['dir'])

    ret = super().exec_()

    if ret == self.Accepted:
      cls.state = self.saveState()
      cls.states[self.name] = {'dir': self.directory().absolutePath()}
    return ret
