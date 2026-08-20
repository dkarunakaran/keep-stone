"""
KeepStone REST API Routes

This module provides REST API endpoints for programmatic access to KeepStone.
All endpoints require API key authentication via Authorization header.
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, date, timedelta
from functools import wraps
import hashlib

from models.artifact import Artifact
from models.project import Project
from models.user import User
from models.project_member import ProjectMember
from models.project_config import ProjectConfig
from models.api_key import ApiKey

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# ============ Response Helpers ============

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


# ============ Serialization Helpers ============

def artifact_to_dict(artifact):
    """Convert artifact to dictionary"""
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


def project_to_dict(project):
    """Convert project to dictionary"""
    return {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'is_default': project.is_default,
        'created_at': project.created_at.isoformat() if project.created_at else None,
    }


def user_to_dict(user):
    """Convert user to dictionary (safe)"""
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
    }


# ============ Authentication ============

def get_api_user(session):
    """Authenticate and return user from API key"""
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
    api_key = ApiKey.get_by_raw_key(session, raw_key)

    if not api_key:
        return None, None

    if not api_key.is_valid():
        return None, None

    # Get the associated user
    user = session.query(User).filter_by(id=api_key.user_id).first()

    if not user or not user.is_active:
        return None, None

    # Update last used
    api_key.update_last_used()
    session.commit()

    return user, api_key


def require_api_key(permission='read'):
    """
    Decorator to require API key authentication.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get session from kwargs or use global
            from app import session as db_session

            user, api_key = get_api_user(db_session)

            if not user:
                return api_error('Invalid or missing API key', 401, 'UNAUTHORIZED')

            if not api_key.has_permission(permission):
                return api_error(f'Insufficient permissions. Required: {permission}', 403, 'FORBIDDEN')

            # Store in flask g for access in route
            g.api_user = user
            g.api_key = api_key
            g.db_session = db_session

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============ Health Check ============

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Public health check endpoint"""
    return api_response({'status': 'healthy', 'service': 'keepstone-api'})


# ============ Artifact Endpoints ============

@api_bp.route('/artifacts', methods=['GET'])
@require_api_key('read')
def list_artifacts():
    """List artifacts with optional filters"""
    session = g.db_session
    project_id = request.args.get('project_id', type=int)
    type_name = request.args.get('type_name')
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    search = request.args.get('search', '').strip()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = session.query(Artifact)

    if not include_deleted:
        query = query.filter(Artifact.deleted == False)

    if project_id:
        query = query.filter(Artifact.project_id == project_id)

    if type_name:
        query = query.filter(Artifact.type_name == type_name)

    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            (Artifact.name.ilike(search_filter) | Artifact.content.ilike(search_filter))
        )

    total = query.count()
    artifacts = query.order_by(Artifact.created_at.desc()).limit(limit).offset(offset).all()

    return api_response({
        'artifacts': [artifact_to_dict(a) for a in artifacts],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@api_bp.route('/artifacts/<int:artifact_id>', methods=['GET'])
@require_api_key('read')
def get_artifact(artifact_id):
    """Get a specific artifact by ID"""
    session = g.db_session
    artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:
        return api_error(f'Artifact with ID {artifact_id} not found', 404, 'NOT_FOUND')

    return api_response({'artifact': artifact_to_dict(artifact)})


@api_bp.route('/artifacts', methods=['POST'])
@require_api_key('write')
def create_artifact():
    """Create a new artifact"""
    session = g.db_session
    data = request.get_json()

    if not data:
        return api_error('Request body is required', 400, 'BAD_REQUEST')

    name = data.get('name')
    content = data.get('content')
    type_name = data.get('type_name')
    project_id = data.get('project_id')
    expiry_date = data.get('expiry_date')

    if not name or not content or not type_name:
        return api_error('name, content, and type_name are required', 400, 'BAD_REQUEST')

    # Parse expiry date if provided
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        except ValueError:
            return api_error('Invalid expiry_date format. Use YYYY-MM-DD', 400, 'BAD_REQUEST')

    artifact = Artifact(
        name=name,
        content=content,
        type_name=type_name,
        project_id=project_id,
        expiry_date=parsed_expiry,
        created_at=datetime.utcnow(),
    )
    session.add(artifact)
    session.commit()

    # Try to add to ChromaDB if available
    try:
        from utils.chroma_utils import ChromaDbClient
        chroma_client = ChromaDbClient()
        chroma_client.add_artifact(artifact)
    except Exception:
        pass  # ChromaDB is optional

    return api_response({'artifact': artifact_to_dict(artifact)}, 'Artifact created successfully', 201)


@api_bp.route('/artifacts/<int:artifact_id>', methods=['PUT'])
@require_api_key('write')
def update_artifact(artifact_id):
    """Update an existing artifact"""
    session = g.db_session
    artifact = session.query(Artifact).filter(
        Artifact.id == artifact_id,
        Artifact.deleted == False
    ).first()

    if not artifact:
        return api_error(f'Artifact with ID {artifact_id} not found', 404, 'NOT_FOUND')

    data = request.get_json()
    if not data:
        return api_error('Request body is required', 400, 'BAD_REQUEST')

    if 'name' in data:
        artifact.name = data['name']
    if 'content' in data:
        artifact.content = data['content']
    if 'type_name' in data:
        artifact.type_name = data['type_name']
    if 'expiry_date' in data:
        if data['expiry_date']:
            try:
                artifact.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                return api_error('Invalid expiry_date format. Use YYYY-MM-DD', 400, 'BAD_REQUEST')
        else:
            artifact.expiry_date = None

    session.commit()

    # Update in ChromaDB if available
    try:
        from utils.chroma_utils import ChromaDbClient
        chroma_client = ChromaDbClient()
        chroma_client.update_artifact(artifact)
    except Exception:
        pass

    return api_response({'artifact': artifact_to_dict(artifact)}, 'Artifact updated successfully')


@api_bp.route('/artifacts/<int:artifact_id>', methods=['DELETE'])
@require_api_key('write')
def delete_artifact(artifact_id):
    """Soft delete an artifact"""
    session = g.db_session
    artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:
        return api_error(f'Artifact with ID {artifact_id} not found', 404, 'NOT_FOUND')

    artifact.soft_delete()
    session.commit()

    # Delete from ChromaDB if available
    try:
        from utils.chroma_utils import ChromaDbClient
        chroma_client = ChromaDbClient()
        chroma_client.delete_artifact(artifact_id)
    except Exception:
        pass

    return api_response(message=f'Artifact {artifact_id} deleted successfully')


@api_bp.route('/artifacts/search', methods=['GET'])
@require_api_key('read')
def search_artifacts():
    """Search artifacts by text"""
    session = g.db_session
    query_text = request.args.get('q', '').strip()
    project_id = request.args.get('project_id', type=int)
    limit = request.args.get('limit', 20, type=int)

    if not query_text:
        return api_error('Query parameter "q" is required', 400, 'BAD_REQUEST')

    search_filter = f'%{query_text}%'
    query = session.query(Artifact).filter(
        Artifact.deleted == False,
        (Artifact.name.ilike(search_filter) | Artifact.content.ilike(search_filter))
    )

    if project_id:
        query = query.filter(Artifact.project_id == project_id)

    artifacts = query.limit(limit).all()

    return api_response({'artifacts': [artifact_to_dict(a) for a in artifacts]})


@api_bp.route('/artifacts/semantic-search', methods=['POST'])
@require_api_key('read')
def semantic_search():
    """Perform semantic search using embeddings"""
    session = g.db_session
    data = request.get_json()

    if not data or not data.get('query'):
        return api_error('Request body with "query" field is required', 400, 'BAD_REQUEST')

    query_text = data['query']
    k = data.get('k', 5)

    try:
        from utils.chroma_utils import ChromaDbClient
        chroma_client = ChromaDbClient()
        results = chroma_client.query(query_text, k=k)

        # Enrich with full artifact data
        enriched_results = []
        for result in results:
            artifact_id = result.get('artifact_id')
            if artifact_id:
                artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
                if artifact and not artifact.deleted:
                    enriched_results.append({
                        'artifact': artifact_to_dict(artifact),
                        'relevance_score': result.get('score'),
                    })

        return api_response({'results': enriched_results})
    except Exception as e:
        return api_error(f'Semantic search error: {str(e)}', 500, 'INTERNAL_ERROR')


# ============ Project Endpoints ============

@api_bp.route('/projects', methods=['GET'])
@require_api_key('read')
def list_projects():
    """List all projects"""
    session = g.db_session
    projects = session.query(Project).all()

    result = []
    for p in projects:
        artifact_count = session.query(Artifact).filter(
            Artifact.project_id == p.id,
            Artifact.deleted == False
        ).count()
        proj_dict = project_to_dict(p)
        proj_dict['artifact_count'] = artifact_count
        result.append(proj_dict)

    return api_response({'projects': result})


@api_bp.route('/projects/<int:project_id>', methods=['GET'])
@require_api_key('read')
def get_project(project_id):
    """Get a specific project with artifact count"""
    session = g.db_session
    project = session.query(Project).filter(Project.id == project_id).first()

    if not project:
        return api_error(f'Project with ID {project_id} not found', 404, 'NOT_FOUND')

    artifact_count = session.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.deleted == False
    ).count()

    result = project_to_dict(project)
    result['artifact_count'] = artifact_count

    return api_response({'project': result})


@api_bp.route('/projects', methods=['POST'])
@require_api_key('write')
def create_project():
    """Create a new project"""
    session = g.db_session
    data = request.get_json()

    if not data or not data.get('name'):
        return api_error('Project name is required', 400, 'BAD_REQUEST')

    project = Project(
        name=data['name'],
        description=data.get('description'),
        created_at=datetime.utcnow(),
    )
    session.add(project)
    session.commit()

    return api_response({'project': project_to_dict(project)}, 'Project created successfully', 201)


@api_bp.route('/projects/<int:project_id>/artifacts', methods=['GET'])
@require_api_key('read')
def get_project_artifacts(project_id):
    """Get all artifacts for a project"""
    session = g.db_session
    project = session.query(Project).filter(Project.id == project_id).first()

    if not project:
        return api_error(f'Project with ID {project_id} not found', 404, 'NOT_FOUND')

    artifacts = session.query(Artifact).filter(
        Artifact.project_id == project_id,
        Artifact.deleted == False
    ).order_by(Artifact.created_at.desc()).all()

    return api_response({'artifacts': [artifact_to_dict(a) for a in artifacts]})


@api_bp.route('/projects/<int:project_id>/types', methods=['GET'])
@require_api_key('read')
def get_project_types(project_id):
    """Get configured artifact types for a project"""
    session = g.db_session
    configs = session.query(ProjectConfig).filter(ProjectConfig.project_id == project_id).all()
    types = [c.config_value for c in configs if c.config_key == "type"]

    return api_response({'project_id': project_id, 'types': types})


# ============ User Endpoints ============

@api_bp.route('/users', methods=['GET'])
@require_api_key('read')
def list_users():
    """List all users (admin only)"""
    session = g.db_session

    if not g.api_user.is_admin:
        return api_error('Admin access required', 403, 'FORBIDDEN')

    users = session.query(User).all()
    return api_response({'users': [user_to_dict(u) for u in users]})


@api_bp.route('/users/me', methods=['GET'])
@require_api_key('read')
def get_current_user():
    """Get the authenticated user's info"""
    return api_response({'user': user_to_dict(g.api_user)})


