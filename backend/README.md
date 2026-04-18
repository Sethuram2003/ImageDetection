# ImageDetection Backend - FastAPI Application

Professional FastAPI backend for the Vanishing Point Detection system with an interactive web frontend.

## Features

✨ **Core Features**
- RESTful API for vanishing point detection
- Interactive web dashboard
- Real-time image analysis
- Beautiful, responsive UI
- Drag-and-drop file upload
- High-quality PNG visualizations
- Classification results and detailed metrics

🚀 **Technical Stack**
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Frontend**: Vanilla JavaScript + HTML5 + CSS3
- **Image Processing**: OpenCV, NumPy, scikit-learn
- **Visualization**: Matplotlib

## Installation

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Setup Steps

1. **Activate virtual environment** (from project root)
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Start the Server
```bash
cd /Users/sethuramgauthamr/Documents/Projects/ImageDetection/backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Access the Application
Open your browser and navigate to:
```
http://localhost:8000
```

## API Endpoints

### Frontend
- **GET** `/` - Main dashboard page

### Analysis
- **POST** `/api/detect` - Analyze image for vanishing points
  - **Parameter**: `file` (multipart image file)
  - **Returns**: JSON with analysis results
  
  **Response Example:**
  ```json
  {
    "status": "success",
    "file_id": "abc123def456",
    "image_size": {"width": 1920, "height": 1440},
    "lines_detected": 45,
    "vanishing_points_count": 2,
    "vanishing_points": [
      {
        "id": 1,
        "x": 960.5,
        "y": 720.3,
        "significance": 18
      },
      {
        "id": 2,
        "x": -150.2,
        "y": 580.1,
        "significance": 12
      }
    ],
    "analysis": {
      "classification": "Multi-Point Perspective",
      "description": "Clear geometric structure with two-point perspective..."
    },
    "visualization_url": "/api/visualization/abc123def456",
    "timestamp": "2024-04-16T10:30:00"
  }
  ```

- **GET** `/api/visualization/{file_id}` - Retrieve the analysis visualization PNG

### Health
- **GET** `/api/health` - Health check endpoint

## Project Structure

```
backend/
├── app.py                      # FastAPI application
├── templates/
│   └── index.html             # Frontend HTML
├── static/
│   ├── style.css              # Styling
│   └── script.js              # Frontend logic
├── uploads/                   # Uploaded images
│   └── outputs/               # Generated visualizations
└── README.md                  # This file
```

## Configuration

### Allowed File Types
- `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.tiff`

### File Size Limit
- Maximum 50MB per upload

### Upload Directory
- Images are stored in `backend/uploads/`
- Visualizations are saved to `backend/uploads/outputs/`
- Files are automatically cleaned up (keep only recent analyses)

## API Usage Examples

### cURL
```bash
# Analyze an image
curl -X POST -F "file=@/path/to/image.jpg" http://localhost:8000/api/detect

# Get visualization
curl http://localhost:8000/api/visualization/file_id > visualization.png

# Health check
curl http://localhost:8000/api/health
```

### Python
```python
import requests

# Analyze image
with open('image.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/detect',
        files={'file': f}
    )
    results = response.json()
    print(f"Detected {results['vanishing_points_count']} vanishing points")

# Download visualization
viz_response = requests.get(
    f"http://localhost:8000/api/visualization/{results['file_id']}"
)
with open('visualization.png', 'wb') as f:
    f.write(viz_response.content)
```

### JavaScript/Fetch
```javascript
// Analyze image
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/detect', {
    method: 'POST',
    body: formData
});

const results = await response.json();
```

## Understanding Results

### Vanishing Point Count
- **0 VPs**: No clear structure (organic/natural scenes)
- **1 VP**: Strong single perspective (typical of real photographs)
- **2 VPs**: Multi-point perspective (architectural photos)
- **3+ VPs**: Complex geometry or potential AI artifacts

### Significance Score
- Represents the number of line intersections at that vanishing point
- Higher values indicate stronger, more reliable convergence points
- Used for filtering out weak/spurious detections

### Classification
- **Single Perspective (Real Photo Likely)**: 1 clear VP
- **Multi-Point Perspective**: 2 VPs (common in buildings/corners)
- **Complex/Suspicious Geometry**: 3+ VPs (empirically more common in AI)

## Troubleshooting

### Port Already in Use
```bash
# Kill existing process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
python -m uvicorn app:app --port 8001
```

### Module Not Found
```bash
# Ensure requirements are installed
pip install -r requirements.txt

# Verify venv is activated
which python
```

### Image Upload Issues
- Check file format (must be valid image)
- Ensure file size is under 50MB
- Try a different image if one fails

### Slow Analysis
- Large images are automatically scaled to 1200px max dimension
- Complex images with many lines take longer
- Consider using smaller/simpler test images

## Development

### Running with Auto-Reload
```bash
python -m uvicorn app:app --reload
```

### Accessing API Documentation
FastAPI provides automatic API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Testing
```bash
# Test the API directly
curl http://localhost:8000/api/health
```

## Performance

### Typical Analysis Times
- Small image (< 500px): ~500ms
- Medium image (500-1200px): ~1-2s
- Large image (> 1200px, auto-scaled): ~2-5s

### Memory Usage
- Base application: ~150-200MB
- Per concurrent request: ~50-100MB
- Temporary file cleanup: Automatic

## Security

### CORS
- Currently allows all origins (for development)
- Restrict in production: `allow_origins=["yourdomain.com"]`

### File Validation
- File type checking (MIME type)
- File size limits (50MB max)
- Filename sanitization

### Uploaded Files
- Stored in isolated `uploads/` directory
- Auto-cleanup recommended for production
- Not served directly (controlled access)

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

### Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables (Planned)
- `UPLOAD_DIR`: Custom upload directory
- `MAX_FILE_SIZE`: Maximum upload size
- `ALLOWED_ORIGINS`: CORS whitelist

## Future Enhancements

🔄 **Planned Features**
- Batch processing endpoint
- Export results to CSV/JSON
- WebSocket for real-time progress
- Image comparison tool
- Advanced filtering options
- User session management
- Analytics dashboard

## License

This project is part of the ImageDetection suite. See parent repository for details.

## Support

For issues or questions:
1. Check this README
2. Review API documentation at `/docs`
3. Check logs from uvicorn output
4. Verify all dependencies are installed
