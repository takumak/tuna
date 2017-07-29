import numpy as np

from fitparameters import *
from fitgraphitems import *



__all__ = ['FitHandlePosition', 'FitHandleLine', 'FitHandleTheta']



class FitHandleBase:
  def __init__(self, view):
    self.view = view
    self.view.sigRangeChanged.connect(self.viewScaleChanged)
    FitHandleBase.viewScaleChanged(self)

  def viewScaleChanged(self):
    r = self.view.viewRect()
    s = self.view.size()
    rx = r.width()/s.width()
    ry = r.height()/s.height()
    self.ratio = rx, ry

  def getGraphItems(self):
    raise NotImplementedError()


class FitHandlePosition(FitHandleBase):
  def __init__(self, view, x, y):
    super().__init__(view)

    self.x = x
    self.y = y

  def getGraphItems(self):
    return [PointItem(self.x, self.y)]


class FitHandleLine(FitHandleBase):
  def __init__(self, view, x1, y1, x2, y2):
    super().__init__(view)

    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2

  def getGraphItems(self):
    return [LineItem(self.x1, self.y1, self.x2, self.y2), PointItem(self.x2, self.y2)]


class FitHandleTheta(FitHandleBase):
  def __init__(self, view, cx, cy, theta, length):
    super().__init__(view)

    self.cx = cx
    self.cy = cy
    self.theta = theta
    self.length = length

    self.x = FitParameter('x', self.getX())
    self.y = FitParameter('y', self.getY())

    cx.valueChanged.connect(self.updateXY)
    cy.valueChanged.connect(self.updateXY)
    theta.valueChanged.connect(self.updateXY)

  def viewScaleChanged(self):
    super().viewScaleChanged()
    self.updateXY()

  def atan(self, x, y, prev=None):
    if x == 0:
      theta = np.pi/2*(1 if y>=0 else -1)
    else:
      theta = np.arctan2(y, x)
    if theta < 0: theta += np.pi*2
    return theta

  def viewTheta(self):
    theta = self.theta.value()
    rx, ry = self.ratio
    x = np.cos(theta)/rx
    y = np.sin(theta)/ry
    return self.atan(x, y)

  def getX(self):
    return self.cx.value() + self.length*np.cos(self.viewTheta())*self.ratio[0]

  def getY(self):
    return self.cy.value() + self.length*np.sin(self.viewTheta())*self.ratio[1]

  def updateXY(self):
    self.x.setValue(self.getX())
    self.y.setValue(self.getY())

  def xyfilter(self, x, y):
    theta = self.atan(x - self.cx.value(), y - self.cy.value())
    self.theta.setValue(theta)
    return self.getX(), self.getY()

  def getGraphItems(self):
    return [LineItem(self.cx, self.cy, self.x, self.y),
            PointItem(self.x, self.y, self.xyfilter)]


