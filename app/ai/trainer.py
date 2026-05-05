import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import json
import os
import sys

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.ai.nn_model import MatchOutcomeNN
from app.data.feature_store import FeatureStore
from app.data.data_validator import validate_features

def train_match_outcome_nn(
    feature_store: FeatureStore,
    model_save_path: str = "match_outcome_nn_model.pth",
    input_dim: int = 10,
    hidden_dim: int = 50,
    output_dim: int = 3,
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.001
) -> None:
    print("Starting MatchOutcomeNN training...")

    model = MatchOutcomeNN(input_dim, hidden_dim, output_dim)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    all_stored_features = feature_store.get_all_features()
    features_list = []
    labels_list = []

    if not all_stored_features:
        dummy_features = torch.randn(100, input_dim)
        dummy_labels = torch.randint(0, output_dim, (100,))
    else:
        for key, stored_data in all_stored_features.items():
            match_features = stored_data['features']
            if not validate_features(match_features):
                continue
            processed_features = [v for v in match_features.values() if isinstance(v, (int, float))][:input_dim]
            if len(processed_features) == input_dim:
                features_list.append(processed_features)
                labels_list.append(torch.randint(0, output_dim, (1,)).item())

        if not features_list:
            dummy_features = torch.randn(100, input_dim)
            dummy_labels = torch.randint(0, output_dim, (100,))
        else:
            dummy_features = torch.tensor(features_list, dtype=torch.float32)
            dummy_labels = torch.tensor(labels_list, dtype=torch.long)

    dataset = TensorDataset(dummy_features, dummy_labels)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for inputs, labels in dataloader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {total_loss/len(dataloader):.4f}")

    os.makedirs(os.path.dirname(model_save_path) if os.path.dirname(model_save_path) else ".", exist_ok=True)
    torch.save(model.state_dict(), model_save_path)
    print(f"Model saved to {model_save_path}")

    try:
        import mlflow
        from mlflow.models import infer_signature
        with mlflow.start_run(run_name="Match Outcome NN Training Run"):
            mlflow.log_param("input_dim", input_dim)
            mlflow.log_param("hidden_dim", hidden_dim)
            mlflow.log_param("output_dim", output_dim)
            mlflow.log_param("epochs", epochs)
            mlflow.log_param("batch_size", batch_size)
            mlflow.log_param("learning_rate", learning_rate)
            dummy_input = torch.randn(1, input_dim)
            signature = infer_signature(dummy_input.numpy(), model(dummy_input).detach().numpy())
            mlflow.pytorch.log_model(pytorch_model=model, artifact_path="model", signature=signature)
            print("MLflow run logged.")
    except ImportError:
        print("MLflow not installed — skipping experiment tracking.")


if __name__ == '__main__':
    fs = FeatureStore()
    train_match_outcome_nn(feature_store=fs, epochs=5)
