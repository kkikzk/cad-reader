"""
STEP File PMI Data Structures

Defines the data structures for PMI (Product Manufacturing Information) in ISO-10303.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class ToleranceType(Enum):
    """Types of geometric tolerances"""
    ANGULARITY = "angularity"
    CIRCULAR_RUNOUT = "circular_runout"
    COAXIALITY = "coaxiality"
    CONCENTRICITY = "concentricity"
    CYLINDRICITY = "cylindricity"
    FLATNESS = "flatness"
    LINE_PROFILE = "line_profile"
    PARALLELISM = "parallelism"
    PERPENDICULARITY = "perpendicularity"
    POSITION = "position"
    ROUNDNESS = "roundness"
    STRAIGHTNESS = "straightness"
    SURFACE_PROFILE = "surface_profile"
    SYMMETRY = "symmetry"
    TOTAL_RUNOUT = "total_runout"
    UNKNOWN = "unknown"


class ToleranceModifier(Enum):
    """Tolerance modifiers"""
    MAXIMUM_MATERIAL_REQUIREMENT = "MMC"  # Ⓜ
    LEAST_MATERIAL_REQUIREMENT = "LMC"    # Ⓛ
    REGARDLESS_OF_FEATURE_SIZE = "RFS"    # (Default)
    FREE_STATE = "FREE_STATE"
    TANGENT_PLANE = "TANGENT_PLANE"
    PROJECTED_TOLERANCE_ZONE = "PROJECTED"
    UNEQUALLY_DISPOSED = "UNEQUALLY_DISPOSED"
    UNKNOWN = "unknown"


# =============================================================================
# Semantic PMI - Dimensions
# =============================================================================

@dataclass
class MeasureValue:
    """Measurement value"""
    value: float
    unit: str = ""
    raw_entity_id: Optional[int] = None
    
    def __str__(self) -> str:
        if self.unit:
            return f"{self.value} {self.unit}"
        return str(self.value)


@dataclass
class DimensionalLocation:
    """Dimensional Location (DIMENSIONAL_LOCATION)"""
    entity_id: int
    name: str = ""
    description: str = ""
    value: Optional[MeasureValue] = None
    tolerance: Optional['PlusMinusTolerance'] = None
    # Referenced entity IDs
    relating_shape_aspect_id: Optional[int] = None
    related_shape_aspect_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'description': self.description,
            'value': str(self.value) if self.value else None,
            'tolerance': self.tolerance.to_dict() if self.tolerance else None,
        }


@dataclass
class DimensionalSize:
    """Dimensional Size (DIMENSIONAL_SIZE)"""
    entity_id: int
    name: str = ""
    applies_to_id: Optional[int] = None
    value: Optional[MeasureValue] = None
    tolerance: Optional['PlusMinusTolerance'] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'value': str(self.value) if self.value else None,
            'tolerance': self.tolerance.to_dict() if self.tolerance else None,
        }


@dataclass
class Dimensions:
    """Container for dimensional data"""
    locations: List[DimensionalLocation] = field(default_factory=list)
    sizes: List[DimensionalSize] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'locations': [d.to_dict() for d in self.locations],
            'sizes': [d.to_dict() for d in self.sizes],
        }


# =============================================================================
# Semantic PMI - Tolerances
# =============================================================================

@dataclass
class DatumReference:
    """Datum Reference"""
    label: str  # 'A', 'B', 'C' etc.
    precedence: str = ""  # 'primary', 'secondary', 'tertiary'
    entity_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'label': self.label,
            'precedence': self.precedence,
        }


@dataclass
class GeometricTolerance:
    """Geometric Tolerance (GEOMETRIC_TOLERANCE family)"""
    entity_id: int
    name: str = ""
    description: str = ""
    tolerance_type: ToleranceType = ToleranceType.UNKNOWN
    value: Optional[MeasureValue] = None
    modifiers: List[ToleranceModifier] = field(default_factory=list)
    datum_references: List[DatumReference] = field(default_factory=list)
    zone_form: str = ""  # 'cylindrical', 'spherical', etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'description': self.description,
            'tolerance_type': self.tolerance_type.value,
            'value': str(self.value) if self.value else None,
            'modifiers': [m.value for m in self.modifiers],
            'datum_references': [d.to_dict() for d in self.datum_references],
            'zone_form': self.zone_form,
        }


@dataclass
class PlusMinusTolerance:
    """Dimensional Tolerance (PLUS_MINUS_TOLERANCE)"""
    entity_id: int
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None
    # For symmetric tolerances
    range_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'upper_bound': self.upper_bound,
            'lower_bound': self.lower_bound,
            'range_value': self.range_value,
        }
    
    def __str__(self) -> str:
        if self.range_value is not None:
            return f"±{self.range_value}"
        if self.upper_bound is not None and self.lower_bound is not None:
            return f"+{self.upper_bound}/-{abs(self.lower_bound)}"
        return ""


@dataclass
class Tolerances:
    """Container for tolerance data"""
    geometric_tolerances: List[GeometricTolerance] = field(default_factory=list)
    plus_minus_tolerances: List[PlusMinusTolerance] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'geometric_tolerances': [t.to_dict() for t in self.geometric_tolerances],
            'plus_minus_tolerances': [t.to_dict() for t in self.plus_minus_tolerances],
        }


# =============================================================================
# Semantic PMI - Datums
# =============================================================================

@dataclass
class Datum:
    """Datum (DATUM)"""
    entity_id: int
    label: str = ""  # 'A', 'B', 'C' etc.
    name: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'label': self.label,
            'name': self.name,
            'description': self.description,
        }


@dataclass
class DatumFeature:
    """Datum Feature (DATUM_FEATURE)"""
    entity_id: int
    name: str = ""
    description: str = ""
    product_definitional: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'description': self.description,
            'product_definitional': self.product_definitional,
        }


@dataclass
class Datums:
    """Container for datum data"""
    datums: List[Datum] = field(default_factory=list)
    datum_features: List[DatumFeature] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'datums': [d.to_dict() for d in self.datums],
            'datum_features': [d.to_dict() for d in self.datum_features],
        }


# =============================================================================
# Semantic PMI Container
# =============================================================================

@dataclass
class SemanticPMI:
    """Container for Semantic PMI (meaningful data)"""
    dimensions: Dimensions = field(default_factory=Dimensions)
    tolerances: Tolerances = field(default_factory=Tolerances)
    datums: Datums = field(default_factory=Datums)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dimensions': self.dimensions.to_dict(),
            'tolerances': self.tolerances.to_dict(),
            'datums': self.datums.to_dict(),
        }


# =============================================================================
# Presentation PMI
# =============================================================================

@dataclass
class PolylineData:
    """Polyline Data"""
    entity_id: int
    name: str = ""
    point_ids: List[int] = field(default_factory=list)
    point_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'point_count': self.point_count,
        }


@dataclass
class CurveData:
    """Curve Data"""
    entity_id: int
    name: str = ""
    curve_type: str = ""  # 'line', 'circle', 'b_spline', etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'curve_type': self.curve_type,
        }


@dataclass
class StyleData:
    """Style Data"""
    entity_id: int
    color: Optional[str] = None  # RGB or named color
    line_width: Optional[float] = None
    font: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'color': self.color,
            'line_width': self.line_width,
            'font': self.font,
        }


@dataclass
class PresentationPMI:
    """Container for Presentation PMI (visual data)"""
    polylines: List[PolylineData] = field(default_factory=list)
    curves: List[CurveData] = field(default_factory=list)
    styles: List[StyleData] = field(default_factory=list)
    annotation_count: int = 0  # Total number of ANNOTATION family entities
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'polylines_count': len(self.polylines),
            'curves_count': len(self.curves),
            'styles_count': len(self.styles),
            'annotation_count': self.annotation_count,
        }


# =============================================================================
# Associations
# =============================================================================

@dataclass
class PMIAssociation:
    """Association between PMI and geometry"""
    entity_id: int
    name: str = ""
    pmi_entity_id: Optional[int] = None
    pmi_entity_type: str = ""
    geometry_entity_id: Optional[int] = None
    presentation_entity_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'pmi_entity_id': self.pmi_entity_id,
            'pmi_entity_type': self.pmi_entity_type,
            'geometry_entity_id': self.geometry_entity_id,
            'presentation_entity_id': self.presentation_entity_id,
        }


@dataclass
class Associations:
    """Container for association data"""
    associations: List[PMIAssociation] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'associations': [a.to_dict() for a in self.associations],
            'count': len(self.associations),
        }


# =============================================================================
# Main PMI Container
# =============================================================================

@dataclass
class PMI:
    """Container for all PMI data"""
    semantic: SemanticPMI = field(default_factory=SemanticPMI)
    presentation: PresentationPMI = field(default_factory=PresentationPMI)
    associations: Associations = field(default_factory=Associations)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'semantic': self.semantic.to_dict(),
            'presentation': self.presentation.to_dict(),
            'associations': self.associations.to_dict(),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of PMI"""
        return {
            'dimensions': {
                'locations': len(self.semantic.dimensions.locations),
                'sizes': len(self.semantic.dimensions.sizes),
            },
            'tolerances': {
                'geometric': len(self.semantic.tolerances.geometric_tolerances),
                'plus_minus': len(self.semantic.tolerances.plus_minus_tolerances),
            },
            'datums': {
                'datums': len(self.semantic.datums.datums),
                'features': len(self.semantic.datums.datum_features),
            },
            'presentation': {
                'polylines': len(self.presentation.polylines),
                'annotation_count': self.presentation.annotation_count,
            },
            'associations': len(self.associations.associations),
        }
