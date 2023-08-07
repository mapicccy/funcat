# -*- coding: utf-8 -*-
#

import pkgutil

__version__ = pkgutil.get_data(__package__, 'VERSION.txt').decode('ascii').strip()

version_info = tuple(int(v) if v.isdigit() else v for v in __version__.split('.'))

__main_version__ = "%s.%s.x" % (version_info[0], version_info[1])

del pkgutil

from .api import *
from .indicators import *

from .data.tushare_backend import TushareDataBackend
from .data.akshare_backend import AkshareDataBackend
from .data.akshare_hk_backend import AkshareHKDataBackend
from .context import ExecutionContext as funcat_execution_context

funcat_execution_context(date=20170104,
                         order_book_id="000001.SH",
                         data_backend=TushareDataBackend())._push()
