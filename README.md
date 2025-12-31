# Junglore Backend

FastAPI backend for the Junglore wildlife conservation platform with admin panel.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git

### Setup & Run

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start server:**
   ```bash
   ./start.sh
   # OR
   python3 start_with_large_limits.py
   ```

4. **Access:**
   - **API**: http://127.0.0.1:8000
   - **Admin**: http://127.0.0.1:8000/admin (uses same credentials as environment variables)
   - **Docs**: http://127.0.0.1:8000/api/docs

## 📧 Email Verification

- **Current Status**: Email service disabled (POSTMARK_SERVER_TOKEN not configured)
- **Signup Behavior**: Users can register, OTP logged in server logs for manual verification
- **To Enable Email**: Set POSTMARK_SERVER_TOKEN environment variable with valid Postmark token
- **Manual Verification**: Check Railway logs for OTP codes until email service is configured

## 🔐 Security Notes

- **Admin Password**: Default `admin123` only allowed in development
- **Production**: Requires strong admin password (change ADMIN_PASSWORD environment variable)
- **Password Requirements**: 6-72 characters (bcrypt limitation)

## 📁 Structure

```
app/
├── admin/          # Admin panel
├── api/            # API endpoints  
├── core/           # Configuration
├── db/             # Database
├── models/         # Data models
└── main.py         # FastAPI app
```

## 🔧 Configuration

- **requirements.txt**: Dependencies
- **start_with_large_limits.py**: Server (50MB upload limit)
- **start.sh**: Startup script

## 🎨 Features

### Admin Panel
- Media management (upload, edit, delete)
- Content management (blogs, case studies)
- User authentication
- Featured images management

### API
- RESTful endpoints
- File upload (50MB limit)
- Authentication & authorization
- Auto-generated documentation

## 🗄️ Database

- SQLite (default) with SQLAlchemy ORM
- Auto-created on first run
- Alembic migrations

## 🔧 Development

```bash
# Install dependencies
pip install - requirements.txt

# Run tests
pytest

# Start development server
python3 start_with_large_limits.py
```

## 📝 Environment Variables

The application uses these optional environment variables:
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SECRET_KEY`: JWT secret key (auto-generated if not set)
- `DEBUG`: Enable debug mode (default: False)

## 🚨 Troubleshooting

### Common Issues

**Admin templates not found:**
- Ensure `app/admin/templates/` files are committed to git
- Check `.gitignore` doesn't exclude admin templates

**File upload errors:**
- Verify upload directory permissions
- Check file size limits (50MB max)

**Database errors:**
- Delete `app.db` to reset database
- Run migrations: `alembic upgrade head`

### Support

For issues or questions, check the admin panel logs or API documentation at `/api/docs`.