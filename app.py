import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.taskvise import app  # noqa: E402
from backend.taskvise.core import *  # noqa: E402,F401,F403

if __name__ == '__main__':
    create_sample_users()
    ensure_demo_org_integrity(force=True)
    sync_demo_role_passwords()
    debug_enabled = _truthy(os.environ.get('TASKVISE_DEBUG', 'true'), default=True)
    reloader_override = os.environ.get('TASKVISE_USE_RELOADER')
    if reloader_override is None:
        use_reloader = os.name != 'nt'
    else:
        use_reloader = _truthy(reloader_override, default=False)
    app.run(
        debug=debug_enabled,
        port=_safe_int(os.environ.get('PORT', '5000'), 5000),
        use_reloader=use_reloader,
    )
