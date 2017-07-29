import numpy as np
import pyqtgraph as pg

from toolbase import ToolBase



class FitTool(ToolBase):
  name = 'fit'
  label = 'Fit'

  def __init__(self):
    super().__init__()
    self.functions = []

  def getLines(self):
    return self.lines

  def getGraphItems(self):
    items = []
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)
    for i, f in enumerate(self.functions):
      items += f.getGraphItems(x, pen=pg.mkPen(color='#000000', width=2))
    return items
