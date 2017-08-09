from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QLabel

from toolbase import ToolBase
from settingobj import SettingObj
from commonwidgets import *
from smoothing import *
from bgsubtraction import *
from interpolation import *
from dialogs import *



__all__ = ['ToolWidgetBase', 'MethodSelectorSmooth', 'MethodSelectorBGSub', 'MethodSelectorInterp']



class ToolWidgetBase(QWidget, SettingObj):
  plotRequested = pyqtSignal(ToolBase, bool, name='plotRequested')
  xlsxRecalcMsg = 'Press F9 (for Excel) or Ctrl+Shift+F9 (for LibreOffice) to re-calculate cell formulae'

  def __init__(self, graphWidget):
    super().__init__()
    self.tool = self.toolClass(graphWidget)
    self.tool.cleared.connect(self.clear)
    self.tool.added.connect(self.add)
    self.methodSelectors = []

  def clear(self):
    raise NotImplementedError()

  def add(self, line):
    raise NotImplementedError()

  def saveState(self):
    state = super().saveState()
    state['tool'] = self.tool.saveState()
    for sel in self.methodSelectors:
      state['curr_%s' % sel.name] = sel.currentItem().name
    return state

  def restoreState(self, state):
    super().restoreState(state)
    if 'tool' in state: self.tool.restoreState(state['tool'])
    for sel in self.methodSelectors:
      key = 'curr_%s' % sel.name
      if key in state:
        sel.setCurrentItem(state[key])

  def addMethodSelector(self, sel):
    for obj in sel.items:
      self.addSettingObj(obj)
    self.methodSelectors.append(sel)

  def exportXlsx(self):
    dlg = FileDialog('export_xlsx')
    if dlg.exec_() != dlg.Accepted:
      return
    filename = dlg.selectedFiles()[0]

    import xlsxwriter
    wb = xlsxwriter.Workbook(filename)
    try:
      self.writeXlsx(wb)
    finally:
      wb.close()

  def newSession(self):
    self.tool.newSession()



class MethodSelectorBase(QWidget):
  selectionChanged = pyqtSignal()

  def __init__(self, name, label, items):
    super().__init__()

    self.name  = name
    self.label = label
    self.items = items

    self.combo = ComboBoxWithDescriptor()
    self.descriptors = {}

    vbox = VBoxLayout()
    self.setLayout(vbox)

    hbox = HBoxLayout()
    hbox.addWidget(QLabel(label))
    hbox.addWidget(self.combo)
    hbox2 = HBoxLayout()
    hbox2.addLayout(hbox)
    hbox2.addStretch(1)
    vbox.addLayout(hbox2)
    self.comboHBox = hbox

    optl = VBoxLayout()
    optl.setContentsMargins(40, 0, 0, 0)
    hbox = HBoxLayout()
    hbox.addLayout(optl)
    hbox.addStretch(1)
    vbox.addLayout(hbox)
    self.setup(optl, items)


  def setup(self, optlayout, items):
    def selected(idx):
      for i in range(self.combo.count()):
        item, opt = self.combo.itemData(i)
        if opt is None: continue

        if i == idx:
          opt.show()
        else:
          opt.hide()
      self.selectionChanged.emit()

    for item in items:
      opt = item.getSettingWidget()
      self.combo.addItem(item.label, [item, opt])

      desc = None
      func = getattr(item, 'descriptionWidget', None)
      if callable(func):
        desc = func()
      elif hasattr(item, 'desc'):
        desc = DescriptionWidget()
        desc.addLabel(item.desc)

      if desc:
        self.descriptors[item] = desc
        self.combo.setItemData(self.combo.count()-1, desc, Qt.UserRole+1)

      if opt:
        optlayout.addWidget(opt)

    self.combo.setCurrentIndex(0)
    selected(self.combo.currentIndex())
    self.combo.currentIndexChanged.connect(selected)

  def currentItem(self):
    return self.combo.currentData()[0]

  def setCurrentItem(self, item):
    if isinstance(item, str):
      name = item
    else:
      name = item.name

    for i in range(self.combo.count()):
      item, opt = self.combo.itemData(i)
      if item.name == name:
        self.combo.setCurrentIndex(i)
        break



class MethodSelectorSmooth(MethodSelectorBase):
  def __init__(self):
    super().__init__('smooth', 'Smoothing', [SmoothNop(), SmoothSavGol()])

class MethodSelectorBGSub(MethodSelectorBase):
  def __init__(self):
    super().__init__('bgsub', 'BG subtraction', [
      BGSubNop(), BGSubMinimum(), BGSubLeftEdge(), BGSubRightEdge()])

class MethodSelectorInterp(MethodSelectorBase):
  def __init__(self, dx):
    super().__init__('interp', 'Interpolation', [
      InterpCubicSpline(), InterpLinear(), InterpPchip(),
      InterpAkima(), InterpKrogh(), InterpBarycentric()])

    self.comboHBox.addWidget(QLabel('dx'))
    self.comboHBox.addWidget(dx.getWidget())
