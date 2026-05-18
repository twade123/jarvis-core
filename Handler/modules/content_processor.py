"""
Content Processor — Image, PDF, and document handling for LLM inputs.

Extracted from handler_claude.py. Handles:
- Image loading, validation, optimization, and format conversion
- PDF text extraction (PyMuPDF, PyPDF2 fallback)
- Jupyter notebook reading
- Multimodal message content building
- Base64 encoding/decoding
- URL-based image processing

All functions are standalone — no ClaudeHandler dependency.
Works with any LLM backend (Anthropic multimodal, OpenAI vision, etc.)
"""

import base64
import io
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Supported file extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.svg'}
PDF_EXTENSIONS = {'.pdf'}
NOTEBOOK_EXTENSIONS = {'.ipynb'}
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.m',
    '.html', '.css', '.scss', '.less', '.xml', '.json', '.yaml', '.yml',
    '.toml', '.ini', '.cfg', '.conf', '.env', '.sh', '.bash', '.zsh',
    '.md', '.txt', '.rst', '.csv', '.tsv', '.sql', '.graphql',
    '.dockerfile', '.gitignore', '.editorconfig', '.prettierrc',
}

# Image size limits
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_IMAGE_DIMENSION = 8000  # pixels
ANTHROPIC_MAX_PIXELS = 1_568 * 1_568  # ~2.4M pixels


def is_image_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def is_pdf_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in PDF_EXTENSIONS


def is_notebook_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in NOTEBOOK_EXTENSIONS


def is_base64_string(s: str) -> bool:
    """Check if a string is valid base64."""
    if not s or len(s) < 20:
        return False
    try:
        pattern = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
        return bool(pattern.match(s[:100]))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def load_image_file(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Load an image file and return (base64_data, media_type).
    
    Validates size and format. Returns (None, None) on failure.
    """
    try:
        file_path = os.path.expanduser(file_path)
        if not os.path.exists(file_path):
            logger.error(f"Image not found: {file_path}")
            return None, None
        
        size = os.path.getsize(file_path)
        if size > MAX_IMAGE_BYTES:
            logger.error(f"Image too large: {size} bytes (max {MAX_IMAGE_BYTES})")
            return None, None
        
        ext = os.path.splitext(file_path)[1].lower()
        media_type_map = {
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
        }
        media_type = media_type_map.get(ext, 'image/png')
        
        with open(file_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode('utf-8')
        
        return data, media_type
    except Exception as e:
        logger.error(f"Error loading image {file_path}: {e}")
        return None, None


def optimize_image(image_data: bytes, max_size: int = MAX_IMAGE_BYTES, 
                   max_dimension: int = MAX_IMAGE_DIMENSION) -> bytes:
    """Optimize image size for API submission.
    
    Resizes and compresses if needed. Requires Pillow.
    Returns original bytes if Pillow not available.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data))
        
        # Resize if dimensions too large
        w, h = img.size
        if w > max_dimension or h > max_dimension:
            ratio = min(max_dimension / w, max_dimension / h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            logger.info(f"Resized image from {w}x{h} to {new_size[0]}x{new_size[1]}")
        
        # Check total pixel count (Anthropic limit)
        w, h = img.size
        if w * h > ANTHROPIC_MAX_PIXELS:
            ratio = (ANTHROPIC_MAX_PIXELS / (w * h)) ** 0.5
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Compress
        buf = io.BytesIO()
        fmt = 'PNG' if img.mode == 'RGBA' else 'JPEG'
        quality = 85
        img.save(buf, format=fmt, quality=quality, optimize=True)
        
        # If still too large, reduce quality
        while buf.tell() > max_size and quality > 20:
            quality -= 15
            buf = io.BytesIO()
            img.save(buf, format=fmt, quality=quality, optimize=True)
        
        return buf.getvalue()
    except ImportError:
        logger.warning("Pillow not available for image optimization")
        return image_data
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        return image_data


def validate_image_size(image_data: bytes) -> Dict[str, Any]:
    """Validate image dimensions and size for API compatibility.
    
    Returns {"valid": bool, "width": int, "height": int, "size_bytes": int, "issues": []}
    """
    result = {"valid": True, "issues": [], "size_bytes": len(image_data)}
    
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data))
        w, h = img.size
        result["width"] = w
        result["height"] = h
        
        if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
            result["issues"].append(f"Dimensions {w}x{h} exceed max {MAX_IMAGE_DIMENSION}")
            result["valid"] = False
        
        if w * h > ANTHROPIC_MAX_PIXELS:
            result["issues"].append(f"Pixel count {w*h:,} exceeds Anthropic limit {ANTHROPIC_MAX_PIXELS:,}")
            result["valid"] = False
    except ImportError:
        result["width"] = result["height"] = 0
        result["issues"].append("Pillow not available for dimension check")
    
    if len(image_data) > MAX_IMAGE_BYTES:
        result["issues"].append(f"Size {len(image_data):,} bytes exceeds max {MAX_IMAGE_BYTES:,}")
        result["valid"] = False
    
    return result


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(file_path: str, max_chars: int = 50000) -> str:
    """Extract text from PDF. Tries PyMuPDF first, falls back to PyPDF2."""
    file_path = os.path.expanduser(file_path)
    
    # Try PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(file_path)
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        if text.strip():
            return text[:max_chars]
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {file_path}: {e}")
    
    # Try PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text[:max_chars]
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"PyPDF2 failed for {file_path}: {e}")
    
    return f"[PDF file: {file_path} — install PyMuPDF or PyPDF2 to extract text]"


