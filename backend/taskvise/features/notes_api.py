"""Team notes API."""
from ..core import app
from ..core import (
    NOTES_CSV,
    append_csv,
    datetime,
    ensure_notes_csv,
    jsonify,
    login_required,
    read_csv,
    request,
    session,
    uuid,
    write_csv,
)


@app.route('/api/notes', methods=['GET'])
@login_required
def api_notes_list():
    ensure_notes_csv()
    rows = read_csv(NOTES_CSV)
    return jsonify(rows)


@app.route('/api/notes', methods=['POST'])
@login_required
def api_notes_create():
    ensure_notes_csv()
    data = request.get_json(force=True) or {}
    note_id = str(uuid.uuid4())
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = {
        'id': note_id,
        'title': (data.get('title') or '').strip(),
        'content': data.get('content') or '',
        'author': session.get('full_name') or session.get('username') or 'User',
        'author_id': session.get('user_id',''),
        'priority': data.get('priority','medium'),
        'is_pinned': 'true' if data.get('is_pinned') in [True,'true','1'] else 'false',
        'created_at': now,
        'updated_at': now,
        'visible_to': 'all'
    }
    append_csv(NOTES_CSV, row, ['id','title','content','author','author_id','priority','is_pinned','created_at','updated_at','visible_to'])
    return jsonify({'ok': True, 'id': note_id})


@app.route('/api/notes/<note_id>', methods=['PUT'])
@login_required
def api_notes_update(note_id):
    ensure_notes_csv()
    data = request.get_json(force=True) or {}
    rows = read_csv(NOTES_CSV)
    updated = False
    for r in rows:
        if str(r.get('id')) == str(note_id):
            if 'title' in data: r['title'] = data['title']
            if 'content' in data: r['content'] = data['content']
            if 'priority' in data: r['priority'] = data['priority']
            if 'is_pinned' in data: r['is_pinned'] = 'true' if data.get('is_pinned') in [True,'true','1'] else 'false'
            r['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            updated = True
            break
    if not updated:
        return jsonify({'error': 'not_found'}), 404
    write_csv(NOTES_CSV, rows, ['id','title','content','author','author_id','priority','is_pinned','created_at','updated_at','visible_to'])
    return jsonify({'ok': True})


@app.route('/api/notes/<note_id>', methods=['DELETE'])
@login_required
def api_notes_delete(note_id):
    ensure_notes_csv()
    rows = read_csv(NOTES_CSV)
    new_rows = [r for r in rows if str(r.get('id')) != str(note_id)]
    write_csv(NOTES_CSV, new_rows, ['id','title','content','author','author_id','priority','is_pinned','created_at','updated_at','visible_to'])
    return jsonify({'ok': True})
