// API Configuration
const API_URL = '/api';
let currentUser = null;
let uploadedFiles = [];
let plagiarismChart = null;
let aiChart = null;
let allFeedback = [];

// Initialize translations
document.addEventListener('DOMContentLoaded', function() {
    Translations.updatePageLanguage();
    
    // Listen for language changes
    document.addEventListener('languageChanged', function(e) {
        // Update dynamic content if needed
        updateDynamicContent();
    });
});

// Update dynamic content when language changes
function updateDynamicContent() {
    // Reload data that contains translated text
    if (document.getElementById('section-dashboard').classList.contains('active')) {
        loadRecentResults();
    }
    if (document.getElementById('section-results').classList.contains('active')) {
        loadResults();
    }
    if (document.getElementById('section-submissions').classList.contains('active')) {
        loadSubmissions();
    }
    if (document.getElementById('section-questions').classList.contains('active')) {
        loadQuestions();
    }
    if (document.getElementById('section-feedback').classList.contains('active')) {
        loadFeedback();
    }
    if (document.getElementById('section-ai-results').classList.contains('active')) {
        loadAIResults();
    }
}

// ==================================================
// MODAL FUNCTIONS
// ==================================================
function showModal(title, message, type = 'info') {
    document.getElementById('infoModalTitle').textContent = title;
    document.getElementById('infoModalMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('infoModal')).show();
}

function showConfirm(title, message, onConfirm) {
    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModalMessage').textContent = message;
    window.confirmCallback = onConfirm;
    new bootstrap.Modal(document.getElementById('confirmModal')).show();
}

function confirmAction() {
    if (window.confirmCallback) window.confirmCallback();
    bootstrap.Modal.getInstance(document.getElementById('confirmModal')).hide();
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}" style="color: ${type === 'success' ? 'var(--success)' : 'var(--danger)'};"></i><span>${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================================================
// SECTION NAVIGATION
// ==================================================
function showSection(sectionId) {
    document.querySelectorAll('.sidebar-menu-link').forEach(link => link.classList.remove('active'));
    const activeLink = Array.from(document.querySelectorAll('.sidebar-menu-link')).find(link => link.getAttribute('onclick')?.includes(`'${sectionId}'`));
    if (activeLink) activeLink.classList.add('active');
    
    document.querySelectorAll('.content-section').forEach(section => section.classList.remove('active'));
    document.getElementById(`section-${sectionId}`).classList.add('active');
    
    const titles = {
        'dashboard': Translations.t('nav_dashboard'),
        'upload': Translations.t('nav_upload'),
        'results': Translations.t('nav_results'),
        'submissions': Translations.t('nav_submissions'),
        'questions': Translations.t('nav_questions'),
        'feedback': Translations.t('nav_feedback'),
        'ai-results': Translations.t('nav_ai')
    };
    document.getElementById('pageTitle').textContent = titles[sectionId];
    
    if (sectionId === 'results') loadResults();
    if (sectionId === 'submissions') loadSubmissions();
    if (sectionId === 'questions') loadQuestions();
    if (sectionId === 'feedback') loadFeedback();
    if (sectionId === 'ai-results') loadAIResults();
    
    if (window.innerWidth <= 768) document.getElementById('sidebar').classList.remove('show');
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('show');
}

// ==================================================
// AUTHENTICATION
// ==================================================
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    setupEventListeners();
});

function checkAuthStatus() {
    fetch(`${API_URL}/current-user`, { credentials: 'include' })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.user) {
                currentUser = data.user;
                if (currentUser.role !== 'student') {
                    window.location.href = '/index.html';
                    return;
                }
                updateUserInfo();
                loadDashboardData();
                startNotificationPolling();
            } else {
                window.location.href = '/index.html';
            }
        })
        .catch(() => window.location.href = '/index.html');
}

function updateUserInfo() {
    document.getElementById('userName').textContent = currentUser.full_name || currentUser.username;
    document.getElementById('userAvatar').textContent = (currentUser.full_name || currentUser.username).charAt(0).toUpperCase();
}

