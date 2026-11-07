"""Optional model boundary; torch-molecule is NOT required by the converter.

The caller owns training/loading a suitable predictor and target metadata.
No weights are downloaded and no model is fitted here.
"""
import json
from pathlib import Path


def predict_with_fitted_model(predictor, molecules_json, *, target_name, units, model_id):
    if not all(isinstance(x, str) and x.strip() for x in [target_name, units, model_id]):
        raise ValueError("Supply a target, units (or 'dimensionless') and model/checkpoint identifier.")
    document = json.loads(Path(molecules_json).read_text(encoding="utf-8"))
    molecules = document["molecules"]
    smiles = [m["smiles"] for m in molecules]
    if not smiles:
        raise ValueError("No successfully parsed molecules are available for prediction.")
    result = predictor.predict(smiles)
    return {"record_ids": [m["id"] for m in molecules], "target": target_name,
            "units": units, "model_id": model_id, "raw_prediction": result}
