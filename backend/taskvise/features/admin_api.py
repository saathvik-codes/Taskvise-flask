"""Admin JSON API and the platform-admin hand-off."""
from ..core import app
from ..core import (
    ADMIN_DATA_DIR,
    Counter,
    EMP_CSV,
    EMP_FIELDNAMES,
    PAYMENTS_CSV,
    PROJECTS_CSV,
    PROJECT_FIELDNAMES,
    PROJECT_MEMBERS_CSV,
    PROJECT_MEMBER_FIELDNAMES,
    TASKS_CSV,
    TASKVISE_ADMIN_URL,
    TASK_FIELDNAMES,
    TEAMS_CSV,
    USERS_CSV,
    USER_FIELDNAMES,
    WORKFORCE_ID_PREFIX,
    _build_employee_index,
    _next_prefixed_id,
    _normalize_list_strings,
    _parse_team_members,
    _safe_int,
    _sort_rows_by_id,
    _sync_project_members,
    admin_required,
    append_csv,
    build_recent_activity,
    datetime,
    delete_by_id,
    ensure_csv,
    ensure_demo_org_integrity,
    find_by_id,
    generate_password_hash,
    generate_secure_password,
    get_admin_dashboard_payload,
    get_admin_system_settings_record,
    get_default_company_name,
    get_next_workforce_id,
    json,
    jsonify,
    merge_fieldnames,
    normalize_project_status,
    normalize_role,
    normalize_task_status,
    notify_project_assignment,
    notify_task_assignment,
    notify_user,
    os,
    persist_workforce_profile,
    platform_admin_required,
    read_csv,
    redirect,
    request,
    save_admin_system_settings_record,
    session,
    taskvise_admin_manager,
    update_by_id,
    write_csv,
)


@app.route('/taskvise-admin/login', methods=['GET', 'POST'])
def taskvise_admin_login():
    return redirect(f"{TASKVISE_ADMIN_URL}/login")


@app.route('/api/admin/employees', methods=['GET', 'POST'])
@admin_required
def api_admin_employees():
    if request.method == 'GET':
        payload = get_admin_dashboard_payload()
        employees = _sort_rows_by_id(payload['employees'], WORKFORCE_ID_PREFIX)
        return jsonify(employees)

    if request.method == 'POST':
        data = request.get_json() or {}
        required = ['name', 'email', 'position', 'department', 'role']
        if any(not data.get(field) for field in required):
            return jsonify({'error': 'Missing required employee fields'}), 400

        all_users = read_csv(USERS_CSV)
        if any(u.get('username','').strip().lower() == data['email'].strip().lower() for u in all_users):
            return jsonify({'error': 'User with this email already exists'}), 409

        new_id = get_next_workforce_id(all_users, read_csv(EMP_CSV))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        provided_password = str(data.get('password', '') or '').strip()
        login_password = provided_password or generate_secure_password()

        user_row = {
            'id': new_id,
            'username': data['email'].strip().lower(),
            'password_hash': generate_password_hash(login_password),
            'full_name': data['name'].strip(),
            'role': normalize_role(data['role']),
            'created_at': now,
            'is_active': 'true'
        }

        employee_row = {
            'id': new_id,
            'name': data['name'].strip(),
            'email': data['email'].strip().lower(),
            'position': data['position'].strip(),
            'department': data['department'].strip(),
            'company': str(data.get('company') or get_default_company_name()).strip(),
            'join_date': now,
            'phone': data.get('phone','').strip(),
            'skills': data.get('skills','').strip(),
            'location': data.get('location','').strip(),
            'last_login': '',
            'password_last_changed': now,
            'avatar_url': '',
            'status': 'active',
            'productivity': str(_safe_int(data.get('productivity', 78), 78))
        }

        storage_status = persist_workforce_profile(user_row, employee_row)

        return jsonify({
            'message': 'Employee created',
            'id': new_id,
            'temporary_password': None if provided_password else login_password,
            'storage_status': storage_status,
        }), 201


