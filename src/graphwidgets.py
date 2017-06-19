import pyqtgraph as pg


class GraphWidget(pg.PlotWidget):
  # https://github.com/LibreOffice/core/blob/master/extras/source/palettes/chart-palettes.soc

  colors = [
    '#004586', '#ff420e', '#ffd320', '#579d1c', '#7e0021', '#83caff',
    '#314004', '#aecf00', '#4b1f6f', '#ff950e', '#c5000b', '#0084d1'
  ]

  def __init__(self):
    vb = pg.ViewBox(border=pg.mkPen(color='#000'))
    super().__init__(viewBox=vb)
    self.setBackground('#fff')
    self.legend = self.addLegend(offset=(10, 10))
    self.lines = []

  def clearItems(self):
    for item in self.items():
      self.removeItem(item)
    self.legend.scene().removeItem(self.legend)
    self.legend = self.addLegend(offset=(10, 10))
    self.lines.clear()

  def add(self, line):
    col = self.colors[(len(self.lines) - 1) % len(self.colors)]
    item = pg.PlotCurveItem(x=line.x, y=line.y, pen=pg.mkPen(color=col, width=2), antialias=True)
    self.addItem(item)
    self.legend.addItem(item, name=line.name)
    self.lines.append(line)