// ==================================================
// GLOBAL AI AVERAGE (single source of truth)
// ==================================================
async function updateGlobalAIAverage() {
    try {
        const response = await fetch(`${API_URL}/history?page=0`, { credentials: 'include' });
        const data = await response.json();
        if (!data.success || !data.history || data.history.length === 0) {
            document.getElementById('aiAverageScore').textContent = '0%';
            if (document.getElementById('aiTotalFiles')) document.getElementById('aiTotalFiles').textContent = '0';
            if (document.getElementById('aiHumanCount')) document.getElementById('aiHumanCount').textContent = '0';
            return;
        }
        let totalFiles = 0, totalAI = 0, humanCount = 0;
        for (const session of data.history) {
            const sessionRes = await fetch(`${API_URL}/history/${session.id}`, { credentials: 'include' });
            const sessionData = await sessionRes.json();
            if (sessionData.success && sessionData.files) {
                sessionData.files.forEach(file => {
                    const aiScore = file.ai_score || 0;
                    totalFiles++;
                    totalAI += aiScore;
                    if (aiScore < 50) humanCount++;
                });
            }
        }
        const avgAI = totalFiles > 0 ? Math.round(totalAI / totalFiles) : 0;
        document.getElementById('aiAverageScore').textContent = avgAI + '%';
        if (document.getElementById('aiTotalFiles')) document.getElementById('aiTotalFiles').textContent = totalFiles;
        if (document.getElementById('aiHumanCount')) document.getElementById('aiHumanCount').textContent = humanCount;
    } catch (error) {
        console.error('Error updating global AI average:', error);
        document.getElementById('aiAverageScore').textContent = '0%';
    }
}

// ==================================================
// DASHBOARD DATA
// ==================================================
function loadDashboardData() {
    loadSubmissionsCount();
    loadQuestionsCount();
    loadFeedbackCount();
    loadRecentResults();
    updateGlobalAIAverage();
    initCharts();
}

function refreshData() {
    loadDashboardData();
    showToast('Data refreshed', 'success');
}

