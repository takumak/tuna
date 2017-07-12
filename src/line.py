import numpy as np



class Line:
  def __init__(self, x, y, name):
    self.x = x
    self.y = y
    self.name = name

  @classmethod
  def cleanUp(cls, x, y):
    X, Y = [], []
    for _x, _y in zip(x, y):
      try:
        _x = float(_x)
        _y = float(_y)
        X.append(_x)
        Y.append(_y)
      except (ValueError, TypeError):
        pass

    return np.array(X), np.array(Y)

  def weightCenter(self):
    if len(self.x) == 0:
      return 0
    return sum(self.x*self.y)/sum(self.y)

  def normalize(self):
    return self.__class__(self.x, self.y/sum(self.y), self.name)

  def xoff(self, off):
    return self.__class__(self.x + off, self.y, self.name)

  def __sub__(self, other):
    if list(self.x) != list(other.x):
      raise RuntimeError('x is not same')
    return self.__class__(self.x, self.y - other.y, self.name)

  def peak(self):
    if len(self.x) == 0:
      return 0, 0
    return max(zip(self.x, self.y), key=lambda p: p[1])
