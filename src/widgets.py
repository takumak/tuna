import os
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import \
  QDialog, QPushButton, QCheckBox, QLabel

from sheetwidgets import SheetWidget
from commonwidgets import VBoxLayout, HBoxLayout



class SelectColumnDialog(QDialog):
  def __init__(self, c, cname, unselect, x, y):
    super().__init__()
    self.c = c


    buttons = [[(unselect, 'Do not use', self.unselect)],
               [(x, 'X', self.X)]]
    buttons.append([(True, 'Y%d' % (y_ + 1), (lambda y_: lambda: self.Y(y_))(y_)) for y_ in y])


    btnlayout = VBoxLayout()
    for r in buttons:
      row = HBoxLayout()
      btnlayout.addLayout(row)
      for enable, text, func in r:
        btn = QPushButton(text)
        btn.clicked.connect((lambda f: f)(func))
        row.addWidget(btn)

    self.applyToAllSheets = QCheckBox('Apply to all sheets')
    self.applyToAllSheets.setChecked(True)

    btn = QPushButton('Cancel')
    btn.clicked.connect(self.reject)
    btnbar2 = HBoxLayout()
    btnbar2.addStretch(1)
    btnbar2.addWidget(btn)

    vbox = VBoxLayout()
    vbox.addWidget(QLabel('Use column "%s" for:' % cname))
    vbox.addLayout(btnlayout)
    vbox.addWidget(self.applyToAllSheets)
    vbox.addLayout(btnbar2)

    self.setLayout(vbox)

  def unselect(self):
    self.useFor = None
    self.accept()

  def X(self):
    self.useFor = 'x'
    self.accept()

  def Y(self, yn):
    self.useFor = 'y%d' % yn
    self.accept()



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
