/* Student Works JavaScript Module */
const StudentWorks = {
    currentStudentId: null,
    currentWorkSessionId: null,
    pollingInterval: null,
    selectedFiles: new Set(),

    init() {
        this.loadStudentsList();
        this.startPolling();
    },

    async loadStudentsList() {
        const container = document.getElementById('studentsListContainer');
        if (!container) return;
        container.innerHTML = '<div class="loading-spinner-small"></div>';

        try {
            const res = await fetch('/api/student-works/students', { credentials: 'include' });
            const data = await res.json();
            if (data.success && Array.isArray(data.students) && data.students.length) {
                let html = '';
                data.students.forEach(student => {
                    const fullName = student.full_name || student.username || 'Student';
                    const name = escapeHtml(fullName);
                    const email = escapeHtml(student.email || '');
                    const initial = escapeHtml(String(fullName).charAt(0).toUpperCase());
                    html += `
                        <div class="student-item" data-student-id="${student.id}" onclick="StudentWorks.selectStudent(${student.id}, '${name.replace(/'/g, "\\'")}')">
                            <div class="student-avatar">${initial}</div>
                            <div class="student-info">
                                <div class="student-name">${name}</div>
                                <div class="student-email">${email}</div>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-users fa-2x"></i><p>No students with uploaded work yet.</p></div>';
            }
        } catch (error) {
            container.innerHTML = '<div class="empty-state text-danger">Unable to load student list.</div>';
            console.error('StudentWorks.loadStudentsList error', error);
        }
    },

    filterStudents() {
        const query = document.getElementById('studentSearchInput').value.toLowerCase();
        document.querySelectorAll('.student-item').forEach(item => {
            const name = item.querySelector('.student-name')?.textContent.toLowerCase() || '';
            item.style.display = name.includes(query) ? 'flex' : 'none';
        });
    },

    async selectStudent(studentId, studentName) {
        this.currentStudentId = studentId;
        this.currentWorkSessionId = null;
        document.querySelectorAll('.student-item').forEach(el => el.classList.remove('active'));
        const selected = document.querySelector(`.student-item[data-student-id="${studentId}"]`);
        if (selected) selected.classList.add('active');

        const chatHeader = document.getElementById('chatHeader');
        const chatMessages = document.getElementById('chatMessages');
        if (chatHeader) chatHeader.innerHTML = `<i class="fas fa-user-graduate"></i> <strong>${escapeHtml(studentName)}</strong> - Select a work to chat`;
        if (chatMessages) chatMessages.innerHTML = '<div class="empty-state">Select a file from the center panel to start conversation</div>';

        const worksContainer = document.getElementById('studentWorksList');
        if (!worksContainer) return;
        worksContainer.innerHTML = '<div class="loading-spinner-small"></div>';

        try {
            const res = await fetch(`/api/student-works/students/${studentId}/works`, { credentials: 'include' });
            const data = await res.json();
            if (data.success && Array.isArray(data.works) && data.works.length) {
                let html = '';
                data.works.forEach(work => {
                    const uploadedAt = work.upload_time ? new Date(work.upload_time).toLocaleString() : 'Unknown';
                    work.files.forEach(file => {
                        const safeFilename = escapeHtml(file.filename || 'File');
                        const aiClass = file.ai_score > 50 ? 'high' : '';
                        const isChecked = this.selectedFiles.has(file.file_id);
                        html += `
                            <div class="work-card ${isChecked ? 'checked' : ''}" data-session-id="${work.session_id}" data-file-id="${file.file_id}">
                                <div class="work-card-header">
                                    <input type="checkbox" class="work-card-checkbox" data-file-id="${file.file_id}" ${isChecked ? 'checked' : ''} onchange="event.stopPropagation(); StudentWorks.toggleFileSelection(${file.file_id}, this.checked)">
                                    <span class="work-filename" style="cursor: pointer; flex: 1;" onclick="StudentWorks.viewFileWithAI(${file.file_id})"><i class="fas fa-file-alt"></i> ${safeFilename}</span>
                                    <span class="ai-score-badge ${aiClass}">AI: ${Number(file.ai_score || 0).toFixed(0)}%</span>
                                </div>
                                <div class="work-card-body">
                                    <small>Uploaded: ${escapeHtml(uploadedAt)}</small>
                                    <div class="work-card-actions">
                                        <button class="btn-sm" onclick="event.stopPropagation(); StudentWorks.viewFileWithAI(${file.file_id})"><i class="fas fa-robot"></i> AI Analysis</button>
                                        <button class="btn-sm" onclick="event.stopPropagation(); StudentWorks.downloadFile(${file.file_id})"><i class="fas fa-download"></i> Download</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                });
                worksContainer.innerHTML = html;
            } else {
                worksContainer.innerHTML = '<div class="empty-state">No works uploaded by this student yet.</div>';
            }
        } catch (error) {
            worksContainer.innerHTML = '<div class="empty-state text-danger">Unable to load works.</div>';
            console.error('StudentWorks.selectStudent error', error);
        }
    },

    toggleFileSelection(fileId, checked) {
        if (checked) {
            this.selectedFiles.add(fileId);
        } else {
            this.selectedFiles.delete(fileId);
        }
        
        // Update UI
        const workCard = document.querySelector(`[data-file-id="${fileId}"]`);
        if (workCard) {
            if (checked) {
                workCard.classList.add('checked');
            } else {
                workCard.classList.remove('checked');
            }
        }
        
        // Show/hide compare button
        const compareBtn = document.getElementById('compareFilesBtn');
        if (compareBtn) {
            compareBtn.style.display = this.selectedFiles.size >= 2 ? 'flex' : 'none';
        }
    },

    openCompareModal() {
        if (this.selectedFiles.size < 2) {
            showToast('Please select at least 2 files to compare', 'error');
            return;
        }
        
        const fileIds = Array.from(this.selectedFiles);
        this.compareTwoFiles(fileIds[0], fileIds[1]);
    },

    async selectWork(sessionId, fileId, filename) {
        this.currentWorkSessionId = sessionId;
        document.querySelectorAll('.work-card').forEach(el => el.classList.remove('selected'));
        const selected = document.querySelector(`.work-card[data-session-id="${sessionId}"][data-file-id="${fileId}"]`);
        if (selected) selected.classList.add('selected');

        const chatHeader = document.getElementById('chatHeader');
        if (chatHeader) chatHeader.innerHTML = `<i class="fas fa-comments"></i> Chat about: <strong>${escapeHtml(filename)}</strong>`;
        await this.loadMessages(sessionId);
    },

    async loadMessages(sessionId) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        messagesContainer.innerHTML = '<div class="loading-spinner-small"></div>';

        try {
            const res = await fetch(`/api/student-works/conversation/${sessionId}`, { credentials: 'include' });
            const data = await res.json();
            if (data.success) {
                if (!Array.isArray(data.messages) || data.messages.length === 0) {
                    messagesContainer.innerHTML = '<div class="empty-state">No messages yet. Start the conversation!</div>';
                    return;
                }
                let html = '';
                data.messages.forEach(msg => {
                    const isLecturer = msg.sender_role === 'lecturer';
                    const msgClass = isLecturer ? 'message-lecturer' : 'message-student';
                    const badge = msg.type && msg.type !== 'text' ? `<span class="message-type-badge">${escapeHtml(msg.type)}</span>` : '';
                    html += `
                        <div class="message ${msgClass}">
                            <div><strong>${escapeHtml(msg.sender_name || (isLecturer ? 'Lecturer' : 'Student'))}</strong> ${badge}</div>
                            <div>${escapeHtml(msg.message)}</div>
                            <div class="message-meta">${new Date(msg.created_at).toLocaleString()}</div>
                        </div>
                    `;
                });
                messagesContainer.innerHTML = html;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } else {
                messagesContainer.innerHTML = '<div class="empty-state text-danger">Unable to load messages.</div>';
            }
        } catch (error) {
            messagesContainer.innerHTML = '<div class="empty-state text-danger">Unable to load messages.</div>';
            console.error('StudentWorks.loadMessages error', error);
        }
    },

    async sendMessage() {
        const input = document.getElementById('chatInput');
        if (!input || !this.currentWorkSessionId) return;
        const message = input.value.trim();
        if (!message) return;
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
                showToast(data.error || 'Failed to send message', 'error');
            }
        } catch (error) {
            showToast('Unable to send message', 'error');
            console.error('StudentWorks.sendMessage error', error);
        }
    },

    async viewFile(fileId) {
        // Show basic file preview (kept for backward compatibility)
        await this.viewFileWithAI(fileId);
    },

    async viewFileWithAI(fileId) {
        try {
            const res = await fetch(`/api/student-works/file/${fileId}`, { credentials: 'include' });
            const data = await res.json();
            if (!data.success) {
                showToast(data.error || 'Unable to load file', 'error');
                return;
            }
            
            const file = data.file || {};
            
            // Fetch AI analysis
            const aiRes = await fetch(`/api/ai-details/${file.session_id || 0}/${encodeURIComponent(file.filename)}`, 
                { credentials: 'include' });
            const aiData = aiRes.ok ? await aiRes.json() : { success: false };
            
            let aiContent = '';
            if (aiData.success && aiData.ai_analysis) {
                const aiAnalysis = aiData.ai_analysis;
                const aiScore = aiAnalysis.overall_score || 0;
                
                aiContent = `
                    <div class="ai-score-box">
                        <div class="ai-score-value">${Number(aiScore).toFixed(0)}%</div>
                        <div>
                            <div class="ai-score-label">AI Detection Score</div>
                            <div class="ai-score-bar">
                                <div class="ai-score-fill" style="width: ${Math.min(aiScore, 100)}%"></div>
                            </div>
                        </div>
                    </div>
                    <div><strong>Detected Phrases:</strong></div>
                `;
                
                if (aiAnalysis.matching_phrases && aiAnalysis.matching_phrases.length) {
                    aiContent += '<ul style="margin: 10px 0; padding-left: 20px;">';
                    aiAnalysis.matching_phrases.slice(0, 10).forEach(phrase => {
                        aiContent += `<li style="margin: 5px 0;"><code>${escapeHtml(phrase)}</code></li>`;
                    });
                    if (aiAnalysis.matching_phrases.length > 10) {
                        aiContent += `<li style="margin: 5px 0; color: #999;">... and ${aiAnalysis.matching_phrases.length - 10} more</li>`;
                    }
                    aiContent += '</ul>';
                }
                
                if (aiAnalysis.sentences && aiAnalysis.sentences.length) {
                    aiContent += '<div style="margin-top: 20px;"><strong>Sentence Analysis:</strong></div>';
                    aiAnalysis.sentences.slice(0, 15).forEach(sent => {
                        if (sent.is_ai) {
                            let highlightedText = escapeHtml(sent.text);
                            if (sent.ai_triggers && sent.ai_triggers.length) {
                                sent.ai_triggers.forEach(trigger => {
                                    const regex = new RegExp(`\\b${trigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
                                    highlightedText = highlightedText.replace(regex, match => 
                                        `<span class="ai-word-highlight">${match}</span>`);
                                });
                            }
                            aiContent += `<div class="ai-sentence-container">${highlightedText}</div>`;
                        }
                    });
                }
            } else {
                aiContent = '<p style="color: #999;">AI analysis not available for this file.</p>';
            }
            
            const modalBody = `
                <h5>${escapeHtml(file.filename || 'File Preview')}</h5>
                <p><strong>AI Score:</strong> ${Number(file.ai_score || 0).toFixed(0)}%</p>
                <div class="progress mb-3">
                    <div class="progress-bar ${file.ai_score > 50 ? 'bg-danger' : 'bg-success'}" role="progressbar" 
                         style="width: ${Number(file.ai_score || 0)}%"></div>
                </div>
                <p><strong>Words:</strong> ${Number(file.word_count || 0)}</p>
                <hr>
                <div style="margin-top: 20px;">
                    ${aiContent}
                </div>
            `;
            
            document.getElementById('aiModalTitle').textContent = 'AI Analysis - ' + (file.filename || 'File');
            document.getElementById('aiAnalysisContent').innerHTML = modalBody;
            new bootstrap.Modal(document.getElementById('aiAnalysisModal')).show();
        } catch (error) {
            showToast('Unable to load file analysis', 'error');
            console.error('StudentWorks.viewFileWithAI error', error);
        }
    },

    async compareTwoFiles(fileId1, fileId2) {
        try {
            const comparisonRes = await fetch(`/api/student-works/compare/${fileId1}/${fileId2}`, 
                { credentials: 'include' });
            const comparisonData = await comparisonRes.json();
            
            if (!comparisonData.success) {
                showToast(comparisonData.error || 'Unable to compare files', 'error');
                return;
            }
            
            const file1Info = comparisonData.file1;
            const file2Info = comparisonData.file2;
            const highlighting = comparisonData.highlighting || { file1: [], file2: [] };
            
            let html = `
                <div class="comparison-container">
                    <div class="comparison-file">
                        <div class="comparison-file-header">
                            <div>
                                <div>${escapeHtml(file1Info.filename)}</div>
                                <span class="ai-score-badge-comparison">AI: ${Number(file1Info.ai_score).toFixed(0)}%</span>
                            </div>
                        </div>
                        <div class="comparison-file-content">
            `;
            
            // Render file1 sentences
            if (highlighting.file1 && highlighting.file1.length) {
                highlighting.file1.forEach(sent => {
                    const className = sent.plagiarized ? 'plagiarized' : '';
                    html += `<div class="comparison-sentence ${className}">`;
                    
                    if (sent.words && sent.words.length) {
                        sent.words.forEach(word => {
                            const wordClass = word.plagiarized ? 'plagiarized' : '';
                            html += `<span class="comparison-word ${wordClass}">${escapeHtml(word.text)}</span> `;
                        });
                    } else {
                        html += escapeHtml(sent.text);
                    }
                    
                    if (sent.plagiarized && sent.matched_with >= 0) {
                        const similarity = sent.similarity || 0;
                        html += `<div class="plagiarism-match-info">Match: ${Number(similarity).toFixed(0)}%</div>`;
                    }
                    html += '</div>';
                });
            }
            
            html += `
                        </div>
                    </div>
                    <div class="comparison-file">
                        <div class="comparison-file-header">
                            <div>
                                <div>${escapeHtml(file2Info.filename)}</div>
                                <span class="ai-score-badge-comparison">AI: ${Number(file2Info.ai_score).toFixed(0)}%</span>
                            </div>
                        </div>
                        <div class="comparison-file-content">
            `;
            
            // Render file2 sentences
            if (highlighting.file2 && highlighting.file2.length) {
                highlighting.file2.forEach(sent => {
                    const className = sent.plagiarized ? 'plagiarized' : '';
                    html += `<div class="comparison-sentence ${className}">`;
                    
                    if (sent.words && sent.words.length) {
                        sent.words.forEach(word => {
                            const wordClass = word.plagiarized ? 'plagiarized' : '';
                            html += `<span class="comparison-word ${wordClass}">${escapeHtml(word.text)}</span> `;
                        });
                    } else {
                        html += escapeHtml(sent.text);
                    }
                    
                    if (sent.plagiarized && sent.matched_with >= 0) {
                        const similarity = sent.similarity || 0;
                        html += `<div class="plagiarism-match-info">Match: ${Number(similarity).toFixed(0)}%</div>`;
                    }
                    html += '</div>';
                });
            }
            
            html += `
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('comparisonContent').innerHTML = html;
            new bootstrap.Modal(document.getElementById('comparisonModal')).show();
        } catch (error) {
            showToast('Unable to compare files', 'error');
            console.error('StudentWorks.compareTwoFiles error', error);
        }
    },

    downloadFile(fileId) {
        window.open(`/api/student-works/download/${fileId}`, '_blank');
    },

    startPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        this.pollingInterval = setInterval(() => {
            if (this.currentWorkSessionId) {
                this.loadMessages(this.currentWorkSessionId);
            }
        }, 10000);
    },

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
};

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return text.toString().replace(/[&<>\"]+/g, function (match) {
        switch (match) {
            case '&': return '&amp;';
            case '<': return '&lt;';
            case '>': return '&gt;';
            case '"': return '&quot;';
            default: return match;
        }
    });
}
