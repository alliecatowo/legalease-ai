# Docling Document Parser Integration

## Overview

The Docling document parser integration provides comprehensive document parsing and OCR capabilities for the LegalEase backend. This implementation enables extraction of text, tables, images, and metadata from various document formats.

## Components

### 1. DoclingParser (`app/workers/pipelines/docling_parser.py`)

A robust document parser that extracts structured content from various document formats.

**Features:**
- Multi-format support: PDF, DOCX, DOC, TXT
- Text extraction with structure preservation
- Table detection and extraction
- Metadata extraction (title, author, dates, etc.)
- OCR fallback for scanned documents
- Automatic format detection

**Key Methods:**

```python
from app.workers.pipelines.docling_parser import DoclingParser

# Initialize parser
parser = DoclingParser(use_ocr=True)

# Parse document from bytes
with open('document.pdf', 'rb') as f:
    file_content = f.read()

result = parser.parse(
    file_content=file_content,
    filename='document.pdf'
)

# Access extracted data
text = result['text']                    # Full text
pages = result['pages']                  # List of page data
metadata = result['metadata']            # Document metadata
structure = result['structure']          # Document structure info
```

**Return Structure:**
```python
{
    'text': str,              # Full extracted text
    'pages': [                # List of pages (PDF only)
        {
            'page_number': int,
            'text': str,
            'char_count': int
        }
    ],
    'metadata': {             # Document metadata
        'page_count': int,
        'title': str,
        'author': str,
        'created': str,
        'modified': str,
        # ... other metadata
    },
    'structure': {            # Document structure
        'type': str,          # 'pdf', 'docx', 'text', etc.
        'paragraphs': list,   # DOCX paragraphs
        'tables': list,       # Extracted tables
    }
}
```

### 2. OCRPipeline (`app/workers/pipelines/ocr_pipeline.py`)

A tiered OCR system for extracting text from scanned documents and images.

**Features:**
- Automatic scanned document detection
- Tesseract OCR integration (primary)
- Pytesseract fallback support
- Confidence scoring
- Multi-page PDF support
- Image format support (JPG, PNG, TIFF, BMP)
- Configurable DPI and language

**Key Methods:**

```python
from app.workers.pipelines.ocr_pipeline import OCRPipeline

# Initialize OCR pipeline
ocr = OCRPipeline(
    language='eng',           # Language code
    dpi=300,                  # DPI for PDF to image conversion
    min_confidence=50.0       # Minimum confidence threshold
)

# Process a document
result = ocr.process('scanned_document.pdf')

# Check results
if result['success']:
    text = result['text']
    confidence = result['avg_confidence']
    pages = result['total_pages']
```

**Return Structure:**
```python
{
    'text': str,                    # Full OCR'd text
    'total_pages': int,             # Number of pages processed
    'successful_pages': int,        # Successfully processed pages
    'total_words': int,             # Total words extracted
    'avg_confidence': float,        # Average confidence score (0-100)
    'page_results': [               # Per-page results
        {
            'text': str,
            'page_num': int,
            'word_count': int,
            'confidence': float,
            'success': bool
        }
    ],
    'success': bool                 # Overall success status
}
```

**Supported Methods:**
- `detect_if_scanned(file_path)` - Detect if PDF is scanned
- `process_pdf(file_path)` - Process PDF with OCR
- `process_image(file_path)` - Process single image
- `process(file_path)` - Auto-detect and process

## Installation

Dependencies have been installed via `uv`:

```bash
cd /home/Allie/develop/legalease/backend
uv add pytesseract pillow pdf2image
```

**Installed packages:**
- `pytesseract>=0.3.13` - Python wrapper for Tesseract OCR
- `pillow>=11.3.0` - Image processing library
- `pdf2image>=1.17.0` - PDF to image conversion

**System Requirements:**

For OCR to work, you need Tesseract installed on your system:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

**Optional Dependencies:**

