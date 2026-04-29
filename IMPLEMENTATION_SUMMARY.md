# Student Works AI Analysis & File Comparison Feature - Implementation Summary

## Overview
Added comprehensive file analysis and comparison capabilities to the Lecturer Dashboard's "Student Works" section, enabling lecturers to:
1. View AI-detected content in files with word-level highlighting
2. Select and compare two files side-by-side with plagiarism detection

---

## Files Modified

### 1. **student_works.py** (API Backend)
**Added:** New comparison endpoint

```python
@student_works_bp.route('/compare/<int:file_id1>/<int:file_id2>', methods=['GET'])
def compare_files(file_id1, file_id2):
```

- **Purpose:** Compare two student work files with word-level plagiarism highlighting
- **Parameters:**
  - `file_id1`: First file ID to compare
  - `file_id2`: Second file ID to compare
- **Returns JSON:**
  ```json
  {
    "success": true,
    "file1": { "id": int, "filename": string, "ai_score": float },
    "file2": { "id": int, "filename": string, "ai_score": float },
    "highlighting": {
      "file1": [...sentences with word-level plagiarism flags...],
      "file2": [...sentences with word-level plagiarism flags...]
    }
  }
  ```
- **Security:** Lecturers can compare any files; students can only compare their own

**Imports Added:**
```python
from similarity import highlight_word_level
from ai_detection import detect_ai_content
```

---

### 2. **lecturer.html** (Frontend UI)

#### A. Work Card UI Changes
- Added checkboxes to each file card for selection
- Changed file click action to open AI analysis modal instead of inline preview
- Added "AI Analysis" button to each file card
- Added "Compare Selected Files" button to works panel header

**Key HTML Changes:**
```html
<!-- Work Card with Checkbox -->
<input type="checkbox" class="work-card-checkbox" 
    onclick="StudentWorks.toggleFileSelection(fileId, checked)">
<span onclick="StudentWorks.viewFileWithAI(fileId)">File Name</span>

<!-- Compare Button in Works Header -->
<button id="compareFilesBtn" class="btn-compare" 
    onclick="StudentWorks.openCompareModal()">
    <i class="fas fa-exchange-alt"></i> Compare Selected
</button>
```

#### B. New Modals Added

**AI Analysis Modal (Line 1032):**
```html
<div class="modal fade" id="aiAnalysisModal">
    <div id="aiAnalysisContent">
        <!-- Dynamically populated with AI analysis -->
    </div>
</div>
```

**File Comparison Modal (Line 1054):**
```html
<div class="modal fade" id="comparisonModal">
    <div id="comparisonContent">
        <!-- Side-by-side comparison with highlighting -->
    </div>
</div>
```

---

### 3. **static/student_works.js** (Client-Side Logic)

#### A. State Management
```javascript
selectedFiles: new Set(),  // Track selected file IDs
```

#### B. New Methods

**`toggleFileSelection(fileId, checked)`**
- Manages file selection checkboxes
- Updates card UI with "checked" class
- Shows/hides "Compare Selected Files" button when 2+ files selected

**`openCompareModal()`**
- Validates that exactly 2 files are selected
- Calls `compareTwoFiles()` with the selected file IDs

**`viewFileWithAI(fileId)`** ⭐ Main Feature
- Fetches file content from `/api/student-works/file/{fileId}`
- Fetches AI analysis from `/api/ai-details/{sessionId}/{filename}`
- Displays modal with:
  - Overall AI score with progress bar
  - Top detected AI phrases
  - First 15 sentences with AI triggers highlighted in red
  - Escaped HTML for security

**`compareTwoFiles(fileId1, fileId2)`** ⭐ Main Feature
- Fetches comparison data from `/api/student-works/compare/{fileId1}/{fileId2}`
- Renders side-by-side comparison with:
  - Left column: File 1 content
  - Right column: File 2 content
  - Plagiarized words highlighted in red
  - Plagiarism match percentages displayed
  - AI scores shown in badges

