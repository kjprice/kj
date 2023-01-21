import os

DATA_DIR = os.path.join('.', 'data')
CACHE_DIR = os.path.join(DATA_DIR, 'cache')

def ensure_directory_exists(dir):
  if not os.path.exists(dir):
    try:
      os.makedirs(dir)
    except FileExistsError:
      pass

def use_cache():
    if 'USE_CACHE' in os.environ:
      use_cache = os.environ['USE_CACHE']
      if use_cache == 'true':
        print('Using cached data')
        return True
    
    return False