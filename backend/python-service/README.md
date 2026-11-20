# CampusOS Authentication Service

The **CampusOS Authentication Service** is a Django REST Framework microservice that manages user identities, multi-role authentication (Super Admin, Admin, Faculty, Student), JSON Web Token (JWT) issuing and refreshing, and initial password setup for CampusOS.

---

## 1. Tech Stack

- **Framework**: Django 5.2 + Django REST Framework 3.18
- **Authentication**: `djangorestframework-simplejwt` + `PyJWT` (HS256)
- **Database**: PostgreSQL (Production) / SQLite3 (Local development fallback)
- **CORS**: `django-cors-headers`
- **WSGI / Production**: `gunicorn` + `whitenoise`

---

## 2. Environment Variables

Create a `.env` file for local development using [.env.example](file:///c:/Users/ASUS/OneDrive/Desktop/CampusOS/backend/python-service/.env.example) as a template.

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `SECRET_KEY` | Django cryptographic signing secret | Required in production |
| `DEBUG` | Enable debug mode (`True` for local, `False` for production) | `False` on Render |
| `ALLOWED_HOSTS` | Comma-separated list of permitted hostnames | `localhost,127.0.0.1,auth.onrender.com` |
| `DATABASE_URL` | Render Managed PostgreSQL connection URL | `postgres://user:pass@host:5432/dbname` |
| `DB_NAME`, `DB_HOST`, ... | Individual PostgreSQL parameters if not using `DATABASE_URL` | See `.env.example` |
| `JWT_SECRET_KEY` | Shared secret for signing JWTs (must match LMS service) | Shared secret string |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_LIFETIME_MINUTES` | Access token lifespan in minutes | `60` |
| `REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token lifespan in days | `7` |
| `CORS_ALLOWED_ORIGINS` | Permitted frontend origins | `http://localhost:3000,https://campusos.onrender.com` |

---

## 3. Super Admin Production Bootstrap

CampusOS Auth includes a dedicated, secure, one-time bootstrap management command:
```bash
python manage.py bootstrap_superadmin
```

This command reads credentials exclusively from environment variables, sets up the initial Super Admin account, and protects existing user roles from unauthorized promotion.

### Required Environment Variables

Configure these variables in your deployment environment (e.g. Render Dashboard):

| Variable | Description |
| :--- | :--- |
| `SUPERADMIN_USERNAME` | Username for the initial Super Admin (e.g. `superadmin`) |
| `SUPERADMIN_EMAIL` | Valid institutional email address (e.g. `admin@campusos.edu`) |
| `SUPERADMIN_PASSWORD` | Cryptographically strong password (at least 16 characters recommended) |

> [!WARNING]
> Never hardcode credentials in code, configuration files, or command arguments. The command will abort immediately if any of these three variables are missing.

### Step-by-Step Execution on Render

1. **Deploy Service**: Deploy the Auth service to Render as a Web Service.
2. **Add Environment Variables**:
   - In the Render Dashboard, navigate to **Environment** > **Add Environment Variable**.
   - Add `SUPERADMIN_USERNAME`, `SUPERADMIN_EMAIL`, and `SUPERADMIN_PASSWORD`.
   - Save the changes (Render will redeploy).
3. **Open Render Shell**:
   - In the Render Dashboard, go to your service's **Shell** tab.
4. **Execute Bootstrap Command**:
   ```bash
   python manage.py bootstrap_superadmin
   ```
   **Output:**
   ```text
   Super Admin 'superadmin' (admin@campusos.edu) successfully created.
   ```
5. **Clean Up Environment Variables (Best Practice)**:
   - Once the Super Admin is created, return to the **Environment** tab in Render.
   - Delete the `SUPERADMIN_PASSWORD` variable to ensure it is not permanently retained in the environment dashboard.

---

## 4. Security Safeguards

- **Zero Credential Exposure**: Passwords are never echoed to `stdout`, `stderr`, or system log files.
- **Strict Role Integrity**: If the specified username already exists with another role (such as `student` or `faculty`), the command **aborts with an error** and will never silently promote the existing account.
- **Idempotent**: If the specified Super Admin already exists with `role='super_admin'`, the command safely reports that the user exists and **does not alter the existing password**.
- **Standard Hashing**: Passwords are saved strictly through Django's PBKDF2 cryptographic password hasher (`is_staff=True`, `is_superuser=True`, `is_active=True`, `role='super_admin'`).

---

## 5. Running Tests

To run the automated test suite for the bootstrap command and accounts app:

```bash
python manage.py test accounts
```
