#%%
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import seaborn as sns
import matplotlib.pyplot as plt

#%%


# Load and preprocess data
def load_data(file_path):
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    # Clean and preprocess data
    df = df[['PS (w%)', 'HDPE (w%)', 'PP (w%)', 
            'Reaction temperature', 'Vapor residence time (s)',
            'Total aromatics (w%)', 'Styrene (w%)', 'BTX (w%)']]
    
    # Handle range values in vapor residence time (take midpoint)
    df['Vapor residence time (s)'] = df['Vapor residence time (s)'].apply(
        lambda x: np.mean(list(map(float, str(x).split('-')))) if '-' in str(x) else float(x)
    )
    
    # Convert all columns to numeric and handle missing values
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    
    return df

# %%
df = load_data('astonML_SESA.xlsx')
X = df[['PS (w%)', 'HDPE (w%)', 
       'Reaction temperature', 'Vapor residence time (s)']]
y = df[['Styrene (w%)', 'BTX (w%)']]

#%%

# %%
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
import pandas as pd
from sklearn.metrics import r2_score

file_path= pd.read_excel('c:/Users/adejare/OneDrive - Iowa State University/Desktop/SESA/PS_Pyrolysis_Report_1/astonML_SESA.xlsx')

# Define the LinearRegressionTorch class
class LinearRegressionTorch(nn.Module):
    def __init__(self, input_size, output_size):
        super(LinearRegressionTorch, self).__init__()
        self.linear = nn.Linear(input_size, output_size)
    
    def forward(self, x):
        return self.linear(x)

# Load and preprocess data
def load_data(file_path):
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    # Clean and preprocess data
    df = df[['PS (w%)', 'HDPE (w%)', 
            'Reaction temperature', 'Vapor residence time (s)',
            'Total aromatics (w%)', 'Styrene (w%)', 'BTX (w%)']]
    
    # Handle range values in vapor residence time (take midpoint)
    df['Vapor residence time (s)'] = df['Vapor residence time (s)'].apply(
        lambda x: np.mean(list(map(float, str(x).split('-')))) if '-' in str(x) else float(x)
    )
    
    # Convert all columns to numeric and handle missing values
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    
    return df

# Prepare data
df = load_data('astonML_SESA.xlsx')
X = df[['PS (w%)', 'HDPE (w%)', 
       'Reaction temperature', 'Vapor residence time (s)']]
y = df[['BTX (w%)', 'Styrene (w%)']]

# Split data
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Convert to PyTorch tensors
X_train_tensor = torch.FloatTensor(X_train_scaled)
y_train_tensor = torch.FloatTensor(y_train.values)
X_test_tensor = torch.FloatTensor(X_test_scaled)
y_test_tensor = torch.FloatTensor(y_test.values)

# Define model and hyperparameters
input_dim = X_train_scaled.shape[1]
output_dim = y_train.shape[1]
model = LinearRegressionTorch(input_size=input_dim, output_size=output_dim)
#%%
# Define loss function and optimizer
loss_fun = nn.MSELoss()
#%%
LR = 0.09
optimizer = torch.optim.SGD(model.parameters(), lr=LR)

# Train the model
losses, slope, bias = [], [], []
NUM_EPOCHS = 1000
for epoch in range(NUM_EPOCHS):
    
    # set gradients to zero
    optimizer.zero_grad()

    # forward pass
    y_pred = model(X_train_tensor)

    # calculate loss
    loss = loss_fun(y_pred, y_train_tensor)
    loss.backward()

    # update parameters
    optimizer.step()

    # get parameters
    for name, param in model.named_parameters():
        if param.requires_grad:
            if name == 'linear.weight':
                slope.append(param.data.numpy())
            if name == 'linear.bias':
                bias.append(param.data.numpy())

    # store loss
    losses.append(float(loss.data))
    # print loss
    if (epoch % 100 == 0):
        print(f"Epoch {epoch}, Loss: {loss.data}")

# Evaluate the model
model.eval()
with torch.no_grad():
    y_pred_test = model(X_test_tensor)
    test_loss = loss_fun(y_pred_test, y_test_tensor)
    print(f"Test Loss: {test_loss:.4f}")

# Calculate per-output metrics
btx_pred = y_pred_test[:, 0].numpy()
styrene_pred = y_pred_test[:, 1].numpy()
btx_true = y_test_tensor[:, 0].numpy()
styrene_true = y_test_tensor[:, 1].numpy()

