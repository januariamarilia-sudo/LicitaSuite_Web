from licitasuite.pipeline.workflow import Workflow
def test_workflow():
    assert len(Workflow().run())==9
