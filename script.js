/**
 * Common JavaScript functions for Armenian Plagiarism Detection System
 */

const API_URL = 'http://127.0.0.1:5000/api';

// ==================================================
// UTILITY FUNCTIONS
// ==================================================

/**
 * Format file size to human readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get file icon class based on extension
 */
function getFileIconClass(ext) {
    const classes = { 
        pdf: 'pdf', 
        doc: 'doc', 
        docx: 'docx', 
        txt: 'txt', 
        rtf: 'rtf' 
    };
    return classes[ext] || '';
}

/**
 * Get file icon based on extension
 */
function getFileIcon(ext) {
    const icons = { 
        pdf: 'fa-file-pdf', 
        doc: 'fa-file-word', 
        docx: 'fa-file-word', 
        txt: 'fa-file-alt', 
        rtf: 'fa-file' 
    };
    return icons[ext] || 'fa-file';
}

/**
 * Get similarity level from score
 */
function getSimilarityLevel(score) {
    if (score >= 80) return 'CRITICAL';
    if (score >= 60) return 'HIGH';
    if (score >= 40) return 'MODERATE';
    if (score >= 20) return 'LOW';
    return 'CLEAN';
}

/**
 * Get color for similarity level
 */
function getLevelColor(level) {
    switch(level) {
        case 'CRITICAL': return '#f72585';
        case 'HIGH': return '#f8961e';
        case 'MODERATE': return '#f9c74f';
        case 'LOW': return '#4cc9f0';
        default: return '#95a5a6';
    }
}

/**
 * Show notification message
 */
function showMessage(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#f72585' : type === 'success' ? '#4cc9f0' : '#4361ee'};
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
    `;
    
    const icon = type === 'error' ? 'fa-exclamation-circle' : 
                 type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
    
    toast.innerHTML = `<i class="fas ${icon}"></i> ${message}`;
    document.body.appendChild(toast);
    
    // Add styles if not already present
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================================================
// FILE UPLOAD HANDLERS
// ==================================================

/**
 * Handle file selection
 */
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    processFiles(files);
}

/**
 * Process uploaded files
 */
function processFiles(files) {
    const validFiles = files.filter(file => {
        const ext = file.name.toLowerCase().split('.').pop();
        return ['txt', 'pdf', 'doc', 'docx', 'rtf'].includes(ext);
    });
    
    if (validFiles.length === 0) {
        showMessage('Please upload only .txt, .pdf, .doc, .docx, or .rtf files', 'error');
        return [];
    }
    
    return validFiles;
}

/**
 * Prevent default drag/drop events
 */
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// ==================================================
// NOTIFICATION FUNCTIONS
// ==================================================

/**
 * Load notifications for current user
 */
async function loadNotifications() {
    try {
        const response = await fetch(`${API_URL}/notifications`, {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.success) {
            updateNotificationBadge(data.unread_count);
            return data.notifications;
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
    return [];
}

/**
 * Update notification badge
 */
function updateNotificationBadge(count) {
    const badges = document.querySelectorAll('.notification-badge');
    badges.forEach(badge => {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'block' : 'none';
    });
}

/**
 * Mark notification as read
 */
async function markNotificationRead(id) {
    try {
        await fetch(`${API_URL}/notifications/${id}/read`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Error marking notification read:', error);
    }
}

/**
 * Mark all notifications as read
 */
async function markAllNotificationsRead() {
    try {
        await fetch(`${API_URL}/notifications/read-all`, {
            method: 'POST',
            credentials: 'include'
        });
        updateNotificationBadge(0);
    } catch (error) {
        console.error('Error marking all notifications read:', error);
    }
}

// ==================================================
// DATE FORMATTING
// ==================================================

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) return 'just now';
    if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
    if (diffHour < 24) return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
    if (diffDay < 7) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
}

/**
 * Format date to standard format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==================================================
// PLAGIARISM HIGHLIGHTING
// ==================================================

/**
 * Generate HTML for plagiarism highlighting
 */
function generateHighlightHTML(sentences, fileName) {
    let html = `<div class="file-column">
        <div class="file-header">
            <i class="fas fa-file-alt"></i>
            <span>${escapeHtml(fileName)}</span>
        </div>
        <div class="sentences-container">`;
    
    sentences.forEach(sent => {
        const levelClass = sent.plagiarized ? ` plagiarism-${sent.class}` : '';
        const similarityTag = sent.plagiarized ? 
            `<span class="similarity-tag ${sent.class}">${sent.similarity}% match</span>` : '';
        
        html += `
            <div class="sentence-item${levelClass}">
                ${similarityTag}
                <div class="sentence-text">${escapeHtml(sent.text)}</div>
            </div>
        `;
    });
    
    html += '</div></div>';
    return html;
}

// ==================================================
// EXPORT FUNCTIONS
// ==================================================

/**
 * Export data as CSV
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    downloadFile(csv, filename, 'text/csv');
}

/**
 * Convert array to CSV
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    
    // Add headers
    csvRows.push(headers.join(','));
    
    // Add data rows
    for (const row of data) {
        const values = headers.map(header => {
            const val = row[header] || '';
            return `"${String(val).replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

/**
 * Download file
 */
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Export functions to global scope
window.showMessage = showMessage;
window.formatFileSize = formatFileSize;
window.escapeHtml = escapeHtml;
window.getFileIconClass = getFileIconClass;
window.getFileIcon = getFileIcon;
window.getSimilarityLevel = getSimilarityLevel;
window.getLevelColor = getLevelColor;
window.formatRelativeTime = formatRelativeTime;
window.formatDate = formatDate;
window.exportToCSV = exportToCSV;