btx_mae = np.mean(np.abs(btx_true - btx_pred))
styrene_mae = np.mean(np.abs(styrene_true - styrene_pred))
print(f"BTX MAE: {btx_mae:.4f}")
print(f"Styrene MAE: {styrene_mae:.4f}")

# Plot training loss
plt.figure(figsize=(10, 5))
plt.plot(losses)
plt.title('Training Loss')
plt.xlabel('Epoch')
plt.ylabel('MSE Loss')
plt.show()

# Plot predictions vs actual values
plt.figure(figsize=(15, 6))
plt.subplot(1, 2, 1)
plt.scatter(btx_true, btx_pred)
plt.plot([min(btx_true), max(btx_true)], [min(btx_true), max(btx_true)], 'r--')
plt.title('BTX: Actual vs Predicted')
plt.xlabel('Actual')
plt.ylabel('Predicted')

plt.subplot(1, 2, 2)
plt.scatter(styrene_true, styrene_pred)
plt.plot([min(styrene_true), max(styrene_true)], [min(styrene_true), max(styrene_true)], 'r--')
plt.title('Styrene: Actual vs Predicted')
plt.xlabel('Actual')
plt.ylabel('Predicted')
plt.tight_layout()
plt.show()

# %%

def calculate_r2(y_true, y_pred):
    """Calculate R² for each output dimension"""
    r2_values = []
    for i in range(y_true.shape[1]):
        r2 = r2_score(y_true[:, i].numpy(), y_pred[:, i].numpy())
        r2_values.append(r2)
    return r2_values

# ... [model training code] ...

# Evaluate the model with R²
model.eval()
with torch.no_grad():
    y_pred_test = model(X_test_tensor)
    test_loss = loss_fun(y_pred_test, y_test_tensor)
    
    # Calculate R² for each target variable
    r2_values = calculate_r2(y_test_tensor, y_pred_test)
    
    print(f"Test Loss: {test_loss:.4f}")
    print(f"BTX R² Score: {r2_values[0]:.4f}")
    print(f"Styrene R² Score: {r2_values[1]:.4f}")

# Enhanced visualization with R² displayed on plots
plt.figure(figsize=(15, 6))
targets = ['BTX (w%)', 'Styrene (w%)']

for i, target in enumerate(targets):
    plt.subplot(1, 2, i+1)
    plt.scatter(y_test_tensor[:, i].numpy(), y_pred_test[:, i].numpy(), alpha=0.7)
    
    # Add perfect prediction line
    min_val = min(y_test_tensor[:, i].min().item(), y_pred_test[:, i].min().item())
    max_val = max(y_test_tensor[:, i].max().item(), y_pred_test[:, i].max().item())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--')
    
    plt.xlabel('Actual')
    plt.ylabel('Predicted')
    plt.title(f'{target}')
    
    # Display R² value directly on plot
    plt.text(min_val + 0.1*(max_val-min_val), max_val - 0.2*(max_val-min_val), 
             f'R² = {r2_values[i]:.4f}', fontsize=12)

plt.tight_layout()
plt.savefig('prediction_performance_with_r2.png')
plt.show()
# %%
#model.save('pyrolysis_model.h5')
torch.save(model.state_dict(), 'pyrolysis_model.pth')
#%%
#where I added batch

# Set learning rate and initialize optimizer
learning_rate = 0.09
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)

# Training configuration
NUM_EPOCHS = 1000
BATCH_SIZE = 4
batches_per_epoch = (len(X_train) + BATCH_SIZE - 1) // BATCH_SIZE  # Calculate total batches per epoch

# Trackers
losses = []
slope, bias = [], []
batch_numbers = []  # To track batch numbers for visualization

# Training loop
fNUM_EPOCHS = 1000
BATCH_SIZE = 4
batches_per_epoch = len(X_train_tensor) // BATCH_SIZE