@app.route('/api/admin/employees/<employee_id>', methods=['DELETE'])
@admin_required
def api_admin_employees_delete(employee_id):
    deleted1 = delete_by_id(EMP_CSV, employee_id, EMP_FIELDNAMES)
    deleted2 = delete_by_id(USERS_CSV, employee_id, USER_FIELDNAMES)

    member_rows = read_csv(PROJECT_MEMBERS_CSV)
    filtered_members = [
        row for row in member_rows
        if str(row.get('employee_id', '')).strip() != str(employee_id).strip()
    ]
    if len(filtered_members) != len(member_rows):
        write_csv(
            PROJECT_MEMBERS_CSV,
            filtered_members,
            merge_fieldnames(filtered_members if filtered_members else member_rows, PROJECT_MEMBER_FIELDNAMES),
        )

    project_rows = read_csv(PROJECTS_CSV)
    project_changed = False
    for project in project_rows:
        current_members = _parse_team_members(project, filtered_members)
        next_members = [member_id for member_id in current_members if member_id != str(employee_id).strip()]
        if next_members != current_members:
            project['team_members'] = ','.join(next_members)
            project_changed = True
    if project_changed:
        write_csv(PROJECTS_CSV, project_rows, merge_fieldnames(project_rows, PROJECT_FIELDNAMES))

    task_rows = read_csv(TASKS_CSV)
    task_changed = False
    for task in task_rows:
        if str(task.get('assignee_id', '')).strip() == str(employee_id).strip():
            task['assignee_id'] = ''
            task['assignee_name'] = ''
            task_changed = True
    if task_changed:
        write_csv(TASKS_CSV, task_rows, merge_fieldnames(task_rows, TASK_FIELDNAMES))

    if deleted1 or deleted2:
        ensure_demo_org_integrity(force=True)
        return jsonify({'message':'Employee deleted'}), 200
    return jsonify({'error':'Employee not found'}), 404


@app.route('/api/admin/employees/<employee_id>', methods=['PUT'])
@admin_required
def api_admin_employees_update(employee_id):
    data = request.get_json(force=True) or {}
    if not data:
        return jsonify({'error': 'invalid_payload'}), 400

    allowed = ['name', 'email', 'position', 'department', 'company', 'phone', 'location', 'skills', 'role', 'status', 'productivity']
    employee_updates = {k: v for k, v in data.items() if k in allowed}
    if not employee_updates:
        return jsonify({'error': 'nothing_to_update'}), 400

    if 'email' in employee_updates:
        normalized_email = str(employee_updates['email'] or '').strip().lower()
        all_users = read_csv(USERS_CSV)
        collision = next(
            (
                user for user in all_users
                if str(user.get('id', '')).strip() != str(employee_id).strip()
                and str(user.get('username', '')).strip().lower() == normalized_email
            ),
            None
        )
        if collision:
            return jsonify({'error': 'email_already_exists'}), 409
        employee_updates['email'] = normalized_email

    if 'role' in employee_updates:
        employee_updates['role'] = normalize_role(employee_updates['role'])
    if 'status' in employee_updates:
        employee_updates['status'] = str(employee_updates['status'] or 'active').strip().lower()
    if 'company' in employee_updates:
        employee_updates['company'] = str(employee_updates['company'] or get_default_company_name()).strip()
    if 'productivity' in employee_updates:
        employee_updates['productivity'] = str(max(0, min(100, _safe_int(employee_updates.get('productivity', 0), 0))))

    updated_emp = update_by_id(EMP_CSV, employee_id, employee_updates, EMP_FIELDNAMES)

    user_updates = {}
    if 'role' in employee_updates:
        user_updates['role'] = employee_updates['role']
    if 'email' in employee_updates:
        user_updates['username'] = employee_updates['email']
    if 'name' in employee_updates:
        user_updates['full_name'] = employee_updates['name']
    if 'status' in employee_updates:
        user_updates['is_active'] = 'true' if employee_updates['status'] != 'inactive' else 'false'

    updated_user = False
    if user_updates:
        if update_by_id(USERS_CSV, employee_id, user_updates, USER_FIELDNAMES):
            updated_user = True

    if not updated_emp and not updated_user:
        return jsonify({'error': 'employee_not_found'}), 404

    ensure_demo_org_integrity(force=True)
    return jsonify({'ok': True})


