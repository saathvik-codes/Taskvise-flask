"""Employee JSON API: tasks, projects, leave, help requests, profile, settings, reports."""
from ..core import app
from ..core import (
    AVATAR_UPLOAD_DIR,
    EMP_CSV,
    EMP_FIELDNAMES,
    HELP_REQUESTS_CSV,
    HELP_REQUEST_FIELDNAMES,
    LEAVE_CSV,
    LEAVE_FIELDNAMES,
    NOTIFICATION_FIELDNAMES,
    NOTIF_CSV,
    PROJECTS_CSV,
    PROJECT_MEMBERS_CSV,
    TASKS_CSV,
    TASK_FIELDNAMES,
    TASK_SUBMISSIONS_CSV,
    TASK_SUBMISSION_FIELDNAMES,
    TASK_SUBMISSION_UPLOAD_DIR,
    USERS_CSV,
    USER_FIELDNAMES,
    WORK_CSV,
    _allowed_task_submission,
    _normalize_help_request_rows,
    _normalize_list_strings,
    _resolve_current_employee_context,
    _resolve_help_request_recipients,
    _resolve_session_employee_task,
    _safe_int,
    _serialize_task_submission,
    _submission_download_path,
    _truthy,
    append_csv,
    create_notification,
    datetime,
    delete_by_id,
    ensure_demo_org_integrity,
    ensure_leave_data_integrity,
    ensure_projects_team_members,
    find_by_id,
    generate_password_hash,
    get_default_company_name,
    get_employee_data,
    get_manager_for_employee,
    get_next_task_id,
    get_team_members,
    get_teamlead_for_employee,
    get_user_settings_record,
    jsonify,
    login_required,
    merge_fieldnames,
    normalize_leave_status,
    normalize_role,
    normalize_task_status,
    notify_employee_progress_update,
    notify_user,
    notify_users,
    os,
    read_csv,
    request,
    resolve_employee_candidate_ids,
    save_user_settings_record,
    secure_filename,
    session,
    task_matches_employee,
    update_by_id,
    update_project_progress,
    url_for,
    uuid,
    verify_password,
    write_csv,
)


@app.route('/api/employee/tasks/update-status', methods=['POST'])
@login_required
def api_employee_update_task_status():
    ensure_demo_org_integrity()
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(force=True) or {}
    task_id = data.get('task_id') or data.get('id')
    new_status = data.get('status')
    if not task_id or not new_status:
        return jsonify({'error': 'missing parameters'}), 400
    new_status = normalize_task_status(new_status)
    task, employee_id, _employee, _candidate_ids = _resolve_session_employee_task(task_id)
    if not task:
        return jsonify({'error': 'not found or forbidden'}), 404
    updates = {'status': new_status}
    if employee_id:
        updates['assignee_id'] = employee_id
    if new_status == 'completed':
        updates['progress'] = '100'
        if _safe_int(task.get('actual_hours', 0), 0) <= 0:
            updates['actual_hours'] = str(max(1, _safe_int(task.get('estimated_hours', 1), 1)))
    elif new_status == 'in-progress' and _safe_int(task.get('progress', 0), 0) <= 0:
        updates['progress'] = '10'
    updated = update_by_id(TASKS_CSV, task_id, updates, TASK_FIELDNAMES)
    if not updated:
        return jsonify({'error': 'update failed'}), 500
    updated_task = find_by_id(TASKS_CSV, task_id) or task
    if updated_task.get('project_id'):
        update_project_progress(updated_task['project_id'])
    notify_employee_progress_update(updated_task, employee_id or user_id, 'status', new_status.replace('-', ' '))
    return jsonify({'ok': True})


@app.route('/api/employee/tasks/start-timer', methods=['POST'])
@login_required
def api_employee_start_task_timer():
    ensure_demo_org_integrity()
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(force=True) or {}
    task_id = str(data.get('task_id') or data.get('id') or '').strip()
    if not task_id:
        return jsonify({'error': 'missing_task_id'}), 400

    task, employee_id, _employee, _candidate_ids = _resolve_session_employee_task(task_id)
    if not task:
        return jsonify({'error': 'task_not_found'}), 404

    work_logs = read_csv(WORK_CSV)
    active_log = next((
        row for row in work_logs
        if str(row.get('employee_id', '')).strip() == str(employee_id or user_id).strip()
        and str(row.get('task_id', '')).strip() == task_id
        and not str(row.get('end_time') or '').strip()
    ), None)
    if active_log:
        return jsonify({'ok': True, 'already_running': True, 'work_log_id': active_log.get('id')})

    started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    work_row = {
        'id': str(uuid.uuid4()),
        'employee_id': str(employee_id or user_id).strip(),
        'task_id': task_id,
        'start_time': started_at,
        'end_time': '',
        'duration_minutes': '0',
        'notes': str(data.get('notes') or 'Timer started from employee dashboard.').strip(),
    }
    append_csv(WORK_CSV, work_row, ['id', 'employee_id', 'task_id', 'start_time', 'end_time', 'duration_minutes', 'notes'])
    update_by_id(
        TASKS_CSV,
        task_id,
        {
            'assignee_id': str(employee_id or user_id).strip(),
            'status': 'in-progress',
            'progress': str(max(10, _safe_int(task.get('progress', 0), 0))),
        },
        TASK_FIELDNAMES,
    )
    updated_task = find_by_id(TASKS_CSV, task_id) or task
    if updated_task.get('project_id'):
        update_project_progress(updated_task['project_id'])
    notify_employee_progress_update(updated_task, employee_id or user_id, 'timer', 'started')
    return jsonify({'ok': True, 'work_log_id': work_row['id'], 'started_at': started_at})


