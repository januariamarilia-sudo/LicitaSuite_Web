from licitasuite.engine.pipeline import Pipeline
from licitasuite.generators.docx_engine.ata_generator import AtaGenerator
from licitasuite.validation.engine import ValidationEngine

def test_imports():
    assert Pipeline
    assert AtaGenerator
    assert ValidationEngine
