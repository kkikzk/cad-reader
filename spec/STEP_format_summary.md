# STEPファイルのフォーマット概要 / STEP File Format Overview

## 概要 / Overview
- **規格 / Standard**: ISO標準規格 (ISO 10303)
- **用途 / Usage**: 異なるCAD/CAMシステム間でCADデータを交換するための中間ファイルフォーマット / Intermediate file format for exchanging CAD data between different CAD/CAM systems
- **類似規格 / Similar Standard**: IGES (Initial Graphics Exchange Specification)
- **正式名称 / Official Title**: Industrial automation systems and integration – Product data representation and exchange
- **拡張子 / Extensions**: .step, .stp, .p21

## STEPファイルのデータ構造 / STEP File Data Structure
ファイル全体は `ISO-10303-21;` で始まり、 `END-ISO-10303-21;` で終了します。 / The file begins with `ISO-10303-21;` and ends with `END-ISO-10303-21;`.

### セクション構成 / Section Structure
1. **HEADER** (ヘッダーセクション / Header Section)
   - `FILE_DESCRIPTION(...)`
   - `FILE_NAME(...)`
   - `FILE_SCHEMA(...)`
   - `FILE_POPULATION(...)` (Ver.3+)
   - `SECTION_LANGUAGE(...)` (Ver.3+)
   - `SECTION_CONTEXT(...)` (Ver.3+)

2. **ANCHOR** (アンカーセクション / Anchor Section)
   - 外部からの参照用アンカーポイント / Anchor points for external references

3. **REFERENCE** (リファレンスセクション / Reference Section)
   - 外部リソースへの参照 / References to external resources
   - 例 / Example: `#9998 = <http://www.hoge.com/>;`

4. **DATA** (データセクション / Data Section)
   - 実際のモデルデータ / Actual model data
   - 例 / Example: `#5=APPLICATION_CONTEXT('automotive design');`

5. **SIGNATURE** (シグネチャーセクション / Signature Section)
   - デジタル署名 / Digital signature

### その他の仕様 / Other Specifications
- **バージョン3の特徴 / Version 3 Features**: 外部リソース参照、ZIP圧縮アーカイブ、UTF-8エンコード、デジタル署名のサポート / Support for external resource references, ZIP-based compressed archives, UTF-8 encoding, and digital signatures
- **コメント / Comments**: `/* ... */` (C言語スタイル / C-style)

## DATAセクションの詳細 / Data Section Details
- 特定のEXPRESSスキーマに従ったアプリケーションデータが含まれます。 / Contains application data according to a specific EXPRESS schema.
- **インスタンスID / Instance ID**: `＃1234` の形式（正の整数）。ファイル内でローカルに一意。 / Format: `＃1234` (positive integer). Locally unique within the file.
- **データ形式 / Data Format**: `エンティティ名 ( 属性1, 属性2, ... );` / `ENTITY_NAME ( Attribute1, Attribute2, ... );`
  - 例 / Example: `#16 = CARTESIAN_POINT(...);`
- **未設定属性 / Unset Attribute**: `$`
- **派生属性 / Derived Attribute**: `*` (スーパータイプの位置 / at supertype position)
- **列挙/ブール値 / Enumeration/Boolean Values**: `.TRUE.`, `.UNSPECIFIED.` など（ドットで囲む / enclosed in dots）

## 主なエンティティ定義 / Major Entity Definitions

### CARTESIAN_POINT
座標点 (x, y, z) を定義します。 / Defines a coordinate point (x, y, z).
- **形式 / Format**: `CARTESIAN_POINT ( Label, ( x, y, z ) );`
- **例 / Example**: `#1 = CARTESIAN_POINT ( 'NONE', ( 1.0, 2.0, 3.0 ) );`

### DIRECTION
方向ベクトル（通常は単位ベクトル）を定義します。 / Defines a direction vector (usually a unit vector).
- **形式 / Format**: `DIRECTION ( Label, ( x, y, z ) );`
- **例 / Example**: `#3 = DIRECTION ( 'NONE', ( 0.0, 0.0, -1.0 ) );`

