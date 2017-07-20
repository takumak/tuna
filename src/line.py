import numpy as np
import pyqtgraph as pg



class Line:
  def __init__(self, name, x, y, y_):
    self.name = name
    self.x = np.array(x)
    self.y = np.array(y)
    self.y_ = None if y_ is None else np.array(y_)
    self.plotErrors = False

  @classmethod
  def cleanUp(cls, x, y, y_):
    X, Y, Y_ = [], [], []
    for xi, yi, yi_ in zip(x, y, y_):
      try:
        xi = float(xi)
        yi = float(yi)
        yi_ = float(yi_)
      except (ValueError, TypeError):
        continue

      if True in np.isnan([xi, yi, yi_]):
        continue

      X.append(xi)
      Y.append(yi)
      Y_.append(yi_)

    return np.array(X), np.array(Y), np.array(Y_)

  def weightCenter(self):
    if len(self.x) == 0: return 0
    return np.sum(self.x*self.y)/np.sum(self.y)

  def normalize(self):
    if len(self.x) == 0: return self
    sumy = np.sum(self.y)
    y = self.y/sumy
    if self.y_ is None:
      return self.__class__(self.name, self.x, y, None)

    sumy_ = np.sqrt(np.sum(self.y_**2))
    y_ = np.sqrt((1/sumy)**2*(self.y_**2) + (y/sumy**2)**2*(sumy_**2))
    return self.__class__(self.name, self.x, y, y_)

  def xoff(self, off):
    return self.__class__(self.name, self.x + off, self.y, self.y_)

  def __sub__(self, other):
    if list(self.x) != list(other.x):
      raise RuntimeError('x is not same: %s vs %s' % (self.x, other.x))
    y = self.y - other.y
    if self.y_ is None:
      return self.__class__(self.name, self.x, y, other.y_)
    if other.y_ is None:
      return self.__class__(self.name, self.x, y, self.y_)

    y_ = np.sqrt(self.y_**2 + other.y_**2)
    return self.__class__(self.name, self.x, y, y_)

  def peak(self):
    if len(self.x) == 0:
      return 0, 0
    return max(zip(self.x, self.y), key=lambda p: p[1])

  def getGraphItems(self, color):
    pen = pg.mkPen(color=color, width=2)
    items = [pg.PlotCurveItem(x=self.x, y=self.y, pen=pen, antialias=True)]
    if self.plotErrors:
      items.append(pg.ErrorBarItem(
        x=self.x, y=self.y, height=self.y_*2, beam=0.2, pen=pen, antialias=True))
      items.append(pg.ScatterPlotItem(
        x=self.x, y=self.y, brush=pg.mkBrush(color=color), antialias=True))
    return items
