"""Manager and HR JSON API (also project and task progress)."""
from ..core import app
from ..core import (
    DB_BACKEND,
    EMP_CSV,
    LEAVE_CSV,
    LEAVE_FIELDNAMES,
    NOTIFICATION_FIELDNAMES,
    NOTIF_CSV,
    PROJECTS_CSV,
    PROJECT_FIELDNAMES,
    PROJECT_MEMBERS_CSV,
    TASKS_CSV,
    TASK_FIELDNAMES,
    TEAMS_CSV,
    TEAM_FIELDNAMES,
    VALID_LEAVE_STATUSES,
    _mongo_collection,
    _normalize_list_strings,
    _safe_int,
    _sync_project_members,
    append_csv,
    build_manager_analytics_payload,
    calculate_employee_productivity,
    calculate_project_progress,
    create_notification,
    datetime,
    delete_by_id,
    ensure_demo_org_integrity,
    ensure_leave_data_integrity,
    ensure_projects_team_members,
    find_by_id,
    get_default_company_name,
    get_manager_data,
    get_next_project_id,
    get_next_task_id,
    get_team_members,
    jsonify,
    login_required,
    merge_fieldnames,
    normalize_leave_status,
    normalize_project_status,
    normalize_task_status,
    notify_employee_progress_update,
    notify_project_assignment,
    notify_task_assignment,
    notify_user,
    read_csv,
    request,
    session,
    update_by_id,
    update_project_progress,
    write_csv,
)


@app.route('/api/manager/stats')
@login_required
def api_manager_stats():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({})
    user_id = session.get('user_id')
    data = get_manager_data(user_id)
    return jsonify(data.get('stats', {}))


@app.route('/api/manager/employees')
@login_required
def api_manager_employees():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('employees', []))


@app.route('/api/manager/projects')
@login_required
def api_manager_projects():
    ensure_projects_team_members()
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('projects', []))


@app.route('/api/manager/notifications')
@login_required
def api_manager_notifications():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('notifications', []))


@app.route('/api/manager/notifications/read-all', methods=['POST'])
@login_required
def api_manager_notifications_read_all():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
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


@app.route('/api/manager/notifications/<notification_id>/read', methods=['POST'])
@login_required
def api_manager_notification_read(notification_id):
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403
    user_id = session.get('user_id')
    notification = find_by_id(NOTIF_CSV, notification_id)
    if not notification or str(notification.get('user_id', '')).strip() != str(user_id).strip():
        return jsonify({'error': 'notification_not_found'}), 404
    update_by_id(NOTIF_CSV, notification_id, {'is_read': 'true'}, NOTIFICATION_FIELDNAMES)
    return jsonify({'ok': True})


@app.route('/api/manager/tasks/<task_id>', methods=['PUT', 'DELETE'])
@login_required
def api_manager_update_task(task_id):
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403

    if request.method == 'DELETE':
        task = find_by_id(TASKS_CSV, task_id)
        deleted = delete_by_id(TASKS_CSV, task_id, TASK_FIELDNAMES)
        if not deleted:
            return jsonify({'error': 'task_not_found'}), 404
        if task and str(task.get('assignee_id', '')).strip():
            notify_user(
                task.get('assignee_id'),
                'Task Removed',
                f'Task "{task.get("title", "Untitled Task")}" was removed from your assignments.',
                'task',
            )
        return jsonify({'ok': True})

    data = request.get_json(force=True) or {}
    existing_task = find_by_id(TASKS_CSV, task_id)
    if not existing_task:
        return jsonify({'error': 'task_not_found'}), 404

    updates = {}
    if 'title' in data:
        updates['title'] = str(data['title'] or '').strip()
    if 'description' in data:
        updates['description'] = str(data['description'] or '').strip()
    if 'priority' in data:
        updates['priority'] = str(data['priority'] or 'medium').strip().lower()
    if 'status' in data:
        updates['status'] = normalize_task_status(data['status'])
    if 'dueDate' in data or 'due_date' in data:
        raw_due_date = data.get('dueDate', data.get('due_date', ''))
        try:
            dt = datetime.fromisoformat(str(raw_due_date).replace('Z',''))
            updates['due_date'] = dt.strftime('%Y-%m-%d')
        except Exception:
            updates['due_date'] = str(raw_due_date)[:10]
    if 'estimatedHours' in data or 'estimated_hours' in data:
        updates['estimated_hours'] = str(max(0, _safe_int(data.get('estimatedHours', data.get('estimated_hours', 0)), 0)))
    if 'actualHours' in data or 'actual_hours' in data:
        updates['actual_hours'] = str(max(0, _safe_int(data.get('actualHours', data.get('actual_hours', 0)), 0)))
    if 'progress' in data:
        updates['progress'] = str(max(0, min(100, _safe_int(data.get('progress', 0), 0))))
    if 'project_id' in data or 'project' in data:
        updates['project_id'] = str(data.get('project_id', data.get('project', '')) or '').strip()
    if 'assignee_id' in data or 'assignedTo' in data:
        assignee_id = str(data.get('assignee_id', data.get('assignedTo', '')) or '').strip()
        assignee = next(
            (employee for employee in read_csv(EMP_CSV) if str(employee.get('id', '')).strip() == assignee_id),
            None,
        )
        if assignee_id and not assignee:
            return jsonify({'error': 'assignee_not_found'}), 404
        updates['assignee_id'] = assignee_id
        updates['assignee_name'] = assignee.get('name', '') if assignee else ''
    if not updates:
        return jsonify({'error': 'nothing_to_update'}), 400

    updated = update_by_id(TASKS_CSV, task_id, updates, TASK_FIELDNAMES)
    if not updated:
        return jsonify({'error': 'task_not_found'}), 404

    task_after = find_by_id(TASKS_CSV, task_id) or {**existing_task, **updates}
    if str(task_after.get('assignee_id', '')).strip():
        notify_task_assignment(
            task_after,
            actor_label=session.get('full_name') or session.get('role', 'Manager').title(),
            is_new_assignment=str(existing_task.get('assignee_id', '')).strip() != str(task_after.get('assignee_id', '')).strip(),
        )
    return jsonify({'ok': True})


