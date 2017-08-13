import os, sys
from PyQt5.QtCore import Qt, QRectF, QByteArray, QBuffer
from PyQt5.QtGui import QImage, QPainter, QGuiApplication
from PyQt5.QtSvg import QSvgRenderer


rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
srcdir = os.path.join(rootdir, 'src')
icondir = os.path.join(rootdir, 'icon')

app = QGuiApplication(sys.argv)

icons = []
svg_small = QSvgRenderer(os.path.join(icondir, 'tuna_small.svg'))
svg_big = QSvgRenderer(os.path.join(icondir, 'tunacan.svg'))
for size in (16, 24, 32, 48, 128, 1024):
  print('generate: %d' % size)
  if size <= 48:
    renderer = svg_small
  else:
    renderer = svg_big

  img = QImage(size, size, QImage.Format_ARGB32)
  img.fill(Qt.transparent)
  painter = QPainter(img)
  renderer.render(painter, QRectF(0, 0, size, size))
  painter.end()

  data = QByteArray()
  buf = QBuffer(data)
  buf.open(buf.WriteOnly)
  img.save(buf, 'PNG')
  buf.close()

  data = data.data()
  icons.append((size, data))
  with open(os.path.join(icondir, 'icon-%d.png' % size), 'wb') as f:
    f.write(data)


with open(os.path.join(srcdir, 'icondata.py'), 'w') as f:
  f.write('icondata = {\n')
  for size, data in icons:
    f.write('  %d: %s,\n' % (size, repr(data)))
  f.write('}\n')

print('done')
