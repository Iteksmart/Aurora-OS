"""
Aurora OS User and Access Management System
Comprehensive user management with role-based access control
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import jwt
import bcrypt
import secrets
from password_strength import PasswordPolicy

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    SUPER_ADMIN = "super_admin"      # Full system access
    ADMIN = "admin"                  # Full cluster management
    OPERATOR = "operator"            # Day-to-day operations
    DEVELOPER = "developer"          # Development and debugging
    ANALYST = "analyst"              # Monitoring and analytics
    VIEWER = "viewer"                # Read-only access
    GUEST = "guest"                  # Limited read access

class Permission(Enum):
    """System permissions"""
    # Cluster management
    CLUSTER_VIEW = "cluster:view"
    CLUSTER_MANAGE = "cluster:manage"
    CLUSTER_CONFIGURE = "cluster:configure"
    
    # Node management
    NODE_VIEW = "node:view"
    NODE_MANAGE = "node:manage"
    NODE_ADD = "node:add"
    NODE_REMOVE = "node:remove"
    
    # User management
    USER_VIEW = "user:view"
    USER_MANAGE = "user:manage"
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    
    # Monitoring
    MONITORING_VIEW = "monitoring:view"
    MONITORING_EXPORT = "monitoring:export"
    ALERTS_MANAGE = "alerts:manage"
    
    # System
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_CONFIGURE = "system:configure"

class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    LOCKED = "locked"

class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"

@dataclass
class Role:
    """User role with permissions"""
    id: str
    name: str
    description: str
    permissions: Set[Permission]
    level: int  # Higher level = more privileged
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "level": self.level
        }

@dataclass
class User:
    """User account"""
    id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    login_attempts: int
    locked_until: Optional[datetime]
    password_changed_at: datetime
    mfa_enabled: bool
    mfa_secret: Optional[str]
    metadata: Dict[str, Any]
    
    # Runtime fields (not stored)
    password_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without sensitive data)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_attempts": self.login_attempts,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "password_changed_at": self.password_changed_at.isoformat(),
            "mfa_enabled": self.mfa_enabled,
            "metadata": self.metadata
        }
    
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        return (
            self.locked_until is not None and 
            datetime.now() < self.locked_until
        )
    
    def is_password_expired(self, max_age_days: int = 90) -> bool:
        """Check if password is expired"""
        age = datetime.now() - self.password_changed_at
        return age.days > max_age_days

@dataclass
class UserSession:
    """User session"""
    id: str
    user_id: str
    token: str
    refresh_token: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    ip_address: str
    user_agent: str
    status: SessionStatus
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status.value
        }
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid"""
        return (
            not self.is_expired() and 
            self.status == SessionStatus.ACTIVE
        )

