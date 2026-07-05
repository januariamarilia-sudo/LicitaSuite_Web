from licitasuite.models.supplier_registry import SupplierRegistry
from licitasuite.engine.supplier_registry_service import SupplierRegistryService

def test_supplier_registry_imports():
    assert SupplierRegistry
    assert SupplierRegistryService
