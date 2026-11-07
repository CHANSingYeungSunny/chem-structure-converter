import json

from chembridge.model_adapter import predict_with_fitted_model


def test_adapter_preserves_record_order(tmp_path):
    source = tmp_path / "molecules.json"
    source.write_text(json.dumps({"molecules": [{"id": "first", "smiles": "CCO"}, {"id": "second", "smiles": "CC"}]}))

    class FakePredictor:
        def predict(self, smiles):
            assert smiles == ["CCO", "CC"]
            return {"prediction": [[1.0], [2.0]]}

    result = predict_with_fitted_model(FakePredictor(), source, target_name="demo", units="dimensionless", model_id="test-fixture")
    assert result["record_ids"] == ["first", "second"]
    assert result["raw_prediction"]["prediction"] == [[1.0], [2.0]]