# ============ Expiry Endpoints ============

@api_bp.route('/artifacts/expiring', methods=['GET'])
@require_api_key('read')
def list_expiring_artifacts():
    """List artifacts expiring soon or already expired"""
    session = g.db_session
    days = request.args.get('days', 14, type=int)
    include_expired = request.args.get('include_expired', 'true').lower() == 'true'

    today = date.today()
    future_date = today + timedelta(days=days)

    query = session.query(Artifact).filter(
        Artifact.deleted == False,
        Artifact.expiry_date.isnot(None)
    )

    if include_expired:
        query = query.filter(Artifact.expiry_date <= future_date)
    else:
        query = query.filter(Artifact.expiry_date >= today, Artifact.expiry_date <= future_date)

    artifacts = query.order_by(Artifact.expiry_date).all()

    results = []
    for a in artifacts:
        artifact_dict = artifact_to_dict(a)
        artifact_dict['days_until_expiry'] = (a.expiry_date - today).days if a.expiry_date else None
        results.append(artifact_dict)

    return api_response({'artifacts': results})


@api_bp.route('/artifacts/expired', methods=['GET'])
@require_api_key('read')
def list_expired_artifacts():
    """List all expired artifacts"""
    session = g.db_session
    today = date.today()

    artifacts = session.query(Artifact).filter(
        Artifact.deleted == False,
        Artifact.expiry_date.isnot(None),
        Artifact.expiry_date < today
    ).order_by(Artifact.expiry_date).all()

    results = []
    for a in artifacts:
        artifact_dict = artifact_to_dict(a)
        artifact_dict['days_expired'] = (today - a.expiry_date).days if a.expiry_date else None
        results.append(artifact_dict)

    return api_response({'artifacts': results})