@app.route('/api/admin/tasks', methods=['GET', 'POST'])
@admin_required
def api_admin_tasks():
    if request.method == 'GET':
        payload = get_admin_dashboard_payload()
        return jsonify(payload['tasks'])

    data = request.get_json(force=True) or {}
    title = str(data.get('title', '')).strip()
    assignee_id = str(data.get('assignedTo', data.get('assignee_id', '')) or '').strip()
    due_date = str(data.get('due_date', data.get('dueDate', '')) or '').strip()[:10]
    if not title or not assignee_id or not due_date:
        return jsonify({'error': 'Missing required task fields'}), 400

    employees = _build_employee_index()
    assignee = employees.get(assignee_id)
    if not assignee:
        return jsonify({'error': 'assignee_not_found'}), 404

    tasks = read_csv(TASKS_CSV)
    task_id = _next_prefixed_id('TSK', tasks, 5)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = {
        'id': task_id,
        'title': title,
        'description': str(data.get('description', '') or '').strip(),
        'project_id': str(data.get('project', data.get('project_id', '')) or '').strip(),
        'assignee_id': assignee_id,
        'assignee_name': assignee.get('name', ''),
        'status': normalize_task_status(data.get('status', 'pending')),
        'priority': str(data.get('priority', 'medium') or 'medium').strip().lower(),
        'created_at': now,
        'due_date': due_date,
        'estimated_hours': str(int(data.get('estimatedHours', data.get('estimated_hours', 0)) or 0)),
        'actual_hours': str(int(data.get('actualHours', data.get('actual_hours', 0)) or 0)),
        'progress': str(max(0, min(100, int(data.get('progress', 0) or 0)))),
    }
    append_csv(TASKS_CSV, row, TASK_FIELDNAMES)
    notify_task_assignment(row, actor_label=session.get('full_name') or 'Administrator', is_new_assignment=True)
    return jsonify({'ok': True, 'id': task_id}), 201


