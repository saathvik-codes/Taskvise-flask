"""TaskVise backend. `core` owns the app, config and storage; `features/*` register the routes."""
from .core import app
from .features import system  # noqa: F401
from .features import auth  # noqa: F401
from .features import pages  # noqa: F401
from .features import employee_api  # noqa: F401
from .features import manager_api  # noqa: F401
from .features import teamlead_api  # noqa: F401
from .features import admin_api  # noqa: F401
from .features import notes_api  # noqa: F401

__all__ = ['app']
