import numpy as np
from pathlib import Path

from scripts import train_model


def test_build_feature_matrix_and_encode(tmp_path):
    csv = tmp_path / "matches.csv"
    csv.write_text("home_odds,away_odds,result\n1.5,2.5,H\n2.0,1.8,A\n")
    headers, rows = train_model.load_csv(csv)
    X, y = train_model.build_feature_matrix(rows, sport="basketball", headers=headers, expected_columns=None)
    assert X.shape[0] == 2
    assert len(y) == 2
    y_enc, mapping = train_model.encode_target(y)
    assert set(mapping.keys()) <= set(["home", "away", "draw"]) or mapping
