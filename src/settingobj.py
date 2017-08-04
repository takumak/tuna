from PyQt5.QtWidgets import QLabel, QGridLayout, QWidget



class SettingObj:
  def __init__(self):
    self.__items = []
    self.__itemsMap = {}
    self.__objects = []
    self.__widget = None

  def connectAllValueChanged(self, func):
    for item in self.__items:
      item.valueChanged.connect(func)

  def disconnectAllValueChanged(self, func):
    for item in self.__items:
      item.valueChanged.disconnect(func)

  def addSettingObj(self, obj):
    self.__objects.append(obj)

  def addSettingItem(self, item):
    self.__items.append(item)
    self.__itemsMap[item.name] = item
    setattr(self, item.name, item)

  def getSettingWidget(self):
    if self.__widget is None:
      self.__widget = self.createSettingWidget()
    return self.__widget

  def createSettingWidget(self):
    if not self.__items:
      return None
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    for r, p in enumerate(self.__items):
      grid.addWidget(QLabel(p.name), r, 0)
      grid.addWidget(p.getWidget(), r, 1)

    widget = QWidget()
    widget.setLayout(grid)
    return widget

  def saveState(self):
    state = {}
    state['items'] = [{'name': p.name, 'value': p.strValue()} for p in self.__items if p.isSet()]
    for obj in self.__objects:
      state[obj.name] = obj.saveState()
    return state

  def restoreState(self, state):
    if 'items' in state:
      for p in state['items']:
        n = p['name']
        if n in self.__itemsMap:
          self.__itemsMap[n].setStrValue(str(p['value']))
    for obj in self.__objects:
      if obj.name in state:
        obj.restoreState(state[obj.name])
