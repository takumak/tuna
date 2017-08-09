import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QFrame, QLabel, QGridLayout

from commonwidgets import *



class FitFuncDescriptor(QFrame):
  def __init__(self, funcClass):
    super().__init__()
    self.funcClass = funcClass

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)

    titleFrame = QFrame()
    titleFrame.setFrameShape(QFrame.StyledPanel)
    titleFrame.setContentsMargins(4, 4, 4, 4)
    titleLabel = QLabel(self.funcClass.label)
    titleLabel.setContentsMargins(16, 4, 16, 4)
    layout = VBoxLayout()
    layout.addWidget(titleLabel)
    titleFrame.setLayout(layout)
    vbox.addWidget(titleFrame)

    import lateximgs
    img = QImage()
    img.loadFromData(getattr(lateximgs, 'fitfunc_%s' % funcClass.name))
    imglabel = QLabel()
    imglabel.setContentsMargins(16, 4, 16, 4)
    imglabel.setPixmap(QPixmap.fromImage(img))
    vbox.addWidget(QLabel('Definition:'))
    vbox.addWidget(imglabel)

    grid = QGridLayout()
    grid.setContentsMargins(16, 4, 4, 16)
    grid.setColumnStretch(1, 1)
    grid.setHorizontalSpacing(16)
    for r, (name, desc) in enumerate(funcClass.parameters):
      grid.addWidget(QLabel(name), r, 0)
      grid.addWidget(QLabel(desc), r, 1)
    vbox.addWidget(QLabel('Parameters:'))
    vbox.addLayout(grid)

    self.setFrameShape(QFrame.StyledPanel)
