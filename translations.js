const Translations = {
    // Current language setting
    currentLanguage: 'en', // Default: English
    
    // Available languages
    languages: {
        'en': 'English',
        'hy': 'Հայերեն'
    },
    
    // Translation dictionary
    translations: {
        'en': {
            // General
            'app_name': 'Student Panel',
            'loading': 'Loading...',
            'refresh': 'Refresh',
            'back': 'Back',
            'cancel': 'Cancel',
            'submit': 'Submit',
            'save': 'Save',
            'delete': 'Delete',
            'edit': 'Edit',
            'view': 'View',
            'close': 'Close',
            'confirm': 'Confirm',
            'search': 'Search...',
            'actions': 'Actions',
            'status': 'Status',
            'date': 'Date',
            'time': 'Time',
            'yes': 'Yes',
            'no': 'No',
            'error': 'Error',
            'success': 'Success',
            'info': 'Information',
            'warning': 'Warning',
            
            // Navigation
            'nav_dashboard': 'Dashboard',
            'nav_upload': 'Upload & Check',
            'nav_results': 'My Results',
            'nav_submissions': 'My Submissions',
            'nav_questions': 'Questions',
            'nav_feedback': 'Feedback',
            'nav_ai': 'AI Detection',
            'nav_logout': 'Logout',
            
            // Dashboard
            'total_submissions': 'Total Submissions',
            'total_checks': 'Plagiarism Checks',
            'pending_questions': 'Pending Questions',
            'avg_ai_score': 'Avg AI Score',
            'recent_results': 'Recent Results',
            'my_trends': 'My Plagiarism Trends',
            'ai_vs_human': 'AI vs Human',
            'files_compared': 'Files Compared',
            'similarity': 'Similarity',
            'ai_score': 'AI Score',
            
            // Upload
            'upload_title': 'Upload Documents for Plagiarism Check',
            'drag_drop': 'Drag & Drop or Click to Upload',
            'supported_formats': 'Supported: .txt, .pdf, .doc, .docx, .rtf (Max 100MB)',
            'choose_files': 'Choose Files',
            'selected_files': 'Selected Files:',
            'clear_all': 'Clear All',
            'check_plagiarism': 'Check Plagiarism',
            'uploading': 'Uploading...',
            'processing': 'Processing...',
            'upload_complete': 'Upload complete!',
            'processing_complete': 'Processing complete!',
            'need_more_files': 'Please upload at least 2 files',
            
            // Results
            'my_results': 'My Plagiarism Results',
            'no_results': 'No Results Found',
            'no_results_desc': 'Upload files to check for plagiarism',
            'comparison': 'Comparison',
            'similarity_score': 'Similarity Score',
            'view_details': 'View Details',
            'overall_similarity': 'Overall Similarity',
            'words': 'Words',
            'submitted': 'Submitted',
            'for_highlighting': 'For detailed text highlighting, please consult your lecturer',
            
            // Submissions
            'my_submissions': 'My Submissions',
            'title': 'Title',
            'files': 'Files',
            'processed': 'Processed',
            'no_submissions': 'No submissions',
            
            // Questions
            'my_questions': 'My Questions',
            'ask_question': 'Ask Question',
            'question_title': 'Title',
            'your_question': 'Your Question',
            'question_placeholder': 'e.g., Plagiarism score explanation',
            'question_detail_placeholder': 'Write your question in detail...',
            'asked': 'Asked',
            'answer': 'Answer',
            'view_answer': 'View Answer',
            'awaiting_answer': 'Awaiting answer',
            'no_questions': 'No questions',
            'question_submitted': 'Question submitted!',
            'question_submitted_at': 'Question submitted at',
            
            // Feedback
            'my_feedback': 'My Feedback',
            'send_feedback': 'Send Feedback',
            'subject': 'Subject',
            'message': 'Message',
            'subject_placeholder': 'e.g., Plagiarism detection issue',
            'message_placeholder': 'Describe your feedback or issue...',
            'sent': 'Sent',
            'reply': 'Reply',
            'view_reply': 'View Reply',
            'no_reply': 'No reply yet',
            'no_feedback': 'No feedback',
            'feedback_sent': 'Feedback sent!',
            'feedback_sent_at': 'Feedback sent at',
            
            // AI Detection
            'ai_detection': 'AI Content Detection Results',
            'files_checked': 'Files Checked',
            'average_ai': 'Average AI Score',
            'human_written': 'Human Written',
            'filename': 'Filename',
            'ai_score_col': 'AI Score',
            'result': 'Result',
            'ai_generated': '⚠️ AI Generated',
            'human_written_badge': '✅ Human Written',
            'no_ai_results': 'No AI results',
            'ai_analysis': 'AI Analysis',
            'ai_probability': 'AI Probability',
            'appears_ai': 'This document appears to be AI-generated',
            'appears_human': 'This document appears to be human-written',
            
            // Notifications
            'notifications': 'Notifications',
            'mark_all_read': 'Mark all read',
            'no_notifications': 'No notifications',
            'just_now': 'just now',
            'minutes_ago': 'minutes ago',
            'hour_ago': 'hour ago',
            'hours_ago': 'hours ago',
            'day_ago': 'day ago',
            'days_ago': 'days ago',
            
            // Time
            'yerevan_time': 'Yerevan Time',
            'today': 'Today',
            'yesterday': 'Yesterday',
            'this_week': 'This week',
            
            // Modals
            'confirm_action': 'Confirm Action',
            'are_you_sure': 'Are you sure?',
            'logout_confirm': 'Are you sure you want to logout?',
            'clear_files_confirm': 'Clear all selected files?',
            'fill_all_fields': 'Please fill all fields',
            
            // Errors
            'error_loading': 'Error loading data',
            'connection_error': 'Connection error',
            'invalid_response': 'Invalid response from server',
            'check_failed': 'Check failed',
            'upload_failed': 'Upload failed',
            
            // Success messages
            'data_refreshed': 'Data refreshed',
            'all_cleared': 'All files cleared',
            'check_complete': 'Plagiarism check complete!',
            'marked_read': 'All notifications marked as read',
            'logout_success': 'Logged out successfully'
        },
        
        'hy': {
            // General
            'app_name': 'Ուսանողի ',
            'loading': 'Բեռնվում է...',
            'refresh': 'Թարմացնել',
            'back': 'Հետ',
            'cancel': 'Չեղարկել',
            'submit': 'Ուղարկել',
            'save': 'Պահպանել',
            'delete': 'Ջնջել',
            'edit': 'Խմբագրել',
            'view': 'Դիտել',
            'close': 'Փակել',
            'confirm': 'Հաստատել',
            'search': 'Որոնել...',
            'actions': 'Գործողություններ',
            'status': 'Կարգավիճակ',
            'date': 'Ամսաթիվ',
            'time': 'Ժամ',
            'yes': 'Այո',
            'no': 'Ոչ',
            'error': 'Սխալ',
            'success': 'Հաջողություն',
            'info': 'Տեղեկություն',
            'warning': 'Զգուշացում',
            
            // Navigation
            'nav_dashboard': 'Վահանակ',
            'nav_upload': 'Վերբեռնում & Ստուգում',
            'nav_results': 'Իմ Արդյունքները',
            'nav_submissions': 'Իմ Հանձնարարությունները',
            'nav_questions': 'Հարցեր',
            'nav_feedback': 'Կարծիք',
            'nav_ai': 'AI Ստուգում',
            'nav_logout': 'Դուրս Գալ',
            
            // Dashboard
            'total_submissions': 'Ընդհանուր Հանձնարարություններ',
            'total_checks': 'Պլագիատի Ստուգումներ',
            'pending_questions': 'Սպասող Հարցեր',
            'avg_ai_score': 'Միջին AI Միավոր',
            'recent_results': 'Վերջին Արդյունքները',
            'my_trends': 'Իմ Պլագիատի Միտումները',
            'ai_vs_human': 'AI vs Մարդ',
            'files_compared': 'Համեմատված Ֆայլեր',
            'similarity': 'Նմանություն',
            'ai_score': 'AI Միավոր',
            
            // Upload
            'upload_title': 'Վերբեռնել Փաստաթղթերը Պլագիատի Ստուգման Համար',
            'drag_drop': 'Քաշել & Գցել կամ Սեղմել Վերբեռնելու Համար',
            'supported_formats': 'Աջակցվող ձևաչափեր՝ .txt, .pdf, .doc, .docx, .rtf (Առավել. 100ՄԲ)',
            'choose_files': 'Ընտրել Ֆայլեր',
            'selected_files': 'Ընտրված Ֆայլեր:',
            'clear_all': 'Մաքրել Բոլորը',
            'check_plagiarism': 'Ստուգել Պլագիատը',
            'uploading': 'Վերբեռնվում է...',
            'processing': 'Մշակվում է...',
            'upload_complete': 'Վերբեռնումն ավարտվեց!',
            'processing_complete': 'Մշակումն ավարտվեց!',
            'need_more_files': 'Խնդրում ենք վերբեռնել առնվազն 2 ֆայլ',
            
            // Results
            'my_results': 'Իմ Պլագիատի Արդյունքները',
            'no_results': 'Արդյունքներ Չեն Գտնվել',
            'no_results_desc': 'Վերբեռնեք ֆայլեր պլագիատը ստուգելու համար',
            'comparison': 'Համեմատություն',
            'similarity_score': 'Նմանության Միավոր',
            'view_details': 'Դիտել Մանրամասները',
            'overall_similarity': 'Ընդհանուր Նմանություն',
            'words': 'Բառեր',
            'submitted': 'Ներկայացված',
            'for_highlighting': 'Մանրամասն տեքստի ընդգծման համար դիմեք ձեր դասախոսին',
            
            // Submissions
            'my_submissions': 'Իմ Հանձնարարությունները',
            'title': 'Վերնագիր',
            'files': 'Ֆայլեր',
            'processed': 'Մշակված',
            'no_submissions': 'Հանձնարարություններ չկան',
            
            // Questions
            'my_questions': 'Իմ Հարցերը',
            'ask_question': 'Հարց տալ',
            'question_title': 'Վերնագիր',
            'your_question': 'Ձեր Հարցը',
            'question_placeholder': 'Օրինակ՝ Պլագիատի միավորի բացատրություն',
            'question_detail_placeholder': 'Մանրամասն գրեք ձեր հարցը...',
            'asked': 'Հարցված',
            'answer': 'Պատասխան',
            'view_answer': 'Դիտել Պատասխանը',
            'awaiting_answer': 'Սպասում է պատասխանի',
            'no_questions': 'Հարցեր չկան',
            'question_submitted': 'Հարցը ուղարկված է!',
            'question_submitted_at': 'Հարցը ուղարկված է',
            
            // Feedback
            'my_feedback': 'Իմ Կարծիքը',
            'send_feedback': 'Ուղարկել Կարծիք',
            'subject': 'Թեմա',
            'message': 'Հաղորդագրություն',
            'subject_placeholder': 'Օրինակ՝ Պլագիատի հայտնաբերման խնդիր',
            'message_placeholder': 'Նկարագրեք ձեր կարծիքը կամ խնդիրը...',
            'sent': 'Ուղարկված',
            'reply': 'Պատասխան',
            'view_reply': 'Դիտել Պատասխանը',
            'no_reply': 'Պատասխան դեռ չկա',
            'no_feedback': 'Կարծիք չկա',
            'feedback_sent': 'Կարծիքը ուղարկված է!',
            'feedback_sent_at': 'Կարծիքը ուղարկված է',
            
            // AI Detection
            'ai_detection': 'AI Բովանդակության Ստուգման Արդյունքներ',
            'files_checked': 'Ստուգված Ֆայլեր',
            'average_ai': 'Միջին AI Միավոր',
            'human_written': 'Մարդու Գրած',
            'filename': 'Ֆայլի Անուն',
            'ai_score_col': 'AI Միավոր',
            'result': 'Արդյունք',
            'ai_generated': '⚠️ AI-ով Գեներացված',
            'human_written_badge': '✅ Մարդու Գրած',
            'no_ai_results': 'AI արդյունքներ չկան',
            'ai_analysis': 'AI Վերլուծություն',
            'ai_probability': 'AI Հավանականություն',
            'appears_ai': 'Այս փաստաթուղթը կարծես AI-ով է գեներացված',
            'appears_human': 'Այս փաստաթուղթը կարծես մարդու կողմից է գրված',
            
            // Notifications
            'notifications': 'Ծանուցումներ',
            'mark_all_read': 'Նշել բոլորը որպես կարդացված',
            'no_notifications': 'Ծանուցումներ չկան',
            'just_now': 'հենց հիմա',
            'minutes_ago': 'րոպե առաջ',
            'hour_ago': 'ժամ առաջ',
            'hours_ago': 'ժամ առաջ',
            'day_ago': 'օր առաջ',
            'days_ago': 'օր առաջ',
            
            // Time
            'yerevan_time': 'Երևանի Ժամ',
            'today': 'Այսօր',
            'yesterday': 'Երեկ',
            'this_week': 'Այս շաբաթ',
            
            // Modals
            'confirm_action': 'Հաստատել Գործողությունը',
            'are_you_sure': 'Համոզված ե՞ք',
            'logout_confirm': 'Համոզված ե՞ք, որ ցանկանում եք դուրս գալ',
            'clear_files_confirm': 'Մաքրել բոլոր ընտրված ֆայլերը',
            'fill_all_fields': 'Խնդրում ենք լրացնել բոլոր դաշտերը',
            
            // Errors
            'error_loading': 'Տվյալները բեռնելիս սխալ',
            'connection_error': 'Կապի սխալ',
            'invalid_response': 'Սերվերից սխալ պատասխան',
            'check_failed': 'Ստուգումը ձախողվեց',
            'upload_failed': 'Վերբեռնումը ձախողվեց',
            
            // Success messages
            'data_refreshed': 'Տվյալները թարմացված են',
            'all_cleared': 'Բոլոր ֆայլերը մաքրված են',
            'check_complete': 'Պլագիատի ստուգումն ավարտվեց',
            'marked_read': 'Բոլոր ծանուցումները նշված են որպես կարդացված',
            'logout_success': 'Դուրս եկաք համակարգից'
        }
    },
    
    // Get translation for a key
    t(key) {
        const lang = this.currentLanguage;
        if (this.translations[lang] && this.translations[lang][key]) {
            return this.translations[lang][key];
        }
        // Fallback to English
        return this.translations['en'][key] || key;
    },
    
    // Change language
    setLanguage(lang) {
        if (this.languages[lang]) {
            this.currentLanguage = lang;
            localStorage.setItem('preferredLanguage', lang);
            this.updatePageLanguage();
        }
    },
    
    // Load saved language preference
    loadLanguagePreference() {
        const saved = localStorage.getItem('preferredLanguage');
        if (saved && this.languages[saved]) {
            this.currentLanguage = saved;
        }
    },
    
    // Update all translatable elements on the page
    updatePageLanguage() {
        // Update elements with data-translate attribute
        document.querySelectorAll('[data-translate]').forEach(el => {
            const key = el.getAttribute('data-translate');
            el.textContent = this.t(key);
        });
        
        // Update placeholders
        document.querySelectorAll('[data-translate-placeholder]').forEach(el => {
            const key = el.getAttribute('data-translate-placeholder');
            el.placeholder = this.t(key);
        });
        
        // Update page title
        const titleEl = document.getElementById('pageTitle');
        if (titleEl) {
            const activeSection = document.querySelector('.content-section.active')?.id;
            if (activeSection) {
                const sectionMap = {
                    'section-dashboard': 'nav_dashboard',
                    'section-upload': 'nav_upload',
                    'section-results': 'nav_results',
                    'section-submissions': 'nav_submissions',
                    'section-questions': 'nav_questions',
                    'section-feedback': 'nav_feedback',
                    'section-ai-results': 'nav_ai'
                };
                const key = sectionMap[activeSection] || 'nav_dashboard';
                titleEl.textContent = this.t(key);
            }
        }
        
        // Dispatch event for components that need to know language changed
        document.dispatchEvent(new CustomEvent('languageChanged', { 
            detail: { language: this.currentLanguage }
        }));
    },
    
    // Create language switcher dropdown
    createLanguageSwitcher() {
        const switcher = document.createElement('div');
        switcher.className = 'language-switcher';
        switcher.innerHTML = `
            <select id="languageSelect" class="form-select form-select-sm" style="width: auto; border-radius: 20px; background: var(--light); border: 1px solid var(--border);">
                <option value="en">🇬🇧 English</option>
                <option value="hy">🇦🇲 Հայերեն</option>
            </select>
        `;
        
        // Add event listener
        setTimeout(() => {
            const select = document.getElementById('languageSelect');
            if (select) {
                select.value = this.currentLanguage;
                select.addEventListener('change', (e) => {
                    this.setLanguage(e.target.value);
                });
            }
        }, 100);
        
        return switcher;
    }
};

// Initialize language preference
Translations.loadLanguagePreference();

// Helper function for easy access
function __(key) {
    return Translations.t(key);
}