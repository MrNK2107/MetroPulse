import importlib, pathlib, pytest
BACKEND = pathlib.Path(__file__).resolve().parents[2]

@pytest.mark.parametrize("rel", ["app/rag", "app/simulation", "app/core", "app/source_ingestion.py",
    "engine/grid.py", "engine/prediction_generator.py", "engine/scenario_parser.py",
    "engine/simulation_explainability.py", "engine/translator.py", "engine/confidence.py",
    "engine/provenance.py", "engine/nl_engine/conversation.py", "engine/nl_engine/group_scorer.py"])
def test_simulator_module_is_gone(rel):
    assert not (BACKEND / rel).exists()

def test_llm_lives_in_app_llm():
    assert hasattr(importlib.import_module("app.llm"), "call_llm")

def test_models_keep_only_live_types():
    import engine.models as m
    for gone in ["SimulationParams", "GridState", "AggregateMetrics", "SimulationFrame", "Prediction"]:
        assert not hasattr(m, gone)
