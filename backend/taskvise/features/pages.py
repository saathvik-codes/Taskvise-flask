"""Server-rendered pages and role dashboards (legacy HTML; the Next.js app in web/ replaces them)."""
from ..core import app
from ..core import (
    LEAVE_CSV,
    PROJECT_MEMBERS_CSV,
    TASKVISE_ADMIN_URL,
    _render_admin_dashboard,
    admin_required,
    datetime,
    get_employee_dashboard_data,
    get_employee_data,
    get_manager_data,
    login_required,
    read_csv,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


@app.route('/')
def index():
    return render_template('landing.html')


@app.route('/landing')
def landing():
    return render_template('landing.html')


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role', 'employee')
    if role == 'platform_admin':
        return redirect(f"{TASKVISE_ADMIN_URL}/dashboard")
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'manager':
        return redirect(url_for('manager_dashboard'))
    elif role == 'hr':
        return redirect(url_for('hr_dashboard'))
    elif role == 'teamlead':
        return redirect(url_for('teamlead_dashboard'))
    else:
        return redirect(url_for('employee_dashboard'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return _render_admin_dashboard()


@app.route('/admin/employees')
@admin_required
def admin_employees():
    return _render_admin_dashboard()


@app.route('/admin/projects')
@admin_required
def admin_projects():
    return _render_admin_dashboard()


@app.route('/admin/tasks')
@admin_required
def admin_tasks():
    return _render_admin_dashboard()


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    return _render_admin_dashboard()


@app.route('/admin/skill-gap-analysis')
@admin_required
def skill_gap_analysis():
    return _render_admin_dashboard()


@app.route('/admin/profile')
@admin_required
def admin_profile():
    return _render_admin_dashboard()


@app.route('/admin/settings')
@admin_required
def admin_settings():
    return _render_admin_dashboard()


@app.route('/manager/settings')
@login_required
def manager_settings():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    employee_data = get_employee_dashboard_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='settings',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []),
                         profile=employee_data['profile'])


@app.route('/hr/dashboard')
@login_required
def hr_dashboard():
    if session.get('role') != 'hr':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='overview',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/hr/<string:view>')
@login_required
def hr_sub_view(view):
    if session.get('role') != 'hr':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    allowed = {
        'overview', 'employees', 'projects', 'tasks', 'leave', 'payments', 'workload-balancer',
        'skill-recommendations', 'team-notes', 'reports', 'notifications', 'profile', 'settings'
    }
    if view not in allowed:
        return redirect(url_for('hr_dashboard'))

    employee_data = get_employee_dashboard_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view=view,
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []),
                         profile=employee_data['profile'])


@app.route('/teamlead/dashboard')
@login_required
def teamlead_dashboard():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='overview',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/profile')
@login_required
def teamlead_profile():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    employee_data = get_employee_dashboard_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='profile',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         profile=employee_data['profile'])


@app.route('/teamlead/settings')
@login_required
def teamlead_settings():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    employee_data = get_employee_dashboard_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='settings',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         profile=employee_data['profile'])


@app.route('/employee/overview')
@login_required
def employee_overview():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_dashboard_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='overview')


@app.route('/employee/profile')
@login_required
def employee_profile():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_dashboard_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='profile')


@app.route('/employee/settings')
@login_required
def employee_settings():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_dashboard_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='settings')


@app.route('/employee/tasks')
@login_required
def employee_tasks():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='tasks')


@app.route('/employee/projects')
@login_required
def employee_projects():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='projects')


@app.route('/employee/workload')
@login_required
def employee_workload():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='workload')


@app.route('/employee/leave')
@login_required
def employee_leave():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='leave')


@app.route('/employee/reports')
@login_required
def employee_reports():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='reports')


@app.route('/employee/notifications')
@login_required
def employee_notifications():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='notifications')


@app.route('/employee/dashboard')
@login_required
def employee_dashboard():
    if session.get('role') not in ['employee', 'admin', 'manager', 'hr', 'teamlead']:
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    employee_data = get_employee_data(user_id)

    if employee_data['profile'].get('skills'):
        if isinstance(employee_data['profile']['skills'], str):
            employee_data['profile']['skills'] = [skill.strip() for skill in employee_data['profile']['skills'].split(',') if skill.strip()]
    else:
        employee_data['profile']['skills'] = []

    return render_template('employee_dashboard.html',
                         profile=employee_data['profile'],
                         stats=employee_data['stats'],
                         tasks=employee_data['tasks'],
                         projects=employee_data['projects'],
                         current_view='overview')


