"""
PMI OCR Module

OCR module to extract text from Presentation PMI images.

Supported OCR engines:
- EasyOCR (Recommended): GPU support, multi-language support
- Tesseract: Lightweight, widely used
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from PIL import Image

# OCR engine availability state
_EASYOCR_AVAILABLE = False
_TESSERACT_AVAILABLE = False

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    pass


@dataclass
class OcrResult:
    """OCR Result"""
    text: str  # Recognized text
    confidence: float  # Confidence (0.0-1.0)
    bbox: Optional[Tuple[int, int, int, int]] = None  # Bounding box (x1, y1, x2, y2)
    
    def __str__(self) -> str:
        return f"{self.text} ({self.confidence:.1%})"


@dataclass
class PmiOcrResult:
    """PMI OCR Result"""
    pmi_name: str  # PMI Name
    pmi_type: str  # PMI Type
    results: List[OcrResult] = field(default_factory=list)
    full_text: str = ""  # Combined text
    
    @property
    def avg_confidence(self) -> float:
        """Average confidence"""
        if not self.results:
            return 0.0
        return sum(r.confidence for r in self.results) / len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pmi_name': self.pmi_name,
            'pmi_type': self.pmi_type,
            'full_text': self.full_text,
            'avg_confidence': self.avg_confidence,
            'results': [
                {'text': r.text, 'confidence': r.confidence}
                for r in self.results
            ]
        }


class PmiOcr:
    """
    OCR class to extract text from PMI images.
    
    Example:
        from presentation_pmi_image_converter import PresentationPmiImageConverter
        from pmi_ocr import PmiOcr
        
        converter = PresentationPmiImageConverter(reader)
        ocr = PmiOcr(engine='easyocr')
        
        img = converter.convert_to_image('Note (256)')
        result = ocr.recognize(img)
        print(result.full_text)
    """
    
    # Recommended presets
    RECOMMENDED_PRESETS = ['ocr_small', 'ocr', 'ocr_large']
    
    def __init__(
        self, 
        engine: str = 'auto',
        languages: List[str] = None,
        gpu: bool = False,
        image_preset: str = 'ocr'
    ):
        """
        Args:
            engine: OCR engine ('auto', 'easyocr', 'tesseract')
            languages: List of languages to recognize (e.g., ['en'], ['en', 'ja'])
            gpu: Whether to use GPU with EasyOCR
            image_preset: Image size preset ('ocr_small', 'ocr', 'ocr_large', 'display', 'thumbnail')
        """
        self.engine = self._select_engine(engine)
        self.languages = languages or ['en']
        self.gpu = gpu
        self.image_preset = image_preset
        self._reader = None  # EasyOCR reader (lazy initialization)
    
    def _select_engine(self, engine: str) -> str:
        """Select available engine"""
        if engine == 'auto':
            if _EASYOCR_AVAILABLE:
                return 'easyocr'
            elif _TESSERACT_AVAILABLE:
                return 'tesseract'
            else:
                raise ImportError(
                    "OCR engine not found."
                    "Please run `pip install easyocr` or `pip install pytesseract`."
                )
        elif engine == 'easyocr':
            if not _EASYOCR_AVAILABLE:
                raise ImportError("Please run `pip install easyocr`.")
            return 'easyocr'
        elif engine == 'tesseract':
            if not _TESSERACT_AVAILABLE:
                raise ImportError("Please run `pip install pytesseract`.")
            return 'tesseract'
        else:
            raise ValueError(f"Unknown engine: {engine}")
    
    def _get_easyocr_reader(self):
        """Get EasyOCR reader (lazy initialization)"""
        if self._reader is None:
            self._reader = easyocr.Reader(self.languages, gpu=self.gpu)
        return self._reader
    
    def recognize(
        self, 
        image: Image.Image,
        preprocess: bool = True
    ) -> List[OcrResult]:
        """
        Recognize text from image.
        
        Args:
            image: PIL Image object
            preprocess: Whether to perform preprocessing
            
        Returns:
            List of OcrResult
        """
        if preprocess:
            image = self._preprocess(image)
        
        if self.engine == 'easyocr':
            return self._recognize_easyocr(image)
        else:
            return self._recognize_tesseract(image)
    
    def _preprocess(self, image: Image.Image) -> Image.Image:
        """Preprocessing for OCR"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast (optional)
        # If invert is needed:
        # from PIL import ImageOps
        # image = ImageOps.invert(image)
        
        return image
    
    def _recognize_easyocr(self, image: Image.Image) -> List[OcrResult]:
        """Recognize with EasyOCR"""
        import numpy as np
        
        reader = self._get_easyocr_reader()
        
        # Convert PIL Image to NumPy array
        img_array = np.array(image)
        
        # Execute recognition
        results = reader.readtext(img_array)
        
        ocr_results = []
        for (bbox, text, confidence) in results:
            # bbox is in [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] format
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            rect_bbox = (
                int(min(x_coords)),
                int(min(y_coords)),
                int(max(x_coords)),
                int(max(y_coords))
            )
            ocr_results.append(OcrResult(
                text=text,
                confidence=confidence,
                bbox=rect_bbox
            ))
        
        return ocr_results
    
    def _recognize_tesseract(self, image: Image.Image) -> List[OcrResult]:
        """Recognize with Tesseract"""
        # Convert language code to Tesseract format
        lang = '+'.join(self.languages)
        
        # Get detailed data
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        
        ocr_results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            conf = data['conf'][i]
            if conf == -1:
                conf = 0
            confidence = conf / 100.0
            
            bbox = (
                data['left'][i],
                data['top'][i],
                data['left'][i] + data['width'][i],
                data['top'][i] + data['height'][i]
            )
            
            ocr_results.append(OcrResult(
                text=text,
                confidence=confidence,
                bbox=bbox
            ))
        
        return ocr_results
    
    def recognize_pmi(
        self,
        converter,  # PresentationPmiImageConverter
        pmi_name: str,
        preset: Optional[str] = None,
        **image_kwargs
    ) -> PmiOcrResult:
        """
        Generate image from PMI and execute OCR.
        
        Args:
            converter: PresentationPmiImageConverter instance
            pmi_name: PMI name
            preset: Image size preset ('ocr_small', 'ocr', 'ocr_large', etc.)
            **image_kwargs: Options passed to convert_to_image
            
        Returns:
            PmiOcrResult
        """
        # Use default if preset is not specified
        if preset is None:
            preset = self.image_preset
        
        # Extract PMI type
        import re
        match = re.match(r'^([A-Za-z\s]+)\s*\(\d+\)', pmi_name)
        pmi_type = match.group(1).strip() if match else pmi_name
        
        # Generate image
        image = converter.convert_to_image(pmi_name, preset=preset, **image_kwargs)
        if image is None:
            return PmiOcrResult(pmi_name=pmi_name, pmi_type=pmi_type)
        
        # Execute OCR
        results = self.recognize(image)
        
        # Combine text (Left to right, Top to bottom)
        sorted_results = sorted(results, key=lambda r: (r.bbox[1] if r.bbox else 0, r.bbox[0] if r.bbox else 0))
        full_text = ' '.join(r.text for r in sorted_results)
        
        return PmiOcrResult(
            pmi_name=pmi_name,
            pmi_type=pmi_type,
            results=results,
            full_text=full_text
        )
    
    def recognize_all_pmi(
        self,
        converter,  # PresentationPmiImageConverter
        preset: Optional[str] = None,
        **image_kwargs
    ) -> List[PmiOcrResult]:
        """
        Execute OCR for all PMI.
        
        Args:
            converter: PresentationPmiImageConverter instance
            preset: Image size preset ('ocr_small', 'ocr', 'ocr_large', etc.)
            **image_kwargs: Options passed to convert_to_image
            
        Returns:
            List of PmiOcrResult
        """
        results = []
        for group in converter.list_pmi_groups():
            result = self.recognize_pmi(converter, group.name, preset=preset, **image_kwargs)
            results.append(result)
        return results


