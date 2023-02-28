import os
import sys
import subprocess
from datetime import datetime
from copy import deepcopy


root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
entry_point = os.path.join(root_path, 'edamon.py')

dt = datetime.now()

dt_start = deepcopy(dt).replace(
    hour=12,
    minute=0,
    second=0,
    microsecond=0
)
dt_end = deepcopy(dt).replace(
    hour=16,
    minute=0,
    second=0,
    microsecond=0
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
timespan = dt_start.strftime(dt_fmt) + " " + dt_end.strftime(dt_fmt)

subprocess.call(['python', entry_point, timespan])
