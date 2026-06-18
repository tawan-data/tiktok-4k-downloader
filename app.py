import os
import re
import subprocess
import shutil
import tempfile
import time
import uuid
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, render_template, url_for, redirect, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import requests
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import extensions and config
from extensions import db, migrate, login_manager, session as session_ext, csrf, cors
from config import config, DevelopmentConfig

# Create app
app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
session_ext.init_app(app)
csrf.init_app(app)
cors.init_app(app)

# Import models (after db init)
from models import User, DownloadHistory, DownloadQueue, Analytics

# Import blueprints
from auth import auth_bp
app.register_blueprint(auth_bp)

# Import API handlers
from tiktok_apis import download_tiktok, get_available_apis

# Create directories
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

# FFmpeg path
FFMPEG_PATH = shutil.which('ffmpeg') or '/usr/bin/ffmpeg'

# ======================
# Utility Functions
# ======================

def check_ffmpeg():
    """ตรวจสอบ FFmpeg"""
    return shutil.which('ffmpeg') is not None

def clean_filename(title):
    """Clean filename"""
    cleaned = re.sub(r"[^\w\s\u0e00-\u0e7f-]", "", title)
    cleaned = cleaned.strip()[:100]
    return cleaned if cleaned else "tiktok_video"

def get_video_info(filepath):
    """Get video info"""
    try:
        cmd = [FFMPEG_PATH, '-i', filepath, '-f', 'null', '-']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        info = {'width': 0, 'height': 0, 'duration': 0, 'size': 0}
        
        size_match = re.search(r'(\d+)x(\d+)', result.stderr)
        if size_match:
            info['width'] = int(size_match.group(1))
            info['height'] = int(size_match.group(2))
        
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})', result.stderr)
        if duration_match:
            h, m, s = map(int, duration_match.groups())
            info['duration'] = h * 3600 + m * 60 + s
        
        info['size'] = os.path.getsize(filepath)
        return info
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {'width': 0, 'height': 0, 'duration': 0, 'size': 0}

