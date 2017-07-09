from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import \
  QVBoxLayout, QHBoxLayout, \
  QWidget, QDialog, QPushButton, QCheckBox, QLabel, \
  QSplitter

class SelectColumnDialog(QDialog):
  def __init__(self, c, cname, unselect, x, y):
    super().__init__()
    self.c = c


    buttons = [[(unselect, 'Do not use', self.unselect)],
               [(x, 'X', self.X)]]
    buttons.append([(True, 'Y%d' % (y_ + 1), (lambda y_: lambda: self.Y(y_))(y_)) for y_ in y])


    btnlayout = QVBoxLayout()
    for r in buttons:
      row = QHBoxLayout()
      btnlayout.addLayout(row)
      for enable, text, func in r:
        btn = QPushButton(text)
        btn.clicked.connect((lambda f: f)(func))
        row.addWidget(btn)

    self.applyToAllSheets = QCheckBox('Apply to all sheets')
    self.applyToAllSheets.setChecked(True)

    btn = QPushButton('Cancel')
    btn.clicked.connect(self.reject)
    btnbar2 = QHBoxLayout()
    btnbar2.addStretch(1)
    btnbar2.addWidget(btn)

    vbox = QVBoxLayout()
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



# class SourcesWidget(QSplitter):
#   def __init__(self):
#     super().__init__(Qt.Horizontal)
#     self.list = QListWidget()
#     self.blank = QWidget()
#     self.addWidget(self.list)
#     self.addWidget(self.blank)

#     self.sheets = []

#   def add(self, sheet):
