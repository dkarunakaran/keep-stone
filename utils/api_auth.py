"""
API Authentication and Utilities for KeepStone REST API
"""
from functools import wraps
from flask import request, jsonify
from datetime import datetime


def api_response(data=None, message=None, status=200, error=None):
    """Standard API response format"""
    response = {'success': status < 400}
    if message:
        response['message'] = message
    if data is not None:
        response['data'] = data
    if error:
        response['error'] = error
    return jsonify(response), status


def api_error(message, status=400, error_code=None):
    """Standard error response"""
    response = {'success': False, 'error': message}
    if error_code:
        response['code'] = error_code
    return jsonify(response), status


def get_api_user():
    """
    Get the user associated with the API key from request headers.
    Returns (user, api_key) tuple or (None, None) if not authenticated.
    """
    from models.user import User
    from models.api_key import ApiKey

    auth_header = request.headers.get('Authorization', '')

    if not auth_header:
        return None, None

    # Support "Bearer <key>" or just "<key>"
    if auth_header.startswith('Bearer '):
        raw_key = auth_header[7:].strip()
    else:
        raw_key = auth_header.strip()

    if not raw_key:
        return None, None

    # Find and validate the API key
    key_hash = ApiKey.hash_key(raw_key)
    api_key = request.session.query(ApiKey).filter_by(key_hash=key_hash).first()

    if not api_key:
        return None, None

    if not api_key.is_valid():
        return None, None

    # Get the associated user
    user = request.session.query(User).filter_by(id=api_key.user_id).first()

    if not user or not user.is_active:
        return None, None

    # Update last used
    api_key.update_last_used()
    request.session.commit()

    return user, api_key


def require_api_key(permission='read'):
    """
    Decorator to require API key authentication.
    Usage: @require_api_key('read') or @require_api_key('write')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g

            # Get session from app context
            from app import session as db_session
            # Store session in request for get_api_user
            class RequestProxy:
                pass
            request.session = db_session

            user, api_key = get_api_user()

            if not user:
                return api_error('Invalid or missing API key', 401, 'UNAUTHORIZED')

            if not api_key.has_permission(permission):
                return api_error(f'Insufficient permissions. Required: {permission}', 403, 'FORBIDDEN')

            # Store in flask g for access in route
            g.api_user = user
            g.api_key = api_key

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_api_user_from_context():
    """Get the authenticated API user from flask g context"""
    from flask import g
    return getattr(g, 'api_user', None)


def artifact_to_api_dict(artifact):
    """Convert artifact to API response dictionary"""
    return {
        'id': artifact.id,
        'name': artifact.name,
        'content': artifact.content,
        'type_name': artifact.type_name,
        'project_id': artifact.project_id,
        'expiry_date': artifact.expiry_date.isoformat() if artifact.expiry_date else None,
        'is_expired': artifact.is_expired() if hasattr(artifact, 'is_expired') else False,
        'images': artifact.images or [],
        'created_at': artifact.created_at.isoformat() if artifact.created_at else None,
        'deleted': artifact.deleted,
    }


def project_to_api_dict(project, session=None, artifact_count=None):
    """Convert project to API response dictionary"""
    result = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'is_default': project.is_default,
        'created_at': project.created_at.isoformat() if project.created_at else None,
    }
    if artifact_count is not None:
        result['artifact_count'] = artifact_count
    return result


def user_to_api_dict(user):
    """Convert user to API response dictionary (without sensitive data)"""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
    }
