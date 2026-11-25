# TaskVise

Task, project, workload and leave management with a view for every role (admin, manager, HR, team lead, employee).

```
.
├── web/                      Next.js 16 frontend (App Router, Tailwind 4)
│   ├── app/(site)/           landing, sign-in, sign-up
│   ├── app/(app)/[role]/     role dashboards: one route, a registry of views per role
│   ├── components/views/     feature views (common.tsx, roles.tsx) and the registry (index.tsx)
│   ├── components/           shell (sidebar, top bar), UI kit
│   └── lib/                  API client, auth context, navigation per role
├── backend/
│   ├── taskvise/             Flask backend
│   │   ├── core.py           app object, configuration, TiDB storage layer, shared helpers
│   │   └── features/         one module per area; importing it registers its routes
│   │       ├── auth.py          sign-in, sign-up, Google, /api/auth/*
│   │       ├── employee_api.py  /api/employee/*  tasks, projects, leave, help, profile, settings, reports
│   │       ├── manager_api.py   /api/manager/*, /api/task, /api/project
│   │       ├── teamlead_api.py  /api/teamlead/*
│   │       ├── admin_api.py     /api/admin/*, company management
│   │       ├── notes_api.py     /api/notes
│   │       ├── pages.py         legacy server-rendered pages (replaced by web/)
│   │       └── system.py        health, static files, error handlers
│   └── taskvise_admin/       platform-admin console (separate Flask app)
├── templates/, static/       legacy pages and shared assets (illustrations, icons)
├── api/index.py              Vercel entry for the Flask backend
└── app.py                    local runner (python app.py)
```

## Data

TiDB Cloud (MySQL compatible) is the only data store. There is no file or MongoDB fallback.
Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` (a local `.env` works), plus `FLASK_SECRET`.
The app refuses to start without them.

No accounts are baked into the code. A founder (platform admin) account exists only when
`TASKVISE_FOUNDER_EMAIL` and `TASKVISE_FOUNDER_PASSWORD` are set. Demo data is created only when
`TASKVISE_SEED_DEMO=1` (never on the hosted site).

## Run locally

```
pip install -r requirements.txt
python app.py                      # Flask on :5000 (set PORT to change)
cd web && npm install && FLASK_URL=http://127.0.0.1:5000 npm run dev
```

The browser only talks to the Next.js origin. `/api`, `/auth` and `/static` are proxied to Flask (see `web/next.config.ts`),
so the session cookie lives on one domain. Set `FLASK_URL` to the deployed Flask URL in production.

## Roles and what they see

| Role | Views |
| --- | --- |
| Employee | overview, tasks, projects, workload and help, leave, reports, notifications, profile, settings |
| Team lead | overview, team, projects, tasks, reports, notifications, profile |
| Manager | overview, team, projects, tasks, leave approvals, reports, notifications, profile |
| HR | the manager views, framed around people and leave |
| Admin | dashboard, employees, projects, tasks, settings |
