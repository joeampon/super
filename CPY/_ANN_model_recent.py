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

file_path= pd.read_excel('C:/Users/adejare/OneDrive - Iowa State University/Desktop/SESA/PS_Pyrolysis_Report_1/astonML_SESA.xlsx')

# Define the LinearRegressionTorch class


# Load and preprocess data
def load_data(file_path):
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    # Clean and preprocess data
    df = df[['PS (w%)', 'HDPE (w%)', 
            'Reaction temperature', 'Vapor residence time (s)',
            'Total aromatics (w%)', 'Styrene (w%)', 'BTX (w%)', 'Gas', 'Liquid']]
    
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
X = df[['PS (w%)','HDPE (w%)',
       'Reaction temperature', 'Vapor residence time (s)']]
y = df[['BTX (w%)', 'Styrene (w%)', 'Total aromatics (w%)', 'Gas', 'Liquid']].values
#%%

#%%
# Split data

#where I added batch

# Set learning rate and initialize optimizer

# %%
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, root_mean_squared_error
import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt
#%%

torch.manual_seed(42)
np.random.seed(42)
random.seed(42)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# Sample input: load your dataset here
#df= pd.read_csv("your_dataset.csv")  # replace with actual file
X = df[['PS (w%)', 'HDPE (w%)',
       'Reaction temperature', 'Vapor residence time (s)']]
y = df[["BTX (w%)", "Styrene (w%)", "Total aromatics (w%)","Gas","Liquid"]].values

# Scale inputs
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Convert to torch tensors
X_train_tensor = torch.FloatTensor(X_train)
y_train_tensor = torch.FloatTensor(y_train)
X_test_tensor = torch.FloatTensor(X_test)
y_test_tensor = torch.FloatTensor(y_test)

# Define the model
class DeepNN(nn.Module):
    def __init__(self, input_size=4, output_size=5):
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

model = DeepNN(input_size=4, output_size=5)

# Training setup
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.002)
epochs = 1000

# Training loop
for epoch in range(epochs):
    model.train()
    optimizer.zero_grad()
    outputs = model(X_train_tensor)
    loss = criterion(outputs, y_train_tensor)
    loss.backward()
    optimizer.step()

    if (epoch+1) % 5 == 0:
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")

# Evaluation
model.eval()
with torch.no_grad():
    y_pred_test = model(X_test_tensor).numpy()
    y_pred_train = model(X_train_tensor).numpy()

# Calculate performance
print("\nModel Performance:")
targets = ["BTX", "Styrene", "Aromatic", "Gas", "Liquid"]
for i, name in enumerate(targets):
    r2 = r2_score(y_test[:, i], y_pred_test[:, i])
    rmse = root_mean_squared_error(y_test[:, i], y_pred_test[:, i])
    mae = mean_absolute_error(y_test[:, i], y_pred_test[:, i])
    print(f"{name} R² Score: {r2:.4f}, RMSE = {rmse:.4f}, MAE = {mae =:.4f}")

test_loss = mean_squared_error(y_test, y_pred_test)
print(f"Test MSE: {test_loss:.4f}")
#%%
X_all_scaled = scaler.transform(X)
X_all_tensor = torch.FloatTensor(X_all_scaled)
with torch.no_grad():
    predictions = model(X_all_tensor).numpy()
    
df['Predicted BTX'] = predictions[:, 0]
df['Predicted Styrene'] = predictions[:, 1]
df['Predicted Aromatic'] = predictions[:, 2]
df['Predicted Gas'] = predictions[:, 3]

df.to_excel("predicted_outputs_from_model.xlsx", index=False)
print("\nPredicted results saved to 'predicted_outputs_from_model.xlsx'.")
#%%

torch.save(model.state_dict(), "deepnn_model.pth")
import joblib
joblib.dump(scaler, "deepnn_scaler.pkl")

# %%
targets = ["BTX", "Styrene", "Aromatic", "Gas", "Liquid", "Solid"]
fig, axes = plt.subplots(2, 3, figsize=(12, 10))

for i, ax in enumerate(axes.flatten()):
    r2 = r2_score(y_test[:, i], y_pred_test[:, i])
    ax.scatter(y_test[:, i], y_pred_test[:, i], alpha=0.7)
    ax.plot([y_test[:, i].min(), y_test[:, i].max()],
            [y_test[:, i].min(), y_test[:, i].max()],
            'r--')
    ax.set_title(f"{targets[i]}: R² = {r2:.4f}")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.grid(True)

plt.tight_layout()
plt.show()
# %%
torch.save(model.state_dict(), "deepnn_model.pth")
import joblib
joblib.dump(scaler, "deepnn_scaler.pkl")
# %%
import torch, numpy as np, random

