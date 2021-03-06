import sys
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QLabel

from commonwidgets import *



class FitFuncDescriptor(DescriptionWidget):
  def __init__(self, funcClass):
    super().__init__()
    self.funcClass = funcClass

    self.addTitle(self.funcClass.label)

    import lateximgs
    img = QImage()
    img.loadFromData(getattr(lateximgs, 'fitfunc_%s' % funcClass.name))
    self.addLabel('Definition:')
    self.addImage(img)

    self.addLabel('Parameters:')
    grid = self.addGrid()
    for r, (name, desc) in enumerate(funcClass.parameters):
      grid.addWidget(QLabel(name), r, 0)
      grid.addWidget(QLabel(desc), r, 1)
