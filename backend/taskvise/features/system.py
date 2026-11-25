"""Health checks, static files and error handlers."""
from ..core import app
from ..core import (
    CSV_SHADOW_SYNC,
    DB_BACKEND,
    MIRROR_MONGODB,
    MIRROR_MYSQL,
    MONGO_DATABASE,
    MONGO_URI,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MongoClient,
    SOURCE_STATIC_DIR,
    STORAGE_ROOT,
    _mongo_client,
    _mysql_connect,
    datetime,
    jsonify,
    mysql,
    os,
    render_template,
    request,
    send_from_directory,
)


@app.route('/api/system/health')
def api_system_health():
    """Check system health including MongoDB and MySQL connectivity."""
    mongo_connected = False
    mongo_status = "Disconnected"
    mysql_connected = False
    mysql_status = "Disconnected"

    try:
        if MongoClient is not None:
            client = _mongo_client()
            client.admin.command('ping')
            mongo_connected = True
            mongo_status = "Connected"
    except Exception as e:
        mongo_status = f"Error: {str(e)[:50]}"

    try:
        if mysql is not None:
            conn = _mysql_connect(include_database=False)
            conn.close()
            mysql_connected = True
            mysql_status = "Connected"
    except Exception as e:
        mysql_status = f"Error: {str(e)[:50]}"

    return jsonify({
        'mongodb': {
            'connected': mongo_connected,
            'status': mongo_status,
            'uri': MONGO_URI if mongo_connected else 'N/A',
            'database': MONGO_DATABASE
        },
        'mysql': {
            'connected': mysql_connected,
            'status': mysql_status,
            'host': MYSQL_HOST,
            'database': MYSQL_DATABASE,
        },
        'backend': DB_BACKEND,
        'mirrors': {
            'mysql': MIRROR_MYSQL,
            'mongodb': MIRROR_MONGODB,
            'csv_shadow': CSV_SHADOW_SYNC,
        },
        'timestamp': datetime.now().isoformat()
    })


@app.route('/static/<path:p>')
def static_proxy(p):
    runtime_static_dir = os.path.join(STORAGE_ROOT, 'static')
    runtime_asset_path = os.path.join(runtime_static_dir, p)
    if (
        os.path.abspath(runtime_static_dir) != os.path.abspath(SOURCE_STATIC_DIR)
        and os.path.exists(runtime_asset_path)
    ):
        return send_from_directory(runtime_static_dir, p)
    return send_from_directory(SOURCE_STATIC_DIR, p)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith('/api/') or request.path.startswith('/static/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('404.html'), 404
