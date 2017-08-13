from PyQt5.QtGui import QPixmap, QIcon

from icondata import icondata



class TunaIcon(QIcon):
  @classmethod
  def get(cls):
    if hasattr(cls, 'instance'):
      return cls.instance

    icon = cls()
    for data in icondata.values():
      pixmap = QPixmap()
      pixmap.loadFromData(data)
      icon.addPixmap(pixmap)

    cls.instance = icon
    return icon
