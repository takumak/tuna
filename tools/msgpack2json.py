import sys, json, umsgpack
json.dump(umsgpack.unpack(sys.stdin.buffer), sys.stdout)
