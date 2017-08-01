import numpy as np

from fitparameters import *
from fitgraphitems import *



__all__ = ['FitHandlePosition', 'FitHandleLine', 'FitHandleTheta']



class FitHandleBase:
  def __init__(self, view):
    self.view = view
    self.view.pixelRatioChanged.connect(self.pixelRatioChanged)

  def pixelRatioChanged(self):
    pass

  def getGraphItems(self, color):
    raise NotImplementedError()


class FitHandlePosition(FitHandleBase):
  def __init__(self, view, x, y):
    super().__init__(view)

    self.x = x
    self.y = y

  def getGraphItems(self, color):
    return [PointItem(self.x, self.y, self.view, color)]


class FitHandleLine(FitHandleBase):
  def __init__(self, view, x1, y1, x2, y2):
    super().__init__(view)

    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2

  def getGraphItems(self, color):
    return [LineItem(self.x1, self.y1, self.x2, self.y2, '#000'),
            PointItem(self.x2, self.y2, self.view, color)]


class FitHandleTheta(FitHandleBase):
  def __init__(self, view, cx, cy, theta, length):
    super().__init__(view)

    self.cx = cx
    self.cy = cy
    self.theta = theta
    self.length = length

    self.x = FitParam('x', self.getX())
    self.y = FitParam('y', self.getY())

    cx.valueChanged.connect(self.updateXY)
    cy.valueChanged.connect(self.updateXY)
    theta.valueChanged.connect(self.updateXY)

  def pixelRatioChanged(self):
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
    rx, ry = self.view.pixelRatio
    x = np.cos(theta)/rx
    y = np.sin(theta)/ry
    return self.atan(x, y)

  def getX(self):
    return self.cx.value() + self.length*np.cos(self.viewTheta())*self.view.pixelRatio[0]

  def getY(self):
    return self.cy.value() + self.length*np.sin(self.viewTheta())*self.view.pixelRatio[1]

  def updateXY(self):
    self.x.setValue(self.getX())
    self.y.setValue(self.getY())

  def xyfilter(self, x, y):
    theta = self.atan(x - self.cx.value(), y - self.cy.value())
    self.theta.setValue(theta)
    return self.getX(), self.getY()

  def getGraphItems(self, color):
    return [LineItem(self.cx, self.cy, self.x, self.y, color),
            CircleItem(self.cx, self.cy, FitParamConst('r', self.length), self.view, color),
            PointItem(self.x, self.y, self.view, color, self.xyfilter)]