For enhanced PDF parsing:
```bash
uv add pymupdf  # PyMuPDF for advanced PDF features
uv add pypdf    # Fallback PDF parser
uv add python-docx  # For DOCX support
```

## Usage Examples

### Example 1: Parse a PDF Document

```python
from app.workers.pipelines.docling_parser import DoclingParser

parser = DoclingParser(use_ocr=True)

with open('contract.pdf', 'rb') as f:
    file_content = f.read()

result = parser.parse(
    file_content=file_content,
    filename='contract.pdf'
)

print(f"Extracted {len(result['text'])} characters")
print(f"Pages: {len(result['pages'])}")
print(f"Text preview: {result['text'][:200]}")
```

### Example 2: OCR a Scanned Document

```python
from app.workers.pipelines.ocr_pipeline import OCRPipeline

ocr = OCRPipeline(
    language='eng',
    dpi=300,
    min_confidence=60.0
)

result = ocr.process('scanned_contract.pdf')

if result['success']:
    print(f"Text: {result['text']}")
    print(f"Confidence: {result['avg_confidence']:.2f}%")
    print(f"Pages: {result['successful_pages']}/{result['total_pages']}")
else:
    print(f"Error: {result.get('error', 'Unknown error')}")
```

### Example 3: Extract Tables from DOCX

```python
from app.workers.pipelines.docling_parser import DoclingParser

parser = DoclingParser(use_ocr=False)

with open('report.docx', 'rb') as f:
    file_content = f.read()

result = parser.parse(
    file_content=file_content,
    filename='report.docx'
)

# Access tables
if 'tables' in result.get('structure', {}):
    for table in result['structure']['tables']:
        print(f"Table {table['index']}: {table['rows']}x{table['cols']}")
        for row in table['data']:
            print(row)
```

### Example 4: Detect and Handle Scanned Documents

```python
from app.workers.pipelines.ocr_pipeline import OCRPipeline

ocr = OCRPipeline()

# Detect if document is scanned
if ocr.detect_if_scanned('document.pdf'):
    print("Document is scanned, using OCR...")
    result = ocr.process('document.pdf')
else:
    print("Document has native text, using text extraction...")
    # Use DoclingParser instead
```

## Integration with LegalEase

### Using in Celery Tasks

```python
from app.workers.pipelines import DoclingParser, OCRPipeline
from celery import shared_task

@shared_task
def process_legal_document(file_id: str):
    """Process a legal document with parsing and OCR."""

    # Get file from storage (MinIO)
    file_content = get_file_from_storage(file_id)

    # Initialize parser with OCR support
    parser = DoclingParser(use_ocr=True)

    # Parse document
    result = parser.parse(
        file_content=file_content,
        filename=f"{file_id}.pdf"
    )

    # Store extracted text and metadata
    save_extracted_data(file_id, result)

    return {
        'file_id': file_id,
        'text_length': len(result['text']),
        'pages': len(result.get('pages', [])),
        'success': True
    }
```

### Document Processing Pipeline

```python
from app.workers.pipelines import DoclingParser, OCRPipeline

def create_document_processor(use_ocr: bool = True):
    """Factory function to create document processor."""
    return DoclingParser(use_ocr=use_ocr)

def process_document_workflow(file_path: str):
    """Complete document processing workflow."""

    # Step 1: Parse document
    parser = create_document_processor(use_ocr=True)

    with open(file_path, 'rb') as f:
        file_content = f.read()

    parsed = parser.parse(
        file_content=file_content,
        filename=file_path
    )

    # Step 2: Extract metadata
    metadata = parsed.get('metadata', {})

    # Step 3: Process text (chunking, embedding, etc.)
    text = parsed['text']

    # Step 4: Store in database
    # ... your storage logic

    return {
        'parsed': parsed,
        'metadata': metadata,
        'text': text
    }
```

## Testing

A test script is provided at `/home/Allie/develop/legalease/backend/test_docling_parser.py`:

```bash
# Run test script
python test_docling_parser.py
```

The test script demonstrates:
- OCR pipeline usage
- Docling parser usage
- Different document formats
- Error handling

