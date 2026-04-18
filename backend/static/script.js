// DOM Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const analyzeBtn = document.getElementById('analyzeBtn');
const resultsSection = document.getElementById('resultsSection');
const loadingState = document.getElementById('loadingState');
const resultsContent = document.getElementById('resultsContent');
const errorState = document.getElementById('errorState');

let selectedFile = null;

// File Upload Handlers
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
        showError('Please select a valid image file (JPG, PNG, etc.)');
        return;
    }
    
    // Validate file size (max 50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size must be less than 50MB');
        return;
    }
    
    selectedFile = file;
    
    // Show file info
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'grid';
    analyzeBtn.style.display = 'flex';
    
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('previewImage').src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Analyze Image
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    analyzeBtn.disabled = true;
    resultsSection.style.display = 'block';
    loadingState.style.display = 'block';
    resultsContent.style.display = 'none';
    errorState.style.display = 'none';
    
    // Scroll to results
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
    try {
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const response = await fetch('/api/detect', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Analysis failed');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        console.error('Error:', error);
        showResultsError(error.message || 'An error occurred during analysis');
    } finally {
        analyzeBtn.disabled = false;
    }
});

function displayResults(data) {
    loadingState.style.display = 'none';
    resultsContent.style.display = 'block';
    errorState.style.display = 'none';
    
    // Update visualization
    document.getElementById('visualizationImage').src = data.visualization_url + `?t=${Date.now()}`;
    
    // Setup download button
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = data.visualization_url;
    downloadBtn.download = `vanishing_points_${data.file_id}.png`;
    
    // Update stats
    document.getElementById('linesCount').textContent = data.lines_detected;
    document.getElementById('vpCount').textContent = data.vanishing_points_count;
    document.getElementById('imageSize').textContent = 
        `${data.image_size.width}×${data.image_size.height}px`;
    
    // Update classification
    const classificationBadge = document.getElementById('classificationBadge');
    classificationBadge.textContent = data.analysis.classification;
    
    // Color code the classification badge based on VP count
    const classMap = {
        0: 'rgba(107, 114, 128, 0.2)',      // gray
        1: 'rgba(34, 197, 94, 0.2)',        // green
        2: 'rgba(59, 130, 246, 0.2)',       // blue
        3: 'rgba(239, 68, 68, 0.2)'         // red
    };
    
    const textColorMap = {
        0: '#6B7280',
        1: '#22C55E',
        2: '#3B82F6',
        3: '#EF4444'
    };
    
    const vpCount = Math.min(data.vanishing_points_count, 3);
    classificationBadge.style.background = classMap[vpCount];
    classificationBadge.style.color = textColorMap[vpCount];
    
    document.getElementById('classificationDescription').textContent = data.analysis.description;
    
    // Update vanishing points list
    if (data.vanishing_points.length > 0) {
        const vpDetails = document.getElementById('vanishingPointsDetails');
        vpDetails.style.display = 'block';
        
        const vpList = document.getElementById('vpList');
        vpList.innerHTML = data.vanishing_points.map((vp, idx) => `
            <div class="vp-item">
                <div class="vp-item-id">Vanishing Point ${vp.id}</div>
                <div class="vp-item-coords">Position: (${vp.x.toFixed(1)}, ${vp.y.toFixed(1)})</div>
                <div class="vp-item-sig">Significance: ${vp.significance} intersections</div>
            </div>
        `).join('');
    } else {
        document.getElementById('vanishingPointsDetails').style.display = 'none';
    }
}

function showResultsError(message) {
    loadingState.style.display = 'none';
    resultsContent.style.display = 'none';
    errorState.style.display = 'block';
    
    document.getElementById('errorMessage').textContent = message;
}

function showError(message) {
    alert(message);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check API health
    fetch('/api/health')
        .then(r => r.json())
        .then(data => console.log('API Status:', data))
        .catch(err => console.error('API Error:', err));
});
