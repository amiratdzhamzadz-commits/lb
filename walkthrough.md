# Algerian Market Pro - Setup & Security Enhancement

## ✅ What was accomplished

### 1. Dependencies Installation
- All packages from `requirements.txt` were installed successfully.
- Key packages: Flask, SQLAlchemy, Flask-Login, Flask-Mail, Flask-Limiter, Flask-Talisman, Flask-Caching, Flask-WTF, Pillow, openpyxl.

### 2. Database Initialization
- Database migrated to support new models: `ChatRoom`, `ChatMessage` + account lockout fields (`login_attempts`, `locked_until`).
- Default admin account created: `admin@market.dz` / `admin123`.

### 3. Security Enhancements
- **CSRF Protection**: Enabled with `Flask-WTF` CSRFProtect.
- **Rate Limiting**: Login limited to 10/15min, live search to 30/min, global 200/day, 50/hour.
- **Account Lockout**: 5 failed login attempts → 15-minute lock.
- **Content Security Policy**: Strict CSP via Flask-Talisman.
- **Secure Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy.
- **Safe Redirects**: `is_safe_url()` validation on next parameter.
- **Input Sanitization**: All user text sanitized via `html.escape()`.
- **Session Protection**: Strong session protection enabled.
- **Session Security**: HTTP-only, SameSite=Lax cookies.
- **File Upload Validation**: Allowed extensions, max size 5MB, image verification.

### 4. Chat System
- **ChatRoom & ChatMessage models** added to database.
- **Routes**: `/chat` (index), `/chat/<machine_id>` (buyer→seller), `/chat/admin/<user_id>` (admin→user).
- **Real-time polling**: AJAX-based message sending/receiving every 3 seconds.
- **Unread counts** visible in navbar.
- **Chat templates**: `chat_index.html`, `chat_room.html`.

### 5. Admin Enhancements
- **Admin Users page**: `/admin/users` with verification toggle.
- **Machine approval/rejection with notifications**.
- **Report management**.
- **Active chat count** on admin dashboard.

### 6. Error Handling
- Custom error pages: 403, 404, 429, 500 with Arabic messages.
- Database rollback on 500 errors.

### 7. Templates
- Created: `403.html`, `404.html`, `500.html`, `admin_users.html`, `chat_index.html`, `chat_room.html`.
- Updated: `base.html` with chat link and unread badge.

## 📍 Running Application
- **URL**: http://127.0.0.1:5000
- **Admin Login**: admin@market.dz / admin123

## 🔧 Maintenance Notes
- Edit `.env` to set real SMTP credentials for email functionality.
- For production, set `debug=False` and use a proper WSGI server (gunicorn).
- The `uploads/` folder stores all machine images.