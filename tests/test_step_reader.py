"""
StepReaderのユニットテスト
"""

import pytest
from pathlib import Path
import sys

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from step_reader import StepReader


class TestStepReader:
    """StepReaderのテストクラス"""
    
    @pytest.fixture
    def sample_step_path(self) -> Path:
        """サンプルSTEPファイルのパスを返す"""
        return Path(__file__).parent / 'fixtures' / 'sample.step'
    
    @pytest.fixture
    def full_sample_step_path(self) -> Path:
        """フルサンプルSTEPファイルのパスを返す"""
        return Path(__file__).parent / 'fixtures' / 'full_sample.step'
    
    def test_load_basic_step_file(self, sample_step_path: Path):
        """基本的なSTEPファイルの読み込みテスト"""
        reader = StepReader(sample_step_path)
        result = reader.load()
        
        assert result is True
        assert reader.iso_version == "ISO-10303-21"
    
    def test_header_section_parsed(self, sample_step_path: Path):
        """HEADERセクションが正しく解析されることをテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        assert len(reader.headers) == 3
        assert any('FILE_DESCRIPTION' in h for h in reader.headers)
        assert any('FILE_NAME' in h for h in reader.headers)
        assert any('FILE_SCHEMA' in h for h in reader.headers)
    
    def test_header_structured(self, sample_step_path: Path):
        """構造化されたヘッダーが正しく解析されることをテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        # FILE_DESCRIPTION
        impl_level = reader.header.file_description.implementation_level
        assert impl_level.raw == "2;1"
        assert impl_level.file_edition == 2
        assert impl_level.minimum_edition == 1
        
        # FILE_NAME
        assert reader.header.file_name.name == "sample.step"
        assert reader.header.file_name.time_stamp == "2026-02-14T10:00:00"
        assert reader.header.file_name.author == ["Author"]
        assert reader.header.file_name.organization == ["Company"]
        
        # FILE_SCHEMA
        assert "AUTOMOTIVE_DESIGN" in reader.header.file_schema.schemas
    
    def test_header_to_dict(self, sample_step_path: Path):
        """ヘッダーを辞書形式に変換できることをテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        header_dict = reader.header.to_dict()
        
        assert 'file_description' in header_dict
        assert 'file_name' in header_dict
        assert 'file_schema' in header_dict
        assert header_dict['file_name']['name'] == "sample.step"
    
    def test_data_section_parsed(self, sample_step_path: Path):
        """DATAセクションが正しく解析されることをテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        # DATAセクションには複数のエンティティがある
        assert len(reader.data) > 0
        
        # #1 = APPLICATION_CONTEXT(...) が存在するはず
        assert 1 in reader.data
        assert 'APPLICATION_CONTEXT' in reader.data[1]
        
        # #10 = CARTESIAN_POINT(...) が存在するはず
        assert 10 in reader.data
        assert 'CARTESIAN_POINT' in reader.data[10]
    
    def test_data_section_key_is_integer(self, sample_step_path: Path):
        """DATAセクションのキーがint型であることをテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        for key in reader.data.keys():
            assert isinstance(key, int)
    
    def test_full_sample_all_sections(self, full_sample_step_path: Path):
        """全セクションを含むサンプルの解析テスト"""
        reader = StepReader(full_sample_step_path)
        reader.load()
        
        # HEADERセクション
        assert len(reader.headers) > 0
        
        # ANCHORセクション
        assert len(reader.anchors) > 0
        
        # REFERENCEセクション
        assert len(reader.references) > 0
        
        # DATAセクション
        assert len(reader.data) > 0
        
        # SIGNATUREセクション
        assert len(reader.signatures) > 0
    
    def test_comments_are_removed(self, full_sample_step_path: Path):
        """コメントが正しく除去されることをテスト"""
        reader = StepReader(full_sample_step_path)
        reader.load()
        
        # コメントが含まれていないことを確認
        for header in reader.headers:
            assert '/*' not in header
            assert '*/' not in header
        
        for _, data in reader.data.items():
            assert '/*' not in data
            assert '*/' not in data
    
    def test_get_summary(self, sample_step_path: Path):
        """サマリー取得のテスト"""
        reader = StepReader(sample_step_path)
        reader.load()
        
        summary = reader.get_summary()
        
        assert 'file_path' in summary
        assert 'iso_version' in summary
        assert 'is_loaded' in summary
        assert 'header_count' in summary
        assert 'data_count' in summary
        assert summary['is_loaded'] is True
    
    def test_nonexistent_file(self):
        """存在しないファイルの読み込みテスト"""
        reader = StepReader(Path('/nonexistent/path/file.step'))
        
        with pytest.warns():
            result = reader.load()
        
        assert result is False
    
    def test_get_raw_content(self, sample_step_path: Path):
        """生データ取得のテスト"""
        reader = StepReader(sample_step_path)
        content = reader.get_raw_content()
        
        assert 'ISO-10303-21' in content
        assert 'HEADER' in content
        assert 'DATA' in content


class TestStepReaderEdgeCases:
    """エッジケースのテスト"""
    
    @pytest.fixture
    def temp_step_file(self, tmp_path: Path) -> Path:
        """一時的なSTEPファイルを作成"""
        step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test'), '1');
ENDSEC;
DATA;
#1 = TEST_ENTITY('value');
ENDSEC;
END-ISO-10303-21;
"""
        file_path = tmp_path / "temp.step"
        file_path.write_text(step_content)
        return file_path
    
    def test_minimal_step_file(self, temp_step_file: Path):
        """最小構成のSTEPファイルテスト"""
        reader = StepReader(temp_step_file)
        result = reader.load()
        
        assert result is True
        assert len(reader.headers) == 1
        assert len(reader.data) == 1
        assert 1 in reader.data
    
    def test_unknown_section_warning(self, tmp_path: Path):
        """未知のセクションに対する警告テスト"""
        step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test'), '1');
ENDSEC;
UNKNOWN_SECTION;
SOME_DATA;
ENDSEC;
DATA;
#1 = TEST('value');
ENDSEC;
END-ISO-10303-21;
"""
        file_path = tmp_path / "unknown_section.step"
        file_path.write_text(step_content)
        
        reader = StepReader(file_path)
        
        with pytest.warns(match="未知のセクション"):
            reader.load()
        
        assert len(reader.others) == 1
        assert reader.others[0]['section_name'] == 'UNKNOWN_SECTION'


class TestExtractTexts:
    """extract_textsメソッドのテスト（OCRベース）"""
    
    def test_extract_texts_no_pmi_returns_empty(self, tmp_path: Path):
        """PMIがない場合は空リストを返すテスト"""
        step_content = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Test'), '1');
FILE_NAME('test.step', '2026-01-01', (''), (''), '', '', '');
FILE_SCHEMA(('SCHEMA'));
ENDSEC;
DATA;
#1 = PRODUCT('ProductA', 'Description', '', (#2));
#2 = LABEL('Label Text');
ENDSEC;
END-ISO-10303-21;
"""
        file_path = tmp_path / "extract_test.step"
        file_path.write_text(step_content)
        
        reader = StepReader(file_path)
        reader.load()
        # PMIがないのでOCRしても空リスト
        texts = reader.extract_texts()
        
        # DATA内の文字列は抽出されない（OCRのみ）
        assert 'ProductA' not in texts
        assert 'Description' not in texts
        assert 'Label Text' not in texts
        # PMIがなければ空
        assert texts == []