@app.route('/api/manager/projects/<project_id>', methods=['PUT'])
@login_required
def api_manager_update_project(project_id):
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True) or {}
    project_before = find_by_id(PROJECTS_CSV, project_id)
    if not project_before:
        return jsonify({'error': 'project_not_found'}), 404
    updates = {}
    for k in ['name', 'description']:
        if k in data:
            updates[k] = str(data[k] or '').strip()
    if 'status' in data:
        updates['status'] = normalize_project_status(data.get('status'))
    if 'deadline' in data or 'end_date' in data:
        raw_deadline = data.get('deadline', data.get('end_date', ''))
        try:
            dt = datetime.fromisoformat(str(raw_deadline).replace('Z',''))
            updates['end_date'] = dt.strftime('%Y-%m-%d')
        except Exception:
            updates['end_date'] = str(raw_deadline)[:10]
    if 'owner_id' in data:
        updates['owner_id'] = str(data.get('owner_id', '') or '').strip()
    if 'company' in data:
        updates['company'] = str(data.get('company') or get_default_company_name()).strip()
    if 'progress' in data:
        updates['progress'] = str(max(0, min(100, _safe_int(data.get('progress', 0), 0))))
    team_members = None
    if 'teamMembers' in data or 'team_members' in data:
        team_members = _normalize_list_strings(data.get('teamMembers', data.get('team_members', [])) or [])
        updates['team_members'] = ','.join(team_members)
    if not updates:
        return jsonify({'error': 'nothing_to_update'}), 400

    updated = update_by_id(PROJECTS_CSV, project_id, updates, PROJECT_FIELDNAMES)
    if not updated:
        return jsonify({'error': 'project_not_found'}), 404
    if team_members is not None:
        _sync_project_members(project_id, team_members)
    project_after = find_by_id(PROJECTS_CSV, project_id) or {**project_before, **updates}
    notify_project_assignment(
        project_after,
        actor_label=session.get('full_name') or session.get('role', 'Manager').title(),
        is_new_assignment=False,
    )
    return jsonify({'ok': True})


@app.route('/api/manager/projects/<project_id>', methods=['DELETE'])
@login_required
def api_manager_delete_project(project_id):
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403

    deleted = delete_by_id(
        PROJECTS_CSV,
        project_id,
        ['id','name','description','owner_id','start_date','end_date','status']
    )
    if not deleted:
        return jsonify({'error': 'project_not_found'}), 404

    member_rows = read_csv(PROJECT_MEMBERS_CSV)
    filtered_members = [m for m in member_rows if str(m.get('project_id')) != str(project_id)]
    write_csv(
        PROJECT_MEMBERS_CSV,
        filtered_members,
        merge_fieldnames(member_rows, ['id', 'project_id', 'employee_id'])
    )

    task_rows = read_csv(TASKS_CSV)
    tasks_changed = False
    for task in task_rows:
        if str(task.get('project_id')) == str(project_id):
            task['project_id'] = ''
            tasks_changed = True
    if tasks_changed:
        write_csv(
            TASKS_CSV,
            task_rows,
            merge_fieldnames(task_rows, ['id','title','description','project_id','assignee_id','status','priority','created_at','due_date'])
        )

    return jsonify({'ok': True})