async function loadSubmissionsCount() {
    try {
        const res = await fetch(`${API_URL}/submissions`, { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            document.getElementById('totalSubmissions').textContent = data.submissions?.length || 0;
            document.getElementById('sidebarSubmissionsCount').textContent = data.submissions?.length || 0;
        }
    } catch (error) { console.error(error); }
}

async function loadQuestionsCount() {
    try {
        const res = await fetch(`${API_URL}/questions`, { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            const pending = data.questions?.filter(q => q.status === 'pending').length || 0;
            document.getElementById('pendingQuestions').textContent = pending;
            document.getElementById('sidebarQuestionsCount').textContent = pending > 0 ? pending : '';
            document.getElementById('sidebarQuestionsCount').classList.toggle('show', pending > 0);
        }
    } catch (error) { console.error(error); }
}

async function loadFeedbackCount() {
    try {
        const res = await fetch(`${API_URL}/feedback/enhanced`, { credentials: 'include' });
        const data = await res.json();
        if (data.success) {
            const pending = data.feedback?.filter(f => f.status === 'pending').length || 0;
            document.getElementById('sidebarFeedbackCount').textContent = pending > 0 ? pending : '';
            document.getElementById('sidebarFeedbackCount').classList.toggle('show', pending > 0);
        }
    } catch (error) { console.error(error); }
}

async function loadRecentResults() {
    try {
        const response = await fetch(`${API_URL}/history?page=0`, { credentials: 'include' });
        const data = await response.json();
        if (!data.success || !data.history) return;
        
        const recent = data.history.slice(0, 5);
        document.getElementById('totalChecks').textContent = data.history.length;
        
        if (recent.length === 0) {
            document.getElementById('recentResults').innerHTML = '<tr><td colspan="5" style="text-align: center;">' + Translations.t('no_recent_results') + '</td></tr>';
            return;
        }
        
        let html = '';
        for (const session of recent) {
            const sessionRes = await fetch(`${API_URL}/history/${session.id}`, { credentials: 'include' });
            const sessionData = await sessionRes.json();
            if (sessionData.success && sessionData.results) {
                sessionData.results.forEach(result => {
                    html += `
                        <tr onclick="viewResultDetails(${session.id}, '${result.file1}', '${result.file2}')">
                            <td>${new Date(session.upload_time).toLocaleString()}</td>
                            <td>${result.file1}<br><small>vs</small><br>${result.file2}</td>
                            <td>
                                <strong>${result.similarity}%</strong>
                                <div class="similarity-meter">
                                    <div class="similarity-fill ${getSimilarityClass(result.similarity)}" style="width: ${result.similarity}%;"></div>
                                </div>
                            </td>
                            <td>
                                ${sessionData.files?.find(f => f.filename === result.file1)?.ai_score || 0}% / 
                                ${sessionData.files?.find(f => f.filename === result.file2)?.ai_score || 0}%
                            </td>
                            <td>
                                <button class="btn-modern btn-primary-modern btn-sm" onclick="event.stopPropagation(); viewResultDetails(${session.id}, '${result.file1}', '${result.file2}')">
                                    <i class="fas fa-eye"></i> View
                                </button>
                            </td>
                        </tr>
                    `;
                });
            }
        }
        document.getElementById('recentResults').innerHTML = html;
    } catch (error) {
        console.error(error);
        document.getElementById('recentResults').innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger);">' + Translations.t('error_loading_results') + '</td></tr>';
    }
}

function getSimilarityClass(percent) {
    if (percent > 70) return 'critical';
    if (percent > 50) return 'high';
    if (percent > 30) return 'moderate';
    return 'low';
}

function initCharts() {
    const ctx1 = document.getElementById('plagiarismChart')?.getContext('2d');
    if (ctx1) {
        if (plagiarismChart) plagiarismChart.destroy();
        plagiarismChart = new Chart(ctx1, {
            type: 'line',
            data: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'], datasets: [{ label: 'My Plagiarism Score', data: [65, 59, 80, 81, 56, 55], borderColor: '#4361ee', backgroundColor: 'rgba(67,97,238,0.1)', tension: 0.4, fill: true }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        });
    }
    const ctx2 = document.getElementById('aiChart')?.getContext('2d');
    if (ctx2) {
        if (aiChart) aiChart.destroy();
        aiChart = new Chart(ctx2, {
            type: 'doughnut',
            data: { labels: ['Human Written', 'AI Generated'], datasets: [{ data: [65, 35], backgroundColor: ['#4cc9f0', '#f72585'], borderWidth: 0 }] },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } }, cutout: '70%' }
        });
    }
}

// ==================================================
// UPLOAD FUNCTIONS
// ==================================================
function setupEventListeners() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    if (uploadArea) {
        uploadArea.addEventListener('click', e => { if (e.target.tagName !== 'BUTTON') fileInput.click(); });
        uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.style.borderColor = '#4361ee'; uploadArea.style.background = '#f0f4ff'; });
        uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '#e2e8f0'; uploadArea.style.background = ''; });
        uploadArea.addEventListener('drop', e => { e.preventDefault(); uploadArea.style.borderColor = '#e2e8f0'; uploadArea.style.background = ''; handleFiles(Array.from(e.dataTransfer.files)); });
    }
    if (fileInput) fileInput.addEventListener('change', e => { handleFiles(Array.from(e.target.files)); e.target.value = ''; });
    document.addEventListener('click', e => {
        const dropdown = document.getElementById('notificationsDropdown');
        const bell = document.querySelector('.notification-bell');
        if (dropdown && bell && !bell.contains(e.target) && !dropdown.contains(e.target)) dropdown.classList.remove('show');
    });
    if (window.innerWidth <= 768) document.getElementById('menuToggle').style.display = 'block';
}

function handleFiles(files) {
    const allowed = ['txt', 'pdf', 'doc', 'docx', 'rtf'];
    files.forEach(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!allowed.includes(ext)) return showToast(`${file.name} (unsupported)`, 'error');
        if (file.size > 100*1024*1024) return showToast(`${file.name} (too large)`, 'error');
        if (!uploadedFiles.some(f => f.name === file.name)) uploadedFiles.push(file);
    });
    updateFileList();
    document.getElementById('checkPlagiarismBtn').disabled = uploadedFiles.length < 2;
}

