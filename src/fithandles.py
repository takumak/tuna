import logging
import numpy as np

from functions import blockable
from fitparameters import *
from fitgraphitems import *



__all__ = ['FitHandlePosition', 'FitHandleLine', 'FitHandleGradient']



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


class FitHandleGradient(FitHandleBase):
  def __init__(self, view, cx, cy, A, length, right=True):
    super().__init__(view)

    self.cx = cx
    self.cy = cy
    self.A = A
    self.length = length
    self.right = right

    self.x = FitParam('x', 0)
    self.y = FitParam('y', 0)

    cx.valueChanged.connect(self.setXY)
    cy.valueChanged.connect(self.setXY)
    A.valueChanged.connect(self.setXY)

    self.setXY()

  def pixelRatioChanged(self):
    self.setXY()

  def xy2theta(self, x, y):
    theta = np.arctan2(y - self.cy.value(), x - self.cx.value())
    if self.right:
      if theta > np.pi/2:
        theta = np.pi/2
      elif theta < -np.pi/2:
        theta = -np.pi/2
    else:
      if 0 <= theta < np.pi/2:
        theta = np.pi/2
      elif -np.pi/2 < theta < 0:
        theta = -np.pi/2
    return theta

  def calcX(self, theta):
    cos = np.cos(self.viewTheta(theta))
    return self.cx.value() + self.length*cos*self.view.pixelRatio[0]

  def calcY(self, theta):
    sin = np.sin(self.viewTheta(theta))
    return self.cy.value() + self.length*sin*self.view.pixelRatio[1]

  @blockable
  def setXY(self):
    dx = 1 if self.right else -1
    dy = self.A.value()*dx
    theta = self.xy2theta(self.cx.value()+dx, self.cy.value()+dy)
    self.x.setValue(self.calcX(theta))
    self.y.setValue(self.calcY(theta))

  def viewTheta(self, theta):
    rx, ry = self.view.pixelRatio
    x = np.cos(theta)/rx
    y = np.sin(theta)/ry
    return np.arctan2(y, x)

  def xyfilter(self, x, y):
    theta = self.xy2theta(x, y)
    self.setXY.block()
    self.A.setValue(np.tan(theta))
    self.setXY.unblock()
    return self.calcX(theta), self.calcY(theta)

  def getGraphItems(self, color):
    return [LineItem(self.cx, self.cy, self.x, self.y, color),
            CircleItem(self.cx, self.cy, FitParamConst('r', self.length), self.view, color),
            PointItem(self.x, self.y, self.view, color, self.xyfilter)]