@app.route('/api/employee/task-submissions')
@login_required
def api_employee_task_submissions():
    employee_id, _employee, candidate_ids, _employees = _resolve_current_employee_context()
    if not employee_id and not candidate_ids:
        return jsonify([])

    rows = [
        _serialize_task_submission(row)
        for row in read_csv(TASK_SUBMISSIONS_CSV)
        if str(row.get('employee_id') or '').strip() == str(employee_id or '').strip()
        or str(row.get('employee_id') or '').strip() in candidate_ids
    ]
    rows.sort(key=lambda row: row.get('created_at', ''), reverse=True)
    return jsonify(rows)


@app.route('/api/employee/tasks/upload', methods=['POST'])
@login_required
def api_employee_upload_task_submission():
    ensure_demo_org_integrity()
    employee_id, employee, candidate_ids, _employees = _resolve_current_employee_context()
    if not employee_id and not candidate_ids:
        return jsonify({'error': 'unauthorized'}), 401

    task_id = str(request.form.get('task_id') or '').strip()
    notes = str(request.form.get('notes') or '').strip()
    uploaded_file = request.files.get('submission') or request.files.get('file')
    if not task_id:
        return jsonify({'error': 'task_id_required'}), 400
    if not uploaded_file or not str(uploaded_file.filename or '').strip():
        return jsonify({'error': 'submission_file_required'}), 400
    if not _allowed_task_submission(uploaded_file.filename):
        return jsonify({'error': 'Only ZIP, RAR, and 7Z files are accepted.'}), 400

    task = next((
        row for row in read_csv(TASKS_CSV)
        if str(row.get('id') or '').strip() == task_id
        and task_matches_employee(
            row,
            candidate_ids,
            username=session.get('username'),
            full_name=session.get('full_name'),
        )
    ), None)
    if not task:
        return jsonify({'error': 'task_not_found'}), 404

    os.makedirs(TASK_SUBMISSION_UPLOAD_DIR, exist_ok=True)
    original_filename = secure_filename(uploaded_file.filename or 'submission.zip')
    stored_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}_{original_filename}"
    disk_path = os.path.join(TASK_SUBMISSION_UPLOAD_DIR, stored_filename)
    uploaded_file.save(disk_path)
    rel_static_path = os.path.join('uploads', 'task_submissions', stored_filename).replace('\\', '/')

    manager_id = str(get_manager_for_employee(employee_id) or '').strip()
    teamlead_id = str(get_teamlead_for_employee(employee_id) or '').strip()
    project_owner_id = str((find_by_id(PROJECTS_CSV, task.get('project_id')) or {}).get('owner_id') or '').strip()
    recipients = _normalize_list_strings([manager_id, teamlead_id, project_owner_id])
    recipients = [recipient for recipient in recipients if recipient and recipient != str(employee_id).strip()]

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    submission_row = {
        'id': str(uuid.uuid4()),
        'task_id': task_id,
        'project_id': str(task.get('project_id') or '').strip(),
        'employee_id': str(employee_id).strip(),
        'employee_name': str(employee.get('name') or session.get('full_name') or session.get('username') or 'Employee').strip(),
        'manager_id': manager_id,
        'teamlead_id': teamlead_id,
        'recipient_ids': ','.join(recipients),
        'original_filename': original_filename,
        'stored_filename': stored_filename,
        'file_path': rel_static_path,
        'file_size': str(os.path.getsize(disk_path)),
        'status': 'submitted',
        'notes': notes,
        'created_at': timestamp,
        'updated_at': timestamp,
    }
    append_csv(TASK_SUBMISSIONS_CSV, submission_row, TASK_SUBMISSION_FIELDNAMES)

    notify_users(
        recipients,
        'Task Package Uploaded',
        f'{submission_row["employee_name"]} uploaded "{original_filename}" for task "{task.get("title") or task_id}". Download: {_submission_download_path(submission_row)}',
        'task',
        email_subject='Task Package Uploaded',
    )

    return jsonify({'ok': True, 'submission': _serialize_task_submission(submission_row)})


@app.route('/api/employee/leave')
@login_required
def api_employee_leave_list():
    ensure_leave_data_integrity()
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    if not user_id and not username:
        return jsonify([])

    employee_rows = read_csv(EMP_CSV)
    candidate_ids = set()
    if user_id:
        for r in employee_rows:
            if r.get('id') == user_id:
                candidate_ids.add(r.get('id'))
                break
    if username:
        for r in employee_rows:
            if (r.get('email') or '').strip().lower() == str(username).strip().lower():
                candidate_ids.add(r.get('id'))
    if full_name:
        for r in employee_rows:
            if (r.get('name') or '').strip().lower() == str(full_name).strip().lower():
                candidate_ids.add(r.get('id'))

    rows = ensure_leave_data_integrity()
    mine = [l for l in rows if l.get('employee_id') in candidate_ids or (user_id and l.get('employee_id') == user_id)]
    for l in mine:
        try:
            sd = datetime.strptime((l.get('start_date') or '')[:10], '%Y-%m-%d').date()
            ed = datetime.strptime((l.get('end_date') or '')[:10], '%Y-%m-%d').date()
            days = (ed - sd).days + 1
            l['days'] = max(days, 0)
        except Exception:
            l['days'] = 0
        l['type'] = l.get('type','') or 'leave'
        l['status'] = normalize_leave_status(l.get('status'))
    mine.sort(key=lambda r: r.get('applied_at',''), reverse=True)
    return jsonify(mine)


