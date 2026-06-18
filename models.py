from datetime import datetime
from flask_login import UserMixin
from extensions import db
import bcrypt

class User(UserMixin, db.Model):
    """User Model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Profile
    full_name = db.Column(db.String(100))
    avatar = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Settings (JSON)
    settings = db.Column(db.JSON, default={
        'default_quality': '4K',
        'default_api': 'tikwm',
        'upscale_method': 'lanczos',
        'dark_mode': False,
        'auto_download': True,
        'notify_complete': True
    })
    
    # Stats
    total_downloads = db.Column(db.Integer, default=0)
    total_size = db.Column(db.BigInteger, default=0)  # bytes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    downloads = db.relationship('DownloadHistory', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Check password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def __repr__(self):
        return f'<User {self.username}>'


class DownloadHistory(db.Model):
    """Download History Model"""
    __tablename__ = 'download_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Video info
    video_id = db.Column(db.String(50))
    title = db.Column(db.String(200))
    author = db.Column(db.String(100))
    duration = db.Column(db.Integer)
    
    # Download info
    original_quality = db.Column(db.String(20))  # 1080p, 720p, etc.
    output_quality = db.Column(db.String(20))    # 4K, 1080p, etc.
    api_used = db.Column(db.String(50))
    upscale_method = db.Column(db.String(50))
    
    # File info
    file_size = db.Column(db.BigInteger)
    file_path = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.String(20), default='completed')  # pending, processing, completed, failed
    error_message = db.Column(db.Text, nullable=True)
    
    # IP
    ip_address = db.Column(db.String(45))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<DownloadHistory {self.id}: {self.title[:30]}>'


class DownloadQueue(db.Model):
    """Download Queue Model"""
    __tablename__ = 'download_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    url = db.Column(db.String(500), nullable=False)
    quality = db.Column(db.String(20), default='4K')
    api = db.Column(db.String(50), default='tikwm')
    upscale_method = db.Column(db.String(50), default='lanczos')
    
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    priority = db.Column(db.Integer, default=0)  # 0=normal, 1=high
    
    result_file = db.Column(db.String(200))
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<DownloadQueue {self.id}: {self.url[:30]}>'


class Analytics(db.Model):
    """Analytics Model"""
    __tablename__ = 'analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Stats
    total_requests = db.Column(db.Integer, default=0)
    successful_downloads = db.Column(db.Integer, default=0)
    failed_downloads = db.Column(db.Integer, default=0)
    
    # API Stats (JSON)
    api_stats = db.Column(db.JSON, default={})
    
    # Quality Stats (JSON)
    quality_stats = db.Column(db.JSON, default={})
    
    # Total size
    total_size = db.Column(db.BigInteger, default=0)
    
    # Unique users
    unique_users = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