# ============ API Key Management ============

@api_bp.route('/api-keys', methods=['GET'])
@require_api_key('read')
def list_api_keys():
    """List user's API keys"""
    session = g.db_session
    keys = session.query(ApiKey).filter(ApiKey.user_id == g.api_user.id).all()

    return api_response({'api_keys': [k.to_dict() for k in keys]})


@api_bp.route('/api-keys', methods=['POST'])
@require_api_key('write')
def create_api_key():
    """Create a new API key"""
    session = g.db_session
    data = request.get_json()

    if not data or not data.get('name'):
        return api_error('API key name is required', 400, 'BAD_REQUEST')

    name = data['name']
    permissions = data.get('permissions', 'read')
    expires_days = data.get('expires_days')

    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    api_key, raw_key = ApiKey.create(
        user_id=g.api_user.id,
        name=name,
        permissions=permissions,
        expires_at=expires_at
    )
    session.add(api_key)
    session.commit()

    # Return the raw key only once
    result = api_key.to_dict()
    result['key'] = raw_key

    return api_response({'api_key': result}, 'API key created. Save this key - it will not be shown again!', 201)


@api_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@require_api_key('write')
def revoke_api_key(key_id):
    """Revoke an API key"""
    session = g.db_session
    api_key = session.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == g.api_user.id
    ).first()

    if not api_key:
        return api_error(f'API key with ID {key_id} not found', 404, 'NOT_FOUND')

    api_key.is_active = False
    session.commit()

    return api_response(message=f'API key {key_id} revoked successfully')