@app.route('/api/employee/leave-request', methods=['POST'])
@login_required
def api_employee_leave_request():
    ensure_leave_data_integrity()
    data = request.get_json(force=True) or {}
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    employee_rows = read_csv(EMP_CSV)
    employee_id = None
    for r in employee_rows:
        if user_id and r.get('id') == user_id:
            employee_id = r.get('id')
            break
    if not employee_id and username:
        for r in employee_rows:
            if (r.get('email') or '').strip().lower() == str(username).strip().lower():
                employee_id = r.get('id'); break
    if not employee_id and full_name:
        for r in employee_rows:
            if (r.get('name') or '').strip().lower() == str(full_name).strip().lower():
                employee_id = r.get('id'); break
    if not employee_id:
        return jsonify({'error':'employee_not_found'}), 400

    sd_raw = (data.get('startDate') or data.get('start_date') or '').strip()
    ed_raw = (data.get('endDate') or data.get('end_date') or '').strip()
    def parse_date(s):
        for fmt in ('%Y-%m-%d','%d-%m-%Y'):
            try:
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None
    sd = parse_date(sd_raw)
    ed = parse_date(ed_raw)
    if not sd or not ed or ed < sd:
        return jsonify({'error':'invalid_dates'}), 400

    row = {
        'id': str(uuid.uuid4()),
        'employee_id': employee_id,
        'start_date': sd.strftime('%Y-%m-%d'),
        'end_date': ed.strftime('%Y-%m-%d'),
        'reason': data.get('reason',''),
        'type': (data.get('type') or data.get('leaveType') or data.get('leave_type') or 'leave').lower(),
        'status': 'pending',
        'applied_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    append_csv(LEAVE_CSV, row, LEAVE_FIELDNAMES)
    return jsonify({'ok': True, 'id': row['id']})


@app.route('/api/employee/leave/apply', methods=['POST'])
@login_required
def api_employee_leave_apply():
    ensure_leave_data_integrity()
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(force=True) or {}
    leave_id = str(uuid.uuid4())
    row = {
        'id': leave_id,
        'employee_id': user_id,
        'start_date': (data.get('start_date') or data.get('startDate') or '')[:10],
        'end_date': (data.get('end_date') or data.get('endDate') or '')[:10],
        'reason': data.get('reason',''),
        'type': (data.get('type') or data.get('leaveType') or data.get('leave_type') or 'leave').lower(),
        'status': 'pending',
        'applied_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    append_csv(LEAVE_CSV, row, LEAVE_FIELDNAMES)
    return jsonify({'ok': True, 'id': leave_id})


@app.route('/api/employee/notifications')
@login_required
def api_employee_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])

    rows = read_csv(NOTIF_CSV)
    mine = []
    for row in rows:
        if str(row.get('user_id', '')) != str(user_id):
            continue
        mine.append({
            'id': row.get('id', ''),
            'title': row.get('title', 'Notification'),
            'message': row.get('message', ''),
            'type': (row.get('type') or 'system').lower(),
            'is_read': str(row.get('is_read', 'false')).lower() == 'true',
            'created_at': row.get('created_at', ''),
        })

    mine.sort(key=lambda r: r.get('created_at', ''), reverse=True)
    return jsonify(mine)


@app.route('/api/employee/notifications/read-all', methods=['POST'])
@login_required
def api_employee_notifications_read_all():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

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


