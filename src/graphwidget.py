from PyQt5.QtCore import pyqtSignal
import pyqtgraph as pg

from graphitems import PlotCurveItem



class ColorPicker:
  def __init__(self, colors):
    self.colors = colors
    self.idx = 0

  def reset(self):
    self.idx = 0

  def next(self):
    c = self.colors[self.idx]
    self.idx += 1
    if self.idx >= len(self.colors):
      self.idx = 0
    return c



class GraphWidget(pg.PlotWidget):
  # https://github.com/LibreOffice/core/blob/master/extras/source/palettes/chart-palettes.soc
  colors = [
    '#004586', '#ff420e', '#ffd320', '#579d1c', '#7e0021', '#83caff',
    '#314004', '#aecf00', '#4b1f6f', '#ff950e', '#c5000b', '#0084d1'
  ]

  pixelRatioChanged = pyqtSignal()

  def __init__(self):
    vb = pg.ViewBox(border=pg.mkPen(color='#000'))
    super().__init__(viewBox=vb)
    self.useOpenGL(True)
    self.setBackground('#fff')
    # self.legend = self.addLegend(offset=(10, 10))
    self.colorpicker = ColorPicker(self.colors)

    self.pixelRatio = None
    self.sigRangeChanged.connect(self.__geometryChanged)
    self.__geometryChanged()

  def getColorPicker(self):
    return self.colorpicker

  def clearItems(self):
    for item in self.items():
      self.removeItem(item)
    # self.legend.scene().removeItem(self.legend)
    # self.legend = self.addLegend(offset=(10, 10))
    self.colorpicker.reset()

  def __geometryChanged(self):
    r = self.viewRect()
    s = self.size()
    rx = r.width()/s.width()
    ry = r.height()/s.height()
    self.pixelRatio = rx, ry
    self.pixelRatioChanged.emit()

  def resizeEvent(self, ev):
    super().resizeEvent(ev)
    self.__geometryChanged()