### VECTOR
向きと大きさを持つベクトルを定義します。 / Defines a vector with direction and magnitude.
- **形式 / Format**: `VECTOR ( Label, Direction_Entity_ID, Magnitude );`
- **例 / Example**: `#66 = VECTOR ( 'NONE', #3, 50.0 );`

### SHAPE_DEFINITION_REPRESENTATION
プロパティ定義と形状表現を関連付けます。 / Associates a property definition with a shape representation.
- **形式 / Format**: `SHAPE_DEFINITION_REPRESENTATION ( property_definition_ID, shape_representation_ID );`
- **例 / Example**: `#67 = SHAPE_DEFINITION_REPRESENTATION ( #30, #42 );`

### PRODUCT_DEFINITION_SHAPE
製品の形状定義。 / Product shape definition.
- **形式 / Format**: `PRODUCT_DEFINITION_SHAPE ( Label, Description, Entity_ID );`
- **例 / Example**: `#30 = PRODUCT_DEFINITION_SHAPE ( 'NONE', 'NONE', #11 );`

### PRODUCT_DEFINITION
製品の定義。 / Product definition.
- **形式 / Format**: `PRODUCT_DEFINITION ( ID, Description, formation_ID, context_ID );`
- **例 / Example**: `#11 = PRODUCT_DEFINITION ( 'UNKNOWN', '', #72, #36 );`

### GEOMETRIC_REPRESENTATION_CONTEXT
幾何表現のコンテキスト（次元、精度、単位系など）を定義します。 / Defines the context for geometric representation (dimensions, precision, units, etc.).
- **構成要素 / Components**:
  - `GEOMETRIC_REPRESENTATION_CONTEXT`: 次元の定義 / Definition of dimensions
  - `GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT`: 不確実性（精度）の定義 / Definition of uncertainty (precision)
  - `GLOBAL_UNIT_ASSIGNED_CONTEXT`: 単位系の定義 / Definition of unit system (LENGTH_UNIT, PLANE_ANGLE_UNIT, SOLID_ANGLE_UNIT, etc.)

### LINE
直線。点とベクトルで定義されます。 / Line. Defined by a point and a vector.
- **形式 / Format**: `LINE ( Label, CARTESIAN_POINT_ID, VECTOR_ID );`
- **例 / Example**: `#57 = LINE ( 'NONE', #104, #66 );`

### TRIMMED_CURVE
トリム曲線（始点と終点で切り取られた曲線）。 / Trimmed curve (curve truncated at start and end points).
- **形式 / Format**: `TRIMMED_CURVE ( Label, Basis_Curve_ID, (Start_Trim_Def), (End_Trim_Def), Sense_Agreement, Master_Rep );`
- **例 / Example**: `#118 = TRIMMED_CURVE ( 'NONE', #57, (PARAMETER_VALUE(0.0), #15), (PARAMETER_VALUE(1.0), #4), .T., .PARAMETER. );`

### CIRCLE / AXIS2_PLACEMENT_3D
円と3次元配置座標系。 / Circle and 3D axis placement coordinate system.
- **CIRCLE形式 / Format**: `CIRCLE ( Label, Placement_ID, Radius );`
- **AXIS2_PLACEMENT_3D形式 / Format**: `AXIS2_PLACEMENT_3D ( Label, Origin_ID, Z_Axis_ID, X_Axis_ID );`

### GEOMETRIC_CURVE_SET
曲線の集合。 / Set of geometric curves.
- **形式 / Format**: `GEOMETRIC_CURVE_SET ( Label, ( Curve_ID_List ) );`

### B_SPLINE_CURVE
Bスプライン曲線。 / B-spline curve.
- **構成 / Components**: 次数、コントロールポイント、曲線形式、閉曲線フラグ、自己交差フラグ、ノットベクトルなどを含みます。 / Includes degree, control points, curve form, closed curve flag, self-intersect flag, knot vector, etc.
