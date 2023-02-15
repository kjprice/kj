import os

def ensure_directory_exists(dir):
  if not os.path.exists(dir):
    try:
      os.makedirs(dir)
    except FileExistsError:
      pass
