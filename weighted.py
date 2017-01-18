from warnings import warn
warn('This module has been superseded by wquantiles. In future, please import '
     'wquantiles as this module has been deprecated and will not appear in '
     'future releases.', DeprecationWarning)
del warn

from wquantiles import * 