## File Structure

```
/home/Allie/develop/legalease/backend/
   app/
      workers/
          pipelines/
              __init__.py                # Module exports
              docling_parser.py          # DoclingParser class
              ocr_pipeline.py            # OCRPipeline class
              embeddings.py              # Existing embedding pipeline
              bm25_encoder.py            # Existing BM25 encoder
   test_docling_parser.py                # Test script
   DOCLING_INTEGRATION.md                # This documentation
```

## Architecture Notes

### DoclingParser Design

The `DoclingParser` is designed with a layered approach:

1. **Format Detection**: Automatically detects file type from extension
2. **Parser Routing**: Routes to appropriate parser (PDF, DOCX, TXT)
3. **Primary Extraction**: Uses native libraries (PyMuPDF, python-docx)
4. **OCR Fallback**: Falls back to OCR for scanned content
5. **Structure Preservation**: Maintains document structure and metadata

### OCRPipeline Design

The `OCRPipeline` uses a tiered approach:

1. **Scanned Detection**: Heuristic detection of scanned documents
2. **Image Conversion**: Converts PDFs to high-DPI images
3. **Tesseract OCR**: Primary OCR using Tesseract engine
4. **Pytesseract Wrapper**: Python integration with confidence scoring
5. **Quality Filtering**: Filters results by confidence threshold

## Performance Considerations

### OCR Performance
- **DPI Setting**: Higher DPI (300-600) improves accuracy but increases processing time
- **Language Models**: Specify exact language for better accuracy
- **Confidence Threshold**: Adjust `min_confidence` to balance accuracy vs completeness
- **Multi-page Processing**: Consider parallel processing for large PDFs

### Memory Management
- Large PDFs can consume significant memory during image conversion
- Consider streaming or batch processing for very large documents
- Close file handles and clear image data after processing

### Optimization Tips
```python
# For large documents, use lower DPI
ocr = OCRPipeline(dpi=150)  # Faster but less accurate

# For high accuracy, use higher DPI and stricter confidence
ocr = OCRPipeline(dpi=600, min_confidence=70.0)

# For multi-language documents
ocr = OCRPipeline(language='eng+fra')  # English + French
```

## Error Handling

Both parsers include comprehensive error handling:

```python
try:
    result = parser.parse(file_content, filename)
    if result.get('success'):
        # Process result
        text = result['text']
    else:
        # Handle parsing failure
        error = result.get('error', 'Unknown error')
        logger.error(f"Parsing failed: {error}")
except Exception as e:
    logger.error(f"Exception during parsing: {e}")
    # Fallback or retry logic
```

## Future Enhancements

Potential improvements:
- [ ] Advanced table extraction with TableFormer
- [ ] Layout analysis using DocLayNet
- [ ] Figure/image caption extraction
- [ ] Multi-column text handling
- [ ] Form field detection
- [ ] Signature detection
- [ ] Redaction detection
- [ ] Quality scoring improvements
- [ ] Parallel page processing
- [ ] GPU acceleration for OCR

## Troubleshooting

### Common Issues

**1. Tesseract Not Found**
```
Error: pytesseract.pytesseract.TesseractNotFoundError
```
Solution: Install Tesseract OCR on your system (see Installation section)

**2. Low OCR Accuracy**
- Increase DPI: `OCRPipeline(dpi=600)`
- Adjust confidence threshold: `min_confidence=40.0`
- Verify correct language: `language='eng'`

**3. Memory Issues with Large PDFs**
- Reduce DPI: `OCRPipeline(dpi=150)`
- Process pages in batches
- Use streaming where possible

**4. Import Errors**
```
ModuleNotFoundError: No module named 'pytesseract'
```
Solution: Install dependencies: `uv add pytesseract pillow pdf2image`

## Support

For issues or questions:
- Check the test script: `test_docling_parser.py`
- Review the source code for detailed implementation
- Consult the logging output for debugging information

## License

Part of the LegalEase backend system.
