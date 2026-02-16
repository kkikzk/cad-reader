"""
STEP File Reader

Class to read STEP files and parse ISO-10303-21 formatted data section by section.

Sections defined in ISO-10303-21:
- HEADER: Header information (FILE_DESCRIPTION, FILE_NAME, FILE_SCHEMA, etc.)
- ANCHOR: Anchor information (Version 3 and later)
- REFERENCE: External reference information (Version 3 and later)
- DATA: Entity data (#ID = Data format)
- SIGNATURE: Digital signature (Version 3 and later)
"""

import re
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional

from step_header import (
    StepHeader, FileDescription, FileName, FileSchema,
    FilePopulation, SectionLanguage, SectionContext, ImplementationLevel
)
from step_pmi import (
    PMI, SemanticPMI, PresentationPMI, Associations,
    Dimensions, DimensionalLocation, DimensionalSize, MeasureValue,
    Tolerances, GeometricTolerance, PlusMinusTolerance, ToleranceType, ToleranceModifier,
    Datums, Datum, DatumFeature, DatumReference,
    PolylineData, CurveData, StyleData, PMIAssociation
)


class StepReader:
    """Class to read and parse STEP files (ISO-10303-21 format)"""
    
    # Section names defined in ISO-10303-21
    KNOWN_SECTIONS = {'HEADER', 'ANCHOR', 'REFERENCE', 'DATA', 'SIGNATURE'}
    
    def __init__(self, file_path: Path):
        """
        Args:
            file_path: Path to the STEP file
        """
        self.file_path = Path(file_path)
        self._content: Optional[str] = None
        
        # Store data for each section
        self.headers: List[str] = []  # Keep existing raw strings for backward compatibility
        self.header: StepHeader = StepHeader()  # Structured header
        self.anchors: List[str] = []
        self.references: Dict[int, str] = {}  # #ID = Data format
        self.data: Dict[int, str] = {}
        self.signatures: List[str] = []
        self.others: List[Dict[str, Any]] = []  # Unknown sections
        
        # PMI data
        self.pmi: PMI = PMI()
        
        # Metadata
        self.iso_version: Optional[str] = None
        self._is_loaded: bool = False
    
    def load(self) -> bool:
        """
        Read STEP file and parse data section by section
        
        Returns:
            True if loading is successful
        """
        # Read file
        if not self._read_file():
            return False
        
        # Data reset
        self._reset_data()
        
        # Remove comments
        content = self._remove_comments(self._content)
        
        # Remove newlines outside string literals
        content = self._normalize_whitespace(content)
        
        # Check ISO version
        if not self._parse_iso_version(content):
            return False
        
        # Parse sections
        self._parse_sections(content)
        
        # Parse PMI
        self._parse_pmi()
        
        self._is_loaded = True
        return True
    
    def _read_file(self) -> bool:
        """Read the file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self._content = f.read()
            return True
        except UnicodeDecodeError:
            # Retry with ISO-8859-1
            try:
                with open(self.file_path, 'r', encoding='iso-8859-1') as f:
                    self._content = f.read()
                return True
            except Exception as e:
                warnings.warn(f"File read error: {e}")
                return False
        except Exception as e:
            warnings.warn(f"File read error: {e}")
            return False
    
    def _reset_data(self) -> None:
        """Reset data"""
        self.headers = []
        self.header = StepHeader()
        self.anchors = []
        self.references = {}
        self.data = {}
        self.signatures = []
        self.others = []
        self.pmi = PMI()
        self.iso_version = None
    
    def _remove_comments(self, content: str) -> str:
        """
        Remove C-style comments /* ... */
        
        Args:
            content: Original content
            
        Returns:
            Content with comments removed
        """
        return re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    def _normalize_whitespace(self, content: str) -> str:
        """
        Remove newlines outside of string literals and condense multiple spaces into one.
        
        Newlines inside string literals enclosed in '' are preserved.
        
        Args:
            content: Original content
            
        Returns:
            Normalized content
        """
        result = []
        in_string = False
        i = 0
        
        while i < len(content):
            char = content[i]
            
            if char == "'" and not in_string:
                # Start of string
                in_string = True
                result.append(char)
            elif char == "'" and in_string:
                # Check for escaped single quote ''
                if i + 1 < len(content) and content[i + 1] == "'":
                    # Escaped single quote
                    result.append(char)
                    result.append(content[i + 1])
                    i += 1
                else:
                    # End of string
                    in_string = False
                    result.append(char)
            elif char in '\n\r' and not in_string:
                # Replace newline outside of string with space
                # But only if the previous character was not a space
                if result and result[-1] not in ' \t\n\r':
                    result.append(' ')
            elif char in ' \t' and not in_string:
                # Add space outside of string only if the previous character was not a space
                if result and result[-1] not in ' \t\n\r':
                    result.append(' ')
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _parse_iso_version(self, content: str) -> bool:
        """
        Parse ISO version
        
        Args:
            content: File content
            
        Returns:
            True if valid ISO-10303-21 format
        """
        # Look for ISO-10303-21; format
        match = re.search(r'ISO-10303-21\s*;', content, re.IGNORECASE)
        if match:
            self.iso_version = "ISO-10303-21"
            return True
        
        warnings.warn("Not in ISO-10303-21 format. Aborting read.")
        return False
    
    def _parse_sections(self, content: str) -> None:
        """
        Parse each section
        
        Args:
            content: File content
        """
        # Remove ISO-10303-21; and END-ISO-10303-21;
        content = re.sub(r'ISO-10303-21\s*;', '', content, flags=re.IGNORECASE)
        content = re.sub(r'END-ISO-10303-21\s*;', '', content, flags=re.IGNORECASE)
        
        # Section pattern: SECTION_NAME; ... ENDSEC;
        # Section name starts with a letter and consists of alphanumeric characters and underscores
        section_pattern = re.compile(
            r'\b([A-Za-z][A-Za-z0-9_]*)\s*;\s*(.*?)\s*ENDSEC\s*;',
            re.DOTALL | re.IGNORECASE
        )
        
        for match in section_pattern.finditer(content):
            section_name = match.group(1).upper()
            section_content = match.group(2).strip()
            
            if section_name == 'HEADER':
                self._parse_header_section(section_content)
            elif section_name == 'ANCHOR':
                self._parse_anchor_section(section_content)
            elif section_name == 'REFERENCE':
                self._parse_reference_section(section_content)
            elif section_name == 'DATA':
                self._parse_data_section(section_content)
            elif section_name == 'SIGNATURE':
                self._parse_signature_section(section_content)
            elif section_name not in self.KNOWN_SECTIONS:
                # Unknown section
                warnings.warn(f"Unknown section found: {section_name}")
                self.others.append({
                    'section_name': section_name,
                    'content': section_content
                })
    
    def _parse_header_section(self, content: str) -> None:
        """
        Parse HEADER section
        
        Contains statements like FILE_DESCRIPTION, FILE_NAME, FILE_SCHEMA, etc.
        
        Args:
            content: Section content
        """
        # Split statements by semicolon and store them
        statements = self._split_statements(content)
        self.headers = [stmt.strip() for stmt in statements if stmt.strip()]
        
        # Parse structured header
        self.header = StepHeader()
        
        for stmt in self.headers:
            entity_name, args = self._parse_entity(stmt)
            
            if entity_name == 'FILE_DESCRIPTION':
                self.header.file_description = self._parse_file_description(args)
            elif entity_name == 'FILE_NAME':
                self.header.file_name = self._parse_file_name(args)
            elif entity_name == 'FILE_SCHEMA':
                self.header.file_schema = self._parse_file_schema(args)
            elif entity_name == 'FILE_POPULATION':
                self.header.file_population = self._parse_file_population(args)
            elif entity_name == 'SECTION_LANGUAGE':
                self.header.section_language = self._parse_section_language(args)
            elif entity_name == 'SECTION_CONTEXT':
                self.header.section_context = self._parse_section_context(args)
            else:
                # Unknown header entry
                self.header.unknown_entries.append(stmt)
    
    def _parse_entity(self, statement: str) -> tuple:
        """
        Parse entity statement and split into entity name and arguments
        
        Example: "FILE_DESCRIPTION(('desc'), '2;1')" -> ("FILE_DESCRIPTION", "('desc'), '2;1'")
        
        Args:
            statement: Entity statement
            
        Returns:
            Tuple of (entity name, argument string)
        """
        match = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$', statement, re.DOTALL)
        if match:
            return (match.group(1).upper(), match.group(2))
        return ('', statement)
    
    def _parse_argument_list(self, args_str: str) -> List[str]:
        """
        Parse argument list and split into individual arguments
        
        Splits by comma considering nested parentheses
        
        Args:
            args_str: Argument string
            
        Returns:
            List of arguments
        """
        args = []
        current = ""
        paren_depth = 0
        in_string = False
        
        for char in args_str:
            if char == "'" and not in_string:
                in_string = True
                current += char
            elif char == "'" and in_string:
                in_string = False
                current += char
            elif char == '(' and not in_string:
                paren_depth += 1
                current += char
            elif char == ')' and not in_string:
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0 and not in_string:
                args.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            args.append(current.strip())
        
        return args
    
    def _parse_string_list(self, list_str: str) -> List[str]:
        """
        Parse string list format
        
        Example: "('item1', 'item2')" -> ['item1', 'item2']
        
        Args:
            list_str: List formatted string
            
        Returns:
            List of strings
        """
        # Remove parentheses
        list_str = list_str.strip()
        if list_str.startswith('(') and list_str.endswith(')'):
            list_str = list_str[1:-1].strip()
        
        if not list_str:
            return []
        
        # Split arguments
        items = self._parse_argument_list(list_str)
        
        # Remove quotes from each item
        result = []
        for item in items:
            item = item.strip()
            if item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            result.append(self._decode_step_string(item))
        
        return result
    
    def _parse_string(self, s: str) -> str:
        """
        Remove quotes from string and decode STEP encoding
        
        Args:
            s: Quoted string
            
        Returns:
            String with quotes removed and decoded
        """
        s = s.strip()
        if s.startswith("'") and s.endswith("'"):
            s = s[1:-1]
        return self._decode_step_string(s)
    
    def _decode_step_string(self, s: str) -> str:
        """
        Decode ISO-10303-21 encoded string
        
        Encoding format:
        - \\X2\\XXXX\\X0\\: UTF-16BE (Basic Multilingual Plane)
        - \\X4\\XXXXXXXX\\X0\\: UTF-32BE (Supplementary Planes)
        - \\X\\XX: ISO 8859-1 (Latin-1) one byte
        - \\S\\X: ISO 8859-1 high byte (0x80-0xFF)
        - \\P?\\: Code page specification (mostly ignored)
        
        Args:
            s: Encoded string
            
        Returns:
            Decoded string
        """
        if not s:
            return s
        
        result = []
        i = 0
        
        while i < len(s):
            # \X2\....\X0\ pattern (UTF-16BE)
            if s[i:i+4] == '\\X2\\':
                i += 4
                hex_chars = []
                while i < len(s) and s[i:i+4] != '\\X0\\':
                    hex_chars.append(s[i])
                    i += 1
                if i < len(s):
                    i += 4  # Skip \X0\
                
                hex_str = ''.join(hex_chars)
                # Decode 4 chars at a time as UTF-16 code points
                try:
                    chars = []
                    for j in range(0, len(hex_str), 4):
                        if j + 4 <= len(hex_str):
                            code_point = int(hex_str[j:j+4], 16)
                            chars.append(chr(code_point))
                    result.append(''.join(chars))
                except ValueError:
                    # Keep original string on decode failure
                    result.append('\\X2\\' + hex_str + '\\X0\\')
            
            # \X4\........\X0\ pattern (UTF-32BE)
            elif s[i:i+4] == '\\X4\\':
                i += 4
                hex_chars = []
                while i < len(s) and s[i:i+4] != '\\X0\\':
                    hex_chars.append(s[i])
                    i += 1
                if i < len(s):
                    i += 4  # Skip \X0\
                
                hex_str = ''.join(hex_chars)
                # Decode 8 chars at a time as UTF-32 code points
                try:
                    chars = []
                    for j in range(0, len(hex_str), 8):
                        if j + 8 <= len(hex_str):
                            code_point = int(hex_str[j:j+8], 16)
                            chars.append(chr(code_point))
                    result.append(''.join(chars))
                except ValueError:
                    result.append('\\X4\\' + hex_str + '\\X0\\')
            
            # \X\XX pattern (ISO 8859-1 1 byte)
            elif s[i:i+3] == '\\X\\' and i + 5 <= len(s):
                try:
                    code = int(s[i+3:i+5], 16)
                    result.append(chr(code))
                    i += 5
                except ValueError:
                    result.append(s[i])
                    i += 1
            
            # \S\X pattern (ISO 8859-1 high byte)
            elif s[i:i+3] == '\\S\\' and i + 4 <= len(s):
                try:
                    # Add 0x80 to the code of the character after \S\
                    code = ord(s[i+3]) + 0x80
                    result.append(chr(code))
                    i += 4
                except (ValueError, IndexError):
                    result.append(s[i])
                    i += 1
            
            # \P?\ pattern (Code page specification, skip)
            elif s[i:i+2] == '\\P' and i + 4 <= len(s) and s[i+3] == '\\':
                i += 4  # Skip \P?\ 
            
            # Normal character
            else:
                result.append(s[i])
                i += 1
        
        return ''.join(result)
    
    def _parse_file_description(self, args_str: str) -> FileDescription:
        """
        Parse FILE_DESCRIPTION
        
        FILE_DESCRIPTION(description, implementation_level)
        
        Args:
            args_str: Argument string
            
        Returns:
            FileDescription object
        """
        args = self._parse_argument_list(args_str)
        
        fd = FileDescription()
        if len(args) >= 1:
            fd.description = self._parse_string_list(args[0])
        if len(args) >= 2:
            level_str = self._parse_string(args[1])
            fd.implementation_level = ImplementationLevel.parse(level_str)
        
        return fd
    
    def _parse_file_name(self, args_str: str) -> FileName:
        """
        Parse FILE_NAME
        
        FILE_NAME(name, time_stamp, author, organization, 
                  preprocessor_version, originating_system, authorisation)
        
        Args:
            args_str: Argument string
            
        Returns:
            FileName object
        """
        args = self._parse_argument_list(args_str)
        
        fn = FileName()
        if len(args) >= 1:
            fn.name = self._parse_string(args[0])
        if len(args) >= 2:
            fn.time_stamp = self._parse_string(args[1])
        if len(args) >= 3:
            fn.author = self._parse_string_list(args[2])
        if len(args) >= 4:
            fn.organization = self._parse_string_list(args[3])
        if len(args) >= 5:
            fn.preprocessor_version = self._parse_string(args[4])
        if len(args) >= 6:
            fn.originating_system = self._parse_string(args[5])
        if len(args) >= 7:
            fn.authorisation = self._parse_string(args[6])
        
        return fn
    
    def _parse_file_schema(self, args_str: str) -> FileSchema:
        """
        Parse FILE_SCHEMA
        
        FILE_SCHEMA((schema_name, ...))
        
        Args:
            args_str: Argument string
            
        Returns:
            FileSchema object
        """
        fs = FileSchema()
        fs.schemas = self._parse_string_list(args_str.strip())
        return fs
    
    def _parse_file_population(self, args_str: str) -> FilePopulation:
        """
        Parse FILE_POPULATION (STEP Version 3)
        
        FILE_POPULATION(governing_schema, determination_method, governed_sections)
        
        Args:
            args_str: Argument string
            
        Returns:
            FilePopulation object
        """
        args = self._parse_argument_list(args_str)
        
        fp = FilePopulation()
        if len(args) >= 1:
            fp.governing_schema = self._parse_string(args[0])
        if len(args) >= 2:
            fp.determination_method = self._parse_string(args[1])
        if len(args) >= 3:
            fp.governed_sections = self._parse_string_list(args[2])
        
        return fp
    
    def _parse_section_language(self, args_str: str) -> SectionLanguage:
        """
        Parse SECTION_LANGUAGE (STEP Version 3)
        
        SECTION_LANGUAGE(language)
        
        Args:
            args_str: Argument string
            
        Returns:
            SectionLanguage object
        """
        sl = SectionLanguage()
        sl.language = self._parse_string(args_str.strip())
        return sl
    
    def _parse_section_context(self, args_str: str) -> SectionContext:
        """
        Parse SECTION_CONTEXT (STEP Version 3)
        
        SECTION_CONTEXT(context)
        
        Args:
            args_str: Argument string
            
        Returns:
            SectionContext object
        """
        sc = SectionContext()
        sc.context = self._parse_string(args_str.strip())
        return sc
    
    def _parse_anchor_section(self, content: str) -> None:
        """
        Parse ANCHOR section
        
        Args:
            content: Section content
        """
        statements = self._split_statements(content)
        self.anchors = [stmt.strip() for stmt in statements if stmt.strip()]
    
    def _parse_reference_section(self, content: str) -> None:
        """
        Parse REFERENCE section
        
        Stored in format: #ID = DATA;
        ID is stored as key (int), DATA after = is stored as value in dictionary
        
        Args:
            content: Section content
        """
        # Search for pattern: #number = ... ;
        entity_pattern = re.compile(
            r'#(\d+)\s*=\s*(.*?)\s*;',
            re.DOTALL
        )
        
        for match in entity_pattern.finditer(content):
            entity_id = int(match.group(1))
            entity_data = match.group(2).strip()
            self.references[entity_id] = entity_data
    
    def _parse_data_section(self, content: str) -> None:
        """
        Parse DATA section
        
        Stored in format: #ID = DATA;
        ID is stored as key (int), DATA after = is stored as value in dictionary
        
        Args:
            content: Section content
        """
        # Search for pattern: #number = ... ;
        # Handle multi-line matches
        entity_pattern = re.compile(
            r'#(\d+)\s*=\s*(.*?)\s*;',
            re.DOTALL
        )
        
        for match in entity_pattern.finditer(content):
            entity_id = int(match.group(1))
            entity_data = match.group(2).strip()
            self.data[entity_id] = entity_data
    
    def _parse_signature_section(self, content: str) -> None:
        """
        Parse SIGNATURE section
        
        Args:
            content: Section content
        """
        statements = self._split_statements(content)
        self.signatures = [stmt.strip() for stmt in statements if stmt.strip()]
    
    def _split_statements(self, content: str) -> List[str]:
        """
        Split statements by semicolon
        Semicolons inside parentheses are ignored
        
        Args:
            content: Content to split
            
        Returns:
            List of statements
        """
        statements = []
        current = ""
        paren_depth = 0
        
        for char in content:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ';' and paren_depth == 0:
                if current.strip():
                    statements.append(current.strip())
                current = ""
            else:
                current += char
        
        # Last statement (if no trailing semicolon)
        if current.strip():
            statements.append(current.strip())
        
        return statements
    
    def extract_texts(
        self, 
        unique: bool = True,
        ocr_engine: str = 'auto',
        ocr_preset: str = 'ocr',
        ocr_languages: List[str] = None,
        temp_dir: Optional[Path] = None,
        min_confidence: float = 0.5,
        keep_temp_dir: bool = False
    ) -> List[str]:
        """
        Extract text from Presentation PMI images using OCR
        
        Converts PMI polyline data to images and performs text recognition using OCR engine.
        
        Args:
            unique: If True, merges duplicate texts (default: True)
                    If False, outputs same text multiple times
            ocr_engine: OCR engine ('auto', 'easyocr', 'tesseract')
            ocr_preset: Image size preset ('ocr_small', 'ocr', 'ocr_large')
            ocr_languages: List of OCR recognition languages (e.g. ['en'], ['en', 'ja'])
            temp_dir: Directory for temporary files (default: current directory)
            min_confidence: Minimum confidence for OCR results (results below this are excluded)
            keep_temp_dir: If True, do not delete temporary directory
        
        Returns:
            List of extracted texts
        """
        if not self._is_loaded:
            if not self.load():
                return []
        
        texts = []
        seen = set()
        
        # Execute OCR processing
        ocr_texts = self._extract_texts_via_ocr(
            ocr_engine=ocr_engine,
            ocr_preset=ocr_preset,
            ocr_languages=ocr_languages,
            temp_dir=temp_dir,
            min_confidence=min_confidence,
            keep_temp_dir=keep_temp_dir
        )
        for text in ocr_texts:
            if unique:
                if text not in seen:
                    seen.add(text)
                    texts.append(text)
            else:
                texts.append(text)
        
        return texts
    
    def _extract_texts_via_ocr(
        self,
        ocr_engine: str = 'auto',
        ocr_preset: str = 'ocr',
        ocr_languages: List[str] = None,
        temp_dir: Optional[Path] = None,
        min_confidence: float = 0.5,
        keep_temp_dir: bool = False
    ) -> List[str]:
        """
        Execute OCR on Presentation PMI images and extract text
        
        Args:
            ocr_engine: OCR engine
            ocr_preset: Image size preset
            ocr_languages: Recognition languages list
            temp_dir: Temporary file directory
            min_confidence: Minimum confidence
            keep_temp_dir: If True, do not delete temporary directory
            
        Returns:
            List of texts extracted via OCR
        """
        try:
            from presentation_pmi_image_converter import PresentationPmiImageConverter
            from pmi_ocr import PmiOcr, check_ocr_availability
        except ImportError as e:
            warnings.warn(f"Failed to import OCR module: {e}")
            return []
        
        # Check OCR engine availability
        availability = check_ocr_availability()
        if not any(availability.values()):
            warnings.warn("OCR engine not available. Please run `pip install easyocr` or `pip install pytesseract`.")
            return []
        
        # Set temporary directory
        if temp_dir is None:
            temp_dir = Path.cwd()
        else:
            temp_dir = Path(temp_dir)
        
        # Create temporary directory
        temp_ocr_dir = temp_dir / f".step_ocr_temp_{id(self)}"
        temp_ocr_dir.mkdir(parents=True, exist_ok=True)
        
        ocr_texts = []
        
        try:
            # Initialize converter and OCR
            converter = PresentationPmiImageConverter(self)
            ocr = PmiOcr(
                engine=ocr_engine,
                languages=ocr_languages or ['en'],
                image_preset=ocr_preset
            )
            
            # Execute OCR for all PMI groups
            for group in converter.list_pmi_groups():
                try:
                    # Generate image and save temporarily
                    img = converter.convert_to_image(group.name, preset=ocr_preset)
                    if img is None:
                        continue
                    
                    # Save to temporary file
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', group.name)
                    temp_image_path = temp_ocr_dir / f"{safe_name}.png"
                    img.save(temp_image_path)
                    
                    # Execute OCR
                    result = ocr.recognize_pmi(converter, group.name, preset=ocr_preset)
                    
                    # Extract text with confidence above threshold
                    if result.full_text and result.avg_confidence >= min_confidence:
                        ocr_texts.append(result.full_text)
                    
                    # Extract from individual results
                    for r in result.results:
                        if r.text and r.confidence >= min_confidence:
                            if r.text not in ocr_texts:
                                ocr_texts.append(r.text)
                                
                except Exception as e:
                    warnings.warn(f"Error during OCR of PMI '{group.name}': {e}")
                    continue
                    
        finally:
            # Remove temporary directory (only if keep_temp_dir is False)
            if not keep_temp_dir and temp_ocr_dir.exists():
                shutil.rmtree(temp_ocr_dir, ignore_errors=True)
            elif keep_temp_dir:
                warnings.warn(f"Keeping temporary directory: {temp_ocr_dir}")
        
        return ocr_texts
    
    def get_raw_content(self) -> str:
        """
        Get STEP file raw data
        
        Returns:
            File content
        """
        if self._content is None:
            self._read_file()
        return self._content or ""
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get loaded data summary
        
        Returns:
            Summary info
        """
        return {
            'file_path': str(self.file_path),
            'iso_version': self.iso_version,
            'is_loaded': self._is_loaded,
            'header_count': len(self.headers),
            'anchor_count': len(self.anchors),
            'reference_count': len(self.references),
            'data_count': len(self.data),
            'signature_count': len(self.signatures),
            'unknown_section_count': len(self.others),
        }
    
    # =========================================================================
    # PMI Parsing
    # =========================================================================
    
    def _parse_pmi(self) -> None:
        """
        Extract PMI information from DATA section
        """
        self.pmi = PMI()
        
        # Semantic PMI
        self._parse_pmi_dimensions()
        self._parse_pmi_tolerances()
        self._parse_pmi_datums()
        
        # Presentation PMI
        self._parse_pmi_presentation()
        
        # Associations
        self._parse_pmi_associations()
    
    def _parse_pmi_dimensions(self) -> None:
        """Parse dimension data"""
        for entity_id, entity_data in self.data.items():
            entity_type = self._get_entity_type(entity_data)
            
            if entity_type == 'DIMENSIONAL_LOCATION':
                dim = self._parse_dimensional_location(entity_id, entity_data)
                if dim:
                    self.pmi.semantic.dimensions.locations.append(dim)
            
            elif entity_type == 'DIMENSIONAL_SIZE':
                dim = self._parse_dimensional_size(entity_id, entity_data)
                if dim:
                    self.pmi.semantic.dimensions.sizes.append(dim)
    
    def _parse_dimensional_location(self, entity_id: int, entity_data: str) -> Optional[DimensionalLocation]:
        """Parse DIMENSIONAL_LOCATION"""
        # DIMENSIONAL_LOCATION('name','description',#ref1,#ref2)
        match = re.match(r"DIMENSIONAL_LOCATION\s*\((.*)\)", entity_data, re.DOTALL)
        if not match:
            return None
        
        args = self._parse_argument_list(match.group(1))
        
        dim = DimensionalLocation(entity_id=entity_id)
        if len(args) >= 1:
            dim.name = self._parse_string(args[0])
        if len(args) >= 2:
            dim.description = self._parse_string(args[1])
        if len(args) >= 3:
            ref_match = re.match(r'#(\d+)', args[2].strip())
            if ref_match:
                dim.relating_shape_aspect_id = int(ref_match.group(1))
        if len(args) >= 4:
            ref_match = re.match(r'#(\d+)', args[3].strip())
            if ref_match:
                dim.related_shape_aspect_id = int(ref_match.group(1))
        
        # Search for related value (from SHAPE_DIMENSION_REPRESENTATION)
        dim.value = self._find_dimension_value(entity_id)
        
        return dim
    
    def _parse_dimensional_size(self, entity_id: int, entity_data: str) -> Optional[DimensionalSize]:
        """Parse DIMENSIONAL_SIZE"""
        # DIMENSIONAL_SIZE(#applies_to,'name')
        match = re.match(r"DIMENSIONAL_SIZE\s*\((.*)\)", entity_data, re.DOTALL)
        if not match:
            return None
        
        args = self._parse_argument_list(match.group(1))
        
        dim = DimensionalSize(entity_id=entity_id)
        if len(args) >= 1:
            ref_match = re.match(r'#(\d+)', args[0].strip())
            if ref_match:
                dim.applies_to_id = int(ref_match.group(1))
        if len(args) >= 2:
            dim.name = self._parse_string(args[1])
        
        # Search for related value
        dim.value = self._find_dimension_value(entity_id)
        
        return dim
    
    def _find_dimension_value(self, dimension_id: int) -> Optional[MeasureValue]:
        """
        Find value associated with dimension
        SHAPE_DIMENSION_REPRESENTATION -> LENGTH_MEASURE_WITH_UNIT
        """
        for eid, edata in self.data.items():
            if edata.startswith('SHAPE_DIMENSION_REPRESENTATION'):
                # Check for reference to dimension_id
                if f'#{dimension_id}' in edata or f'#{dimension_id},' in edata or f'#{dimension_id})' in edata:
                    # Look for value reference
                    refs = re.findall(r'#(\d+)', edata)
                    for ref in refs:
                        ref_id = int(ref)
                        if ref_id in self.data:
                            ref_data = self.data[ref_id]
                            measure = self._parse_measure_value(ref_id, ref_data)
                            if measure:
                                return measure
        return None
    
    def _parse_measure_value(self, entity_id: int, entity_data: str) -> Optional[MeasureValue]:
        """Extract value from LENGTH_MEASURE_WITH_UNIT etc"""
        # LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(value),#unit_ref)
        match = re.search(r'LENGTH_MEASURE\s*\(\s*([0-9.E+-]+)\s*\)', entity_data)
        if match:
            try:
                value = float(match.group(1))
                return MeasureValue(value=value, unit="", raw_entity_id=entity_id)
            except ValueError:
                pass
        return None
    
    def _parse_pmi_tolerances(self) -> None:
        """Parse tolerance data"""
        for entity_id, entity_data in self.data.items():
            entity_type = self._get_entity_type(entity_data)
            
            # Geometric tolerance
            if 'TOLERANCE' in entity_type and entity_type not in ['PLUS_MINUS_TOLERANCE', 'TOLERANCE_VALUE', 'TOLERANCE_ZONE', 'TOLERANCE_ZONE_FORM']:
                tol = self._parse_geometric_tolerance(entity_id, entity_data)
                if tol:
                    self.pmi.semantic.tolerances.geometric_tolerances.append(tol)
            
            # Dimensional tolerance
            elif entity_type == 'PLUS_MINUS_TOLERANCE':
                tol = self._parse_plus_minus_tolerance(entity_id, entity_data)
                if tol:
                    self.pmi.semantic.tolerances.plus_minus_tolerances.append(tol)
    
    def _parse_geometric_tolerance(self, entity_id: int, entity_data: str) -> Optional[GeometricTolerance]:
        """Parse geometric tolerance"""
        entity_type = self._get_entity_type(entity_data)
        
        tol = GeometricTolerance(entity_id=entity_id)
        
        # Determine tolerance type
        tol.tolerance_type = self._determine_tolerance_type(entity_type)
        
        # Extract name and description
        # GEOMETRIC_TOLERANCE('name','description',#value_ref,#shape_ref)
        match = re.search(r"GEOMETRIC_TOLERANCE\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", entity_data)
        if match:
            tol.name = match.group(1)
            tol.description = match.group(2)
        
        # Extract tolerance value
        value_ref_match = re.search(r"GEOMETRIC_TOLERANCE\s*\([^)]*,\s*#(\d+)", entity_data)
        if value_ref_match:
            value_id = int(value_ref_match.group(1))
            if value_id in self.data:
                tol.value = self._parse_measure_value(value_id, self.data[value_id])
        
        # Extract modifiers
        if 'MAXIMUM_MATERIAL_REQUIREMENT' in entity_data:
            tol.modifiers.append(ToleranceModifier.MAXIMUM_MATERIAL_REQUIREMENT)
        if 'LEAST_MATERIAL_REQUIREMENT' in entity_data:
            tol.modifiers.append(ToleranceModifier.LEAST_MATERIAL_REQUIREMENT)
        
        # Extract datum references
        tol.datum_references = self._extract_datum_references(entity_data)
        
        # Extract tolerance zone form
        zone_match = re.search(r"TOLERANCE_ZONE_FORM\s*\(\s*'([^']*)'", entity_data)
        if zone_match:
            tol.zone_form = zone_match.group(1)
        else:
            # Look in references
            for ref in re.findall(r'#(\d+)', entity_data):
                ref_id = int(ref)
                if ref_id in self.data and 'TOLERANCE_ZONE_FORM' in self.data[ref_id]:
                    zone_match = re.search(r"TOLERANCE_ZONE_FORM\s*\(\s*'([^']*)'", self.data[ref_id])
                    if zone_match:
                        tol.zone_form = zone_match.group(1)
                        break
        
        return tol
    
    def _determine_tolerance_type(self, entity_type: str) -> ToleranceType:
        """Determine tolerance type from entity type"""
        type_mapping = {
            'ANGULARITY_TOLERANCE': ToleranceType.ANGULARITY,
            'CIRCULAR_RUNOUT_TOLERANCE': ToleranceType.CIRCULAR_RUNOUT,
            'COAXIALITY_TOLERANCE': ToleranceType.COAXIALITY,
            'CONCENTRICITY_TOLERANCE': ToleranceType.CONCENTRICITY,
            'CYLINDRICITY_TOLERANCE': ToleranceType.CYLINDRICITY,
            'FLATNESS_TOLERANCE': ToleranceType.FLATNESS,
            'LINE_PROFILE_TOLERANCE': ToleranceType.LINE_PROFILE,
            'PARALLELISM_TOLERANCE': ToleranceType.PARALLELISM,
            'PERPENDICULARITY_TOLERANCE': ToleranceType.PERPENDICULARITY,
            'POSITION_TOLERANCE': ToleranceType.POSITION,
            'ROUNDNESS_TOLERANCE': ToleranceType.ROUNDNESS,
            'STRAIGHTNESS_TOLERANCE': ToleranceType.STRAIGHTNESS,
            'SURFACE_PROFILE_TOLERANCE': ToleranceType.SURFACE_PROFILE,
            'SYMMETRY_TOLERANCE': ToleranceType.SYMMETRY,
            'TOTAL_RUNOUT_TOLERANCE': ToleranceType.TOTAL_RUNOUT,
        }
        
        for key, value in type_mapping.items():
            if key in entity_type:
                return value
        
        return ToleranceType.UNKNOWN
    
    def _extract_datum_references(self, entity_data: str) -> List[DatumReference]:
        """Extract datum references from entity data"""
        datum_refs = []
        
        # Look for DATUM_REFERENCE_COMPARTMENT
        compartment_refs = re.findall(r'DATUM_REFERENCE_COMPARTMENT', entity_data)
        
        # Look for DATUM_SYSTEM
        system_refs = re.findall(r'#(\d+)', entity_data)
        for ref in system_refs:
            ref_id = int(ref)
            if ref_id in self.data:
                ref_data = self.data[ref_id]
                if 'DATUM_SYSTEM' in ref_data:
                    # Get DATUM_REFERENCE_COMPARTMENT from DATUM_SYSTEM
                    compartment_matches = re.findall(r'#(\d+)', ref_data)
                    precedences = ['.PRIMARY.', '.SECONDARY.', '.TERTIARY.']
                    prec_idx = 0
                    for comp_ref in compartment_matches:
                        comp_id = int(comp_ref)
                        if comp_id in self.data and 'DATUM_REFERENCE_COMPARTMENT' in self.data[comp_id]:
                            # Get reference to DATUM
                            comp_data = self.data[comp_id]
                            datum_match = re.findall(r'#(\d+)', comp_data)
                            for datum_ref in datum_match:
                                datum_id = int(datum_ref)
                                if datum_id in self.data and self.data[datum_id].startswith('DATUM('):
                                    # Get label from DATUM
                                    label_match = re.search(r"DATUM\s*\([^)]*'([A-Z])'\s*\)", self.data[datum_id])
                                    if label_match:
                                        precedence = precedences[prec_idx] if prec_idx < len(precedences) else ''
                                        datum_refs.append(DatumReference(
                                            label=label_match.group(1),
                                            precedence=precedence.strip('.').lower(),
                                            entity_id=datum_id
                                        ))
                                        prec_idx += 1
                                        break
        
        return datum_refs
    
    def _parse_plus_minus_tolerance(self, entity_id: int, entity_data: str) -> Optional[PlusMinusTolerance]:
        """Parse PLUS_MINUS_TOLERANCE"""
        # PLUS_MINUS_TOLERANCE(#range_ref, #dimension_ref)
        tol = PlusMinusTolerance(entity_id=entity_id)
        
        refs = re.findall(r'#(\d+)', entity_data)
        if refs:
            # First reference is TOLERANCE_VALUE
            range_id = int(refs[0])
            if range_id in self.data:
                range_data = self.data[range_id]
                # Get value from TOLERANCE_VALUE
                measure_match = re.search(r'LENGTH_MEASURE\s*\(\s*([0-9.E+-]+)\s*\)', range_data)
                if measure_match:
                    try:
                        tol.range_value = float(measure_match.group(1))
                    except ValueError:
                        pass
        
        return tol
    
    def _parse_pmi_datums(self) -> None:
        """Parse datum data"""
        for entity_id, entity_data in self.data.items():
            entity_type = self._get_entity_type(entity_data)
            
            if entity_type == 'DATUM':
                datum = self._parse_datum(entity_id, entity_data)
                if datum:
                    self.pmi.semantic.datums.datums.append(datum)
            
            elif entity_type == 'DATUM_FEATURE':
                feature = self._parse_datum_feature(entity_id, entity_data)
                if feature:
                    self.pmi.semantic.datums.datum_features.append(feature)
    
    def _parse_datum(self, entity_id: int, entity_data: str) -> Optional[Datum]:
        """Parse DATUM"""
        # DATUM('name','description',#ref,.T.,'A')
        datum = Datum(entity_id=entity_id)
        
        # Extract label ('A', 'B', 'C' etc.)
        label_match = re.search(r"'([A-Z])'\s*\)", entity_data)
        if label_match:
            datum.label = label_match.group(1)
        
        # Extract name
        name_match = re.match(r"DATUM\s*\(\s*'([^']*)'", entity_data)
        if name_match:
            datum.name = name_match.group(1)
        
        return datum
    
    def _parse_datum_feature(self, entity_id: int, entity_data: str) -> Optional[DatumFeature]:
        """Parse DATUM_FEATURE"""
        # DATUM_FEATURE('name','description',#ref,.T.)
        feature = DatumFeature(entity_id=entity_id)
        
        match = re.match(r"DATUM_FEATURE\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", entity_data)
        if match:
            feature.name = match.group(1)
            feature.description = match.group(2)
        
        if '.F.' in entity_data:
            feature.product_definitional = False
        
        return feature
    
    def _parse_pmi_presentation(self) -> None:
        """Parse presentation PMI"""
        annotation_count = 0
        
        for entity_id, entity_data in self.data.items():
            entity_type = self._get_entity_type(entity_data)
            
            # Collect POLYLINE
            if entity_type == 'POLYLINE':
                polyline = self._parse_polyline(entity_id, entity_data)
                if polyline:
                    self.pmi.presentation.polylines.append(polyline)
            
            # Count ANNOTATION types
            if 'ANNOTATION' in entity_type:
                annotation_count += 1
        
        self.pmi.presentation.annotation_count = annotation_count
    
    def _parse_polyline(self, entity_id: int, entity_data: str) -> Optional[PolylineData]:
        """Parse POLYLINE"""
        # POLYLINE('name',(#point1,#point2,...))
        polyline = PolylineData(entity_id=entity_id)
        
        name_match = re.match(r"POLYLINE\s*\(\s*'([^']*)'", entity_data)
        if name_match:
            polyline.name = name_match.group(1)
        
        # Count point references
        point_refs = re.findall(r'#(\d+)', entity_data)
        polyline.point_count = len(point_refs)
        polyline.point_ids = [int(p) for p in point_refs]
        
        return polyline
    
    def _parse_pmi_associations(self) -> None:
        """Parse PMI to geometry associations"""
        for entity_id, entity_data in self.data.items():
            entity_type = self._get_entity_type(entity_data)
            
            if entity_type == 'DRAUGHTING_MODEL_ITEM_ASSOCIATION':
                assoc = self._parse_association(entity_id, entity_data)
                if assoc:
                    self.pmi.associations.associations.append(assoc)
    
    def _parse_association(self, entity_id: int, entity_data: str) -> Optional[PMIAssociation]:
        """Parse DRAUGHTING_MODEL_ITEM_ASSOCIATION"""
        # DRAUGHTING_MODEL_ITEM_ASSOCIATION('name',$,#pmi,#model,#presentation)
        assoc = PMIAssociation(entity_id=entity_id)
        
        name_match = re.match(r"DRAUGHTING_MODEL_ITEM_ASSOCIATION\s*\(\s*'([^']*)'", entity_data)
        if name_match:
            assoc.name = name_match.group(1)
        
        refs = re.findall(r'#(\d+)', entity_data)
        if len(refs) >= 1:
            pmi_id = int(refs[0])
            assoc.pmi_entity_id = pmi_id
            if pmi_id in self.data:
                assoc.pmi_entity_type = self._get_entity_type(self.data[pmi_id])
        
        if len(refs) >= 2:
            assoc.geometry_entity_id = int(refs[1])
        
        if len(refs) >= 3:
            assoc.presentation_entity_id = int(refs[2])
        
        return assoc
    
    def _get_entity_type(self, entity_data: str) -> str:
        """Extract type name from entity data"""
        # For complex entities (TYPE1()TYPE2()...)
        if entity_data.startswith('('):
            # Extract first type
            match = re.search(r'\(([A-Z_]+)', entity_data)
            if match:
                return match.group(1)
        
        # Normal entities
        match = re.match(r'([A-Z_][A-Z0-9_]*)', entity_data)
        if match:
            return match.group(1)
        
        return ""
