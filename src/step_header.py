"""
STEP File Header Data Structures

Defines the data structure of the HEADER section of ISO-10303-21.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class ImplementationLevel:
    """
    implementation_level of ISO 10303-21
    
    Format: 'file_edition;minimum_edition' (e.g., '2;1')
    
    - file_edition: The Edition used by this file
    - minimum_edition: The minimum Edition required for reading
    
    '2;1' = Written in Edition 2, but readable by an Edition 1 reader
    """
    raw: str = ""
    file_edition: Optional[int] = None
    minimum_edition: Optional[int] = None
    
    @classmethod
    def parse(cls, level_str: str) -> 'ImplementationLevel':
        """
        Parse implementation_level string
        
        Args:
            level_str: Format like '2;1' or '1'
            
        Returns:
            ImplementationLevel object
        """
        result = cls(raw=level_str)
        
        if not level_str:
            return result
        
        # Parse '2;1' format
        match = re.match(r'^(\d+);(\d+)$', level_str.strip())
        if match:
            result.file_edition = int(match.group(1))
            result.minimum_edition = int(match.group(2))
            return result
        
        # '1' format (single number)
        single_match = re.match(r'^(\d+)$', level_str.strip())
        if single_match:
            edition = int(single_match.group(1))
            result.file_edition = edition
            result.minimum_edition = edition
            return result
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def __str__(self) -> str:
        if self.file_edition is not None and self.minimum_edition is not None:
            return f"Edition {self.file_edition} (min: {self.minimum_edition})"
        return self.raw


@dataclass
class FileDescription:
    """
    FILE_DESCRIPTION Entity
    
    FILE_DESCRIPTION(description, implementation_level)
    
    - description: List of free-form descriptions (LIST [1:?] OF STRING(256))
    - implementation_level: Compliance level standardized in ISO 10303-21
    """
    description: List[str] = field(default_factory=list)
    implementation_level: ImplementationLevel = field(default_factory=ImplementationLevel)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'description': self.description,
            'implementation_level': self.implementation_level.to_dict()
        }


@dataclass
class FileName:
    """
    FILE_NAME Entity
    
    FILE_NAME(name, time_stamp, author, organization, 
              preprocessor_version, originating_system, authorisation)
    """
    name: str = ""
    time_stamp: str = ""
    author: List[str] = field(default_factory=list)
    organization: List[str] = field(default_factory=list)
    preprocessor_version: str = ""
    originating_system: str = ""
    authorisation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileSchema:
    """
    FILE_SCHEMA Entity
    
    FILE_SCHEMA((schema_name, ...))
    """
    schemas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FilePopulation:
    """
    FILE_POPULATION Entity (STEP Version 3 and later)
    
    FILE_POPULATION(governing_schema, determination_method, governed_sections)
    """
    governing_schema: str = ""
    determination_method: str = ""
    governed_sections: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SectionLanguage:
    """
    SECTION_LANGUAGE Entity (STEP Version 3 and later)
    
    SECTION_LANGUAGE(language)
    """
    language: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SectionContext:
    """
    SECTION_CONTEXT Entity (STEP Version 3 and later)
    
    SECTION_CONTEXT(context)
    """
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StepHeader:
    """
    Entire HEADER section of a STEP file
    """
    file_description: FileDescription = field(default_factory=FileDescription)
    file_name: FileName = field(default_factory=FileName)
    file_schema: FileSchema = field(default_factory=FileSchema)
    
    # Optional elements for STEP Version 3 and later
    file_population: Optional[FilePopulation] = None
    section_language: Optional[SectionLanguage] = None
    section_context: Optional[SectionContext] = None
    
    # Unknown header entries
    unknown_entries: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = {
            'file_description': self.file_description.to_dict(),
            'file_name': self.file_name.to_dict(),
            'file_schema': self.file_schema.to_dict(),
        }
        
        if self.file_population:
            result['file_population'] = self.file_population.to_dict()
        if self.section_language:
            result['section_language'] = self.section_language.to_dict()
        if self.section_context:
            result['section_context'] = self.section_context.to_dict()
        if self.unknown_entries:
            result['unknown_entries'] = self.unknown_entries
        
        return result
