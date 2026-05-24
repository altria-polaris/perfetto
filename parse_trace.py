import sys
with open('test_ggo.pftrace', 'rb') as f:
  data = f.read()
print(f"File size: {len(data)}")