@app.route('/api/employee/notifications/<notification_id>/read', methods=['POST'])
@login_required
def api_employee_notification_read(notification_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    notification = find_by_id(NOTIF_CSV, notification_id)
    if not notification or str(notification.get('user_id', '')).strip() != str(user_id).strip():
        return jsonify({'error': 'notification_not_found'}), 404
    update_by_id(NOTIF_CSV, notification_id, {'is_read': 'true'}, NOTIFICATION_FIELDNAMES)
    return jsonify({'ok': True})


@app.route('/api/employee/notifications/<notification_id>', methods=['DELETE'])
@login_required
def api_employee_notification_delete(notification_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    notification = find_by_id(NOTIF_CSV, notification_id)
    if not notification or str(notification.get('user_id', '')).strip() != str(user_id).strip():
        return jsonify({'error': 'notification_not_found'}), 404
    delete_by_id(NOTIF_CSV, notification_id, NOTIFICATION_FIELDNAMES)
    return jsonify({'ok': True})


@app.route('/api/employee/profile/update', methods=['POST'])
@login_required
def api_employee_profile_update():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(force=True) or {}
    fields = {}
    user_updates = {}
    for k in ['name','email','phone','location','department','company','position','skills']:
        if k not in data:
            continue
        v = data[k]
        if k == 'skills' and isinstance(v, str):
            v = ','.join([s.strip() for s in v.split(',') if s.strip()])
        if k == 'email':
            v = str(v or '').strip().lower()
            if not v:
                continue
            users = read_csv(USERS_CSV)
            collision = next(
                (
                    user for user in users
                    if str(user.get('id', '')).strip() != str(user_id).strip()
                    and str(user.get('username', '')).strip().lower() == v
                ),
                None
            )
            if collision:
                return jsonify({'error': 'email_already_exists'}), 409
            user_updates['username'] = v
        elif k == 'name':
            user_updates['full_name'] = str(v or '').strip()
        fields[k] = v
    if not fields:
        return jsonify({'error': 'no changes'}), 400
    ids, _ = resolve_employee_candidate_ids(user_id, session.get('username'), session.get('full_name'))
    target_emp_id = next(iter(ids), None)
    if not target_emp_id:
        return jsonify({'error': 'employee_not_found'}), 404
    ok = update_by_id(EMP_CSV, target_emp_id, fields, EMP_FIELDNAMES)
    user_ok = True
    if user_updates:
        user_ok = update_by_id(USERS_CSV, user_id, user_updates, USER_FIELDNAMES)
        if user_updates.get('username'):
            session['username'] = user_updates['username']
        if user_updates.get('full_name'):
            session['full_name'] = user_updates['full_name']
    if ok or user_ok:
        ensure_demo_org_integrity(force=True)
    return jsonify({'ok': bool(ok or user_ok), 'success': bool(ok or user_ok)})


@app.route('/api/employee/profile/avatar', methods=['POST'])
@login_required
def api_employee_profile_avatar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    avatar_file = request.files.get('avatar')
    if not avatar_file or not avatar_file.filename:
        return jsonify({'error': 'missing_file'}), 400

    original_name = secure_filename(avatar_file.filename)
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.webp'}:
        return jsonify({'error': 'unsupported_file_type'}), 400

    try:
        os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
        filename = f"{user_id}_{int(datetime.now().timestamp())}{ext}"
        disk_path = os.path.join(AVATAR_UPLOAD_DIR, filename)
        avatar_file.save(disk_path)

        rel_static_path = f"uploads/avatars/{filename}"
        ids, _ = resolve_employee_candidate_ids(user_id, session.get('username'), session.get('full_name'))
        target_emp_id = next(iter(ids), None)

        if target_emp_id:
            updated = update_by_id(EMP_CSV, target_emp_id, {'avatar_url': rel_static_path}, EMP_FIELDNAMES)
            if not updated:
                print(f"Warning: Couldn't update employee avatar row for id {target_emp_id}")
        else:
            print("Warning: no matching employee id found for avatar update (profile may be fallback account)")

        return jsonify({
            'ok': True,
            'success': True,
            'avatar_url': rel_static_path,
            'avatar_src': url_for('static', filename=rel_static_path)
        })
    except Exception as e:
        print(f"Avatar upload error:", e)
        return jsonify({'ok': False, 'success': False, 'error': str(e)}), 500


@app.route('/api/employee/password/update', methods=['POST'])
@login_required
def api_employee_password_update():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(force=True) or {}
    user_row = find_by_id(USERS_CSV, user_id)
    if not user_row:
        return jsonify({'error': 'user_not_found'}), 404

    current_password = str(data.get('current_password', data.get('currentPassword', '')) or '').strip()
    new_password = str(data.get('new_password', data.get('newPassword', '')) or '').strip()
    updates = {}

    if new_password:
        if not current_password:
            return jsonify({'error': 'current_password_required'}), 400
        stored_password = user_row.get('password_hash') or user_row.get('password') or ''
        if not verify_password(stored_password, current_password):
            return jsonify({'error': 'invalid_current_password'}), 400
        if len(new_password) < 6:
            return jsonify({'error': 'password_too_short'}), 400
        updates['password_hash'] = generate_password_hash(new_password)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user_ok = True
    if updates:
        user_ok = update_by_id(USERS_CSV, user_id, updates, USER_FIELDNAMES)
    emp_ok = update_by_id(EMP_CSV, user_id, {'password_last_changed': timestamp}, EMP_FIELDNAMES)
    return jsonify({'ok': bool(user_ok and emp_ok), 'success': bool(user_ok and emp_ok)})


@app.route('/api/employee/password/change', methods=['POST'])
@login_required
def api_employee_password_change():
    return api_employee_password_update()


@app.route('/api/employee/settings')
@login_required
def api_employee_settings():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401
    settings, _rows = get_user_settings_record(user_id)
    return jsonify({
        'ok': True,
        'success': True,
        'settings': {
            'emailNotifications': _truthy(settings.get('email_notifications'), True),
            'pushNotifications': _truthy(settings.get('push_notifications')),
            'taskReminders': _truthy(settings.get('task_reminders'), True),
            'deadlineAlerts': _truthy(settings.get('deadline_alerts'), True),
            'theme': settings.get('theme', 'system'),
            'language': settings.get('language', 'en'),
            'timezone': settings.get('timezone', 'UTC'),
            'updatedAt': settings.get('updated_at', ''),
        }
    })


@app.route('/api/employee/settings/update', methods=['POST'])
@login_required
def api_employee_settings_update():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(force=True) or {}
    incoming = {
        'email_notifications': 'true' if _truthy(data.get('emailNotifications'), True) else 'false',
        'push_notifications': 'true' if _truthy(data.get('pushNotifications')) else 'false',
        'task_reminders': 'true' if _truthy(data.get('taskReminders'), True) else 'false',
        'deadline_alerts': 'true' if _truthy(data.get('deadlineAlerts'), True) else 'false',
        'theme': str(data.get('theme') or 'system'),
        'language': str(data.get('language') or 'en'),
        'timezone': str(data.get('timezone') or 'UTC'),
    }
    record = save_user_settings_record(user_id, incoming)
    return jsonify({'ok': True, 'success': True, 'settings': record})


@app.route('/api/employee/data/export')
@login_required
def api_employee_data_export():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    username = session.get('username')
    full_name = session.get('full_name')
    candidate_ids, _ = resolve_employee_candidate_ids(user_id, username, full_name)

    employee_data = get_employee_data(user_id)
    settings, _rows = get_user_settings_record(user_id)
    all_leaves = ensure_leave_data_integrity()
    leaves = [l for l in all_leaves if str(l.get('employee_id', '')) in {str(v) for v in candidate_ids}]
    notifications = [
        n for n in read_csv(NOTIF_CSV)
        if str(n.get('user_id', '')) == str(user_id)
    ]

    payload = {
        'exported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user': {
            'id': user_id,
            'username': username,
            'full_name': full_name,
            'role': session.get('role', 'employee'),
        },
        'profile': employee_data.get('profile', {}),
        'stats': employee_data.get('stats', {}),
        'tasks': employee_data.get('tasks', []),
        'projects': employee_data.get('projects', []),
        'leave_requests': leaves,
        'notifications': notifications,
        'settings': settings,
    }
    return jsonify({'ok': True, 'success': True, 'data': payload})


@app.route('/api/employee/account/delete-request', methods=['POST'])
@login_required
def api_employee_account_delete_request():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'unauthorized'}), 401

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    users = read_csv(USERS_CSV)
    fieldnames = merge_fieldnames(users, ['id','username','password_hash','full_name','role','created_at','is_active','deletion_requested','deletion_requested_at'])
    ok = update_by_id(
        USERS_CSV,
        user_id,
        {'deletion_requested': 'true', 'deletion_requested_at': now},
        fieldnames
    )
    create_notification(
        user_id,
        'Account Deletion Request Submitted',
        'Your account deletion request has been recorded and sent for review.',
        'system'
    )
    return jsonify({'ok': bool(ok), 'success': bool(ok)})