@app.route('/api/manager/leave')
@login_required
def api_manager_leave_list():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify([])
    actor_role = session.get('role')
    status = normalize_leave_status(request.args.get('status'))
    rows = ensure_leave_data_integrity()
    if actor_role not in {'hr', 'admin'}:
        visible_ids = {
            str(employee.get('id', '')).strip()
            for employee in get_manager_data(session.get('user_id')).get('employees', [])
            if str(employee.get('id', '')).strip()
        }
        rows = [row for row in rows if str(row.get('employee_id', '')).strip() in visible_ids]
    if status:
        rows = [r for r in rows if normalize_leave_status(r.get('status')) == status]
    return jsonify(rows)


@app.route('/api/manager/leave/update', methods=['POST'])
@login_required
def api_manager_leave_update():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403
    actor_role = session.get('role')
    data = request.get_json(force=True) or {}
    leave_id = data.get('id')
    new_status = normalize_leave_status(data.get('status'))
    if not leave_id or new_status not in VALID_LEAVE_STATUSES:
        return jsonify({'error': 'invalid'}), 400
    rows = ensure_leave_data_integrity()
    leave_row = next((r for r in rows if str(r.get('id')) == str(leave_id)), None)
    if not leave_row:
        return jsonify({'error': 'not found'}), 404
    if actor_role not in {'hr', 'admin'}:
        visible_ids = {
            str(employee.get('id', '')).strip()
            for employee in get_manager_data(session.get('user_id')).get('employees', [])
            if str(employee.get('id', '')).strip()
        }
        if str(leave_row.get('employee_id', '')).strip() not in visible_ids:
            return jsonify({'error': 'forbidden'}), 403

    updated = update_by_id(LEAVE_CSV, leave_id, {'status': new_status}, LEAVE_FIELDNAMES)
    if not updated:
        return jsonify({'error': 'not found'}), 404

    if new_status in ['approved', 'rejected']:
        leave_type = str(leave_row.get('type') or 'leave').replace('-', ' ').title()
        start_date = str(leave_row.get('start_date') or '')
        end_date = str(leave_row.get('end_date') or '')
        create_notification(
            leave_row.get('employee_id'),
            f"Leave Request {new_status.title()}",
            f"Your {leave_type} leave request ({start_date} to {end_date}) was {new_status}.",
            'leave',
        )
    return jsonify({'ok': True})


@app.route('/api/manager/tasks')
@login_required
def api_manager_tasks():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify([])
    manager_data = get_manager_data(session.get('user_id'))
    return jsonify(manager_data.get('tasks', []))


@app.route('/api/manager/tasks/assign', methods=['POST'])
@login_required
def api_manager_assign_task():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True) or {}
    existing_tasks = read_csv(TASKS_CSV)
    task_id = get_next_task_id(existing_tasks)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    assignee_id = str(data.get('assignedTo', data.get('assignee_id', '')) or '').strip()
    project_id = str(data.get('project', data.get('project_id', '')) or '').strip()
    due_date = str(data.get('due_date', data.get('dueDate', '')) or '').strip()[:10]
    assignee_name = ''
    for employee in read_csv(EMP_CSV):
        if str(employee.get('id', '')).strip() == assignee_id:
            assignee_name = employee.get('name', '')
            break
    row = {
        'id': task_id,
        'title': data.get('title','').strip(),
        'description': data.get('description',''),
        'project_id': project_id,
        'assignee_id': assignee_id,
        'assignee_name': assignee_name,
        'status': normalize_task_status(data.get('status', 'pending')),
        'priority': str(data.get('priority','medium') or 'medium').strip().lower(),
        'created_at': created_at,
        'due_date': due_date,
        'estimated_hours': str(_safe_int(data.get('estimated_hours', data.get('estimatedHours', 0)), 0)),
        'actual_hours': str(_safe_int(data.get('actual_hours', data.get('actualHours', 0)), 0)),
        'progress': str(max(0, min(100, _safe_int(data.get('progress', 0), 0)))),
    }
    append_csv(TASKS_CSV, row, TASK_FIELDNAMES)
    ensure_demo_org_integrity(force=True)
    notify_task_assignment(row, actor_label=session.get('full_name') or session.get('role', 'Manager').title(), is_new_assignment=True)
    return jsonify({'id': task_id, 'ok': True})