@app.route('/api/admin/tasks/<task_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_admin_task_detail(task_id):
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
    task_before = find_by_id(TASKS_CSV, task_id)
    if not task_before:
        return jsonify({'error': 'task_not_found'}), 404
    updates = {}
    if 'title' in data:
        updates['title'] = str(data.get('title', '')).strip()
    if 'description' in data:
        updates['description'] = str(data.get('description', '') or '').strip()
    if 'priority' in data:
        updates['priority'] = str(data.get('priority', 'medium') or 'medium').strip().lower()
    if 'status' in data:
        updates['status'] = normalize_task_status(data.get('status'))
    if 'dueDate' in data or 'due_date' in data:
        updates['due_date'] = str(data.get('dueDate', data.get('due_date', '')) or '').strip()[:10]
    if 'estimatedHours' in data or 'estimated_hours' in data:
        updates['estimated_hours'] = str(int(data.get('estimatedHours', data.get('estimated_hours', 0)) or 0))
    if 'actualHours' in data or 'actual_hours' in data:
        updates['actual_hours'] = str(int(data.get('actualHours', data.get('actual_hours', 0)) or 0))
    if 'progress' in data:
        updates['progress'] = str(max(0, min(100, int(data.get('progress', 0) or 0))))
    if 'assignee_id' in data or 'assignedTo' in data:
        assignee_id = str(data.get('assignee_id', data.get('assignedTo', '')) or '').strip()
        employee = _build_employee_index().get(assignee_id)
        if assignee_id and not employee:
            return jsonify({'error': 'assignee_not_found'}), 404
        updates['assignee_id'] = assignee_id
        updates['assignee_name'] = employee.get('name', '') if employee else ''
    if 'project_id' in data or 'project' in data:
        updates['project_id'] = str(data.get('project_id', data.get('project', '')) or '').strip()
    if not updates:
        return jsonify({'error': 'nothing_to_update'}), 400

    updated = update_by_id(TASKS_CSV, task_id, updates, TASK_FIELDNAMES)
    if not updated:
        return jsonify({'error': 'task_not_found'}), 404
    task_after = find_by_id(TASKS_CSV, task_id) or {**task_before, **updates}
    if str(task_after.get('assignee_id', '')).strip():
        notify_task_assignment(
            task_after,
            actor_label=session.get('full_name') or 'Administrator',
            is_new_assignment=str(task_before.get('assignee_id', '')).strip() != str(task_after.get('assignee_id', '')).strip(),
        )
    return jsonify({'ok': True})


@app.route('/api/admin/projects', methods=['GET', 'POST'])
@admin_required
def api_admin_projects():
    if request.method == 'GET':
        payload = get_admin_dashboard_payload()
        return jsonify(payload['projects'])

    data = request.get_json(force=True) or {}
    name = str(data.get('name', '')).strip()
    deadline = str(data.get('deadline', data.get('end_date', '')) or '').strip()[:10]
    if not name or not deadline:
        return jsonify({'error': 'Missing required project fields'}), 400

    projects = read_csv(PROJECTS_CSV)
    project_id = _next_prefixed_id('PRJ', projects, 4)
    team_members = _normalize_list_strings(data.get('teamMembers', data.get('team_members', [])) or [])
    row = {
        'id': project_id,
        'name': name,
        'description': str(data.get('description', '') or '').strip(),
        'owner_id': str(data.get('owner_id', session.get('user_id', '')) or '').strip(),
        'start_date': datetime.now().strftime('%Y-%m-%d'),
        'end_date': deadline,
        'status': normalize_project_status(data.get('status', 'planning')),
        'team_members': ','.join(team_members),
        'company': str(data.get('company') or get_default_company_name()).strip(),
        'progress': str(max(0, min(100, int(data.get('progress', 0) or 0)))),
    }
    append_csv(PROJECTS_CSV, row, PROJECT_FIELDNAMES)
    _sync_project_members(project_id, team_members)
    notify_project_assignment(row, actor_label=session.get('full_name') or 'Administrator', is_new_assignment=True)
    return jsonify({'ok': True, 'id': project_id}), 201


@app.route('/api/admin/projects/<project_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_admin_project_detail(project_id):
    if request.method == 'DELETE':
        deleted = delete_by_id(PROJECTS_CSV, project_id, PROJECT_FIELDNAMES)
        if not deleted:
            return jsonify({'error': 'project_not_found'}), 404
        _sync_project_members(project_id, [])
        task_rows = read_csv(TASKS_CSV)
        changed = False
        for task in task_rows:
            if str(task.get('project_id', '')).strip() == str(project_id).strip():
                task['project_id'] = ''
                changed = True
        if changed:
            write_csv(TASKS_CSV, task_rows, merge_fieldnames(task_rows, TASK_FIELDNAMES))
        return jsonify({'ok': True})

    data = request.get_json(force=True) or {}
    project_before = find_by_id(PROJECTS_CSV, project_id)
    if not project_before:
        return jsonify({'error': 'project_not_found'}), 404
    updates = {}
    if 'name' in data:
        updates['name'] = str(data.get('name', '')).strip()
    if 'description' in data:
        updates['description'] = str(data.get('description', '') or '').strip()
    if 'status' in data:
        updates['status'] = normalize_project_status(data.get('status', 'planning'))
    if 'deadline' in data or 'end_date' in data:
        updates['end_date'] = str(data.get('deadline', data.get('end_date', '')) or '').strip()[:10]
    if 'progress' in data:
        updates['progress'] = str(max(0, min(100, int(data.get('progress', 0) or 0))))
    if 'owner_id' in data:
        updates['owner_id'] = str(data.get('owner_id', '') or '').strip()
    if 'company' in data:
        updates['company'] = str(data.get('company') or get_default_company_name()).strip()
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
    notify_project_assignment(project_after, actor_label=session.get('full_name') or 'Administrator', is_new_assignment=False)
    return jsonify({'ok': True})


@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    payload = get_admin_dashboard_payload()
    tasks = payload['tasks']
    projects = payload['projects']
    employees = payload['employees']
    return jsonify({
        'totalEmployees': len(employees),
        'activeProjects': len([p for p in projects if p.get('status') in ['active','planning']]),
        'completedTasks': len([t for t in tasks if t.get('status') == 'completed']),
        'totalTasks': len(tasks)
    })


@app.route('/api/admin/settings', methods=['GET', 'PUT'])
@admin_required
def api_admin_settings_data():
    if request.method == 'GET':
        record, _rows = get_admin_system_settings_record()
        return jsonify(record)

    payload = request.get_json(force=True) or {}
    saved = save_admin_system_settings_record(payload)
    return jsonify({'ok': True, 'settings': saved})


@app.route('/api/taskvise/companies', methods=['GET'])
@platform_admin_required
def get_taskvise_companies():
    try:
        if taskvise_admin_manager is not None:
            companies = taskvise_admin_manager.get_all_companies()
        else:
            company_csv = os.path.join(ADMIN_DATA_DIR, 'companies.csv')
            ensure_csv(company_csv, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
            companies = read_csv(company_csv)
        return jsonify({'success': True, 'companies': companies})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/taskvise/companies', methods=['POST'])
@platform_admin_required
def add_taskvise_company():
    try:
        data = request.json
        company = {
            'company_name': data.get('company_name'),
            'industry': data.get('industry'),
            'country': data.get('country'),
            'employees_count': data.get('employees_count', 0),
            'users_assigned': data.get('users_assigned', 0),
            'plan_type': data.get('plan_type', 'professional'),
            'contact_email': data.get('contact_email')
        }
        if taskvise_admin_manager is not None:
            company = taskvise_admin_manager.add_company(company)
        else:
            company_csv = os.path.join(ADMIN_DATA_DIR, 'companies.csv')
            ensure_csv(company_csv, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
            companies = read_csv(company_csv)
            company['id'] = str(max([int(c.get('id', 0)) for c in companies] + [0]) + 1)
            company['signup_date'] = datetime.now().strftime('%Y-%m-%d')
            company['status'] = 'active'
            append_csv(company_csv, company, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
        return jsonify({'success': True, 'company': company})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/taskvise/companies/<company_id>', methods=['PUT'])
@platform_admin_required
def update_taskvise_company(company_id):
    try:
        data = request.json
        if taskvise_admin_manager is not None:
            taskvise_admin_manager.update_company(company_id, data)
        else:
            company_csv = os.path.join(ADMIN_DATA_DIR, 'companies.csv')
            update_by_id(company_csv, company_id, data, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/taskvise/companies/<company_id>', methods=['DELETE'])
@platform_admin_required
def delete_taskvise_company(company_id):
    try:
        if taskvise_admin_manager is not None:
            taskvise_admin_manager.delete_company(company_id)
        else:
            company_csv = os.path.join(ADMIN_DATA_DIR, 'companies.csv')
            delete_by_id(company_csv, company_id, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/taskvise/admin/stats', methods=['GET'])
@platform_admin_required
def get_taskvise_admin_stats():
    try:
        ensure_demo_org_integrity()
        if taskvise_admin_manager is not None:
            companies = taskvise_admin_manager.get_all_companies()
            admin_stats = taskvise_admin_manager.get_admin_statistics()
        else:
            company_csv = os.path.join(ADMIN_DATA_DIR, 'companies.csv')
            ensure_csv(company_csv, ['id', 'company_name', 'industry', 'country', 'employees_count', 'users_assigned', 'signup_date', 'status', 'plan_type', 'contact_email'])
            companies = read_csv(company_csv)
            admin_stats = {}
        users = read_csv(USERS_CSV)
        employees = read_csv(EMP_CSV)
        projects = read_csv(PROJECTS_CSV)
        tasks = read_csv(TASKS_CSV)
        teams = read_csv(TEAMS_CSV)
        payments = read_csv(PAYMENTS_CSV)
        role_distribution = Counter(normalize_role(user.get('role', 'employee')) for user in users)
        tasks_by_status = Counter(normalize_task_status(task.get('status')) for task in tasks)
        stats = {
            'total_companies': admin_stats.get('total_companies', len(companies)),
            'active_companies': admin_stats.get('active_companies', len([c for c in companies if c.get('status') == 'active'])),
            'total_employees': len(employees),
            'total_users': len([user for user in users if normalize_role(user.get('role')) != 'platform_admin']),
            'enterprise_plans': admin_stats.get('enterprise_plans', len([c for c in companies if c.get('plan_type') == 'enterprise'])),
            'professional_plans': admin_stats.get('professional_plans', len([c for c in companies if c.get('plan_type') == 'professional'])),
            'total_projects': len(projects),
            'active_projects': len([project for project in projects if normalize_project_status(project.get('status')) in {'active', 'planning'}]),
            'total_tasks': len(tasks),
            'completed_tasks': len([task for task in tasks if normalize_task_status(task.get('status')) == 'completed']),
            'total_teams': len(teams),
            'monthly_payroll': sum(_safe_int(row.get('base_salary', 0), 0) + _safe_int(row.get('bonus', 0), 0) for row in payments if str(row.get('payment_status', '')).strip().lower() != 'hold'),
            'role_distribution': dict(role_distribution),
            'tasks_by_status': dict(tasks_by_status),
            'recent_activity': build_recent_activity(employees, projects, tasks, limit=8),
        }
        
        return jsonify({'success': True, **stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/taskvise/admin/settings', methods=['POST'])
@platform_admin_required
def save_taskvise_settings():
    try:
        data = request.json
        settings_dir = ADMIN_DATA_DIR
        os.makedirs(settings_dir, exist_ok=True)
        settings_file = os.path.join(settings_dir, 'settings.json')
        
        with open(settings_file, 'w') as f:
            json.dump(data, f)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/taskvise-admin')
@platform_admin_required
def taskvise_admin_dashboard():
    return redirect(f"{TASKVISE_ADMIN_URL}/dashboard")
