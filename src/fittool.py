import numpy as np
import pyqtgraph as pg

from line import Line
from toolbase import ToolBase



class FitTool(ToolBase):
  name = 'fit'
  label = 'Fit'

  def __init__(self):
    super().__init__()
    self.functions = []
    self.fitCurveItem = None

  def setFunctions(self, functions):
    self.functions = functions
    for func in functions:
      func.parameterChanged.connect(self.updateFitCurve)
    self.updateFitCurve()

  def updateFitCurve(self):
    if self.fitCurveItem is None:
      return

    x, y = self.fitCurveItem.getData()
    y = np.sum([f.y(x) for f in self.functions], axis=0)
    self.fitCurveItem.setData(x=x, y=y)

  def getLines(self):
    return [l.normalize() for l in self.lines]

  def getGraphItems(self, colorpicker):
    items = []
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)
    for i, f in enumerate(self.functions):
      items += f.getGraphItems(x, colorpicker.next())

    if self.fitCurveItem is None:
      self.fitCurveItem = pg.PlotCurveItem(
        x=x, y=np.zeros(len(x)), name='Fit', antialias=True)
    self.updateFitCurve()
    self.fitCurveItem.setPen(color=colorpicker.next(), width=2)
    items.append(self.fitCurveItem)

    return items
