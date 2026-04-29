// Student Works Module
const StudentWorks = {
    currentStudentId: null,
    currentWorkSessionId: null,
    pollingInterval: null,
    
    init() {
        this.loadStudentsList();
        this.startPolling();
    },
    
    async loadStudentsList() {
        const container = document.getElementById('studentsListContainer');
        container.innerHTML = '<div class="loading-spinner-small"></div>';
        try {
            const res = await fetch('/api/student-works/students', { credentials: 'include' });
            const data = await res.json();
            if (data.success && data.students.length) {
                let html = '<div class="students-list-header"><input type="text" class="form-control" placeholder="Search students..." id="studentSearchInput" onkeyup="StudentWorks.filterStudents()"></div>';
                data.students.forEach(s => {
                    html += `
                        <div class="student-item" data-student-id="${s.id}" onclick="StudentWorks.selectStudent(${s.id}, '${escapeHtml(s.full_name)}')">
                            <div class="student-avatar">${(s.full_name.charAt(0) || 'S').toUpperCase()}</div>
                            <div class="student-info">
                                <div class="student-name">${escapeHtml(s.full_name)}</div>
                                <div class="student-email">${escapeHtml(s.email)}</div>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-users fa-3x"></i><p>No students have uploaded files yet.</p></div>';
            }
        } catch(e) {
            container.innerHTML = '<div class="empty-state text-danger">Error loading students</div>';
        }
    },
    
    filterStudents() {
        const search = document.getElementById('studentSearchInput').value.toLowerCase();
        const items = document.querySelectorAll('.student-item');
        items.forEach(item => {
            const name = item.querySelector('.student-name')?.textContent.toLowerCase() || '';
            item.style.display = name.includes(search) ? 'flex' : 'none';
        });
    },
    
    async selectStudent(studentId, studentName) {
        this.currentStudentId = studentId;
        this.currentWorkSessionId = null;
        document.querySelectorAll('.student-item').forEach(el => el.classList.remove('active'));
        document.querySelector(`.student-item[data-student-id="${studentId}"]`).classList.add('active');
        document.getElementById('chatHeader').innerHTML = `<i class="fas fa-user-graduate"></i> <strong>${escapeHtml(studentName)}</strong> - Select a work to chat`;
        document.getElementById('chatMessages').innerHTML = '<div class="empty-state">Select a file from the center panel to start conversation</div>';
        
        // Load works for this student
        const worksContainer = document.getElementById('studentWorksList');
        worksContainer.innerHTML = '<div class="loading-spinner-small"></div>';
        try {
            const res = await fetch(`/api/student-works/students/${studentId}/works`, { credentials: 'include' });
            const data = await res.json();
            if (data.success && data.works.length) {
                let html = '<div class="works-header"><h5><i class="fas fa-folder-open"></i> Submitted Works</h5></div>';
                data.works.forEach(work => {
                    work.files.forEach(file => {
                        const aiClass = file.ai_score > 50 ? 'high' : '';
                        html += `
                            <div class="work-card" data-session-id="${work.session_id}" data-file-id="${file.file_id}" onclick="StudentWorks.selectWork(${work.session_id}, ${file.file_id}, '${escapeHtml(file.filename)}')">
                                <div class="work-card-header">
                                    <span class="work-filename"><i class="fas fa-file-alt"></i> ${escapeHtml(file.filename)}</span>
                                    <span class="ai-score-badge ${aiClass}">AI: ${file.ai_score}%</span>
                                </div>
                                <div class="work-card-body">
                                    <small>Uploaded: ${new Date(work.upload_time).toLocaleString()}</small>
                                    <div class="work-card-actions">
                                        <button class="btn-sm btn-outline-modern" onclick="event.stopPropagation(); StudentWorks.viewFile(${file.file_id})"><i class="fas fa-eye"></i> View</button>
                                        <button class="btn-sm btn-outline-modern" onclick="event.stopPropagation(); StudentWorks.downloadFile(${file.file_id})"><i class="fas fa-download"></i> Download</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                });
                worksContainer.innerHTML = html;
            } else {
                worksContainer.innerHTML = '<div class="empty-state">No works uploaded yet.</div>';
            }
        } catch(e) {
            worksContainer.innerHTML = '<div class="empty-state text-danger">Error loading works</div>';
        }
    },
    
    async selectWork(sessionId, fileId, filename) {
        this.currentWorkSessionId = sessionId;
        document.querySelectorAll('.work-card').forEach(el => el.classList.remove('selected'));
        document.querySelector(`.work-card[data-session-id="${sessionId}"]`).classList.add('selected');
        
        document.getElementById('chatHeader').innerHTML = `<i class="fas fa-comments"></i> Chat about: <strong>${escapeHtml(filename)}</strong>`;
        await this.loadMessages(sessionId);
    },
    
    async loadMessages(sessionId) {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = '<div class="loading-spinner-small"></div>';
        try {
            const res = await fetch(`/api/student-works/conversation/${sessionId}`, { credentials: 'include' });
            const data = await res.json();
            if (data.success) {
                if (data.messages.length === 0) {
                    messagesContainer.innerHTML = '<div class="empty-state">No messages yet. Start the conversation!</div>';
                } else {
                    let html = '';
                    data.messages.forEach(msg => {
                        const isLecturer = msg.sender_role === 'lecturer';
                        const msgClass = isLecturer ? 'message-lecturer' : 'message-student';
                        const typeBadge = msg.type !== 'text' ? `<span class="message-type-badge">${msg.type}</span>` : '';
                        html += `
                            <div class="message ${msgClass}">
                                <div><strong>${escapeHtml(msg.sender_name)}</strong> ${typeBadge}</div>
                                <div>${escapeHtml(msg.message)}</div>
                                <div class="message-meta">${new Date(msg.created_at).toLocaleString()}</div>
                            </div>
                        `;
                    });
                    messagesContainer.innerHTML = html;
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }
        } catch(e) {
            messagesContainer.innerHTML = '<div class="empty-state text-danger">Error loading messages</div>';
        }
    },
    
    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message || !this.currentWorkSessionId) return;
        input.value = '';
        try {
            const res = await fetch(`/api/student-works/conversation/${this.currentWorkSessionId}/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, type: 'text' }),
                credentials: 'include'
            });
            const data = await res.json();
            if (data.success) {
                await this.loadMessages(this.currentWorkSessionId);
            } else {
                showToast('Failed to send message', 'error');
            }
        } catch(e) {
            showToast('Error sending message', 'error');
        }
    },
    
    async viewFile(fileId) {
        try {
            const res = await fetch(`/api/student-works/file/${fileId}`, { credentials: 'include' });
            const data = await res.json();
            if (data.success) {
                const file = data.file;
                const modalBody = `
                    <h5>${escapeHtml(file.filename)}</h5>
                    <p><strong>AI Score:</strong> ${file.ai_score}%</p>
                    <div class="progress mb-3"><div class="progress-bar bg-${file.ai_score > 50 ? 'danger' : 'success'}" style="width: ${file.ai_score}%"></div></div>
                    <p><strong>Words:</strong> ${file.word_count}</p>
                    <hr>
                    <h6>Content Preview:</h6>
                    <div style="max-height: 300px; overflow-y: auto; background: #f8f9ff; padding: 1rem; border-radius: 8px;">
                        ${escapeHtml(file.text_preview)}
                    </div>
                    ${file.full_text.length > 1000 ? `<button class="btn btn-link mt-2" onclick="alert('Full text available in download')">Download full file</button>` : ''}
                `;
                document.getElementById('infoModalMessage').innerHTML = modalBody;
                new bootstrap.Modal(document.getElementById('infoModal')).show();
            }
        } catch(e) {
            showToast('Failed to load file', 'error');
        }
    },
    
    downloadFile(fileId) {
        window.open(`/api/student-works/download/${fileId}`, '_blank');
    },
    
    startPolling() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        this.pollingInterval = setInterval(() => {
            if (this.currentWorkSessionId) {
                this.loadMessages(this.currentWorkSessionId);
            }
        }, 10000);
    },
    
    stopPolling() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
    }
};

// Helper
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}