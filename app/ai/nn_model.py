try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = None
import os

# Force CPU — avoids CUDA errors on CPU-only hosts
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_base = (nn.Module if TORCH_AVAILABLE else object) if nn is not None else object

class MatchOutcomeNN(_base):
    """
    A basic neural network for match outcome prediction.
    It takes a vector of match features and outputs probabilities for Home Win, Draw, and Away Win.
    """
    def __init__(self, input_size: int, hidden_size: int, num_classes: int):
        super(MatchOutcomeNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        return out