@app.route('/api/manager/projects/create', methods=['POST'])
@login_required
def api_manager_create_project():
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
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
    ensure_demo_org_integrity(force=True)
    notify_project_assignment(row, actor_label=session.get('full_name') or session.get('role', 'Manager').title(), is_new_assignment=True)
    return jsonify({'id': project_id, 'ok': True})


@app.route('/api/manager/team/members', methods=['GET'])
@login_required
def api_manager_team_members():
    """Get all employees under this manager"""
    if session.get('role') != 'manager':
        return jsonify([])

    manager_id = session.get('user_id')
    team_member_ids = get_team_members(manager_id)

    if not team_member_ids:
        return jsonify([])

    employees = read_csv(EMP_CSV)
    team_emps = [e for e in employees if e.get('id') in team_member_ids]

    result = []
    for emp in team_emps:
        result.append({
            'id': emp.get('id'),
            'name': emp.get('name'),
            'email': emp.get('email'),
            'position': emp.get('position'),
            'department': emp.get('department'),
            'productivity': calculate_employee_productivity(emp.get('id'))
        })

    return jsonify(result)


@app.route('/api/manager/team/assign', methods=['POST'])
@login_required
def api_manager_assign_team():
    """Assign employees to a manager."""
    if session.get('role') != 'manager':
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(force=True) or {}
    manager_id = session.get('user_id')
    employee_ids = _normalize_list_strings(data.get('employee_ids', []))

    if DB_BACKEND != 'mongodb':
        ensure_demo_org_integrity()
        teams = read_csv(TEAMS_CSV)
        team = next((row for row in teams if str(row.get('manager_id', '')).strip() == str(manager_id).strip()), None)
        if not team:
            return jsonify({'error': 'team_not_found'}), 404

        # Ensure employees stay in one team only.
        for row in teams:
            if row is team:
                continue
            current_members = _normalize_list_strings(str(row.get('member_ids', '')).split(','))
            next_members = [member_id for member_id in current_members if member_id not in employee_ids]
            if next_members != current_members:
                row['member_ids'] = ','.join(next_members)

        team['member_ids'] = ','.join(employee_ids)
        team['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        write_csv(TEAMS_CSV, teams, TEAM_FIELDNAMES)
        ensure_demo_org_integrity(force=True)
        return jsonify({'ok': True})

    try:
        team_coll = _mongo_collection('team_assignments')
        team_coll.update_one(
            {'manager_id': manager_id},
            {'$set': {
                'manager_id': manager_id,
                'manager_name': session.get('full_name'),
                'employee_ids': employee_ids,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }},
            upsert=True
        )
        return jsonify({'ok': True})
    except Exception as e:
        print(f"Team assignment error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/project/<project_id>/progress', methods=['PUT'])
@login_required
def api_update_project_progress(project_id):
    """Update project progress"""
    if session.get('role') not in ['manager', 'admin']:
        return jsonify({'error': 'forbidden'}), 403

    try:
        update_project_progress(project_id)
        progress = calculate_project_progress(project_id)
        return jsonify({'progress': progress, 'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/task/<task_id>/progress', methods=['PUT'])
@login_required
def api_update_task_progress(task_id):
    """Update task progress"""
    data = request.get_json(force=True) or {}
    progress = int(data.get('progress', 0))

    try:
        update_by_id(TASKS_CSV, task_id, {'progress': str(progress)}, TASK_FIELDNAMES)

        task = find_by_id(TASKS_CSV, task_id)
        if task and task.get('project_id'):
            update_project_progress(task['project_id'])
        actor_id = str(session.get('user_id') or (task or {}).get('assignee_id') or '').strip()
        if task and actor_id:
            notify_employee_progress_update(task, actor_id, 'progress', f'{progress}%')

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/manager/analytics')
@login_required
def api_manager_analytics():
    """Get manager analytics for team performance"""
    user_id = session.get('user_id')
    if session.get('role') not in ['manager', 'hr', 'admin', 'teamlead']:
        return jsonify({'error': 'forbidden'}), 403

    return jsonify(build_manager_analytics_payload(user_id))