class UserManagementSystem:
    """User and access management system"""
    
    def __init__(self, jwt_secret: str):
        self.logger = logging.getLogger(__name__)
        self.jwt_secret = jwt_secret
        
        # Data storage
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.sessions: Dict[str, UserSession] = {}
        
        # Configuration
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.session_duration = timedelta(hours=24)
        self.password_policy = PasswordPolicy.from_names(
            length=8,
            uppercase=1,
            numbers=1,
            special=1
        )
        
        # Initialize roles and default admin
        self._initialize_roles()
        self._initialize_default_admin()
    
    def _initialize_roles(self):
        """Initialize default roles with permissions"""
        roles = [
            Role(
                id="super_admin",
                name="Super Administrator",
                description="Full system access",
                permissions=set(Permission),
                level=100
            ),
            Role(
                id="admin",
                name="Administrator",
                description="Full cluster management",
                permissions={
                    Permission.CLUSTER_VIEW, Permission.CLUSTER_MANAGE, Permission.CLUSTER_CONFIGURE,
                    Permission.NODE_VIEW, Permission.NODE_MANAGE, Permission.NODE_ADD, Permission.NODE_REMOVE,
                    Permission.USER_VIEW, Permission.USER_MANAGE, Permission.USER_CREATE,
                    Permission.MONITORING_VIEW, Permission.MONITORING_EXPORT, Permission.ALERTS_MANAGE,
                    Permission.SYSTEM_BACKUP, SYSTEM_LOGS
                },
                level=80
            ),
            Role(
                id="operator",
                name="Operator",
                description="Day-to-day operations",
                permissions={
                    Permission.CLUSTER_VIEW,
                    Permission.NODE_VIEW, Permission.NODE_MANAGE,
                    Permission.MONITORING_VIEW, Permission.ALERTS_MANAGE,
                    Permission.SYSTEM_LOGS
                },
                level=60
            ),
            Role(
                id="developer",
                name="Developer",
                description="Development and debugging",
                permissions={
                    Permission.CLUSTER_VIEW,
                    Permission.NODE_VIEW,
                    Permission.MONITORING_VIEW, Permission.MONITORING_EXPORT,
                    Permission.SYSTEM_LOGS
                },
                level=50
            ),
            Role(
                id="analyst",
                name="Analyst",
                description="Monitoring and analytics",
                permissions={
                    Permission.CLUSTER_VIEW,
                    Permission.NODE_VIEW,
                    Permission.MONITORING_VIEW, Permission.MONITORING_EXPORT
                },
                level=40
            ),
            Role(
                id="viewer",
                name="Viewer",
                description="Read-only access",
                permissions={
                    Permission.CLUSTER_VIEW,
                    Permission.NODE_VIEW,
                    Permission.MONITORING_VIEW
                },
                level=20
            ),
            Role(
                id="guest",
                name="Guest",
                description="Limited read access",
                permissions={
                    Permission.CLUSTER_VIEW
                },
                level=10
            )
        ]
        
        for role in roles:
            self.roles[role.id] = role
    
    def _initialize_default_admin(self):
        """Initialize default admin user"""
        admin_user = User(
            id="admin-001",
            username="admin",
            email="admin@auroraos.local",
            full_name="System Administrator",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=None,
            login_attempts=0,
            locked_until=None,
            password_changed_at=datetime.now(),
            mfa_enabled=False,
            mfa_secret=None,
            metadata={"auto_created": True}
        )
        
        # Set default password (aurora123)
        password_hash = bcrypt.hashpw("aurora123".encode('utf-8'), bcrypt.gensalt())
        admin_user.password_hash = password_hash.decode('utf-8')
        
        self.users[admin_user.id] = admin_user
        self.logger.info("Default admin user initialized")
    
    async def create_user(self, username: str, email: str, full_name: str, 
                         role: UserRole, password: str, created_by: str) -> Tuple[bool, str]:
        """Create a new user"""
        try:
            # Validate inputs
            if not username or not email or not password:
                return False, "Username, email, and password are required"
            
            # Check if username already exists
            for user in self.users.values():
                if user.username == username:
                    return False, "Username already exists"
                if user.email == email:
                    return False, "Email already exists"
            
            # Validate password strength
            if len(self.password_policy.test(password)) > 0:
                return False, "Password does not meet security requirements"
            
            # Create user
            user = User(
                id=str(uuid.uuid4()),
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                status=UserStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_login=None,
                login_attempts=0,
                locked_until=None,
                password_changed_at=datetime.now(),
                mfa_enabled=False,
                mfa_secret=None,
                metadata={"created_by": created_by}
            )
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            user.password_hash = password_hash.decode('utf-8')
            
            self.users[user.id] = user
            
            self.logger.info(f"User created: {username} by {created_by}")
            return True, "User created successfully"
            
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return False, f"Error creating user: {str(e)}"
    
    async def authenticate_user(self, username: str, password: str, 
                              ip_address: str, user_agent: str) -> Tuple[bool, str, Optional[UserSession]]:
        """Authenticate user and create session"""
        try:
            # Find user
            user = None
            for u in self.users.values():
                if u.username == username:
                    user = u
                    break
            
            if not user:
                self.logger.warning(f"Login attempt for unknown user: {username}")
                return False, "Invalid credentials", None
            
            # Check account status
            if user.status != UserStatus.ACTIVE:
                return False, f"Account is {user.status.value}", None
            
            # Check if account is locked
            if user.is_locked():
                return False, "Account is temporarily locked", None
            
            # Check password expiration
            if user.is_password_expired():
                return False, "Password has expired", None
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                # Increment login attempts
                user.login_attempts += 1
                user.updated_at = datetime.now()
                
                # Lock account if too many attempts
                if user.login_attempts >= self.max_login_attempts:
                    user.locked_until = datetime.now() + self.lockout_duration
                    self.logger.warning(f"Account locked due to failed attempts: {username}")
                
                return False, "Invalid credentials", None
            
            # Reset login attempts on successful login
            user.login_attempts = 0
            user.last_login = datetime.now()
            user.updated_at = datetime.now()
            
            # Create session
            session = await self._create_session(user.id, ip_address, user_agent)
            
            self.logger.info(f"User authenticated: {username} from {ip_address}")
            return True, "Authentication successful", session
            
        except Exception as e:
            self.logger.error(f"Error authenticating user: {e}")
            return False, f"Authentication error: {str(e)}", None
    
    async def _create_session(self, user_id: str, ip_address: str, user_agent: str) -> UserSession:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user_id,
            'session_id': session_id,
            'exp': int((now + self.session_duration).timestamp()),
            'iat': int(now.timestamp())
        }, self.jwt_secret, algorithm='HS256')
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(32)
        
        session = UserSession(
            id=session_id,
            user_id=user_id,
            token=token,
            refresh_token=refresh_token,
            created_at=now,
            expires_at=now + self.session_duration,
            last_accessed=now,
            ip_address=ip_address,
            user_agent=user_agent,
            status=SessionStatus.ACTIVE
        )
        
        self.sessions[session_id] = session
        return session
    
    async def validate_session(self, token: str) -> Tuple[bool, Optional[User]]:
        """Validate session token"""
        try:
            # Decode JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload.get('session_id')
            user_id = payload.get('user_id')
            
            if not session_id or not user_id:
                return False, None
            
            # Check session
            if session_id not in self.sessions:
                return False, None
            
            session = self.sessions[session_id]
            if not session.is_valid():
                return False, None
            
            # Update last accessed
            session.last_accessed = datetime.now()
            
            # Get user
            if user_id not in self.users:
                return False, None
            
            user = self.users[user_id]
            
            # Check user status
            if user.status != UserStatus.ACTIVE:
                return False, None
            
            return True, user
            
        except jwt.ExpiredSignatureError:
            return False, None
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return False, None
    
    async def logout_user(self, token: str) -> bool:
        """Logout user and terminate session"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            session_id = payload.get('session_id')
            
            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]
                session.status = SessionStatus.TERMINATED
                del self.sessions[session_id]
                
                self.logger.info(f"User logged out: session {session_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error logging out user: {e}")
            return False
    
    def check_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        # Get user role
        role_name = user.role.value
        if role_name not in self.roles:
            return False
        
        role = self.roles[role_name]
        
        # Check if permission is in role
        return permission in role.permissions
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for a user"""
        role_name = user.role.value
        if role_name not in self.roles:
            return set()
        
        return self.roles[role_name].permissions
    
    async def update_user(self, user_id: str, **kwargs) -> Tuple[bool, str]:
        """Update user information"""
        try:
            if user_id not in self.users:
                return False, "User not found"
            
            user = self.users[user_id]
            
            # Update allowed fields
            updatable_fields = ['email', 'full_name', 'role', 'status', 'metadata']
            
            for field, value in kwargs.items():
                if field in updatable_fields:
                    setattr(user, field, value)
            
            user.updated_at = datetime.now()
            
            self.logger.info(f"User updated: {user.username}")
            return True, "User updated successfully"
            
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return False, f"Error updating user: {str(e)}"
    
    async def change_password(self, user_id: str, old_password: str, 
                            new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        try:
            if user_id not in self.users:
                return False, "User not found"
            
            user = self.users[user_id]
            
            # Verify old password
            if not bcrypt.checkpw(old_password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return False, "Current password is incorrect"
            
            # Validate new password
            if len(self.password_policy.test(new_password)) > 0:
                return False, "New password does not meet security requirements"
            
            # Update password
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            user.password_hash = password_hash.decode('utf-8')
            user.password_changed_at = datetime.now()
            user.updated_at = datetime.now()
            
            # Invalidate all sessions for this user
            for session_id, session in list(self.sessions.items()):
                if session.user_id == user_id:
                    session.status = SessionStatus.TERMINATED
                    del self.sessions[session_id]
            
            self.logger.info(f"Password changed for user: {user.username}")
            return True, "Password changed successfully"
            
        except Exception as e:
            self.logger.error(f"Error changing password: {e}")
            return False, f"Error changing password: {str(e)}"
    
    def get_users_list(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get list of users"""
        users_list = []
        
        for user in self.users.values():
            if not include_inactive and user.status != UserStatus.ACTIVE:
                continue
            
            users_list.append(user.to_dict())
        
        return sorted(users_list, key=lambda u: u['username'])
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions"""
        sessions_list = []
        
        for session in self.sessions.values():
            if session.is_valid():
                session_data = session.to_dict()
                # Add user information
                if session.user_id in self.users:
                    user = self.users[session.user_id]
                    session_data['username'] = user.username
                    session_data['full_name'] = user.full_name
                
                sessions_list.append(session_data)
        
        return sorted(sessions_list, key=lambda s: s['last_accessed'], reverse=True)
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Test function
async def test_user_management():
    """Test the user management system"""
    ums = UserManagementSystem("test-secret-key")
    
    # Test user creation
    success, message = await ums.create_user(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role=UserRole.DEVELOPER,
        password="TestPass123!",
        created_by="admin"
    )
    
    print(f"User creation: {success} - {message}")
    
    # Test authentication
    success, message, session = await ums.authenticate_user(
        username="testuser",
        password="TestPass123!",
        ip_address="127.0.0.1",
        user_agent="Test Agent"
    )
    
    print(f"Authentication: {success} - {message}")
    
    if session:
        # Test session validation
        valid, user = await ums.validate_session(session.token)
        print(f"Session validation: {valid} - User: {user.username if user else 'None'}")
        
        # Test logout
        logout_success = await ums.logout_user(session.token)
        print(f"Logout: {logout_success}")
    
    # List users
    users = ums.get_users_list()
    print(f"Total users: {len(users)}")

if __name__ == "__main__":
    asyncio.run(test_user_management())