@app.route('/api/employee/help-requests')
@login_required
def api_employee_help_requests():
    employee_id, _employee, candidate_ids, _employees = _resolve_current_employee_context()
    if not employee_id:
        return jsonify({'error': 'employee_not_found'}), 404

    valid_requester_ids = {str(employee_id).strip()} | {str(value).strip() for value in candidate_ids or set()}
    requests = [
        row for row in _normalize_help_request_rows(read_csv(HELP_REQUESTS_CSV))
        if str(row.get('requester_id', '')).strip() in valid_requester_ids
    ]
    return jsonify({'requests': requests})


@app.route('/api/employee/help-request', methods=['POST'])
@login_required
def api_employee_help_request():
    employee_id, employee_row, candidate_ids, _employees = _resolve_current_employee_context()
    if not employee_id:
        return jsonify({'error': 'employee_not_found'}), 404

    data = request.get_json(force=True) or {}
    message = str(data.get('message') or '').strip()
    task_id = str(data.get('task_id', data.get('task', '')) or '').strip()
    urgency = str(data.get('urgency') or 'medium').strip().lower()
    recipient_type = str(data.get('recipient_type', data.get('recipientType', 'manager')) or 'manager').strip().lower()
    request_type = str(data.get('request_type', data.get('requestType', '')) or '').strip().lower()
    explicit_recipient_id = str(data.get('recipient_id', data.get('recipientId', '')) or '').strip()

    if not message:
        return jsonify({'error': 'message_required'}), 400
    if urgency not in {'low', 'medium', 'high'}:
        urgency = 'medium'
    if recipient_type not in {'manager', 'teammate'}:
        recipient_type = 'manager'
    if not request_type:
        request_type = 'collaboration' if recipient_type == 'teammate' else 'help'

    username = session.get('username')
    full_name = session.get('full_name')
    task = None
    if task_id:
        task = next((
            row for row in read_csv(TASKS_CSV)
            if str(row.get('id', '')).strip() == task_id
            and task_matches_employee(row, candidate_ids, username=username, full_name=full_name)
        ), None)
        if not task:
            return jsonify({'error': 'task_not_found'}), 404

    recipients = _resolve_help_request_recipients(
        employee_id,
        recipient_type=recipient_type,
        explicit_recipient_id=explicit_recipient_id,
    )
    if not recipients:
        return jsonify({'error': 'no_help_recipients_available'}), 400

    requester_name = str(employee_row.get('name') or session.get('full_name') or session.get('username') or 'Employee').strip()
    task_title = str((task or {}).get('title') or data.get('task_title', data.get('taskTitle', '')) or 'General workload support').strip()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []

    request_title = 'Help Request'
    request_verb = 'requested help'
    if request_type == 'collaboration':
        request_title = 'Collaboration Request'
        request_verb = 'requested collaboration'
    elif request_type == 'extension':
        request_title = 'Deadline Extension Request'
        request_verb = 'requested a deadline extension'

    for recipient in recipients:
        row = {
            'id': str(uuid.uuid4()),
            'requester_id': employee_id,
            'requester_name': requester_name,
            'task_id': task_id,
            'task_title': task_title,
            'message': message,
            'urgency': urgency,
            'status': 'pending',
            'recipient_type': recipient_type,
            'recipient_id': str(recipient.get('id') or '').strip(),
            'recipient_name': str(recipient.get('name') or '').strip(),
            'request_type': request_type,
            'created_at': created_at,
            'updated_at': created_at,
        }
        append_csv(HELP_REQUESTS_CSV, row, HELP_REQUEST_FIELDNAMES)
        rows.append(row)

        recipient_message = f'{requester_name} {request_verb}.'
        details = []
        if task_title:
            details.append(f'Task: {task_title}')
        details.append(f'Urgency: {urgency.title()}')
        if details:
            recipient_message = f'{recipient_message} ' + ' | '.join(details)
        recipient_message = f'{recipient_message} Message: {message}'

        notify_user(
            row['recipient_id'],
            request_title,
            recipient_message,
            'help',
            email_subject=request_title,
        )

    recipient_labels = ', '.join(row.get('recipient_name', '') for row in rows if row.get('recipient_name'))
    confirmation_message = f'Your request was sent to {recipient_labels or "the available team"}.'
    if task_title:
        confirmation_message = f'{confirmation_message} Task: {task_title}.'
    create_notification(employee_id, 'Help Request Sent', confirmation_message, 'help')

    return jsonify({
        'ok': True,
        'message': confirmation_message,
        'requests_created': len(rows),
        'requests': rows,
    })


