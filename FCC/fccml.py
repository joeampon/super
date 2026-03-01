#%%
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
from sklearn import tree
import numpy as np
from sklearn.linear_model import LinearRegression

import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.neighbors import KNeighborsRegressor
#%%
data = pd.read_csv('matiasDataClean.csv').dropna()
# %%
# The first two columns are the inputs 
X = data.iloc[:, 0:2].values
# The columns from 3 to the end are the outputs
y = data.iloc[:, 2:].values
# %%# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# %%
# Function to train and evaluate a model
def train_and_evaluate_model(model, X_train, y_train, X_test, y_test):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"Model: {model.__class__.__name__}")
    print(f"Mean Squared Error: {mse:.4f}")
    print(f"R^2 Score: {r2:.4f}")
    print(f"Mean Absolute Error: {mae:.4f}\n")
    
    return model
model = DecisionTreeRegressor(random_state=42)
train_and_evaluate_model(model, X_train, y_train, X_test, y_test)


# %%
# Show an example prediction
example_input = np.array([[0.5, 0.5]])
example_prediction = model.predict(example_input)
print(f"Example input: {example_input}")
# %%
print(f"Example prediction: {example_prediction}")

# %%
# store the model
joblib.dump(model, 'fccCycleTimeToProds.pkl')
# %%
# Load the model
loaded_model = joblib.load('fccCycleTimeToProds.pkl')
# %%
example_input = np.array([[0.5, 0.5]])
loaded_model.predict(example_input)
# %%