torch.manual_seed(42)
np.random.seed(42)
random.seed(42)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# %%
# Function to predict product yields vs. temperature
def predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=20):
    """
    Sweep reaction temperature and predict BTX, Styrene, Total aromatics, and Liquid.
    
    Parameters:
        model: trained PyTorch model
        scaler: fitted StandardScaler
        ps: PS content (w%)
        hdpe: HDPE content (w%)
        tau: vapor residence time (s)
        temp_range: tuple(min_temp, max_temp) in °C
        steps: number of temperature points
    
    Returns:
        DataFrame of predictions
    """
    temps = np.linspace(temp_range[0], temp_range[1], steps)
    X_sweep = pd.DataFrame({
        'PS (w%)': [ps] * steps,
        'HDPE (w%)': [hdpe] * steps,
        'Reaction temperature': temps,
        'Vapor residence time (s)': [tau] * steps
    })
    
    # Scale inputs
    X_scaled = scaler.transform(X_sweep)
    X_tensor = torch.FloatTensor(X_scaled)
    
    # Predictions
    model.eval()
    with torch.no_grad():
        preds = model(X_tensor).numpy()
    
    results = pd.DataFrame({
        'Temperature (°C)': temps,
        'Predicted BTX (w%)': preds[:, 0],
        'Predicted Styrene (w%)': preds[:, 1],
        'Predicted Aromatics (w%)': preds[:, 2],
        'Predicted Liquid (w%)': preds[:, 4]
    })
    
    return results

# Example usage
results = predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=25)
print(results)

# Plot trends
plt.figure(figsize=(10, 6))
plt.plot(results['Temperature (°C)'], results['Predicted BTX (w%)'], label='BTX')
plt.plot(results['Temperature (°C)'], results['Predicted Styrene (w%)'], label='Styrene')
plt.plot(results['Temperature (°C)'], results['Predicted Aromatics (w%)'], label='Aromatics')
plt.plot(results['Temperature (°C)'], results['Predicted Liquid (w%)'], label='Liquid')
plt.xlabel("Reaction Temperature (°C)")
plt.ylabel("Yield (w%)")
plt.title("Predicted Yields vs. Reaction Temperature")
plt.legend()
plt.grid(True)
plt.show()


# %%
# %%
# Function to predict product yields vs. temperature
def predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=20):
    """
    Sweep reaction temperature and predict BTX, Styrene, Total aromatics, and Liquid.

    Parameters:
        model: trained PyTorch model
        scaler: fitted StandardScaler
        ps: PS content (w%)
        hdpe: HDPE content (w%)
        tau: vapor residence time (s)
        temp_range: tuple(min_temp, max_temp) in °C
        steps: number of temperature points

    Returns:
        DataFrame of predictions including a total % check
    """
    temps = np.linspace(temp_range[0], temp_range[1], steps)
    X_sweep = pd.DataFrame({
        'PS (w%)': [ps] * steps,
        'HDPE (w%)': [hdpe] * steps,
        'Reaction temperature': temps,
        'Vapor residence time (s)': [tau] * steps
    })

    # Scale inputs
    X_scaled = scaler.transform(X_sweep)
    X_tensor = torch.FloatTensor(X_scaled)

    # Predictions
    model.eval()
    with torch.no_grad():
        preds = model(X_tensor).numpy()

    # Build results DataFrame
    results = pd.DataFrame({
        'Temperature (°C)': temps,
        'Predicted BTX (w%)': preds[:, 0],
        'Predicted Styrene (w%)': preds[:, 1],
        'Predicted Aromatics (w%)': preds[:, 2],
        'Predicted Gas (w%)': preds[:, 3],
        'Predicted Liquid (w%)': preds[:, 4],
       # 'Predicted Solid (w%)': preds[:, 5],
    })

    # Add total % column for sanity check
    results['Total (w%)'] = (
        results['Predicted BTX (w%)'] +
        results['Predicted Styrene (w%)'] +
        results['Predicted Aromatics (w%)'] +
        results['Predicted Gas (w%)'] +
        results['Predicted Liquid (w%)']
        #results['Predicted Solid (w%)']
    )

    return results


# Example usage
results = predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=25)
print(results)

