"""Team lead JSON API."""
from ..core import app
from .manager_api import api_manager_delete_project, api_manager_update_project, api_manager_update_task
from ..core import (
    EMP_CSV,
    NOTIFICATION_FIELDNAMES,
    NOTIF_CSV,
    PROJECTS_CSV,
    PROJECT_FIELDNAMES,
    TASKS_CSV,
    TASK_FIELDNAMES,
    _normalize_list_strings,
    _safe_int,
    _sync_project_members,
    append_csv,
    build_manager_analytics_payload,
    datetime,
    find_by_id,
    get_default_company_name,
    get_manager_data,
    get_next_project_id,
    get_next_task_id,
    jsonify,
    login_required,
    merge_fieldnames,
    normalize_project_status,
    normalize_task_status,
    notify_project_assignment,
    notify_task_assignment,
    read_csv,
    request,
    session,
    update_by_id,
    write_csv,
)


@app.route('/api/teamlead/stats')
@login_required
def api_teamlead_stats():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    user_id = session.get('user_id')
    data = get_manager_data(user_id)
    return jsonify(data.get('stats', {}))


@app.route('/api/teamlead/notifications')
@login_required
def api_teamlead_notifications():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('notifications', []))


@app.route('/api/teamlead/notifications/read-all', methods=['POST'])
@login_required
def api_teamlead_notifications_read_all():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    user_id = session.get('user_id')
    rows = read_csv(NOTIF_CSV)
    changed = False
    for row in rows:
        if str(row.get('user_id', '')).strip() != str(user_id).strip():
            continue
        if str(row.get('is_read', 'false')).lower() != 'true':
            row['is_read'] = 'true'
            changed = True
    if changed:
        write_csv(NOTIF_CSV, rows, merge_fieldnames(rows, NOTIFICATION_FIELDNAMES))
    return jsonify({'ok': True, 'updated': changed})


@app.route('/api/teamlead/notifications/<notification_id>/read', methods=['POST'])
@login_required
def api_teamlead_notification_read(notification_id):
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    user_id = session.get('user_id')
    notification = find_by_id(NOTIF_CSV, notification_id)
    if not notification or str(notification.get('user_id', '')).strip() != str(user_id).strip():
        return jsonify({'error': 'notification_not_found'}), 404
    update_by_id(NOTIF_CSV, notification_id, {'is_read': 'true'}, NOTIFICATION_FIELDNAMES)
    return jsonify({'ok': True})


@app.route('/api/teamlead/employees')
@login_required
def api_teamlead_employees():
    if session.get('role') != 'teamlead':
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('employees', []))


@app.route('/api/teamlead/projects')
@login_required
def api_teamlead_projects():
    if session.get('role') != 'teamlead':
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('projects', []))


@app.route('/api/teamlead/tasks')
@login_required
def api_teamlead_tasks():
    if session.get('role') != 'teamlead':
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('tasks', []))


@app.route('/api/teamlead/analytics')
@login_required
def api_teamlead_analytics():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    return jsonify(build_manager_analytics_payload(session.get('user_id')))


@app.route('/api/teamlead/tasks/assign', methods=['POST'])
@login_required
def api_teamlead_assign_task():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True) or {}
    existing_tasks = read_csv(TASKS_CSV)
    task_id = get_next_task_id(existing_tasks)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    assignee_id = str(data.get('assignee_id', data.get('assignedTo', '')) or '').strip()
    project_id = str(data.get('project_id', data.get('project', '')) or '').strip()
    assignee_name = data.get('assignee_name','')
    try:
        emps = read_csv(EMP_CSV)
        for e in emps:
            if str(e.get('id', '')).strip() == assignee_id:
                assignee_name = e.get('name') or assignee_name
                break
    except Exception:
        pass

    row = {
        'id': task_id,
        'title': data.get('title','Untitled Task'),
        'description': data.get('description',''),
        'project_id': project_id,
        'assignee_id': assignee_id,
        'assignee_name': assignee_name or '',
        'status': normalize_task_status(data.get('status','pending')),
        'priority': str(data.get('priority','medium') or 'medium').strip().lower(),
        'created_at': created_at,
        'due_date': str(data.get('due_date', data.get('dueDate', '')) or '')[:10],
        'estimated_hours': str(_safe_int(data.get('estimated_hours', data.get('estimatedHours', 0)), 0)),
        'actual_hours': str(_safe_int(data.get('actual_hours', data.get('actualHours', 0)), 0)),
        'progress': str(max(0, min(100, _safe_int(data.get('progress', 0), 0)))),
    }
    append_csv(TASKS_CSV, row, TASK_FIELDNAMES)
    notify_task_assignment(row, actor_label=session.get('full_name') or 'Team Lead', is_new_assignment=True)
    return jsonify({'id': task_id, 'ok': True})


@app.route('/api/teamlead/tasks/<task_id>', methods=['PUT', 'DELETE'])
@login_required
def api_teamlead_update_task(task_id):
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    return api_manager_update_task(task_id)


@app.route('/api/teamlead/projects/create', methods=['POST'])
@login_required
def api_teamlead_create_project():
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True) or {}
    existing_projects = read_csv(PROJECTS_CSV)
    project_id = get_next_project_id(existing_projects)
    now = datetime.now().strftime('%Y-%m-%d')
    members = _normalize_list_strings(data.get('teamMembers', data.get('team_members', [])) or [])
    row = {
        'id': project_id,
        'name': data.get('name','').strip(),
        'description': data.get('description',''),
        'owner_id': str(data.get('owner_id') or session.get('user_id','')).strip(),
        'start_date': now,
        'end_date': str(data.get('deadline', data.get('end_date', '')) or '')[:10],
        'status': normalize_project_status(data.get('status','planning')),
        'team_members': ','.join(members),
        'company': str(data.get('company') or get_default_company_name()).strip(),
        'progress': str(max(0, min(100, _safe_int(data.get('progress', 0), 0)))),
    }
    append_csv(PROJECTS_CSV, row, PROJECT_FIELDNAMES)
    _sync_project_members(project_id, members)
    notify_project_assignment(row, actor_label=session.get('full_name') or 'Team Lead', is_new_assignment=True)
    return jsonify({'id': project_id, 'ok': True})


@app.route('/api/teamlead/projects/<project_id>', methods=['PUT'])
@login_required
def api_teamlead_update_project(project_id):
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    return api_manager_update_project(project_id)


@app.route('/api/teamlead/projects/<project_id>', methods=['DELETE'])
@login_required
def api_teamlead_delete_project(project_id):
    if session.get('role') != 'teamlead':
        return jsonify({'error': 'forbidden'}), 403
    return api_manager_delete_project(project_id)
