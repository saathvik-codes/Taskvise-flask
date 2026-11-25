"""Sign-in, sign-up, Google sign-in and the JSON auth endpoints."""
from ..core import app
from ..core import (
    DB_BACKEND,
    EMP_CSV,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    USERS_CSV,
    _google_redirect_uri,
    _session_user_payload,
    _start_user_session,
    _truthy,
    _use_database,
    authenticate_user_credentials,
    datetime,
    ensure_demo_org_integrity,
    generate_password_hash,
    generate_secure_password,
    get_default_company_name,
    get_next_workforce_id,
    get_role_access_description,
    get_role_description,
    get_role_title,
    json,
    jsonify,
    normalize_role,
    parse,
    persist_workforce_profile,
    read_csv,
    redirect,
    render_template,
    request,
    session,
    time,
    url_for,
    urllib_error,
    urllib_request,
    uuid,
)


@app.route('/auth/google')
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return render_template('login.html', error='Google Sign-In is not configured.')

    redirect_uri = _google_redirect_uri()
    parsed_redirect = parse.urlparse(redirect_uri)
    current_host = (request.host or '').split(':')[0].lower()
    target_host = (parsed_redirect.hostname or '').lower()
    if target_host and current_host and target_host != current_host:
        aligned_login_url = parse.urlunparse((
            request.scheme,
            parsed_redirect.netloc,
            url_for('google_login'),
            '',
            '',
            ''
        ))
        return redirect(aligned_login_url)

    state = uuid.uuid4().hex
    session['google_oauth_state'] = state
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    }
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + parse.urlencode(params)
    return redirect(auth_url)


