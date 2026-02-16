"""
STEP File Text Extractor

Main module to extract text data from STEP files.
"""

import argparse
import sys
from pathlib import Path

from step_reader import StepReader


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract text data from STEP files (using OCR)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Usage examples:
  python main.py sample.step
  python main.py sample.step --ocr-preset ocr_small
  python main.py sample.step --min-confidence 0.8
'''
    )
    parser.add_argument('step_file', type=Path, help='Path to the STEP file')
    parser.add_argument('--ocr-engine', type=str, default='easyocr',
                        choices=['auto', 'easyocr', 'tesseract'],
                        help='OCR engine (default: easyocr)')
    parser.add_argument('--ocr-preset', type=str, default='ocr',
                        choices=['ocr_small', 'ocr', 'ocr_large'],
                        help='OCR image size preset (default: ocr)')
    parser.add_argument('--ocr-languages', type=str, nargs='+', default=['en'],
                        help='OCR recognition languages (default: en)')
    parser.add_argument('--min-confidence', type=float, default=0.5,
                        help='OCR minimum confidence (default: 0.5)')
    parser.add_argument('--temp-dir', type=Path, default=None,
                        help='OCR temporary directory (default: current directory)')
    parser.add_argument('--keep-temp-dir', action='store_true',
                        help='Do not delete OCR temporary directory')
    
    args = parser.parse_args()
    
    step_file_path = args.step_file
    
    if not step_file_path.exists():
        print(f"Error: File not found: {step_file_path}")
        sys.exit(1)
    
    if not step_file_path.suffix.lower() in ['.step', '.stp', '.p21']:
        print(f"Warning: File may not be a STEP file: {step_file_path}")
    
    print(f"Loading STEP file: {step_file_path}")
    print("-" * 50)
    
    # Load STEP file
    reader = StepReader(step_file_path)
    
    if not reader.load():
        print("Error: Failed to load file")
        sys.exit(1)
    
    # Show summary
    summary = reader.get_summary()
    print(f"ISO Version: {summary['iso_version']}")
    print(f"HEADER Section: {summary['header_count']} items")
    print(f"ANCHOR Section: {summary['anchor_count']} items")
    print(f"REFERENCE Section: {summary['reference_count']} items")
    print(f"DATA Section: {summary['data_count']} entities")
    print(f"SIGNATURE Section: {summary['signature_count']} items")
    
    if summary['unknown_section_count'] > 0:
        print(f"Unknown Sections: {summary['unknown_section_count']} items")
    
    print("-" * 50)
    
    # Show HEADER section content
    header = reader.header
    
    print("\n[HEADER Section]")
    
    # FILE_DESCRIPTION
    print("  [FILE_DESCRIPTION]")
    print("    description:")
    for desc in header.file_description.description:
        print(f"      - {desc}")
    impl_level = header.file_description.implementation_level
    print(f"    implementation_level:")
    print(f"      raw: '{impl_level.raw}'")
    print(f"      file_edition: {impl_level.file_edition}")
    print(f"      minimum_edition: {impl_level.minimum_edition}")
    
    # FILE_NAME
    print("  [FILE_NAME]")
    print(f"    name: {header.file_name.name}")
    print(f"    time_stamp: {header.file_name.time_stamp}")
    print(f"    author: {header.file_name.author}")
    print(f"    organization: {header.file_name.organization}")
    print(f"    preprocessor_version: {header.file_name.preprocessor_version}")
    print(f"    originating_system: {header.file_name.originating_system}")
    print(f"    authorisation: {header.file_name.authorisation}")
    
    # FILE_SCHEMA
    print("  [FILE_SCHEMA]")
    print(f"    schemas: {header.file_schema.schemas}")
    
    # Optional elements
    if header.file_population:
        print("  [FILE_POPULATION]")
        print(f"    governing_schema: {header.file_population.governing_schema}")
        print(f"    determination_method: {header.file_population.determination_method}")
    
    if header.section_language:
        print("  [SECTION_LANGUAGE]")
        print(f"    language: {header.section_language.language}")
    
    if header.section_context:
        print("  [SECTION_CONTEXT]")
        print(f"    context: {header.section_context.context}")
    
    if header.unknown_entries:
        print("  [Unknown Entries]")
        for entry in header.unknown_entries:
            print(f"    - {entry}")
    
    # Show ANCHOR section content
    if reader.anchors:
        print("\n[ANCHOR Section]")
        for i, anchor in enumerate(reader.anchors, 1):
            print(f"  {i}. {anchor}")
    
    # Show REFERENCE section content
    if reader.references:
        print("\n[REFERENCE Section]")
        for entity_id, entity_data in sorted(reader.references.items()):
            print(f"  #{entity_id} = {entity_data}")
    
    # Show part of DATA section
    if reader.data:
        print("\n[DATA Section]")
        for i, (entity_id, entity_data) in enumerate(sorted(reader.data.items())[:10], 1):
            # Truncate too long data
            display_data = entity_data[:80] + "..." if len(entity_data) > 80 else entity_data
            print(f"  #{entity_id} = {display_data}")
        
        if len(reader.data) > 10:
            print(f"  ... and {len(reader.data) - 10} more")
    
    # Show SIGNATURE section content
    if reader.signatures:
        print("\n[SIGNATURE Section]")
        for i, sig in enumerate(reader.signatures, 1):
            print(f"  {i}. {sig}")
    
    # Show PMI data
    pmi = reader.pmi
    pmi_summary = pmi.get_summary()
    
    print("\n[PMI Data]")
    
    # Semantic PMI - Dimensions
    print("  [Semantic PMI - Dimensions]")
    print(f"    Dimensional Location (DIMENSIONAL_LOCATION): {pmi_summary['dimensions']['locations']} items")
    print(f"    Dimensional Size (DIMENSIONAL_SIZE): {pmi_summary['dimensions']['sizes']} items")
    
    # Show first few items
    for i, dim in enumerate(pmi.semantic.dimensions.locations[:5], 1):
        value_str = str(dim.value) if dim.value else "N/A"
        print(f"      {i}. #{dim.entity_id}: {dim.name or '(no name)'} = {value_str}")
    if len(pmi.semantic.dimensions.locations) > 5:
        print(f"      ... and {len(pmi.semantic.dimensions.locations) - 5} more")
    
    # Semantic PMI - Tolerances
    print("  [Semantic PMI - Tolerances]")
    print(f"    Geometric Tolerances: {pmi_summary['tolerances']['geometric']} items")
    print(f"    Dimensional Tolerances (±): {pmi_summary['tolerances']['plus_minus']} items")
    
    # Details of geometric tolerances
    for i, tol in enumerate(pmi.semantic.tolerances.geometric_tolerances[:5], 1):
        value_str = str(tol.value) if tol.value else "N/A"
        modifiers = ', '.join([m.value for m in tol.modifiers]) if tol.modifiers else ""
        datums = ', '.join([d.label for d in tol.datum_references]) if tol.datum_references else ""
        print(f"      {i}. #{tol.entity_id}: {tol.tolerance_type.value} = {value_str}")
        if modifiers:
            print(f"         Modifiers: {modifiers}")
        if datums:
            print(f"         Datum References: {datums}")
    if len(pmi.semantic.tolerances.geometric_tolerances) > 5:
        print(f"      ... and {len(pmi.semantic.tolerances.geometric_tolerances) - 5} more")
    
    # Semantic PMI - Datums
    print("  [Semantic PMI - Datums]")
    print(f"    Datums: {pmi_summary['datums']['datums']} items")
    print(f"    Datum Features: {pmi_summary['datums']['features']} items")
    
    for datum in pmi.semantic.datums.datums:
        print(f"      - [{datum.label}] #{datum.entity_id}")
    
    # Presentation PMI
    print("  [Presentation PMI]")
    print(f"    Polylines: {pmi_summary['presentation']['polylines']} items")
    print(f"    Annotations: {pmi_summary['presentation']['annotation_count']} items")
    
    # Associations
    print("  [Associations]")
    print(f"    Associations: {pmi_summary['associations']} items")
    
    # Extract and show text data (placed at the end)
    print("\n[Extracted Text]")

    print(f"  OCR: engine={args.ocr_engine}, preset={args.ocr_preset}, "
          f"languages={args.ocr_languages}, min_confidence={args.min_confidence}")
    if args.keep_temp_dir:
        print(f"  Keeping temporary directory")
    print("  Processing OCR...")

    texts = reader.extract_texts(
        ocr_engine=args.ocr_engine,
        ocr_preset=args.ocr_preset,
        ocr_languages=args.ocr_languages,
        temp_dir=args.temp_dir,
        min_confidence=args.min_confidence,
        keep_temp_dir=args.keep_temp_dir
    )
    
    print(f"  Extracted Items: {len(texts)} items")
    for i, text in enumerate(texts, 1):
        # Escape newlines and tabs
        display_text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        # Truncate if too long
        if len(display_text) > 100:
            display_text = display_text[:100] + "..."
        print(f"    {i:3}. {display_text}")
    
    print("\nLoading completed!")


if __name__ == "__main__":
    main()
