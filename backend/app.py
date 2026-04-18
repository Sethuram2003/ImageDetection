import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from fastapi.requests import Request
from starlette.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from PIL import Image
import io

# Add parent directory to path to import VanishingPointDetector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test import VanishingPointDetector

# Initialize FastAPI app
app = FastAPI(
    title="ImageDetection - Vanishing Point Detector",
    description="Detect vanishing points in images to analyze geometric consistency",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = UPLOAD_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Allowed file extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.get("/")
async def root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/detect")
async def detect_vanishing_points(file: UploadFile = File(...)):
    """
    API endpoint to detect vanishing points in an uploaded image.
    
    Args:
        file: Image file to analyze
        
    Returns:
        JSON with analysis results and visualization URL
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower()
        saved_filename = f"{file_id}{file_ext}"
        saved_path = UPLOAD_DIR / saved_filename
        
        # Save uploaded file
        contents = await file.read()
        with open(saved_path, "wb") as f:
            f.write(contents)
        
        # Run detection
        try:
            detector = VanishingPointDetector(str(saved_path))
            results = detector.detect(visualize=True, save_visualization=str(OUTPUT_DIR / f"{file_id}_visualization.png"))
            
            # Prepare response
            response_data = {
                "status": "success",
                "file_id": file_id,
                "original_filename": file.filename,
                "image_size": {
                    "width": detector.width,
                    "height": detector.height
                },
                "lines_detected": results["lines_detected"],
                "vanishing_points_count": results["vp_count"],
                "vanishing_points": [
                    {
                        "id": i + 1,
                        "x": float(vp[0][0]),
                        "y": float(vp[0][1]),
                        "significance": int(vp[1])
                    }
                    for i, vp in enumerate(results["vanishing_points_scored"])
                ],
                "analysis": {
                    "classification": _classify_image(results["vp_count"]),
                    "description": _get_description(results["vp_count"])
                },
                "visualization_url": f"/api/visualization/{file_id}",
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse(content=response_data)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@app.get("/api/visualization/{file_id}")
async def get_visualization(file_id: str):
    """
    Retrieve the visualization PNG for a processed image.
    
    Args:
        file_id: Unique identifier for the processed image
        
    Returns:
        PNG image file
    """
    vis_path = OUTPUT_DIR / f"{file_id}_visualization.png"
    
    if not vis_path.exists():
        raise HTTPException(status_code=404, detail="Visualization not found")
    
    return FileResponse(path=vis_path, media_type="image/png")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ImageDetection Vanishing Point Detector",
        "version": "1.0.0"
    }


def _classify_image(vp_count: int) -> str:
    """Classify image based on vanishing point count"""
    if vp_count == 0:
        return "No Clear Structure"
    elif vp_count == 1:
        return "Single Perspective (Real Photo Likely)"
    elif vp_count == 2:
        return "Multi-Point Perspective"
    else:
        return "Complex/Suspicious Geometry"


def _get_description(vp_count: int) -> str:
    """Get detailed description based on VP count"""
    descriptions = {
        0: "Scene lacks strong converging parallel lines. May be natural/organic.",
        1: "Strong, clean geometric structure typical of single-perspective real scenes (roads, corridors).",
        2: "Clear geometric structure with two-point perspective (street corners, buildings).",
        3: "Complex geometric scene or potential inconsistencies (empirically more common in AI-generated images)."
    }
    return descriptions.get(vp_count, descriptions[3])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