# Plot trends
plt.figure(figsize=(10, 6))
plt.plot(results['Temperature (°C)'], results['Predicted BTX (w%)'], label='BTX')
plt.plot(results['Temperature (°C)'], results['Predicted Styrene (w%)'], label='Styrene')
plt.plot(results['Temperature (°C)'], results['Predicted Aromatics (w%)'], label='Aromatics')
plt.plot(results['Temperature (°C)'], results['Predicted Liquid (w%)'], label='Liquid')
plt.xlabel("Reaction Temperature (°C)")
plt.ylabel("Yield (w%)")
plt.title("Predicted Yields vs. Reaction Temperature")
plt.legend()
plt.grid(True)
plt.show()
#%%
# %%
# Function to predict product yields vs. temperature
# %%
# Function to predict product yields vs. temperature
def predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=20):
    """
    Sweep reaction temperature and predict BTX, Styrene, Total aromatics, and Liquid.

    Notes:
        - BTX and Styrene are sub-fractions of Total Aromatics
        - Total Aromatics is a fraction of the Liquid yield
    """
    temps = np.linspace(temp_range[0], temp_range[1], steps)
    X_sweep = pd.DataFrame({
        'PS (w%)': [ps] * steps,
        'HDPE (w%)': [hdpe] * steps,
        'Reaction temperature': temps,
        'Vapor residence time (s)': [tau] * steps
    })

    # Scale inputs
    X_scaled = scaler.transform(X_sweep)
    X_tensor = torch.FloatTensor(X_scaled)

    # Predictions
    model.eval()
    with torch.no_grad():
        preds = model(X_tensor).numpy()

    # Extract predicted values
    liquid_pred   = preds[:, 4]     # Liquid yield
    arom_pred     = preds[:, 2]     # Aromatic fraction in liquid
    btx_pred      = preds[:, 0]     # BTX fraction of aromatics
    styrene_pred  = preds[:, 1]     # Styrene fraction of aromatics

    # Calculate totals properly
    aromatics_in_liquid = (liquid_pred * arom_pred) / 100
    btx_in_liquid       = (aromatics_in_liquid * btx_pred) / 100
    styrene_in_liquid   = (aromatics_in_liquid * styrene_pred) / 100

    results = pd.DataFrame({
        'Temperature (°C)': temps,
        'Liquid (w%)': liquid_pred,
        'Total Aromatics in Liquid (w%)': aromatics_in_liquid,
        'BTX in Liquid (w%)': btx_in_liquid,
        'Styrene in Liquid (w%)': styrene_in_liquid,
        'Gas (w%)': preds[:, 3],
        #'Solid (w%)': preds[:, 5]
    })

    # Add a mass balance check: Liquid + Gas
    results['Overall Yield (w%)'] = results['Liquid (w%)'] + results['Gas (w%)']

    return results


# Example usage
results = predict_vs_temperature(model, scaler, ps=100, hdpe=0, tau=1.0, temp_range=(400, 800), steps=25)
print(results.head())

# Plot Aromatics breakdown
plt.figure(figsize=(10, 6))
plt.plot(results['Temperature (°C)'], results['Liquid (w%)'], label='Liquid')
plt.plot(results['Temperature (°C)'], results['Total Aromatics in Liquid (w%)'], label='Aromatics in Liquid')
plt.plot(results['Temperature (°C)'], results['BTX in Liquid (w%)'], label='BTX in Liquid')
plt.plot(results['Temperature (°C)'], results['Styrene in Liquid (w%)'], label='Styrene in Liquid')
plt.xlabel("Reaction Temperature (°C)")
plt.ylabel("Yield (w%)")
plt.title("Predicted Liquid & Aromatics Yields vs. Reaction Temperature")
plt.legend()
plt.grid(True)
plt.show()

# %%
# %% Predict at fixed temperatures
import numpy as np
import pandas as pd

# Define input conditions
# Example: PS = 100, HDPE = 0, tau = 1.0 s (change as needed)
temps = [500, 525, 550, 575, 600, 625, 650, 675, 700, 725, 750, 775, 800]
ps_val = 100.0
hdpe_val = 0.0
tau_val = 1.0

new_data = pd.DataFrame({
    "PS (w%)": [ps_val] * len(temps),
    "HDPE (w%)": [hdpe_val] * len(temps),
    "Reaction temperature": temps,
    "Vapor residence time (s)": [tau_val] * len(temps)
})

# Scale and convert to tensor
new_scaled = scaler.transform(new_data)
new_tensor = torch.FloatTensor(new_scaled)

# Predict
model.eval()
with torch.no_grad():
    preds = model(new_tensor).numpy()

# Put results in DataFrame
pred_df = pd.DataFrame(preds, columns=["BTX (w%)", "Styrene (w%)", "Total aromatics (w%)", "Gas (w%)", "Liquid (w%)"])
pred_df.insert(0, "Temperature (°C)", temps)

print("\nPredictions at selected temperatures:")
print(pred_df)

# Optionally save
pred_df.to_excel("fixed_temperature_predictions.xlsx", index=False)

# %%
