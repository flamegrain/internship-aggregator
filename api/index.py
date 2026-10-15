import sys
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(curr_dir)
for p in [curr_dir, parent_dir]:
    if p and p not in sys.path:
        sys.path.insert(0, p)

import backend.main
from backend.main import app

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = app