function updateFileList() {
    const container = document.getElementById('fileList');
    if (uploadedFiles.length === 0) { container.innerHTML = ''; return; }
    let html = '<h5>Selected Files:</h5>';
    uploadedFiles.forEach((file, i) => {
        html += `<div class="file-item"><span><i class="fas fa-file"></i> ${escapeHtml(file.name)} (${(file.size/1024).toFixed(1)} KB)</span><span class="file-remove" onclick="removeFile(${i})" style="color: var(--danger); cursor: pointer;"><i class="fas fa-times"></i></span></div>`;
    });
    container.innerHTML = html;
}

function removeFile(index) { uploadedFiles.splice(index, 1); updateFileList(); document.getElementById('checkPlagiarismBtn').disabled = uploadedFiles.length < 2; }
function clearAll() { if (uploadedFiles.length && confirm('Clear all files?')) { uploadedFiles = []; updateFileList(); document.getElementById('checkPlagiarismBtn').disabled = true; showToast('All files cleared', 'success'); } }

function showProgress(percent) {
    const progress = document.getElementById('uploadProgress');
    const bar = document.getElementById('uploadProgressBar');
    const text = document.getElementById('progressText');
    progress.style.display = 'block';
    bar.style.width = percent + '%';
    bar.textContent = percent + '%';
    text.textContent = percent < 100 ? `Uploading... ${Math.round(percent)}%` : 'Processing...';
}

