# Define the model

import torch
import torch.nn as nn

class DeepNN(nn.Module):
    def __init__(self, input_size=4, output_size=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_size)
        )

    def forward(self, x):
        return self.net(x)