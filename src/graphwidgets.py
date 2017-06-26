import pyqtgraph as pg

class GraphWidget(pg.PlotWidget):
  def __init__(self):
    vb = pg.ViewBox(border=pg.mkPen(color='#000'))
    super().__init__(viewBox=vb)
    self.setBackground('#fff')
    self.legend = self.addLegend(offset=(10, 10))
    self.lines = []
    self.setViewportUpdateMode(self.FullViewportUpdate)

  def clearItems(self):
    for item in self.items():
      self.removeItem(item)
    self.legend.scene().removeItem(self.legend)
    self.legend = self.addLegend(offset=(10, 10))
    self.lines.clear()