async function checkPlagiarism() {
    if (uploadedFiles.length < 2) return showModal('Error', 'Please upload at least 2 files', 'error');
    const formData = new FormData();
    uploadedFiles.forEach(f => formData.append('files', f));
    showModal('Processing', 'Starting plagiarism check...', 'info');
    document.getElementById('uploadProgress').style.display = 'block';
    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener('progress', e => { if (e.lengthComputable) showProgress((e.loaded/e.total)*100); });
    xhr.addEventListener('load', async function() {
        document.getElementById('uploadProgress').style.display = 'none';
        try {
            const data = JSON.parse(xhr.response);
            if (data.success) {
                showToast('Plagiarism check complete', 'success');
                await fetch(`${API_URL}/submissions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: data.session_id, title: 'Assignment Submission', description: 'Submitted multiple files' }),
                    credentials: 'include'
                }).catch(console.error);
                await updateGlobalAIAverage();
                await loadDashboardData();
                showSection('results');
                loadResults();
            } else {
                showModal('Error', data.error || 'Check failed', 'error');
            }
        } catch(e) { showModal('Error', 'Invalid response', 'error'); }
    });
    xhr.addEventListener('error', () => { document.getElementById('uploadProgress').style.display = 'none'; showModal('Error', 'Network error', 'error'); });
    xhr.open('POST', `${API_URL}/armenian-check`);
    xhr.withCredentials = true;
    xhr.send(formData);
}

// ==================================================
// RESULTS SECTION
// ==================================================
async function loadResults() {
    const container = document.getElementById('resultsList');
    container.innerHTML = '<div style="text-align: center; padding: 3rem;"><div class="loading-spinner"></div><p>' + Translations.t('loading_results') + '</p></div>';
    try {
        const response = await fetch(`${API_URL}/history?page=0`, { credentials: 'include' });
        const data = await response.json();
        if (!data.success || !data.history || data.history.length === 0) {
            container.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-chart-line fa-4x text-muted"></i><h3 class="mt-3">' + Translations.t('no_results_found') + '</h3><p class="text-muted">' + Translations.t('upload_files_message') + '</p></div>';
            return;
        }
        let html = '';
        for (const session of data.history) {
            const sessionRes = await fetch(`${API_URL}/history/${session.id}`, { credentials: 'include' });
            const sessionData = await sessionRes.json();
            if (sessionData.success && sessionData.results) {
                sessionData.results.forEach(result => {
                    const file1AI = sessionData.files?.find(f => f.filename === result.file1)?.ai_score || 0;
                    const file2AI = sessionData.files?.find(f => f.filename === result.file2)?.ai_score || 0;
                    html += `
                        <div class="result-card" onclick="viewResultDetails(${session.id}, '${result.file1}', '${result.file2}')">
                            <div class="result-header"><h5><i class="fas fa-file-alt" style="color: var(--primary);"></i> Comparison</h5><span class="similarity-badge ${result.plagiarism_level}">${result.plagiarism_level}</span></div>
                            <div class="result-files"><div class="result-file"><i class="fas fa-file"></i> ${escapeHtml(result.file1)}<div class="ai-score-small mt-2"><i class="fas fa-robot"></i> AI: ${file1AI}%</div></div><div class="result-file"><i class="fas fa-file"></i> ${escapeHtml(result.file2)}<div class="ai-score-small mt-2"><i class="fas fa-robot"></i> AI: ${file2AI}%</div></div></div>
                            <div style="text-align: center; margin: 1rem 0;"><div class="similarity-large" style="color: ${getSimilarityColor(result.similarity)};">${result.similarity}%</div><p class="text-muted">Similarity Score</p></div>
                            <div style="display: flex; justify-content: space-between; align-items: center;"><small class="text-muted">${new Date(session.upload_time).toLocaleString()}</small><button class="btn-modern btn-primary-modern btn-sm" onclick="event.stopPropagation(); viewResultDetails(${session.id}, '${result.file1}', '${result.file2}')"><i class="fas fa-eye"></i> View Details</button></div>
                        </div>
                    `;
                });
            }
        }
        container.innerHTML = html;
    } catch (error) {
        console.error(error);
        container.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--danger);">' + Translations.t('failed_load_results') + '</div>';
    }
}

function getSimilarityColor(percent) {
    if (percent > 70) return '#f72585';
    if (percent > 50) return '#f8961e';
    if (percent > 30) return '#ffd166';
    return '#4cc9f0';
}

function viewResultDetails(sessionId, file1, file2) {
    fetch(`${API_URL}/history/${sessionId}`, { credentials: 'include' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const result = data.results?.find(r => r.file1 === file1 && r.file2 === file2);
                const file1AI = data.files?.find(f => f.filename === file1)?.ai_score || 0;
                const file2AI = data.files?.find(f => f.filename === file2)?.ai_score || 0;
                let html = `
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <h2 style="font-size: 4rem; color: ${getSimilarityColor(result?.similarity || 0)};">${result?.similarity || 0}%</h2>
                        <p class="text-muted">Overall Similarity</p>
                        <span class="similarity-badge ${result?.plagiarism_level}" style="font-size: 1rem;">${result?.plagiarism_level || 'Unknown'}</span>
                    </div>
                    <div class="row">
                        <div class="col-md-6"><div class="card"><div class="card-header bg-primary text-white"><i class="fas fa-file"></i> ${escapeHtml(file1)}</div><div class="card-body"><p><strong>AI Score:</strong> ${file1AI}%</p><p><strong>Words:</strong> ${data.files?.find(f => f.filename === file1)?.word_count || 0}</p><div class="progress"><div class="progress-bar ${file1AI > 50 ? 'bg-danger' : 'bg-success'}" style="width: ${file1AI}%">${file1AI}% AI</div></div></div></div></div>
                        <div class="col-md-6"><div class="card"><div class="card-header bg-primary text-white"><i class="fas fa-file"></i> ${escapeHtml(file2)}</div><div class="card-body"><p><strong>AI Score:</strong> ${file2AI}%</p><p><strong>Words:</strong> ${data.files?.find(f => f.filename === file2)?.word_count || 0}</p><div class="progress"><div class="progress-bar ${file2AI > 50 ? 'bg-danger' : 'bg-success'}" style="width: ${file2AI}%">${file2AI}% AI</div></div></div></div></div>
                    </div>
                    <div class="alert alert-info mt-3"><i class="fas fa-info-circle"></i> For detailed text highlighting, please consult your lecturer.</div>
                `;
                document.getElementById('resultModalBody').innerHTML = html;
                new bootstrap.Modal(document.getElementById('resultModal')).show();
            }
        });
}

function filterResults() {
    const search = document.getElementById('resultsSearch').value.toLowerCase();
    document.querySelectorAll('.result-card').forEach(card => {
        card.style.display = card.textContent.toLowerCase().includes(search) ? 'block' : 'none';
    });
}

// ==================================================
// SUBMISSIONS SECTION
// ==================================================
async function loadSubmissions() {
    try {
        const response = await fetch(`${API_URL}/submissions`, { credentials: 'include' });
        const data = await response.json();
        if (data.success && data.submissions && data.submissions.length > 0) {
            let html = '';
            data.submissions.forEach(sub => {
                html += `
                    <tr onclick="viewSubmission(${sub.session_id})">
                        <td>${new Date(sub.submitted_at).toLocaleString()}</td>
                        <td>${escapeHtml(sub.title || 'Assignment')}</td>
                        <td>2 files</td>
                        <td><span class="status-badge status-answered">Processed</span></td>
                        <td><button class="btn-modern btn-primary-modern btn-sm" onclick="event.stopPropagation(); viewSubmission(${sub.session_id})"><i class="fas fa-eye"></i> View</button></td>
                    </tr>
                `;
            });
            document.getElementById('submissionsList').innerHTML = html;
        } else {
            document.getElementById('submissionsList').innerHTML = '<tr><td colspan="5" style="text-align: center;">' + Translations.t('no_submissions_student') + '</td></tr>';
        }
    } catch (error) {
        console.error('Error loading submissions:', error);
        document.getElementById('submissionsList').innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger);">' + Translations.t('error_loading_submissions') + '</td></tr>';
    }
}
function viewSubmission(sessionId) { showSection('results'); }

// ==================================================
// QUESTIONS SECTION
// ==================================================
async function loadQuestions() {
    try {
        const response = await fetch(`${API_URL}/questions`, { credentials: 'include' });
        const data = await response.json();
        if (data.success && data.questions && data.questions.length > 0) {
            let html = '';
            data.questions.forEach(q => {
                html += `
                    <tr>
                        <td>${escapeHtml(q.title)}</td>
                        <td>${new Date(q.created_at).toLocaleString()}</td>
                        <td><span class="status-badge status-${q.status}">${q.status}</span></td>
                        <td>
                            ${q.status === 'answered' ? 
                                `<button class="btn-modern btn-outline-modern btn-sm" onclick="viewAnswer('${escapeHtml(q.question)}', '${escapeHtml(q.answer)}')">
                                    <i class="fas fa-eye"></i> View Answer
                                </button>` : 
                                '<span class="text-muted">Awaiting answer</span>'}
                         </td>
                     </tr>
                `;
            });
            document.getElementById('questionsList').innerHTML = html;
        } else {
            document.getElementById('questionsList').innerHTML = '<tr><td colspan="4" style="text-align: center;">' + Translations.t('no_questions_student') + '</td></tr>';
        }
    } catch (error) {
        console.error('Error loading questions:', error);
        document.getElementById('questionsList').innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--danger);">' + Translations.t('error_loading_questions') + '</td></tr>';
    }
}
function openQuestionModal() {
    document.getElementById('questionTitle').value = '';
    document.getElementById('questionText').value = '';
    new bootstrap.Modal(document.getElementById('questionModal')).show();
}
async function submitQuestion() {
    const title = document.getElementById('questionTitle').value.trim();
    const question = document.getElementById('questionText').value.trim();
    if (!title || !question) return showModal('Error', 'Please fill all fields', 'error');
    try {
        const response = await fetch(`${API_URL}/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, question }),
            credentials: 'include'
        });
        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('questionModal')).hide();
            showToast('Question submitted', 'success');
            loadQuestions();
        } else {
            showModal('Error', data.error || 'Failed to submit', 'error');
        }
    } catch (error) {
        showModal('Error', 'Connection error', 'error');
    }
}