def check_ocr_availability() -> Dict[str, bool]:
    """Check OCR engine availability"""
    return {
        'easyocr': _EASYOCR_AVAILABLE,
        'tesseract': _TESSERACT_AVAILABLE,
    }


if __name__ == '__main__':
    import sys
    
    # Check OCR engines
    print("OCR Engine Status:")
    for engine, available in check_ocr_availability().items():
        status = "✓ Available" if available else "✗ Not Installed"
        print(f"  {engine}: {status}")
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python pmi_ocr.py <STEP_FILE>")
        print("  python pmi_ocr.py <STEP_FILE> <PMI_NAME>")
        print("  python pmi_ocr.py <STEP_FILE> --all")
        sys.exit(0)
    
    from step_reader import StepReader
    from presentation_pmi_image_converter import PresentationPmiImageConverter
    
    step_file = Path(sys.argv[1])
    
    print(f"\nLoading STEP file: {step_file}")
    reader = StepReader(step_file)
    reader.load()
    
    converter = PresentationPmiImageConverter(reader)
    ocr = PmiOcr(engine='auto')
    
    print(f"OCR Engine: {ocr.engine}")
    
    if len(sys.argv) == 2:
        # List PMI Groups
        print("\nPMI Groups:")
        for group in converter.list_pmi_groups()[:10]:
            print(f"  {group.name}")
        print("  ...")
        print(f"\nExample: python pmi_ocr.py {sys.argv[1]} \"Note (256)\"")
    
    elif sys.argv[2] == '--all':
        # OCR all PMI
        print("\nProcessing all PMI with OCR...")
        results = ocr.recognize_all_pmi(converter)
        
        for result in results:
            if result.full_text:
                print(f"\n[{result.pmi_name}]")
                print(f"  Text: {result.full_text}")
                print(f"  Confidence: {result.avg_confidence:.1%}")
    
    else:
        # OCR specified PMI
        pmi_name = sys.argv[2]
        print(f"\nProcessing PMI '{pmi_name}' with OCR...")
        
        result = ocr.recognize_pmi(converter, pmi_name)
        
        if result.results:
            print(f"\nRecognition Results:")
            for r in result.results:
                print(f"  {r}")
            print(f"\nCombined Text: {result.full_text}")
            print(f"Average Confidence: {result.avg_confidence:.1%}")
        else:
            print("No text recognized")
