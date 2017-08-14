import os
import struct

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
icondir = os.path.join(rootdir, 'icon')

sizes = [
  (b'icp4', 16),
  (b'icp5', 32),
  (b'icp6', 64),
  (b'ic07', 128),
  (b'ic10', 1024)
]

with open(os.path.join(icondir, 'tuna.icns'), 'wb') as f:
  filesize = 8
  f.seek(8, 0) # 0 means "from start of file"

  for header, size in sizes:
    data = open(os.path.join(icondir, 'icon-%d.png' % size), 'rb').read()
    blocksize = 8 + len(data)
    f.write(struct.pack('>4sI', header, blocksize))
    f.write(data)
    filesize += blocksize

  f.seek(0, 0)
  f.write(struct.pack('>4sI', b'icns', filesize))
