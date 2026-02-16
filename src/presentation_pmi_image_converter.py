"""
Presentation PMI Image Converter

Module for converting Presentation PMI polyline data to Pillow images.

Presentation PMI includes elements such as:
- Notes (Note, General Note, Balloon Note)
- Feature Control Frames (Geometric Tolerance Frames)
- Dimensions
- Material Specifications
- Enterprise Identifiers
- Part Identifiers
- etc.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise ImportError("Pillow is required. Please install it with `pip install Pillow`.")

from step_reader import StepReader
from step_pmi import PolylineData


# =============================================================================
# Image Size Presets
# =============================================================================

@dataclass
class ImageSizePreset:
    """Image size preset configuration"""
    name: str
    pixels_per_unit: float
    min_size: Tuple[int, int]
    max_size: Tuple[int, int]
    padding: int
    line_width: int
    description: str = ""


# Defined presets
IMAGE_PRESETS: Dict[str, ImageSizePreset] = {
    # OCR optimized (small)
    'ocr_small': ImageSizePreset(
        name='ocr_small',
        pixels_per_unit=100.0,
        min_size=(50, 30),
        max_size=(2000, 1500),
        padding=5,
        line_width=1,
        description='For OCR (Small size)'
    ),
    # OCR optimized (standard)
    'ocr': ImageSizePreset(
        name='ocr',
        pixels_per_unit=200.0,
        min_size=(80, 40),
        max_size=(4000, 3000),
        padding=10,
        line_width=2,
        description='For OCR (Standard)'
    ),
    # OCR optimized (large)
    'ocr_large': ImageSizePreset(
        name='ocr_large',
        pixels_per_unit=300.0,
        min_size=(100, 50),
        max_size=(6000, 4500),
        padding=15,
        line_width=2,
        description='For OCR (Large size)'
    ),
    # For display (high resolution)
    'display': ImageSizePreset(
        name='display',
        pixels_per_unit=500.0,
        min_size=(100, 50),
        max_size=(4000, 2000),
        padding=20,
        line_width=2,
        description='For Display (High Resolution)'
    ),
    # Thumbnail
    'thumbnail': ImageSizePreset(
        name='thumbnail',
        pixels_per_unit=50.0,
        min_size=(30, 20),
        max_size=(200, 100),
        padding=3,
        line_width=1,
        description='Thumbnail'
    ),
}


def get_preset(name: str) -> ImageSizePreset:
    """Get preset"""
    if name not in IMAGE_PRESETS:
        available = ', '.join(IMAGE_PRESETS.keys())
        raise ValueError(f"Unknown preset: {name}. Available: {available}")
    return IMAGE_PRESETS[name]


def list_presets() -> List[ImageSizePreset]:
    """List all presets"""
    return list(IMAGE_PRESETS.values())


@dataclass
class Point2D:
    """2D Point"""
    x: float
    y: float


@dataclass
class BoundingBox:
    """Bounding Box"""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
    
    @property
    def center(self) -> Point2D:
        return Point2D(
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2
        )


@dataclass
class Stroke:
    """Coordinate data for one polyline (stroke)"""
    polyline_id: int
    name: str = ""
    points: List[Point2D] = field(default_factory=list)
    
    @property
    def point_count(self) -> int:
        return len(self.points)
    
    @property
    def bounding_box(self) -> Optional[BoundingBox]:
        if not self.points:
            return None
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))


@dataclass
class PmiGroup:
    """Group of PMI elements with the same name"""
    name: str  # PMI name (e.g., 'Note (256)', 'Feature Control Frame (14)')
    pmi_type: str  # PMI type (e.g., 'Note', 'Feature Control Frame')
    polyline_ids: List[int] = field(default_factory=list)
    polyline_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'pmi_type': self.pmi_type,
            'polyline_count': self.polyline_count,
        }


class PresentationPmiImageConverter:
    """
    Class to convert Presentation PMI polyline data to Pillow images.
    
    Detects appropriate 2D planes from STEP file 3D coordinates and
    renders polylines as images.
    """
    
    # Pattern to extract PMI type
    # e.g., 'Feature Control Frame (14)' -> 'Feature Control Frame'
    #       'Note (256)' -> 'Note'
    #       'General Note (146) "General Note"' -> 'General Note'
    PMI_TYPE_PATTERN = re.compile(r'^([A-Za-z\s]+)\s*\(\d+\)')
    
    def __init__(self, reader: StepReader):
        """
        Args:
            reader: Loaded StepReader
        """
        self.reader = reader
        self._coord_pattern = re.compile(
            r'\(\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*,\s*([-\d.eE+]+)\s*\)'
        )
    
    def list_pmi_groups(self) -> List[PmiGroup]:
        """
        List unique PMI groups in Presentation PMI.
        
        Returns:
            List of PmiGroups (sorted by number of polylines descending)
        """
        groups: Dict[str, PmiGroup] = {}
        
        for polyline in self.reader.pmi.presentation.polylines:
            name = polyline.name
            if not name:
                continue
            
            if name not in groups:
                # Extract PMI type
                pmi_type = self._extract_pmi_type(name)
                groups[name] = PmiGroup(
                    name=name,
                    pmi_type=pmi_type,
                )
            
            groups[name].polyline_ids.append(polyline.entity_id)
            groups[name].polyline_count += 1
        
        # Sort by number of polylines
        return sorted(groups.values(), key=lambda g: -g.polyline_count)
    
    def list_pmi_types(self) -> Dict[str, int]:
        """
        Get number of groups per PMI type.
        
        Returns:
            Dictionary {PMI type: number of groups}
        """
        groups = self.list_pmi_groups()
        type_counts: Dict[str, int] = {}
        for g in groups:
            type_counts[g.pmi_type] = type_counts.get(g.pmi_type, 0) + 1
        return dict(sorted(type_counts.items(), key=lambda x: -x[1]))
    
    def _extract_pmi_type(self, name: str) -> str:
        """Extract type from PMI name"""
        match = self.PMI_TYPE_PATTERN.match(name)
        if match:
            return match.group(1).strip()
        return name
    
    def get_polyline_ids_by_name(self, pmi_name: str) -> List[int]:
        """
        Get polyline IDs belonging to a specific PMI name.
        
        Args:
            pmi_name: PMI name (e.g., 'Note (256)')
            
        Returns:
            List of polyline IDs
        """
        return [
            p.entity_id
            for p in self.reader.pmi.presentation.polylines
            if p.name == pmi_name
        ]
    
    def get_polyline_ids_by_type(self, pmi_type: str) -> List[int]:
        """
        Get all polyline IDs belonging to a specific PMI type.
        
        Args:
            pmi_type: PMI type (e.g., 'Note', 'Feature Control Frame')
            
        Returns:
            List of polyline IDs
        """
        ids = []
        for p in self.reader.pmi.presentation.polylines:
            if self._extract_pmi_type(p.name) == pmi_type:
                ids.append(p.entity_id)
        return ids
    
    def extract_strokes(self, polyline_ids: List[int]) -> List[Stroke]:
        """
        Extract coordinate data from specified polyline IDs.
        
        Automatically detects major 2D planes from 3D coordinates and converts to Point2D.
        
        Args:
            polyline_ids: Polyline entity IDs to extract
            
        Returns:
            List of Strokes
        """
        # Convert to ID set (for fast lookup)
        id_set = set(polyline_ids)
        
        # Get target polylines
        polylines = [
            p for p in self.reader.pmi.presentation.polylines
            if p.entity_id in id_set
        ]
        
        if not polylines:
            return []
        
        # First collect all coordinates to determine major plane
        all_3d_points: List[Tuple[float, float, float]] = []
        for polyline in polylines:
            for pid in polyline.point_ids:
                point_3d = self._get_cartesian_point(pid)
                if point_3d:
                    all_3d_points.append(point_3d)
        
        if not all_3d_points:
            return []
        
        # Detect major plane (exclude axis with minimum variance)
        plane_axes = self._detect_plane(all_3d_points)
        
        # Convert each polyline to Stroke
        strokes: List[Stroke] = []
        for polyline in polylines:
            stroke = Stroke(polyline_id=polyline.entity_id, name=polyline.name)
            for pid in polyline.point_ids:
                point_3d = self._get_cartesian_point(pid)
                if point_3d:
                    # Project to detected plane
                    point_2d = self._project_to_2d(point_3d, plane_axes)
                    stroke.points.append(point_2d)
            if stroke.points:
                strokes.append(stroke)
        
        return strokes
    
    def _get_cartesian_point(self, entity_id: int) -> Optional[Tuple[float, float, float]]:
        """Get CARTESIAN_POINT coordinates from entity ID"""
        if entity_id not in self.reader.data:
            return None
        
        data = self.reader.data[entity_id]
        match = self._coord_pattern.search(data)
        if match:
            return (
                float(match.group(1)),
                float(match.group(2)),
                float(match.group(3))
            )
        return None
    
    def _detect_plane(self, points: List[Tuple[float, float, float]]) -> Tuple[int, int]:
        """
        Detect major 2D plane axis indices from 3D point cloud.
        
        Excludes the axis with minimum variance and returns the remaining 2 axes.
        
        Returns:
            (x_axis_index, y_axis_index) - 0=X, 1=Y, 2=Z
        """
        if not points:
            return (0, 1)  # Default is X-Y plane
        
        # Calculate variance for each axis
        variances = []
        for axis in range(3):
            values = [p[axis] for p in points]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            variances.append(variance)
        
        # Exclude axis with minimum variance
        min_variance_axis = variances.index(min(variances))
        
        # Return remaining 2 axes (preserve order)
        axes = [i for i in range(3) if i != min_variance_axis]
        return (axes[0], axes[1])
    
    def _project_to_2d(
        self, 
        point_3d: Tuple[float, float, float], 
        plane_axes: Tuple[int, int]
    ) -> Point2D:
        """Project 3D point to specified plane"""
        return Point2D(
            x=point_3d[plane_axes[0]],
            y=point_3d[plane_axes[1]]
        )
    
    def calculate_image_size(
        self,
        strokes: List[Stroke],
        pixels_per_unit: float = 500.0,
        min_size: Tuple[int, int] = (100, 50),
        max_size: Tuple[int, int] = (4000, 2000),
        padding: int = 20,
        preset: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Calculate appropriate image size from stroke data.
        
        Args:
            strokes: List of Strokes
            pixels_per_unit: Pixels per coordinate unit (resolution)
            min_size: Minimum image size (width, height)
            max_size: Maximum image size (width, height)
            padding: Padding in pixels
            preset: Preset name ('ocr_small', 'ocr', 'ocr_large', 'display', 'thumbnail')
            
        Returns:
            Tuple of (width, height)
        """
        # Use preset if specified
        if preset:
            p = get_preset(preset)
            pixels_per_unit = p.pixels_per_unit
            min_size = p.min_size
            max_size = p.max_size
            padding = p.padding
        
        if not strokes:
            return min_size
        
        # Calculate bounding box for all strokes
        all_points: List[Point2D] = []
        for stroke in strokes:
            all_points.extend(stroke.points)
        
        if not all_points:
            return min_size
        
        xs = [p.x for p in all_points]
        ys = [p.y for p in all_points]
        bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
        
        # Calculate pixel size from coordinate range
        width = int(bbox.width * pixels_per_unit) + 2 * padding
        height = int(bbox.height * pixels_per_unit) + 2 * padding
        
        # Clamp between min and max size
        width = max(min_size[0], min(max_size[0], width))
        height = max(min_size[1], min(max_size[1], height))
        
        return (width, height)
    
    def strokes_to_image(
        self,
        strokes: List[Stroke],
        image_size: Optional[Tuple[int, int]] = None,
        auto_size: bool = True,
        pixels_per_unit: float = 500.0,
        padding: int = 20,
        line_width: int = 2,
        background_color: int = 255,
        line_color: int = 0,
        flip_y: bool = True,
        preset: Optional[str] = None
    ) -> Image.Image:
        """
        Convert stroke data to Pillow image.
        
        Args:
            strokes: List of Strokes
            image_size: Output image size (width, height). Auto-calculated if None
            auto_size: If True, automatically calculate image size based on data size
            pixels_per_unit: Pixels per coordinate unit (used when auto_size=True)
            padding: Padding in pixels
            line_width: Line width
            background_color: Background color (0-255, grayscale)
            line_color: Line color (0-255, grayscale)
            flip_y: Whether to flip Y axis (correct for coordinate system differences)
            preset: Preset name ('ocr_small', 'ocr', 'ocr_large', 'display', 'thumbnail')
            
        Returns:
            PIL Image object
        """
        # Use preset if specified
        if preset:
            p = get_preset(preset)
            pixels_per_unit = p.pixels_per_unit
            padding = p.padding
            line_width = p.line_width
        
        # Determine image size
        if image_size is None or auto_size:
            image_size = self.calculate_image_size(
                strokes, 
                pixels_per_unit=pixels_per_unit,
                padding=padding,
                preset=preset
            )
        if not strokes:
            return Image.new('L', image_size, background_color)
        
        # Calculate bounding box for all strokes
        all_points: List[Point2D] = []
        for stroke in strokes:
            all_points.extend(stroke.points)
        
        if not all_points:
            return Image.new('L', image_size, background_color)
        
        xs = [p.x for p in all_points]
        ys = [p.y for p in all_points]
        bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))
        
        # Create image
        img = Image.new('L', image_size, background_color)
        draw = ImageDraw.Draw(img)
        
        # Drawing area (considering padding)
        draw_width = image_size[0] - 2 * padding
        draw_height = image_size[1] - 2 * padding
        
        if draw_width <= 0 or draw_height <= 0:
            return img
        
        # Calculate scale (preserve aspect ratio)
        scale_x = draw_width / bbox.width if bbox.width > 0 else 1
        scale_y = draw_height / bbox.height if bbox.height > 0 else 1
        scale = min(scale_x, scale_y)
        
        # Center offset
        scaled_width = bbox.width * scale
        scaled_height = bbox.height * scale
        offset_x = padding + (draw_width - scaled_width) / 2
        offset_y = padding + (draw_height - scaled_height) / 2
        
        def transform(p: Point2D) -> Tuple[float, float]:
            """Convert coordinates to image coordinates"""
            x = (p.x - bbox.min_x) * scale + offset_x
            y = (p.y - bbox.min_y) * scale + offset_y
            if flip_y:
                y = image_size[1] - y
            return (x, y)
        
        # Draw each stroke
        for stroke in strokes:
            if len(stroke.points) < 2:
                # Draw small circle for single point
                if stroke.points:
                    x, y = transform(stroke.points[0])
                    draw.ellipse(
                        [x - line_width, y - line_width, 
                         x + line_width, y + line_width],
                        fill=line_color
                    )
                continue
            
            # Connect points with lines
            image_points = [transform(p) for p in stroke.points]
            draw.line(image_points, fill=line_color, width=line_width)
        
        return img
    
    def convert_to_image(
        self,
        pmi_name: str,
        image_size: Optional[Tuple[int, int]] = None,
        auto_size: bool = True,
        preset: Optional[str] = None,
        **kwargs
    ) -> Optional[Image.Image]:
        """
        Convert elements with specified PMI name to image.
        
        Args:
            pmi_name: PMI name (e.g., 'Note (256)', 'Feature Control Frame (14)')
            image_size: Output image size. Auto-calculated if None
            auto_size: If True, automatically calculate image size based on data size
            preset: Preset name ('ocr_small', 'ocr', 'ocr_large', 'display', 'thumbnail')
            **kwargs: Additional options passed to strokes_to_image
            
        Returns:
            PIL Image object, or None if matching PMI not found
        """
        polyline_ids = self.get_polyline_ids_by_name(pmi_name)
        
        if not polyline_ids:
            return None
        
        strokes = self.extract_strokes(polyline_ids)
        return self.strokes_to_image(strokes, image_size=image_size, auto_size=auto_size, preset=preset, **kwargs)
    
    def convert_type_to_image(
        self,
        pmi_type: str,
        image_size: Optional[Tuple[int, int]] = None,
        auto_size: bool = True,
        **kwargs
    ) -> Optional[Image.Image]:
        """
        Convert all elements of specified PMI type to a single image.
        
        Args:
            pmi_type: PMI type (e.g., 'Note', 'Feature Control Frame')
            image_size: Output image size. Auto-calculated if None
            auto_size: If True, automatically calculate image size based on data size
            **kwargs: Additional options passed to strokes_to_image
            
        Returns:
            PIL Image object
        """
        polyline_ids = self.get_polyline_ids_by_type(pmi_type)
        
        if not polyline_ids:
            return None
        
        strokes = self.extract_strokes(polyline_ids)
        return self.strokes_to_image(strokes, image_size=image_size, auto_size=auto_size, **kwargs)
    
    def save_image(
        self,
        pmi_name: str,
        output_path: Path,
        image_size: Optional[Tuple[int, int]] = None,
        auto_size: bool = True,
        **kwargs
    ) -> bool:
        """
        Save PMI as image file.
        
        Args:
            pmi_name: PMI name
            output_path: Output file path
            image_size: Output image size. Auto-calculated if None
            auto_size: If True, automatically calculate image size based on data size
            **kwargs: Additional options passed to strokes_to_image
            
        Returns:
            True if save successful
        """
        img = self.convert_to_image(pmi_name, image_size=image_size, auto_size=auto_size, **kwargs)
        if img is None:
            return False
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        return True
    
    def save_all_images(
        self,
        output_dir: Path,
        image_size: Optional[Tuple[int, int]] = None,
        auto_size: bool = True,
        **kwargs
    ) -> int:
        """
        Save all PMI groups as individual image files.
        
        Args:
            output_dir: Output directory
            image_size: Output image size. Auto-calculated if None
            auto_size: If True, automatically calculate image size based on data size
            **kwargs: Additional options passed to strokes_to_image
            
        Returns:
            Number of saved images
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        
        for group in self.list_pmi_groups():
            # Sanitize filename
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', group.name)
            safe_name = safe_name.replace(' ', '_')
            output_path = output_dir / f"{safe_name}.png"
            
            if self.save_image(group.name, output_path, image_size=image_size, auto_size=auto_size, **kwargs):
                count += 1
        
        return count


def _sanitize_filename(name: str) -> str:
    """Convert to safe string for filename"""
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    safe = safe.replace(' ', '_')
    return safe


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python presentation_pmi_image_converter.py <STEP_FILE>")
        print("  python presentation_pmi_image_converter.py <STEP_FILE> --list")
        print("  python presentation_pmi_image_converter.py <STEP_FILE> --types")
        print("  python presentation_pmi_image_converter.py <STEP_FILE> <PMI_NAME>")
        print("  python presentation_pmi_image_converter.py <STEP_FILE> --all <OUTPUT_DIR>")
        sys.exit(1)
    
    step_file = Path(sys.argv[1])
    
    reader = StepReader(step_file)
    reader.load()
    
    converter = PresentationPmiImageConverter(reader)
    
    if len(sys.argv) == 2 or sys.argv[2] == '--list':
        # List PMI groups
        print("Presentation PMI Groups:")
        for group in converter.list_pmi_groups():
            print(f"  {group.polyline_count:4d}x {group.name}")
    
    elif sys.argv[2] == '--types':
        # List PMI types
        print("PMI Types:")
        for pmi_type, count in converter.list_pmi_types().items():
            print(f"  {count:4d} Groups: {pmi_type}")
    
    elif sys.argv[2] == '--all':
        # Save all PMI as images (auto size)
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('output_pmi')
        count = converter.save_all_images(output_dir, auto_size=True)
        print(f"Saved {count} images to {output_dir}")
    
    else:
        # Convert specified PMI (auto size)
        pmi_name = sys.argv[2]
        output_path = Path(f"output_{_sanitize_filename(pmi_name)}.png")
        if converter.save_image(pmi_name, output_path, auto_size=True):
            print(f"Save complete: {output_path}")
        else:
            print(f"PMI '{pmi_name}' not found")