// ==================================================
// FEEDBACK SECTION (with View button for all)
// ==================================================
async function loadFeedback() {
    try {
        const response = await fetch(`${API_URL}/feedback/enhanced`, { credentials: 'include' });
        const data = await response.json();
        if (data.success && data.feedback) {
            allFeedback = data.feedback;
            if (data.feedback.length === 0) {
                document.getElementById('feedbackList').innerHTML = `<tr><td colspan="4" style="text-align: center;">${Translations.t('no_feedback')}</td></tr>`;
                return;
            }
            let html = '';
            data.feedback.forEach(f => {
                const statusClass = f.status === 'answered' ? 'status-answered' : 'status-pending';
                const statusText = f.status === 'answered' ? Translations.t('answered') : Translations.t('pending');
                html += `
                    <tr>
                        <td>${escapeHtml(f.subject)}</td>
                        <td>${new Date(f.created_at).toLocaleString()}</td>
                        <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                        <td>
                            <button class="btn-modern btn-primary-modern btn-sm" onclick="viewFeedback(${f.id})">
                                <i class="fas fa-eye"></i> ${Translations.t('view')}
                            </button>
                         </td>
                     </tr>
                `;
            });
            document.getElementById('feedbackList').innerHTML = html;
            const pendingCount = data.feedback.filter(f => f.status === 'pending').length;
            document.getElementById('sidebarFeedbackCount').textContent = pendingCount > 0 ? pendingCount : '';
            document.getElementById('sidebarFeedbackCount').classList.toggle('show', pendingCount > 0);
        }
    } catch (error) {
        console.error('Error loading feedback:', error);
        document.getElementById('feedbackList').innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--danger);">${Translations.t('error_loading')}</td></tr>`;
    }
}
function openFeedbackModal() {
    document.getElementById('feedbackSubject').value = '';
    document.getElementById('feedbackMessage').value = '';
    new bootstrap.Modal(document.getElementById('feedbackModal')).show();
}
async function submitFeedback() {
    const subject = document.getElementById('feedbackSubject').value.trim();
    const message = document.getElementById('feedbackMessage').value.trim();
    if (!subject || !message) return showModal('Error', 'Please fill all fields', 'error');
    try {
        const response = await fetch(`${API_URL}/feedback/enhanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, message }),
            credentials: 'include'
        });
        const data = await response.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('feedbackModal')).hide();
            showToast('Feedback sent', 'success');
            loadFeedback();
        } else {
            showModal('Error', data.error || 'Failed to send', 'error');
        }
    } catch (error) {
        showModal('Error', 'Connection error', 'error');
    }
}
function viewFeedback(feedbackId) {
    const fb = allFeedback.find(f => f.id === feedbackId);
    if (!fb) {
        showToast('Feedback not found', 'error');
        return;
    }
    document.getElementById('viewFeedbackSubject').textContent = fb.subject;
    document.getElementById('viewFeedbackMessage').textContent = fb.message;
    document.getElementById('viewFeedbackDate').textContent = new Date(fb.created_at).toLocaleString();
    const statusSpan = document.getElementById('viewFeedbackStatus');
    statusSpan.textContent = fb.status === 'answered' ? 'Answered' : 'Pending';
    statusSpan.className = `badge ${fb.status === 'answered' ? 'bg-success' : 'bg-warning'}`;
    const replyContainer = document.getElementById('replyContainer');
    if (fb.status === 'answered' && fb.reply) {
        document.getElementById('viewFeedbackReply').textContent = fb.reply;
        replyContainer.style.display = 'block';
    } else {
        replyContainer.style.display = 'none';
    }
    new bootstrap.Modal(document.getElementById('viewFeedbackModal')).show();
}

// ==================================================
// AI RESULTS SECTION
// ==================================================
async function loadAIResults() {
    await updateGlobalAIAverage();
    try {
        const response = await fetch(`${API_URL}/history?page=0`, { credentials: 'include' });
        const data = await response.json();
        if (!data.success || !data.history || data.history.length === 0) {
            document.getElementById('aiResultsList').innerHTML = '<tr><td colspan="5" style="text-align: center;">' + Translations.t('no_ai_results') + '</td></tr>';
            return;
        }
        let html = '';
        for (const session of data.history) {
            const sessionRes = await fetch(`${API_URL}/history/${session.id}`, { credentials: 'include' });
            const sessionData = await sessionRes.json();
            if (sessionData.success && sessionData.files) {
                sessionData.files.forEach(file => {
                    const aiScore = file.ai_score || 0;
                    const level = aiScore > 70 ? 'critical' : (aiScore > 40 ? 'high' : 'low');
                    html += `
                        <tr>
                            <td>${new Date(session.upload_time).toLocaleString()}</td>
                            <td>${escapeHtml(file.filename)}</td>
                            <td><strong>${aiScore}%</strong><div class="similarity-meter"><div class="similarity-fill ${level}" style="width: ${aiScore}%;"></div></div></td>
                            <td><span class="status-badge ${aiScore > 50 ? 'status-pending' : 'status-answered'}">${aiScore > 50 ? '⚠️ AI Generated' : '✅ Human Written'}</span></td>
                            <td><button class="btn-modern btn-outline-modern btn-sm" onclick="showModal('AI Analysis', 'AI Score: ${aiScore}%\\nThis document appears to be ${aiScore > 50 ? 'AI-generated' : 'human-written'}.')"><i class="fas fa-info-circle"></i> Details</button></td>
                        </tr>
                    `;
                });
            }
        }
        document.getElementById('aiResultsList').innerHTML = html;
    } catch (error) {
        console.error('Error loading AI results:', error);
        document.getElementById('aiResultsList').innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger);">Error loading AI results</td></tr>';
    }
}

// ==================================================
// NOTIFICATIONS
// ==================================================
function loadNotifications() {
    fetch(`${API_URL}/notifications`, { credentials: 'include' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('notificationBadge').textContent = data.unread_count || 0;
                if (data.notifications) updateNotificationsDropdown(data.notifications);
            }
        })
        .catch(console.error);
}
function startNotificationPolling() {
    loadNotifications();
    setInterval(loadNotifications, 30000);
}
function toggleNotifications() {
    document.getElementById('notificationsDropdown').classList.toggle('show');
}
function updateNotificationsDropdown(notifications) {
    const list = document.getElementById('notificationsList');
    if (notifications.length === 0) {
        list.innerHTML = '<div style="text-align: center; padding: 1rem;"><i class="fas fa-bell-slash"></i><p>No notifications</p></div>';
        return;
    }
    let html = '';
    notifications.slice(0, 10).forEach(n => {
        html += `<div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="notificationClick(${n.id}, '${n.link || ''}')">
                    <div class="notification-title">${escapeHtml(n.title)}</div>
                    <div class="notification-message">${escapeHtml(n.message)}</div>
                    <div class="notification-time">${new Date(n.created_at).toLocaleString()}</div>
                </div>`;
    });
    list.innerHTML = html;
}
function notificationClick(id, link) {
    fetch(`${API_URL}/notifications/${id}/read`, { method: 'POST', credentials: 'include' }).catch(() => {});
    document.getElementById('notificationsDropdown').classList.remove('show');
    if (link) window.location.href = link;
}
function markAllRead() {
    fetch(`${API_URL}/notifications/read-all`, { method: 'POST', credentials: 'include' })
        .then(() => {
            document.getElementById('notificationBadge').textContent = '0';
            loadNotifications();
            showToast('All notifications marked as read', 'success');
        })
        .catch(() => showToast('Failed to mark all as read', 'error'));
}

// ==================================================
// UTILITY FUNCTIONS
// ==================================================
function viewAnswer(question, answer) {
    document.getElementById('answerContent').innerHTML = `<div class="mb-3"><strong>Question:</strong><p>${question}</p></div><div><strong>Answer:</strong><p>${answer}</p></div>`;
    new bootstrap.Modal(document.getElementById('answerModal')).show();
}
function escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
function logout() { showConfirm('Logout', 'Are you sure you want to logout?', () => { fetch(`${API_URL}/logout`, { method: 'POST', credentials: 'include' }).then(() => window.location.href = '/index.html'); }); }