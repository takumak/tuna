def getTableColumnLabel(c):
  label = ''
  while True:
    label = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[c % 26] + label
    if c < 26:
      break
    c = c//26-1
  return label

def parseTableColumnLabel(label):
  if not label:
    raise ValueError('Invalid label: %s' % label)
  ret = -1
  for c in map(ord, label):
    if 0x41 <= c <= 0x5A:
      ret = (ret+1)*26 + (c-0x41)
    else:
      raise ValueError('Invalid label: %s' % label)
  return ret

def getTableCellName(r, c, absx='', absy=''):
  return '%s%s%s%d' % (absx, getTableColumnLabel(c), absy, r+1)

class blockable:
  class functor:
    def __init__(self, blocker, targetobj):
      self.blocker = blocker
      self.targetobj = targetobj

    def block(self):
      self.blocker.blocked[self.targetobj] = True

    def unblock(self):
      self.blocker.blocked[self.targetobj] = False

    def isBlocked(self):
      return self.blocker.blocked.get(self.targetobj, False)

    def __call__(self, *args, **kwargs):
      if self.isBlocked(): return None
      return self.blocker.func(self.targetobj, *args, **kwargs)

  def __init__(self, func):
    self.func = func
    self.blocked = {}

  def __get__(self, obj, cls):
    return self.functor(self, obj)