for epoch in range(NUM_EPOCHS):
    for batch_idx in range(0, len(X_train_tensor), BATCH_SIZE):
        # Get batch data from TENSORS
        X_batch = X_train_tensor[batch_idx:batch_idx+BATCH_SIZE]
        y_batch = y_train_tensor[batch_idx:batch_idx+BATCH_SIZE]
        
        # Forward pass
        optimizer.zero_grad()
        y_pred = model(X_batch)
        
        # Compute loss
        loss = loss_fun(y_pred, y_batch)
        
        # Backpropagation
        loss.backward()
        optimizer.step()
        
    # Parameter tracking and printing remains the same...

        
        # Store loss and batch number
        losses.append(loss.item())
        batch_numbers.append(epoch * batches_per_epoch + (batch_idx//BATCH_SIZE))
        
    # Track parameters at end of each epoch
    with torch.no_grad():
        for name, param in model.named_parameters():
            if 'weight' in name:
                slope.append(param.data.numpy()[0][0])
            elif 'bias' in name:
                bias.append(param.data.numpy()[0])

    # Print progress every 100 epochs
    if epoch % 100 == 0:
        avg_loss = np.mean(losses[-batches_per_epoch:])  # Average loss for current epoch
        print(f"Epoch {epoch:4d} | Batch {batch_idx//BATCH_SIZE:4d} | Avg Loss: {avg_loss:.4f}")

# Visualization
plt.figure(figsize=(15, 5))

# Loss development by batch
plt.subplot(1, 3, 1)
sns.lineplot(x=batch_numbers, y=losses)
plt.title('Loss per Batch')
plt.xlabel('Batch Number')
plt.ylabel('Loss')

# Bias development by epoch
plt.subplot(1, 3, 2)
sns.lineplot(x=range(len(bias)), y=bias)
plt.title('Bias Development')
plt.xlabel('Epoch Number')

# Slope development by epoch
plt.subplot(1, 3, 3)
sns.lineplot(x=range(len(slope)), y=slope)
plt.title('Slope Development')
plt.xlabel('Epoch Number')

plt.tight_layout()
plt.show()

# %%
from skorch import NeuralNetRegressor
from sklearn.model_selection import GridSearchCV

# Convert data to numpy arrays (skorch requirement)
X_train_np = X_train_scaled.astype(np.float32)
y_train_np = y_train.astype(np.float32)

# Define neural network architecture
class PyrolysisNet(nn.Module):
    def __init__(self, num_inputs=3, num_outputs=2):
        super().__init__()
        self.fc1 = nn.Linear(num_inputs, 128)
        self.fc2 = nn.Linear(128, 64)
        self.output = nn.Linear(64, num_outputs)
        
    def forward(self, X):
        X = torch.relu(self.fc1(X))
        X = torch.relu(self.fc2(X))
        return self.output(X)

# Skorch regressor setup
net = NeuralNetRegressor(
    PyrolysisNet,
    max_epochs=200,
    optimizer=torch.optim.SGD,
    optimizer__lr=0.02,
    iterator_train__shuffle=True,
    train_split=False,
    verbose=0
)

# Parameter grid
params = {
    'optimizer__lr': [0.02, 0.05, 0.08],
    'max_epochs': [10, 200, 500],
    'module__num_inputs': [X_train_np.shape[1]],
    'module__num_outputs': [y_train_np.shape[1]]
}

# Grid search
gs = GridSearchCV(net, params, refit=True, cv=3, scoring='r2', verbose=2)
gs.fit(X_train_np, y_train_np)

# Best model evaluation
best_model = gs.best_estimator_
y_pred = best_model.predict(X_test_scaled.astype(np.float32))

print(f"Best R²: {gs.best_score_:.3f} with params: {gs.best_params_}")

# %%
# Convert pandas DataFrames to NumPy arrays before grid search
# After data splitting and scaling, before model training
from skorch import NeuralNetRegressor
from sklearn.model_selection import GridSearchCV
# Convert to numpy arrays for GridSearchCV
X_train_np = X_train_scaled.astype(np.float32)
y_train_np = y_train.values.astype(np.float32)  # Use .values for DataFrame conversion

# Define skorch-compatible model
net = NeuralNetRegressor(
    LinearRegressionTorch,
    max_epochs=10,
    optimizer=torch.optim.SGD,
    optimizer__lr=0.1,
    iterator_train__shuffle=True,
    train_split=False,
    verbose=0
)

# Parameter grid with correct skorch parameter syntax
params = {
    'optimizer__lr': [0.06, 0.07, 0.08, 0.09],  # Fixed parameter name
    'max_epochs': [500, 700, 1200, 1500],
    'module__input_size': [X_train_np.shape[1]],
    'module__output_size': [y_train_np.shape[1]]
}

# Run grid search
gs = GridSearchCV(net, params, refit=True, cv=3, scoring='r2', verbose=2)
gs.fit(X_train_np, y_train_np)

# Best model evaluation
print(f"Best R²: {gs.best_score_:.3f} with params: {gs.best_params_}")

# %%