@app.route('/api/employee/help-request/<request_id>', methods=['DELETE'])
@login_required
def api_employee_help_request_delete(request_id):
    employee_id, _employee, candidate_ids, _employees = _resolve_current_employee_context()
    if not employee_id:
        return jsonify({'error': 'employee_not_found'}), 404

    valid_requester_ids = {str(employee_id).strip()} | {str(value).strip() for value in candidate_ids or set()}
    request_row = next((
        row for row in read_csv(HELP_REQUESTS_CSV)
        if str(row.get('id', '')).strip() == str(request_id).strip()
        and str(row.get('requester_id', '')).strip() in valid_requester_ids
    ), None)
    if not request_row:
        return jsonify({'error': 'help_request_not_found'}), 404

    updated = update_by_id(
        HELP_REQUESTS_CSV,
        request_id,
        {
            'status': 'cancelled',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        HELP_REQUEST_FIELDNAMES,
    )
    if not updated:
        return jsonify({'error': 'help_request_not_found'}), 404

    recipient_id = str(request_row.get('recipient_id') or '').strip()
    task_title = str(request_row.get('task_title') or 'General workload support').strip()
    requester_name = str(request_row.get('requester_name') or session.get('full_name') or 'Employee').strip()

    if recipient_id:
        notify_user(
            recipient_id,
            'Help Request Cancelled',
            f'{requester_name} cancelled the help request for "{task_title}".',
            'help',
            email_subject='Help Request Cancelled',
        )
    create_notification(
        employee_id,
        'Help Request Cancelled',
        f'Your help request for "{task_title}" was cancelled.',
        'help',
    )

    return jsonify({'ok': True})


@app.route('/api/employee/team-info')
@login_required
def api_employee_team_info():
    """Get employee's manager and teammates"""
    user_id, _employee, candidate_ids, _employees = _resolve_current_employee_context()

    if not user_id and not candidate_ids:
        return jsonify({'manager': None, 'teammates': []})

    manager_id = get_manager_for_employee(user_id)
    manager_data = None
    teammates = []

    if manager_id:
        users = read_csv(USERS_CSV)
        manager = next((u for u in users if u.get('id') == manager_id), None)
        if manager:
            manager_data = {
                'id': manager.get('id'),
                'name': manager.get('full_name'),
                'email': manager.get('username')
            }

        team_member_ids = get_team_members(manager_id)
        if team_member_ids:
            employees = read_csv(EMP_CSV)
            for team_id in team_member_ids:
                if team_id != user_id:
                    emp = next((e for e in employees if e.get('id') == team_id), None)
                    if emp:
                        teammates.append({
                            'id': emp.get('id'),
                            'name': emp.get('name'),
                            'position': emp.get('position'),
                            'email': emp.get('email')
                        })

    return jsonify({
        'manager': manager_data,
        'teammates': teammates
    })


@app.route('/api/employee/tasks')
@login_required
def api_employee_tasks():
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    if not user_id and not username:
        return jsonify([])

    candidate_ids, _ = resolve_employee_candidate_ids(user_id, username, full_name)
    tasks = read_csv(TASKS_CSV)
    mine = [
        t for t in tasks
        if task_matches_employee(t, candidate_ids, username=username, full_name=full_name)
    ]
    normalized = []
    for row in mine:
        item = dict(row)
        item['status'] = normalize_task_status(item.get('status'))
        item['priority'] = str(item.get('priority') or 'medium').strip().lower()
        item['due_date'] = str(item.get('due_date') or item.get('dueDate') or '')[:10]
        item['progress'] = int(item.get('progress', 0) or 0)
        normalized.append(item)
    return jsonify(normalized)


@app.route('/api/employee/projects')
@login_required
def api_employee_projects():
    ensure_projects_team_members()
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    if not user_id and not username:
        return jsonify([])

    candidate_ids, _ = resolve_employee_candidate_ids(user_id, username, full_name)

    projects = read_csv(PROJECTS_CSV)
    members = read_csv(PROJECT_MEMBERS_CSV)
    tasks = read_csv(TASKS_CSV)

    ids_to_match = set(candidate_ids)

    member_project_ids = {
        m.get('project_id')
        for m in members
        if m.get('project_id') and m.get('employee_id') in ids_to_match
    }

    task_project_ids = {
        t.get('project_id')
        for t in tasks
        if t.get('project_id') and task_matches_employee(t, ids_to_match, username=username, full_name=full_name)
    }

    visible_project_ids = member_project_ids.union(task_project_ids)

    mine = [
        p for p in projects
        if (user_id and p.get('owner_id') == user_id) or p.get('id') in visible_project_ids
    ]
    normalized = [{
        'id': p.get('id'),
        'name': p.get('name'),
        'description': p.get('description'),
        'status': p.get('status', 'planning'),
        'startDate': p.get('start_date'),
        'endDate': p.get('end_date'),
        'progress': int(p.get('progress', 0) or 0)
    } for p in mine]
    return jsonify(normalized)


@app.route('/api/employee/tasks/<task_id>', methods=['GET'])
@login_required
def api_employee_get_task(task_id):
    """Get a specific task for employee with error handling"""
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    task, _employee_id, _employee, _candidate_ids = _resolve_session_employee_task(task_id)

    if not task:
        return jsonify({'error': 'task not found', 'task_id': task_id}), 404

    return jsonify({
        'id': task.get('id'),
        'title': task.get('title'),
        'description': task.get('description'),
        'status': normalize_task_status(task.get('status')),
        'priority': str(task.get('priority') or 'medium').lower(),
        'progress': int(task.get('progress', 0) or 0),
        'project_id': task.get('project_id'),
        'due_date': task.get('due_date', '')[:10],
        'created_at': task.get('created_at', '')
    })


@app.route('/api/employee/tasks', methods=['POST'])
@login_required
def api_employee_create_task():
    """Create a new task for employee"""
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    employee_id, employee, _candidate_ids, _employees = _resolve_current_employee_context()
    data = request.get_json(force=True) or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    project_id = data.get('project_id') or ''
    priority = (str(data.get('priority', 'medium')).strip().lower())
    due_date = data.get('due_date') or ''

    if not title:
        return jsonify({'error': 'title required'}), 400

    task_id = get_next_task_id(read_csv(TASKS_CSV))
    new_task = {
        'id': task_id,
        'title': title,
        'description': description,
        'project_id': project_id,
        'assignee_id': employee_id or user_id,
        'assignee_name': str((employee or {}).get('name') or session.get('full_name') or session.get('username') or 'Unknown').strip(),
        'status': 'pending',
        'priority': priority,
        'progress': '0',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'due_date': str(due_date or '')[:10],
        'estimated_hours': '0',
        'actual_hours': '0',
    }

    append_csv(TASKS_CSV, new_task, TASK_FIELDNAMES)
    return jsonify({'ok': True, 'task_id': task_id}), 201


@app.route('/api/employee/tasks/<task_id>', methods=['PUT'])
@login_required
def api_employee_update_task(task_id):
    """Update task details for employee"""
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(force=True) or {}

    task, employee_id, _employee, _candidate_ids = _resolve_session_employee_task(task_id)

    if not task:
        return jsonify({'error': 'task not found or not owned'}), 404

    update_fields = {}
    if 'title' in data and data['title']:
        update_fields['title'] = data['title'].strip()
    if 'description' in data:
        update_fields['description'] = (data['description'] or '').strip()
    if 'priority' in data and data['priority']:
        update_fields['priority'] = str(data['priority']).strip().lower()
    if 'progress' in data:
        update_fields['progress'] = min(100, max(0, int(data['progress'] or 0)))
    if 'status' in data and data['status']:
        update_fields['status'] = normalize_task_status(data['status'])
    if 'due_date' in data:
        update_fields['due_date'] = (data['due_date'] or '')[:10]
    if employee_id:
        update_fields['assignee_id'] = employee_id

    if not update_fields:
        return jsonify({'error': 'no fields to update'}), 400

    updated = update_by_id(TASKS_CSV, task_id, update_fields, ['id','title','description','project_id','assignee_id','assignee_name','status','priority','created_at','due_date','progress'])

    if not updated:
        return jsonify({'error': 'update failed'}), 500

    updated_task = find_by_id(TASKS_CSV, task_id) or task
    if updated_task.get('project_id'):
        update_project_progress(updated_task['project_id'])
    notify_employee_progress_update(updated_task, employee_id or user_id, 'details', 'updated')

    return jsonify({'ok': True})


@app.route('/api/employee/tasks/<task_id>', methods=['DELETE'])
@login_required
def api_employee_delete_task(task_id):
    """Delete task for employee"""
    user_id = session.get('user_id')
    username = session.get('username')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    task, _employee_id, _employee, _candidate_ids = _resolve_session_employee_task(task_id)

    if not task:
        return jsonify({'error': 'task not found or not owned'}), 404

    all_tasks = read_csv(TASKS_CSV)
    remaining = [t for t in all_tasks if t.get('id') != task_id]
    write_csv(TASKS_CSV, remaining, TASK_FIELDNAMES)

    return jsonify({'ok': True})


@app.route('/api/employee/<employee_id>')
@login_required
def api_get_employee_details(employee_id):
    """Get employee details - prevents 'not found' errors by validating first"""
    user_id = session.get('user_id')

    if user_id != employee_id and session.get('role') not in {'manager', 'admin', 'hr', 'teamlead'}:
        return jsonify({'error': 'forbidden'}), 403

    employees = read_csv(EMP_CSV)
    users = read_csv(USERS_CSV)
    employee = next((e for e in employees if str(e.get('id', '')).strip() == str(employee_id).strip()), None)
    user = next((u for u in users if str(u.get('id', '')).strip() == str(employee_id).strip()), None)

    if not employee and user:
        employee = {
            'id': user.get('id'),
            'name': user.get('full_name', ''),
            'email': user.get('username', user.get('email', '')),
            'position': normalize_role(user.get('role', 'employee')).title(),
            'department': '',
            'company': get_default_company_name(),
            'join_date': '',
            'phone': '',
            'skills': '',
            'location': '',
            'last_login': '',
            'avatar_url': '',
            'status': 'active' if _truthy(user.get('is_active', 'true'), True) else 'inactive',
            'productivity': '0',
        }

    if not employee:
        return jsonify({
            'error': 'employee not found',
            'employee_id': employee_id,
            'available_employees': [e.get('id') for e in employees[:5]]
        }), 404

    tasks = read_csv(TASKS_CSV)
    candidate_ids, _employee_rows = resolve_employee_candidate_ids(employee.get('id'), employee.get('email'), employee.get('name'))
    emp_tasks = [
        task for task in tasks
        if task_matches_employee(task, candidate_ids, username=employee.get('email'), full_name=employee.get('name'))
    ]
    completed = [t for t in emp_tasks if normalize_task_status(t.get('status')) == 'completed']
    completion_rate = int((len(completed) / len(emp_tasks) * 100) if emp_tasks else 0)
    normalized_role = normalize_role(user.get('role', 'employee') if user else employee.get('role', 'employee'))

    return jsonify({
        'id': employee.get('id'),
        'name': employee.get('name'),
        'email': employee.get('email'),
        'position': employee.get('position'),
        'department': employee.get('department'),
        'company': employee.get('company', get_default_company_name()),
        'phone': employee.get('phone'),
        'skills': employee.get('skills', ''),
        'location': employee.get('location'),
        'join_date': employee.get('join_date'),
        'last_login': employee.get('last_login', ''),
        'avatar_url': employee.get('avatar_url'),
        'role': normalized_role,
        'team_id': employee.get('team_id', ''),
        'team_name': employee.get('team_name', ''),
        'manager_id': employee.get('manager_id', ''),
        'teamlead_id': employee.get('teamlead_id', ''),
        'status': employee.get('status', 'active'),
        'totalTasks': len(emp_tasks),
        'completedTasks': len(completed),
        'completionRate': completion_rate,
        'productivity': _safe_int(employee.get('productivity', completion_rate), completion_rate) or completion_rate
    })


@app.route('/api/employee/analytics')
@login_required
def api_employee_analytics():
    """Get employee analytics and performance metrics"""
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    candidate_ids, _employees = resolve_employee_candidate_ids(user_id, username, full_name)
    tasks = read_csv(TASKS_CSV)
    projects = read_csv(PROJECTS_CSV)
    emp_tasks = [
        t for t in tasks
        if task_matches_employee(t, candidate_ids, username=username, full_name=full_name)
    ]

    statuses = {}
    for t in emp_tasks:
        status = normalize_task_status(t.get('status'))
        statuses[status] = statuses.get(status, 0) + 1

    priorities = {}
    for t in emp_tasks:
        priority = str(t.get('priority', 'medium')).lower()
        priorities[priority] = priorities.get(priority, 0) + 1

    completed = len([t for t in emp_tasks if normalize_task_status(t.get('status')) == 'completed'])
    total = len(emp_tasks)
    completion_rate = int((completed / total * 100) if total > 0 else 0)
    visible_project_ids = {
        str(t.get('project_id') or '').strip()
        for t in emp_tasks
        if str(t.get('project_id') or '').strip()
    }

    return jsonify({
        'totalTasks': total,
        'completedTasks': completed,
        'completionRate': completion_rate,
        'tasksByStatus': statuses,
        'tasksByPriority': priorities,
        'averageProgress': completion_rate,
        'activeProjects': len([
            p for p in projects
            if str(p.get('id') or '').strip() in visible_project_ids
            and str(p.get('status') or '').strip().lower() != 'completed'
        ]),
        'generatedAt': datetime.now().isoformat()
    })


@app.route('/api/employee/reports')
@login_required
def api_employee_reports():
    """Get employee reports with detailed metrics"""
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    if not user_id and not username:
        return jsonify({'error': 'unauthorized'}), 401

    candidate_ids, _employees = resolve_employee_candidate_ids(user_id, username, full_name)
    tasks = read_csv(TASKS_CSV)
    projects = read_csv(PROJECTS_CSV)
    leave = read_csv(LEAVE_CSV)

    emp_tasks = [
        t for t in tasks
        if task_matches_employee(t, candidate_ids, username=username, full_name=full_name)
    ]
    emp_projects = [
        p for p in projects
        if str(p.get('owner_id') or '').strip() in candidate_ids
        or any(member_id in candidate_ids for member_id in _normalize_list_strings(str(p.get('team_members', '')).split(',')))
    ]
    emp_leave = [l for l in leave if str(l.get('employee_id') or '').strip() in candidate_ids]

    tasks_by_month = {}
    for t in emp_tasks:
        try:
            month = (t.get('created_at') or '')[:7]
            if month:
                tasks_by_month[month] = tasks_by_month.get(month, 0) + 1
        except:
            pass

    completed_count = len([t for t in emp_tasks if normalize_task_status(t.get('status')) == 'completed'])
    total_count = len(emp_tasks)
    completion_percent = int((completed_count / total_count * 100) if total_count > 0 else 0)

    return jsonify({
        'reportTitle': 'Employee Performance Report',
        'period': f"{datetime.now().year}-{str(datetime.now().month).zfill(2)}",
        'generatedAt': datetime.now().isoformat(),
        'summary': {
            'totalTasks': total_count,
            'completedTasks': completed_count,
            'pendingTasks': len([t for t in emp_tasks if normalize_task_status(t.get('status')) == 'pending']),
            'inProgressTasks': len([t for t in emp_tasks if normalize_task_status(t.get('status')) == 'in-progress']),
            'completionRate': completion_percent,
            'totalProjects': len(emp_projects),
            'totalLeaves': len(emp_leave),
            'approvedLeaves': len([l for l in emp_leave if normalize_leave_status(l.get('status')) == 'approved']),
            'pendingLeaves': len([l for l in emp_leave if normalize_leave_status(l.get('status')) == 'pending'])
        },
        'tasksTrend': tasks_by_month,
        'performanceGrade': 'A' if completion_percent >= 80 else 'B' if completion_percent >= 60 else 'C'
    })
