import numpy as np



class Line:
  def __init__(self, name, x, y, y_):
    self.name = name
    self.x = np.array(x)
    self.y = np.array(y)
    self.y_ = np.array(y_)

  @classmethod
  def cleanUp(cls, x, y, y_):
    X, Y, Y_ = [], [], []
    for xi, yi, yi_ in zip(x, y, y_):
      try:
        xi = float(xi)
        yi = float(yi)
        yi_ = float(yi_)
        X.append(xi)
        Y.append(yi)
        Y_.append(yi_)
      except (ValueError, TypeError):
        pass

    return np.array(X), np.array(Y), np.array(Y_)

  def weightCenter(self):
    if len(self.x) == 0: return 0
    return np.sum(self.x*self.y)/np.sum(self.y)

  def normalize(self):
    if len(self.x) == 0: return self
    return self.__class__(self.name, self.x, self.y/np.sum(self.y))

  def xoff(self, off):
    return self.__class__(self.name, self.x + off, self.y)

  def __sub__(self, other):
    if list(self.x) != list(other.x):
      raise RuntimeError('x is not same')
    return self.__class__(self.name, self.x, self.y - other.y)

  def peak(self):
    if len(self.x) == 0:
      return 0, 0
    return max(zip(self.x, self.y), key=lambda p: p[1])
