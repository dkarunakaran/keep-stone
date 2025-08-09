# KeepStone User Authentication System

This document describes the implementation of the user authentication and authorization system for KeepStone.

## Overview

The authentication system provides:
- **User Registration & Login** - Secure user authentication with password hashing
- **Role-Based Access Control** - Admin and regular user roles
- **Session Management** - Flask-Login integration with "remember me" functionality
- **Admin User Management** - Interface for admins to create, edit, and delete users
- **Security Features** - Password validation, account activation/deactivation, protected routes

## System Components

### 1. User Model (`models/user.py`)
```python
class User(UserMixin, Base):
    - id: Primary key
    - username: Unique username (3-80 chars, alphanumeric + hyphens/underscores)
    - email: Unique email address
    - password_hash: Hashed password (bcrypt)
    - full_name: Display name
    - is_admin: Admin privileges flag
    - is_active: Account activation status
    - created_at: Account creation timestamp
    - updated_at: Last modification timestamp
    - last_login: Last login timestamp
    - notes: Optional admin notes
```

**Features:**
- Password hashing with Werkzeug security
- Input validation for username, email, and password
- Admin user creation method
- Dictionary serialization for API responses

### 2. Authentication Utilities (`utils/auth_utils.py`)
**Decorators:**
- `@login_required` - Requires user authentication
- `@admin_required` - Requires admin privileges
- `@active_user_required` - Requires active account status

**Helper Functions:**
- `init_default_admin()` - Creates default admin if no users exist
- `validate_user_data()` - Validates user input
- `check_unique_user_fields()` - Ensures username/email uniqueness
- `format_user_for_display()` - Prepares user data for templates

### 3. Authentication Routes
**Login System:**
- `GET/POST /login` - User login page
- `GET /logout` - User logout (requires login)

**User Management (Admin Only):**
- `POST /users/add` - Create new user
- `POST /users/<id>/edit` - Edit existing user
- `POST /users/<id>/delete` - Delete user

### 4. Templates

**Login Page (`templates/login.html`):**
- Modern, responsive design with gradient background
- Username/password fields with validation
- "Remember me" checkbox
- Flash message support
- Auto-focus and keyboard navigation

**Settings Page Enhancement (`templates/settings.html`):**
- User management section for admins
- Add new user form
- Existing users table with edit/delete actions
- Modal dialogs for user editing
- Role and status badges

**Navigation Enhancement (`templates/base.html`):**
- User dropdown menu in navigation
- Current user display with admin badge
- Logout link
- Account settings access

## Security Features

### 1. Password Security
- Minimum 6 characters required
- Werkzeug password hashing (PBKDF2)
- Secure password checking

### 2. Access Control
- Route-level authentication with decorators
- Role-based authorization (admin vs user)
- Account activation controls
- Session management with Flask-Login

### 3. Input Validation
- Username format validation (alphanumeric, hyphens, underscores)
- Email format validation with regex
- Password strength requirements
- SQL injection protection through ORM

### 4. Admin Safeguards
- Prevent admin from deleting their own account
- Prevent admin from deactivating their own account
- Require at least one active admin user
- Audit trail for user activities (logging)

## Installation & Setup

### 1. Install Dependencies
```bash
pip install flask-login>=0.6.3
# Or use the updated requirements.txt
pip install -r requirements.txt
```

### 2. Database Migration
The user table will be created automatically when the application starts.

### 3. Default Admin Account
When the application starts and no users exist, a default admin account is created:
- **Username:** `admin`
- **Email:** `admin@keepstone.local`
- **Password:** `admin123`
- **Role:** Admin

**⚠️ IMPORTANT:** Change the default password immediately after first login!

## Usage Guide

### For End Users

1. **Login:**
   - Navigate to `/login`
   - Enter username and password
   - Optionally check "Remember me"
   - Click "Sign In"

2. **Navigation:**
   - User info displayed in top-right dropdown
   - Access account settings via dropdown
   - Logout via dropdown menu

### For Administrators

1. **Access User Management:**
   - Login as admin user
   - Go to Settings page
   - Scroll to "User Management" section

2. **Add New User:**
   - Fill out user details form
   - Set admin privileges if needed
   - Set account status (active/inactive)
   - Click "Create User"

3. **Edit Existing User:**
   - Click edit button in users table
   - Modify user details in modal
   - Update password if needed
   - Save changes

4. **Delete User:**
   - Click delete button in users table
   - Confirm deletion
   - Note: Cannot delete your own account or last admin

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout user

### User Management (Admin Only)
- `POST /users/add` - Create user
- `POST /users/<id>/edit` - Update user
- `POST /users/<id>/delete` - Delete user

## Configuration

### Flask-Login Settings
```python
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
```

### Session Configuration
- Uses Flask's built-in session management
- "Remember me" functionality available
- Secure session cookies (when HTTPS enabled)

## Testing

Run the authentication test script:
```bash
python test_auth.py
```

This will verify:
- Module imports
- User model functionality
- Database table creation
- Configuration loading

## Security Considerations

### Production Deployment
1. **Change Default Admin Password** - Immediately after first deployment
2. **Use HTTPS** - All authentication should use encrypted connections
3. **Secure Secret Key** - Use a strong, unique Flask secret key
4. **Database Security** - Secure database access and backups
5. **Regular Updates** - Keep dependencies updated for security patches

### Best Practices
1. **Password Policies** - Consider implementing stronger password requirements
2. **Account Lockout** - Consider adding account lockout after failed attempts
3. **Audit Logging** - Log all authentication and authorization events
4. **Session Timeout** - Consider implementing session timeouts
5. **Two-Factor Authentication** - Consider adding 2FA for admin accounts

## Troubleshooting

### Common Issues

1. **Import Errors:**
   ```bash
   pip install flask-login
   ```

2. **Database Errors:**
   - Check database permissions
   - Verify SQLAlchemy configuration
   - Ensure database file is writable

3. **Login Issues:**
   - Verify user exists and is active
   - Check password is correct
   - Confirm Flask secret key is set

4. **Permission Errors:**
   - Verify user has required role
   - Check decorator order on routes
   - Confirm session is active

### Debug Mode
Enable Flask debug mode for development:
```python
app.debug = True
```

### Logging
User activities are logged to console. For production, implement proper logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Future Enhancements

Potential improvements to consider:
1. **Two-Factor Authentication** - TOTP or SMS-based 2FA
2. **Password Reset** - Email-based password reset functionality
3. **Account Lockout** - Temporary lockout after failed attempts
4. **Audit Trail** - Complete audit log of all user actions
5. **API Authentication** - Token-based API authentication
6. **Social Login** - OAuth integration with Google/GitHub/etc.
7. **Password Policies** - Configurable password strength requirements
8. **Session Management** - Advanced session controls and monitoring

## Support

For issues or questions about the authentication system:
1. Check this documentation
2. Review the test script output
3. Check application logs
4. Verify configuration settings
5. Test with a fresh database

The authentication system is designed to be secure, user-friendly, and maintainable while providing the necessary access controls for the KeepStone application.