# ---------------------------------------------------------------------------
# Notebook reading
# ---------------------------------------------------------------------------

def read_notebook(file_path: str) -> str:
    """Read Jupyter notebook and return cell contents as text."""
    try:
        import json
        file_path = os.path.expanduser(file_path)
        with open(file_path) as f:
            nb = json.load(f)
        
        cells = nb.get('cells', [])
        parts = []
        for i, cell in enumerate(cells):
            cell_type = cell.get('cell_type', 'unknown')
            source = ''.join(cell.get('source', []))
            parts.append(f"# Cell {i+1} ({cell_type})\n{source}")
        
        return "\n\n".join(parts)
    except Exception as e:
        return f"Error reading notebook {file_path}: {e}"


# ---------------------------------------------------------------------------
# Text file reading
# ---------------------------------------------------------------------------

def read_text_file(file_path: str, limit: int = 200, offset: int = 0) -> str:
    """Read text file with optional line limit and offset."""
    try:
        file_path = os.path.expanduser(file_path)
        with open(file_path, 'r', errors='replace') as f:
            lines = f.readlines()
        
        total = len(lines)
        selected = lines[offset:offset + limit]
        text = ''.join(selected)
        
        if total > offset + limit:
            remaining = total - offset - limit
            text += f"\n[... {remaining} more lines. Use offset={offset+limit} to continue.]"
        
        return text
    except Exception as e:
        return f"Error reading {file_path}: {e}"


# ---------------------------------------------------------------------------
# Universal file reader
# ---------------------------------------------------------------------------

def read_file(file_path: str, limit: int = 200, offset: int = 0) -> str:
    """Read any supported file type and return text content.
    
    Routes to appropriate reader based on file extension.
    """
    file_path = os.path.expanduser(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in PDF_EXTENSIONS:
        return extract_pdf_text(file_path)
    elif ext in NOTEBOOK_EXTENSIONS:
        return read_notebook(file_path)
    elif ext in IMAGE_EXTENSIONS:
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        return f"[Image file: {file_path}, {size} bytes]"
    else:
        return read_text_file(file_path, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Multimodal message building (for LLMs with vision)
# ---------------------------------------------------------------------------

def build_multimodal_content(text: str, images: List[Dict] = None) -> List[Dict]:
    """Build multimodal message content for the API.
    
    Works with both Anthropic and OpenAI vision APIs.
    
    images: list of {"data": base64_str, "media_type": "image/png"} or {"url": "https://..."}
    
    Returns content blocks in Anthropic format. LLMRouter translates for OpenAI if needed.
    """
    content = []
    
    # Add images first
    if images:
        for img in images:
            if "data" in img:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("media_type", "image/png"),
                        "data": img["data"],
                    }
                })
            elif "url" in img:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": img["url"],
                    }
                })
    
    # Add text
    if text:
        content.append({"type": "text", "text": text})
    
    return content


def process_image_input(image_input: str) -> Optional[Dict]:
    """Process an image input (file path, URL, or base64) into API-ready format.
    
    Returns {"data": base64_str, "media_type": str} or {"url": str} or None.
    """
    if not image_input:
        return None
    
    # URL
    if image_input.startswith(('http://', 'https://')):
        return {"url": image_input}
    
    # File path
    if os.path.exists(os.path.expanduser(image_input)):
        data, media_type = load_image_file(image_input)
        if data:
            return {"data": data, "media_type": media_type}
        return None
    
    # Base64 string
    if is_base64_string(image_input):
        return {"data": image_input, "media_type": "image/png"}
    
    # Data URL
    if image_input.startswith('data:image/'):
        match = re.match(r'data:(image/\w+);base64,(.+)', image_input)
        if match:
            return {"data": match.group(2), "media_type": match.group(1)}
    
    return None