@app.route('/manager/dashboard')
@login_required
def manager_dashboard():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='overview',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/leave')
@login_required
def manager_leave():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='leave',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/payments')
@login_required
def manager_payments():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='payments',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/workload-balancer')
@login_required
def manager_workload_balancer():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='workload-balancer',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/skill-recommendations')
@login_required
def manager_skill_recommendations():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='skill-recommendations',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/team-notes')
@login_required
def manager_team_notes():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='team-notes',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/profile')
@login_required
def manager_profile():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    employee_data = get_employee_dashboard_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='profile',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         profile=employee_data['profile'])


@app.route('/manager/overview')
@login_required
def manager_overview():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='overview',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/employees')
@login_required
def manager_employees():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    flt = (request.args.get('filter') or '').lower()
    employees = manager_data['employees']
    if flt == 'active':
        employees = [e for e in employees if (e.get('last_login') or '').strip()]
    elif flt == 'on-leave':
        leaves = read_csv(LEAVE_CSV)
        today = datetime.now().date()
        def is_on_leave(emp_id):
            for r in leaves:
                if r.get('employee_id') == emp_id and (r.get('status') or '').lower() == 'approved':
                    try:
                        sd = datetime.strptime(r.get('start_date',''), '%Y-%m-%d').date()
                        ed = datetime.strptime(r.get('end_date',''), '%Y-%m-%d').date()
                    except Exception:
                        continue
                    if sd <= today <= ed:
                        return True
            return False
        employees = [e for e in employees if is_on_leave(e.get('id'))]

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='employees',
                         stats=manager_data['stats'],
                         employees=employees,
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/projects')
@login_required
def manager_projects():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    flt = (request.args.get('filter') or '').lower()
    projects = manager_data['projects']
    try:
        members = read_csv(PROJECT_MEMBERS_CSV)
        count_map = {}
        for m in members:
            pid = m.get('project_id')
            if pid:
                count_map[pid] = count_map.get(pid, 0) + 1
        for p in projects:
            p['team_members_count'] = count_map.get(p.get('id'), 0)
    except Exception:
        pass
    if flt == 'active':
        projects = [p for p in projects if (p.get('status') or '').lower() in ['active','planning']]
    elif flt == 'completed':
        projects = [p for p in projects if (p.get('status') or '').lower() == 'completed']

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='projects',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=projects,
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/tasks')
@login_required
def manager_tasks():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    flt = (request.args.get('filter') or '').lower()
    tasks = manager_data['tasks']
    if flt == 'in-progress':
        tasks = [t for t in tasks if (t.get('status') or '').lower() == 'in-progress']
    elif flt == 'overdue':
        today = datetime.now().date()
        def is_overdue(t):
            if (t.get('status') or '').lower() in ['completed','cancelled']:
                return False
            try:
                if t.get('due_date'):
                    dd = datetime.strptime(t['due_date'], '%Y-%m-%d').date()
                    return dd < today
            except Exception:
                return False
            return False
        tasks = [t for t in tasks if is_overdue(t)]

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='tasks',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=tasks,
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/notifications')
@login_required
def manager_notifications():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='notifications',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/manager/reports')
@login_required
def manager_reports():
    if session.get('role') != 'manager':
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    manager_data = get_manager_data(user_id)

    return render_template('manager_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='reports',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'],
                         notifications=manager_data.get('notifications', []),
                         payments=manager_data.get('payments', []),
                         teams=manager_data.get('teams', []))


@app.route('/teamlead/overview')
@login_required
def teamlead_overview():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='overview',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/team-members')
@login_required
def teamlead_team_members():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='team-members',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/projects')
@login_required
def teamlead_projects():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='projects',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/tasks')
@login_required
def teamlead_tasks():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='tasks',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/reports')
@login_required
def teamlead_reports():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='reports',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/workload-balancer')
@login_required
def teamlead_workload_balancer():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='workload-balancer',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/workload')
@app.route('/teamlead/workload/')
@login_required
def teamlead_workload_alias():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    return redirect(url_for('teamlead_workload_balancer'))


@app.route('/teamlead/skill-recommendations')
@login_required
def teamlead_skill_recommendations():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='skill-recommendations',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/skill-development')
@app.route('/teamlead/skill-development/')
@app.route('/teamlead/skills')
@login_required
def teamlead_skill_development_alias():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    return redirect(url_for('teamlead_skill_recommendations'))


@app.route('/teamlead/notifications')
@login_required
def teamlead_notifications():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    manager_data = get_manager_data(user_id)
    return render_template('teamlead_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         current_view='notifications',
                         stats=manager_data['stats'],
                         employees=manager_data['employees'],
                         tasks=manager_data['tasks'],
                         projects=manager_data['projects'])


@app.route('/teamlead/notification')
@app.route('/teamlead/notification/')
@login_required
def teamlead_notifications_alias():
    if session.get('role') != 'teamlead':
        return redirect(url_for('dashboard'))
    return redirect(url_for('teamlead_notifications'))
