[English](#english) | [日本語](#japanese)

<a id="english"></a>

# CAD Reader - STEP File Text Extractor

A Python tool that extracts text data and PMI (Product Manufacturing Information) from STEP files (ISO-10303-21 format).

## Features

- **STEP File Parsing**: Parses ISO-10303-21 format STEP files.
- **PMI Extraction**:
  - Semantic PMI (Dimensions, Tolerances, Datums)
  - Presentation PMI (Polyline data)
- **Text Extraction (OCR)**: Recognizes text by converting Presentation PMI polylines into images for OCR processing.

## Setup

### 1. Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Install OCR Libraries

To use the text extraction feature, installing an OCR library is recommended.

```bash
pip install easyocr  # Recommended (GPU support, multi-language support)
# or
pip install pytesseract  # Lightweight alternative
```

## Usage

### Basic Usage

```bash
python src/main.py <path_to_step_file>
```

### OCR Options

```bash
# Specify preset (adjusts image size for better recognition)
python src/main.py sample.stp --ocr-preset ocr_large

# Specify minimum confidence threshold
python src/main.py sample.stp --min-confidence 0.8

# Keep temporary directory (useful for debugging generated images)
python src/main.py sample.stp --keep-temp-dir
```

### Command Line Options

| Option | Description | Default |
|---|---|---|
| `--ocr-engine` | OCR Engine to use (`auto`, `easyocr`, `tesseract`) | `auto` |
| `--ocr-preset` | Image size preset (`ocr_small`, `ocr`, `ocr_large`) | `ocr` |
| `--ocr-languages` | Languages for OCR recognition | `en` |
| `--min-confidence` | Minimum confidence threshold for OCR results | `0.5` |
| `--temp-dir` | Directory for temporary OCR images | Current directory |
| `--keep-temp-dir` | Flag to keep the temporary directory after execution | False (Deleted) |

## Project Structure

```
cad_reader2/
├── src/
│   ├── __init__.py
│   ├── main.py                           # CLI Entry Point
│   ├── step_reader.py                    # STEP File Loader & Parser
│   ├── step_header.py                    # HEADER Section Data Structure
│   ├── step_pmi.py                       # PMI Data Structure
│   ├── presentation_pmi_image_converter.py  # Converts PMI polylines to images
│   └── pmi_ocr.py                        # OCR processing for PMI images
├── tests/
│   ├── __init__.py
│   ├── fixtures/                         # Test STEP files
│   └── test_step_reader.py               # Unit Tests
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

- **Pillow**: Image processing (Generating PMI images)
- **pytest**: Running tests

### Optional (For OCR)

- **EasyOCR**: High-accuracy OCR with GPU support (Recommended)
- **pytesseract**: Lightweight OCR engine wrapper

## Example Output

```
Loading STEP file: sample.stp
--------------------------------------------------
ISO Version: ISO-10303-21
HEADER Section: 3 items
DATA Section: 45764 entities
--------------------------------------------------

[PMI Data]
  [Semantic PMI - Dimensions]
    Dimensional Location (DIMENSIONAL_LOCATION): 42 items
    Dimensional Size (DIMENSIONAL_SIZE): 11 items
  [Semantic PMI - Tolerances]
    Geometric Tolerances: 50 items
  [Presentation PMI]
    Polylines: 3245 items

[Extracted Text]
  OCR: engine=easyocr, preset=ocr, languages=['en'], min_confidence=0.5
  Processing OCR...
  Extracted Items: 419 items
    1. NOTES:
    2. MATERIAL: ALUMINUM
    ...
```

## License

MIT

---

<a id="japanese"></a>

# CAD Reader - STEP File Text Extractor

STEPファイル（ISO-10303-21形式）からテキストデータとPMI（Product Manufacturing Information）を抽出するPythonツールです。

## 機能

- **STEPファイル解析**: ISO-10303-21形式のSTEPファイルを解析
- **PMI抽出**: 
  - Semantic PMI（寸法、公差、データム）
  - Presentation PMI（ポリラインデータ）
- **テキスト抽出（OCR）**: Presentation PMIのポリラインを画像化してOCRでテキスト認識

## セットアップ

### 1. Python仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. OCR機能を使用する場合（オプション）

```bash
pip install easyocr  # 推奨（GPU対応、多言語サポート）
# または
pip install pytesseract  # 軽量
```

## 使い方

### 基本的な使い方

```bash
python src/main.py <STEPファイルのパス>
```

### OCRオプション

```bash
# プリセット指定（画像サイズ）
python src/main.py sample.stp --ocr-preset ocr_large

# 信頼度閾値指定
python src/main.py sample.stp --min-confidence 0.8

# 一時ディレクトリを保持（デバッグ用）
python src/main.py sample.stp --keep-temp-dir
```

### コマンドラインオプション

| オプション | 説明 | デフォルト |
|------------|------|-----------|
| `--ocr-engine` | OCRエンジン (auto/easyocr/tesseract) | auto |
| `--ocr-preset` | 画像サイズプリセット (ocr_small/ocr/ocr_large) | ocr |
| `--ocr-languages` | OCR認識言語 | en |
| `--min-confidence` | OCR最小信頼度 | 0.5 |
| `--temp-dir` | OCR一時ディレクトリ | カレント |
| `--keep-temp-dir` | 一時ディレクトリを削除しない | 削除する |

## プロジェクト構成

```
cad_reader2/
├── src/
│   ├── __init__.py
│   ├── main.py                           # CLIエントリーポイント
│   ├── step_reader.py                    # STEPファイル読み込み・解析
│   ├── step_header.py                    # HEADERセクションのデータ構造
│   ├── step_pmi.py                       # PMIデータ構造
│   ├── presentation_pmi_image_converter.py  # PMIポリラインを画像に変換
│   └── pmi_ocr.py                        # PMI画像のOCR処理
├── tests/
│   ├── __init__.py
│   ├── fixtures/                         # テスト用STEPファイル
│   └── test_step_reader.py               # ユニットテスト
├── requirements.txt
├── README.md
└── .gitignore
```

## 必要なライブラリ

- **Pillow**: 画像処理（PMI画像生成）
- **pytest**: テスト実行

### オプション（OCR機能）

- **EasyOCR**: GPU対応の高精度OCR（推奨）
- **pytesseract**: 軽量なOCRエンジン

## 出力例

```
STEPファイルを読み込み中: sample.stp
--------------------------------------------------
ISO Version: ISO-10303-21
HEADERセクション: 3 件
DATAセクション: 45764 エンティティ
--------------------------------------------------

【PMIデータ】
  [Semantic PMI - Dimensions]
    位置寸法 (DIMENSIONAL_LOCATION): 42 件
    サイズ寸法 (DIMENSIONAL_SIZE): 11 件
  [Semantic PMI - Tolerances]
    幾何公差: 50 件
  [Presentation PMI]
    ポリライン: 3245 件

【抽出されたテキスト】
  OCR: エンジン=easyocr, プリセット=ocr, 言語=['en'], 最小信頼度=0.5
  OCR処理中...
  抽出件数: 419 件
    1. NOTES:
    2. MATERIAL: ALUMINUM
    ...
```

## ライセンス

MIT