def upscale_to_4k(input_path, output_path, method='lanczos'):
    """Upscale video to 4K"""
    try:
        if not check_ffmpeg():
            logger.error("FFmpeg not found")
            return False
        
        cmd = [
            FFMPEG_PATH,
            '-i', input_path,
            '-vf', f'scale=3840:2160:flags={method}',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        logger.info(f"Upscaling to 4K with method: {method}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return False
    except Exception as e:
        logger.error(f"Upscale error: {e}")
        return False

def download_file(url, output_path):
    """Download file with progress"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

def cleanup_old_files():
    """Cleanup old files"""
    retention_seconds = app.config['FILE_RETENTION_HOURS'] * 3600
    current_time = time.time()
    
    for folder in [app.config['DOWNLOAD_FOLDER'], app.config['TEMP_FOLDER']]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > retention_seconds:
                        try:
                            os.remove(filepath)
                            logger.info(f"Cleaned up: {filepath}")
                        except Exception as e:
                            logger.error(f"Cleanup error: {e}")

# ======================
# Routes
# ======================

@app.route('/')
def index():
    """Home page"""
    apis = get_available_apis()
    return render_template('index.html', apis=apis)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/history')
@login_required
def history_page():
    """History page"""
    return render_template('history.html')

@app.route('/settings')
@login_required
def settings_page():
    """Settings page"""
    return render_template('settings.html')

@app.route('/api/download-info', methods=['POST'])
def get_download_info():
    """Get video info without downloading"""
    try:
        data = request.get_json()
        url = data.get('url')
        api_id = data.get('api', 'tikwm')
        
        if not url or 'tiktok.com' not in url:
            return jsonify({'error': 'Invalid TikTok URL'}), 400
        
        video_data, error = download_tiktok(url, api_id)
        
        if error:
            return jsonify({'error': error}), 400
        
        if not video_data:
            return jsonify({'error': 'No video data found'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'title': video_data.get('title'),
                'author': video_data.get('author'),
                'duration': video_data.get('duration'),
                'quality': video_data.get('quality'),
                'thumbnail': video_data.get('thumbnail'),
                'video_url': video_data.get('video_url'),
                'music_url': video_data.get('music_url'),
                'id': video_data.get('id')
            }
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download and upscale video"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        music_url = data.get('music_url')
        title = data.get('title', 'tiktok_video')
        quality = data.get('quality', '4K')
        upscale_method = data.get('upscale_method', 'lanczos')
        api_used = data.get('api_used', 'tikwm')
        
        if not video_url:
            return jsonify({'error': 'No video URL provided'}), 400
        
        # Generate unique ID
        video_id = str(int(time.time())) + '_' + str(uuid.uuid4())[:8]
        safe_title = clean_filename(title) or 'tiktok'
        filename = f"{safe_title}_{video_id}.mp4"
        
        # Download video
        temp_video = os.path.join(app.config['TEMP_FOLDER'], f'video_{video_id}.mp4')
        logger.info(f"Downloading video: {video_url}")
        
        if not download_file(video_url, temp_video):
            return jsonify({'error': 'Failed to download video'}), 500
        
        # Download audio if available
        temp_audio = None
        if music_url:
            temp_audio = os.path.join(app.config['TEMP_FOLDER'], f'audio_{video_id}.mp3')
            if not download_file(music_url, temp_audio):
                logger.warning("Failed to download audio, continuing without")
                temp_audio = None
        
        # Merge if audio separate
        merged_video = temp_video
        if temp_audio and os.path.exists(temp_audio):
            merged_video = os.path.join(app.config['TEMP_FOLDER'], f'merged_{video_id}.mp4')
            cmd = [
                FFMPEG_PATH, '-y',
                '-i', temp_video,
                '-i', temp_audio,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                merged_video
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            
            # Cleanup temp files
            if os.path.exists(temp_video):
                os.remove(temp_video)
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
        
        # Upscale to 4K if requested
        final_file = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        if quality == '4K' and app.config['ENABLE_4K_UPSCALE']:
            logger.info(f"Upscaling to 4K with {upscale_method}")
            if upscale_to_4k(merged_video, final_file, upscale_method):
                # Remove merged file
                if os.path.exists(merged_video) and merged_video != temp_video:
                    os.remove(merged_video)
            else:
                # Fallback to original quality
                logger.warning("4K upscale failed, using original quality")
                shutil.copy(merged_video, final_file)
                quality = 'Original'
        else:
            # Use original quality
            shutil.copy(merged_video, final_file)
            if os.path.exists(merged_video) and merged_video != temp_video:
                os.remove(merged_video)
        
        # Save to history
        if current_user.is_authenticated:
            history = DownloadHistory(
                user_id=current_user.id,
                video_id=video_id,
                title=title,
                author=data.get('author', 'Unknown'),
                duration=0,
                original_quality=data.get('original_quality', '1080p'),
                output_quality=quality,
                api_used=api_used,
                upscale_method=upscale_method if quality == '4K' else None,
                file_size=os.path.getsize(final_file),
                file_path=final_file,
                filename=filename,
                status='completed'
            )
            db.session.add(history)
            current_user.total_downloads += 1
            current_user.total_size += os.path.getsize(final_file)
            db.session.commit()
        
        # Cleanup old files
        cleanup_old_files()
        
        return jsonify({
            'success': True,
            'message': 'Download completed successfully!',
            'file': {
                'name': filename,
                'size': os.path.getsize(final_file),
                'path': final_file,
                'quality': quality,
                'url': url_for('download_file', filename=filename, _external=True)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-download', methods=['POST'])
def batch_download():
    """Batch download multiple videos"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        quality = data.get('quality', '4K')
        upscale_method = data.get('upscale_method', 'lanczos')
        
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400
        
        if len(urls) > 10:
            return jsonify({'error': 'Maximum 10 videos per batch'}), 400
        
        results = []
        for url in urls:
            if 'tiktok.com' not in url:
                results.append({
                    'url': url,
                    'status': 'failed',
                    'error': 'Invalid TikTok URL'
                })
                continue
            
            try:
                # Get video info
                video_data, error = download_tiktok(url, 'tikwm')
                if error:
                    results.append({
                        'url': url,
                        'status': 'failed',
                        'error': error
                    })
                    continue
                
                # Download
                result = download_video_process(
                    video_data['video_url'],
                    video_data.get('music_url'),
                    video_data.get('title'),
                    quality,
                    upscale_method
                )
                
                results.append({
                    'url': url,
                    'status': 'success' if result else 'failed',
                    'data': result
                })
                
            except Exception as e:
                results.append({
                    'url': url,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'failed'])
        }), 200
        
    except Exception as e:
        logger.error(f"Batch download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
@login_required
def get_history():
    """Get download history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = DownloadHistory.query.filter_by(user_id=current_user.id)
        pagination = query.order_by(DownloadHistory.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'data': {
                'items': [{
                    'id': h.id,
                    'title': h.title,
                    'author': h.author,
                    'quality': h.output_quality,
                    'file_size': h.file_size,
                    'created_at': h.created_at.isoformat(),
                    'filename': h.filename
                } for h in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"History error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
@login_required
def get_stats():
    """Get user stats"""
    try:
        total_downloads = DownloadHistory.query.filter_by(
            user_id=current_user.id,
            status='completed'
        ).count()
        
        total_size = db.session.query(db.func.sum(DownloadHistory.file_size)).filter_by(
            user_id=current_user.id,
            status='completed'
        ).scalar() or 0
        
        # Download by quality
        quality_stats = db.session.query(
            DownloadHistory.output_quality,
            db.func.count(DownloadHistory.id)
        ).filter_by(
            user_id=current_user.id,
            status='completed'
        ).group_by(DownloadHistory.output_quality).all()
        
        # Recent downloads (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent = DownloadHistory.query.filter_by(
            user_id=current_user.id,
            status='completed'
        ).filter(
            DownloadHistory.created_at >= week_ago
        ).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total_downloads': total_downloads,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'recent_downloads': recent,
                'quality_stats': {q: c for q, c in quality_stats},
                'last_download': DownloadHistory.query.filter_by(
                    user_id=current_user.id,
                    status='completed'
                ).order_by(DownloadHistory.created_at.desc()).first().created_at.isoformat() if total_downloads > 0 else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'PUT'])
@login_required
def user_settings():
    """Get or update user settings"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'data': current_user.settings
        }), 200
    
    try:
        data = request.get_json()
        current_user.settings.update(data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'data': current_user.settings
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download file by filename"""
    filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='video/mp4'
    )

@app.route('/api/delete-history/<int:history_id>', methods=['DELETE'])
@login_required
def delete_history(history_id):
    """Delete download history"""
    try:
        history = DownloadHistory.query.filter_by(
            id=history_id,
            user_id=current_user.id
        ).first()
        
        if not history:
            return jsonify({'error': 'History not found'}), 404
        
        # Delete file if exists
        if history.file_path and os.path.exists(history.file_path):
            os.remove(history.file_path)
        
        db.session.delete(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'History deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['DELETE'])
@login_required
def clear_history():
    """Clear all download history"""
    try:
        histories = DownloadHistory.query.filter_by(user_id=current_user.id).all()
        
        for history in histories:
            if history.file_path and os.path.exists(history.file_path):
                os.remove(history.file_path)
        
        DownloadHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All history cleared successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ======================
# Run App
# ======================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=app.config['DEBUG']
    )