@app.route('/auth/google/callback')
def google_callback():
    if request.args.get('error'):
        return render_template('login.html', error='Google Sign-In was cancelled or denied.')

    state = request.args.get('state', '')
    expected_state = session.pop('google_oauth_state', None)
    if not state or not expected_state or state != expected_state:
        return render_template('login.html', error='Google Sign-In failed. Please try again.')

    code = request.args.get('code')
    if not code:
        return render_template('login.html', error='Google Sign-In failed. Missing authorization code.')

    try:
        redirect_uri = _google_redirect_uri()
        token_payload = parse.urlencode({
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')

        token_request = urllib_request.Request(
            'https://oauth2.googleapis.com/token',
            data=token_payload,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        with urllib_request.urlopen(token_request, timeout=12) as token_response:
            token_data = json.loads(token_response.read().decode('utf-8'))

        access_token = token_data.get('access_token', '')
        if not access_token:
            return render_template('login.html', error='Google Sign-In failed while getting access token.')

        profile_request = urllib_request.Request(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        with urllib_request.urlopen(profile_request, timeout=12) as profile_response:
            profile_data = json.loads(profile_response.read().decode('utf-8'))

        email = (profile_data.get('email') or '').strip().lower()
        if not email:
            return render_template('login.html', error='Google account email is unavailable.')

        users = read_csv(USERS_CSV)
        matched_user = next(
            (
                u for u in users
                if ((u.get('username') or u.get('email') or '').strip().lower() == email)
                and _truthy(u.get('is_active', 'true'), default=True)
            ),
            None
        )
        if not matched_user:
            session['google_profile'] = {
                'email': email,
                'full_name': profile_data.get('name', ''),
                'picture': profile_data.get('picture', '')
            }
            return redirect(url_for('google_onboarding'))

        return _start_user_session(matched_user)
    except urllib_error.HTTPError as e:
        body = ''
        try:
            body = e.read().decode('utf-8', errors='ignore')
        except Exception:
            body = ''
        print(f'Google OAuth HTTP error: {e.code} {body}')
        parsed = {}
        try:
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = {}
        error_code = str(parsed.get('error') or '').lower()
        error_description = str(parsed.get('error_description') or '').strip()
        lower_body = body.lower()
        if 'invalid_client' in lower_body or error_code == 'invalid_client':
            return render_template('login.html', error='Google OAuth client credentials are invalid. Recheck Client ID/Secret.')
        if 'redirect_uri_mismatch' in lower_body or error_code == 'redirect_uri_mismatch':
            return render_template(
                'login.html',
                error=f'Google redirect URI mismatch. Configure: {_google_redirect_uri()}'
            )
        if error_description:
            return render_template('login.html', error=f'Google Sign-In failed: {error_description}')
        return render_template('login.html', error='Google Sign-In is unavailable right now. Try email/password.')
    except urllib_error.URLError as e:
        reason = str(getattr(e, 'reason', '') or '').strip()
        print(f'Google OAuth URL error: {reason}')
        if reason:
            return render_template('login.html', error=f'Google Sign-In network error: {reason}')
        return render_template('login.html', error='Google Sign-In is unavailable right now. Try email/password.')
    except Exception as e:
        print(f'Google OAuth error: {e}')
        return render_template('login.html', error='Google Sign-In is unavailable right now. Try email/password.')


@app.route('/auth/google/onboarding', methods=['GET', 'POST'])
def google_onboarding():
    profile = session.get('google_profile')
    if not profile:
        return redirect(url_for('login'))

    if request.method == 'POST':
        role = request.form.get('role')
        designation = request.form.get('designation', '').strip()
        department = request.form.get('department', '').strip()
        skills = request.form.get('skills', '').strip()

        if not role or not designation or not department or not skills:
            return render_template('google_onboarding.html', profile=profile, error='All fields are required.')

        users = read_csv(USERS_CSV)
        if any(u.get('username', '').strip().lower() == profile.get('email', '') for u in users):
            session.pop('google_profile', None)
            return redirect(url_for('login'))

        new_user_id = get_next_workforce_id(users, read_csv(EMP_CSV))
        password = generate_secure_password()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        user_row = {
            'id': new_user_id,
            'username': profile.get('email', ''),
            'password_hash': generate_password_hash(password),
            'full_name': profile.get('full_name', ''),
            'role': normalize_role(role),
            'created_at': now,
            'is_active': 'true'
        }

        employee_row = {
            'id': new_user_id,
            'name': profile.get('full_name', ''),
            'email': profile.get('email', ''),
            'position': designation,
            'department': department,
            'company': get_default_company_name(),
            'join_date': now,
            'phone': '',
            'skills': skills,
            'location': '',
            'last_login': now,
            'password_last_changed': now,
            'avatar_url': profile.get('picture', ''),
            'status': 'active',
            'productivity': '80'
        }

        persist_workforce_profile(user_row, employee_row)

        if _use_database(USERS_CSV) and DB_BACKEND == 'mongodb':
            import time
            time.sleep(0.5)
            stored_users = read_csv(USERS_CSV)
            for u in stored_users:
                if u.get('id') == new_user_id:
                    user_row = u
                    break

        session.pop('google_profile', None)
        return _start_user_session(user_row)

    return render_template('google_onboarding.html', profile=profile)


@app.route('/login', methods=['GET','POST'])
def login():
    ensure_demo_org_integrity()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        matched_user = authenticate_user_credentials(
            username,
            password,
            allowed_roles={'admin', 'manager', 'hr', 'teamlead', 'employee'}
        )
        if matched_user:
            return _start_user_session(matched_user)
        return render_template('login.html', error='Invalid email or password')

    return render_template('login.html')


@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('fullName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        designation = request.form.get('designation')
        department = request.form.get('department')
        skills = request.form.get('skills', '')

        print(f"Form data received: {full_name}, {email}, {phone}, {role}, {designation}, {department}, {skills}")

        if not all([full_name, email, phone, role, designation, department, skills]):
            return render_template('signup.html', error='All fields are required')

        users = read_csv(USERS_CSV)
        if any(u['username'] == email for u in users):
            return render_template('signup.html', error='User with this email already exists')

        user_id = get_next_workforce_id(users, read_csv(EMP_CSV))
        password = generate_secure_password()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        user_row = {
            'id': user_id,
            'username': email,
            'password_hash': generate_password_hash(password),
            'full_name': full_name,
            'role': 'employee',  # self sign-up is always an employee; admins promote people
            
            'created_at': current_time,
            'is_active': 'true'
        }

        employee_row = {
            'id': user_id,
            'name': full_name,
            'email': email,
            'position': designation,
            'department': department,
            'company': get_default_company_name(),
            'join_date': current_time,
            'phone': phone,
            'skills': skills,
            'location': '',
            'last_login': '',
            'password_last_changed': current_time,
            'avatar_url': '',
            'status': 'active',
            'productivity': '76'
        }

        print(f"User row: {user_row}")
        print(f"Employee row: {employee_row}")

        try:
            storage_status = persist_workforce_profile(user_row, employee_row)
            print("User and employee saved successfully")
            print(f"Storage status: {storage_status}")
        except Exception as e:
            print(f"Error saving account data: {e}")
            return render_template('signup.html', error=f'Error saving data: {e}')

        # Shown once on the next page; kept out of the URL so it never lands in history or server logs.
        session['new_credentials'] = {
            'employee_id': user_id, 'employee_name': full_name,
            'username': email, 'password': password, 'role': role,
        }
        return redirect(url_for('show_credentials'))

    return render_template('signup.html')


@app.route('/credentials')
def show_credentials():
    creds = session.pop('new_credentials', None) or {}
    employee_id = creds.get('employee_id', '')
    employee_name = creds.get('employee_name', '')
    username = creds.get('username', '')
    password = creds.get('password', '')
    role = creds.get('role', 'employee')

    if not all([employee_name, username, password]):
        return redirect(url_for('signup'))

    return render_template('credentials.html',
                         employee_id=employee_id,
                         employee_name=employee_name,
                         username=username,
                         password=password,
                         role=role,
                         get_role_title=get_role_title,
                         get_role_description=get_role_description,
                         get_role_access_description=get_role_access_description)


@app.route('/api/auth/me')
def api_auth_me():
    user = _session_user_payload()
    if not user:
        return jsonify({'error': 'Not signed in'}), 401
    return jsonify({'user': user})


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.get_json(silent=True) or {}
    matched = authenticate_user_credentials(
        data.get('username') or data.get('email'), data.get('password'),
        allowed_roles={'admin', 'manager', 'hr', 'teamlead', 'employee'}
    )
    if not matched:
        return jsonify({'error': 'Invalid email or password'}), 401
    _start_user_session(matched)
    return jsonify({'user': _session_user_payload()})


@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/auth/signup', methods=['POST'])
def api_auth_signup():
    data = request.get_json(silent=True) or {}
    required = ['fullName', 'email', 'phone', 'designation', 'department']
    if not all(str(data.get(k) or '').strip() for k in required):
        return jsonify({'error': 'Please fill in every field'}), 400
    email = str(data['email']).strip().lower()
    users = read_csv(USERS_CSV)
    if any(str(u.get('username', '')).lower() == email for u in users):
        return jsonify({'error': 'An account with this email already exists'}), 409
    skills = data.get('skills') or ''
    if isinstance(skills, list):
        skills = ', '.join(str(x).strip() for x in skills if str(x).strip())
    # Public sign-up always creates an employee; managers, HR and admins are promoted by an admin.
    user_id = get_next_workforce_id(users, read_csv(EMP_CSV))
    password = generate_secure_password()
    now_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_name = str(data['fullName']).strip()
    user_row = {'id': user_id, 'username': email, 'password_hash': generate_password_hash(password), 'full_name': full_name,
                'role': 'employee', 'created_at': now_text, 'is_active': 'true'}
    employee_row = {'id': user_id, 'name': full_name, 'email': email, 'position': str(data['designation']).strip(),
                    'department': str(data['department']).strip(), 'company': get_default_company_name(), 'join_date': now_text,
                    'phone': str(data['phone']).strip(), 'skills': skills, 'location': '', 'last_login': '',
                    'password_last_changed': now_text, 'avatar_url': '', 'status': 'active', 'productivity': '76'}
    try:
        persist_workforce_profile(user_row, employee_row)
    except Exception as exc:
        return jsonify({'error': f'Could not save the account: {exc}'}), 500
    return jsonify({'credentials': {'employeeId': user_id, 'name': full_name, 'username': email, 'password': password, 'role': 'employee'}}), 201


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