#### C. Updated Methods
- Modified `selectStudent()` to regenerate checkboxes based on `selectedFiles` state
- Updated work card rendering to include checkboxes and new AI Analysis button

---

### 4. **static/student_works.css** (Styling)

#### New CSS Classes

**File Selection:**
- `.work-card-checkbox`: Styled checkbox (20x20px, primary color accent)
- `.work-card.checked`: Highlight selected cards with primary color border

**AI Analysis Highlighting:**
- `.ai-word-highlight`: Red background (#ff4444), white text, red-highlighted AI trigger words
- `.ai-sentence-container`: Light red background (#fff8f8) with red left border
- `.ai-score-box`: Score display with progress bar
- `.ai-score-bar` / `.ai-score-fill`: Progress visualization

**Comparison View:**
- `.comparison-container`: Grid layout (1fr 1fr on wide screens, stacked on mobile)
- `.comparison-file`: Container for each file column
- `.comparison-file-header`: Header with filename and AI score
- `.comparison-file-content`: Scrollable content area
- `.comparison-sentence`: Individual sentence blocks
- `.comparison-sentence.plagiarized`: Highlighted plagiarized sentences
- `.comparison-word.plagiarized`: Red background for plagiarized words
- `.plagiarism-match-info`: Match percentage indicator

**Compare Button:**
- `.btn-compare`: Gradient button, shows when 2+ files selected

#### Responsive Design
- On screens < 1200px: Comparison grid stacks to single column
- Mobile-optimized for file preview and comparison

---

## User Workflow

### 1. AI Analysis Flow
```
Lecturer → Student Works → Select Student 
→ Click File or "AI Analysis" button
→ Modal opens showing:
   - AI detection score
   - Detected phrases list
   - Sentence-level AI analysis with highlighted triggers
```

### 2. File Comparison Flow
```
Lecturer → Student Works → Select Student
→ Check 2+ file checkboxes → "Compare Selected Files" appears
→ Click button → Comparison modal opens with:
   - Side-by-side file content
   - Red-highlighted plagiarized words
   - Match percentages for detected plagiarism
```

---

## API Endpoints Used

### Existing Endpoints:
- `GET /api/student-works/students` - List students with uploads
- `GET /api/student-works/students/{id}/works` - Get student's files
- `GET /api/student-works/file/{fileId}` - Get file content for preview
- `GET /api/ai-details/{sessionId}/{filename}` - Get AI analysis (enhanced output required)

### New Endpoint:
- `GET /api/student-works/compare/{fileId1}/{fileId2}` - Compare files with word-level highlighting

---

## Implementation Details

### AI Highlighting Algorithm
1. Fetch `/api/ai-details/` endpoint for AI analysis
2. Parse `ai_analysis.matching_phrases` array
3. Use regex to highlight matching phrases in red within sentences
4. Display top phrases and first 15 analyzed sentences

### Plagiarism Highlighting Algorithm
1. Fetch `/api/student-works/compare/` endpoint
2. Uses existing `highlight_word_level()` function which returns:
   - Sentence-level plagiarism flags
   - Word-level plagiarism flags (boolean array)
   - Match percentages
3. Render words with `.plagiarism-word-highlight` class for red highlighting

### Security
- All HTML content is escaped using `escapeHtml()` utility
- File access validated: lecturers can access all files, students only their own
- Session-based authentication required for all endpoints

---

## Technical Stack

- **Backend:** Flask blueprint with SQLite
- **Frontend:** Vanilla JavaScript, Bootstrap 5 modals
- **Highlighting:** Existing `detect_ai_content()` and `highlight_word_level()` functions
- **Styling:** Custom CSS with responsive design

---

## Browser Compatibility

- Modern browsers with:
  - ES6+ JavaScript support
  - CSS Grid support
  - Fetch API support
  - Bootstrap 5 support

---

## Future Enhancements

1. Add export functionality for comparison reports
2. Add batch comparison of multiple files
3. Add annotation/note-taking on highlighted sections
4. Add similarity threshold customization
5. Add export to PDF for AI analysis and comparison reports
