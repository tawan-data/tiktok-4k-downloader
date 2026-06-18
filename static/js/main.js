// ============================================
// TikTok 4K Downloader - Main JavaScript
// ============================================

class TikTokDownloader {
    constructor() {
        this.api = 'tikwm';
        this.quality = '4K';
        this.upscaleMethod = 'lanczos';
        this.isDownloading = false;
        
        this.init();
    }
    
    init() {
        // Bind events
        document.getElementById('downloadBtn')?.addEventListener('click', () => this.handleDownload());
        document.getElementById('tiktokUrl')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleDownload();
        });
        
        // Quality selector
        document.querySelectorAll('.quality-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.quality = btn.dataset.quality;
                this.upscaleMethod = btn.dataset.method || 'lanczos';
            });
        });
        
        // API selector
        document.querySelectorAll('.api-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.api-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.api = btn.dataset.api;
            });
        });
        
        // Dark mode toggle
        document.getElementById('darkModeToggle')?.addEventListener('change', (e) => {
            this.toggleDarkMode(e.target.checked);
        });
        
        // Load saved settings
        this.loadSettings();
    }
    
    async handleDownload() {
        if (this.isDownloading) return;
        
        const urlInput = document.getElementById('tiktokUrl');
        const url = urlInput.value.trim();
        
        if (!url) {
            this.showToast('กรุณาใส่ลิงก์ TikTok', 'warning');
            return;
        }
        
        if (!this.isTikTokUrl(url)) {
            this.showToast('ลิงก์ไม่ถูกต้อง กรุณาใส่ลิงก์ TikTok', 'error');
            return;
        }
        
        this.isDownloading = true;
        const btn = document.getElementById('downloadBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> กำลังดาวน์โหลด...';
        
        try {
            // 1. Get video info
            const info = await this.getVideoInfo(url);
            if (!info.success) {
                throw new Error(info.error || 'Failed to get video info');
            }
            
            // 2. Show preview
            this.showPreview(info.data);
            
            // 3. Download
            const result = await this.downloadVideo(info.data);
            
            if (result.success) {
                this.showToast('ดาวน์โหลดสำเร็จ! 🎉', 'success');
                this.showDownloadButton(result.file);
            } else {
                throw new Error(result.error || 'Download failed');
            }
            
        } catch (error) {
            this.showToast(error.message, 'error');
        } finally {
            this.isDownloading = false;
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-download"></i> ดาวน์โหลด';
        }
    }
    
    async getVideoInfo(url) {
        try {
            const response = await fetch('/api/download-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    api: this.api
                })
            });
            
            return await response.json();
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    async downloadVideo(videoData) {
        try {
            // Show progress
            this.showProgress('กำลังดาวน์โหลด...');
            
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_url: videoData.video_url,
                    music_url: videoData.music_url || null,
                    title: videoData.title,
                    quality: this.quality,
                    upscale_method: this.upscaleMethod,
                    api_used: this.api,
                    author: videoData.author,
                    original_quality: videoData.quality
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.hideProgress();
                return result;
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            this.hideProgress();
            return { success: false, error: error.message };
        }
    }
    
    showPreview(data) {
        const preview = document.getElementById('videoPreview');
        preview.classList.add('show');
        
        document.getElementById('previewThumbnail').src = data.thumbnail || '/static/images/default-thumb.jpg';
        document.getElementById('previewTitle').textContent = data.title || 'No title';
        document.getElementById('previewAuthor').textContent = `👤 ${data.author || 'Unknown'}`;
        document.getElementById('previewDuration').textContent = `⏱️ ${this.formatDuration(data.duration)}`;
        document.getElementById('previewQuality').textContent = `📊 ${data.quality || 'Unknown'}`;
    }
    
    showProgress(text) {
        const container = document.getElementById('progressContainer');
        container.classList.add('show');
        document.getElementById('progressText').textContent = text;
        this.animateProgress();
    }
    
    hideProgress() {
        const container = document.getElementById('progressContainer');
        container.classList.remove('show');
        document.getElementById('progressFill').style.width = '0%';
    }
    
    animateProgress() {
        const fill = document.getElementById('progressFill');
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 5;
            if (progress > 90) {
                clearInterval(interval);
                fill.style.width = '90%';
                return;
            }
            fill.style.width = progress + '%';
        }, 500);
    }
    
    showDownloadButton(file) {
        const container = document.getElementById('downloadResult');
        container.innerHTML = `
            <div class="alert alert-success mt-3">
                <i class="fas fa-check-circle"></i> ดาวน์โหลดสำเร็จ!
                <a href="${file.url}" class="btn btn-success ms-3" download>
                    <i class="fas fa-file-download"></i> ดาวน์โหลดไฟล์ (${this.formatFileSize(file.size)})
                </a>
                <button class="btn btn-outline-secondary ms-2" onclick="window.location.reload()">
                    <i class="fas fa-redo"></i> ใหม่
                </button>
            </div>
        `;
    }
    
    showToast(message, type = 'info') {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast-custom toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
                <span class="toast-message">${message}</span>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    isTikTokUrl(url) {
        const patterns = [
            /tiktok\.com\/@[\w]+\/video\/\d+/,
            /tiktok\.com\/@[\w]+\?lang=/,
            /vm\.tiktok\.com\/[\w]+/,
            /tiktok\.com\/@[\w]+/
        ];
        return patterns.some(p => p.test(url));
    }
    
    formatDuration(seconds) {
        if (!seconds) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unit = 0;
        while (size >= 1024 && unit < units.length - 1) {
            size /= 1024;
            unit++;
        }
        return `${size.toFixed(1)} ${units[unit]}`;
    }
    
    toggleDarkMode(enabled) {
        document.body.classList.toggle('dark-mode', enabled);
        document.body.classList.toggle('light-mode', !enabled);
        document.documentElement.setAttribute('data-bs-theme', enabled ? 'dark' : 'light');
        
        // Save setting
        this.saveSettings({ dark_mode: enabled });
    }
    
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    const settings = data.data;
                    
                    // Dark mode
                    if (settings.dark_mode !== undefined) {
                        document.getElementById('darkModeToggle').checked = settings.dark_mode;
                        this.toggleDarkMode(settings.dark_mode);
                    }
                    
                    // Quality
                    if (settings.default_quality) {
                        document.querySelectorAll('.quality-btn').forEach(btn => {
                            if (btn.dataset.quality === settings.default_quality) {
                                btn.click();
                            }
                        });
                    }
                    
                    // API
                    if (settings.default_api) {
                        document.querySelectorAll('.api-btn').forEach(btn => {
                            if (btn.dataset.api === settings.default_api) {
                                btn.click();
                            }
                        });
                    }
                }
            }
        } catch (error) {
            console.log('Failed to load settings:', error);
        }
    }
    
    async saveSettings(settings) {
        try {
            await fetch('/api/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });
        } catch (error) {
            console.log('Failed to save settings:', error);
        }
    }
}

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', () => {
    window.downloader = new TikTokDownloader();
});

// ===== Toast CSS (injected) =====
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    .toast-custom {
        position: fixed;
        bottom: 30px;
        right: 30px;
        padding: 16px 24px;
        border-radius: 12px;
        background: #1a1a1a;
        color: white;
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        max-width: 500px;
        transform: translateY(100px);
        opacity: 0;
        transition: all 0.3s ease;
        z-index: 9999;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .toast-custom.show {
        transform: translateY(0);
        opacity: 1;
    }
    
    .toast-custom .toast-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .toast-custom .toast-icon {
        font-size: 1.5rem;
    }
    
    .toast-custom .toast-close {
        background: none;
        border: none;
        color: rgba(255,255,255,0.5);
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0 4px;
    }
    
    .toast-custom .toast-close:hover {
        color: white;
    }
    
    .toast-success .toast-icon { color: #00e676; }
    .toast-error .toast-icon { color: #ff1744; }
    .toast-warning .toast-icon { color: #ffea00; }
    .toast-info .toast-icon { color: #00b0ff; }
`;
document.head.appendChild(toastStyles);
