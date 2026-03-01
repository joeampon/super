"""
Training pipeline for PyrolysisNet: predicts pyrolysis product yields
from feedstock composition and operating conditions.

Data: aston.xlsx (566 experiments from literature)
Approach: Masked loss to train on all usable rows despite sparse outputs.

Usage:
    python3.12 system/machine_learning/train.py
"""

import os
import sys
import re
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Shared data directory for CSV exports
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Add project root so we can import the shared plot style
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from system._plot_style import apply_style, COLORS, savefig, figsize

from model import PyrolysisNet

apply_style()

# ============================================================================
# Config
# ============================================================================

SEED = 42
BATCH_SIZE = 32
MAX_EPOCHS = 2000
EARLY_STOP_PATIENCE = 200
LR = 1e-3
WEIGHT_DECAY = 1e-4
SCHEDULER_PATIENCE = 50
SCHEDULER_FACTOR = 0.5
TEST_FRAC = 0.2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, 'aston.xlsx')
MODEL_SAVE_PATH = os.path.join(SCRIPT_DIR, 'pyrolysis_model.pt')
SCALER_SAVE_PATH = os.path.join(SCRIPT_DIR, 'scaler_params.pt')
PLOT_DIR = os.path.join(SCRIPT_DIR, 'plots')

INPUT_COLS = ['HDPE (w%)', 'LDPE (w%)', 'PP (w%)', 'Reaction temperature', 'Vapor residence time (s)']
OUTPUT_COLS = [
    'Liquid', 'Gas', 'Solid',
    'Gasoline range hydrocarbons', 'Diesel range hydrocarbons',
    'Total aromatics (w%)', 'BTX (w%)', 'Wax (>C21)',
]

np.random.seed(SEED)
torch.manual_seed(SEED)


# ============================================================================
# Data Preprocessing
# ============================================================================

def parse_value(val):
    """Convert a cell value to float, handling ranges and inequalities."""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return np.nan
    val = val.strip()
    if not val or val.lower() in ('nan', 'n/a', '-', '–', '—'):
        return np.nan

    # Range: "420-440" or "420–440" → midpoint
    range_match = re.match(r'^([\d.]+)\s*[-–—]\s*([\d.]+)$', val)
    if range_match:
        lo, hi = float(range_match.group(1)), float(range_match.group(2))
        return (lo + hi) / 2.0

    # Inequality: "< 0.2", ">5", "≤ 3.0" → take the numeric value
    ineq_match = re.match(r'^[<>≤≥~≈]\s*([\d.]+)$', val)
    if ineq_match:
        return float(ineq_match.group(1))

    # Try direct conversion
    try:
        return float(val)
    except ValueError:
        return np.nan


def load_and_preprocess():
    """Load aston.xlsx, filter, clean, and return tensors."""
    print("Loading data from", DATA_PATH)
    df = pd.read_excel(DATA_PATH, engine='openpyxl')
    print(f"  Raw rows: {len(df)}")

    # Parse all relevant columns to numeric
    all_cols = INPUT_COLS + OUTPUT_COLS
    for col in all_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_value)
        else:
            print(f"  WARNING: Column '{col}' not found in data!")
            df[col] = np.nan

    # Filter: polyolefin feedstocks (HDPE + LDPE + PP > 0)
    df['HDPE (w%)'] = df['HDPE (w%)'].fillna(0)
    df['LDPE (w%)'] = df['LDPE (w%)'].fillna(0)
    df['PP (w%)'] = df['PP (w%)'].fillna(0)
    polyolefin_mask = (df['HDPE (w%)'] + df['LDPE (w%)'] + df['PP (w%)']) > 0
    df = df[polyolefin_mask].copy()
    print(f"  After polyolefin filter: {len(df)}")

    # Remove solid yield outliers (> 20 wt%); mean is ~3%, these are from
    # studies reporting anomalously high char/solid fractions
    solid_outlier = df['Solid'].notna() & (df['Solid'] > 20)
    n_outliers = solid_outlier.sum()
    df = df[~solid_outlier].copy()
    print(f"  After removing {n_outliers} solid yield outliers (>20 wt%): {len(df)}")

    # Drop rows where BOTH temperature AND VRT are NaN
    both_nan = df['Reaction temperature'].isna() & df['Vapor residence time (s)'].isna()
    df = df[~both_nan].copy()
    print(f"  After dropping both T & VRT NaN: {len(df)}")

    # Drop rows with no output data at all
    has_any_output = df[OUTPUT_COLS].notna().any(axis=1)
    df = df[has_any_output].copy()
    print(f"  After dropping no-output rows: {len(df)}")

    # Impute missing inputs
    temp_median = df['Reaction temperature'].median()
    vrt_median = df['Vapor residence time (s)'].median()
    df['Reaction temperature'] = df['Reaction temperature'].fillna(temp_median)
    df['Vapor residence time (s)'] = df['Vapor residence time (s)'].fillna(vrt_median)
    print(f"  Temperature median (imputed): {temp_median:.1f} °C")
    print(f"  VRT median (imputed): {vrt_median:.2f} s")

    # Extract arrays
    X = df[INPUT_COLS].values.astype(np.float32)
    Y = df[OUTPUT_COLS].values.astype(np.float32)

    # Create NaN mask (True = valid)
    mask = ~np.isnan(Y)
    Y = np.nan_to_num(Y, nan=0.0)

    # Report per-output data availability
    print("\n  Output availability:")
    for i, name in enumerate(OUTPUT_COLS):
        count = mask[:, i].sum()
        print(f"    {name}: {count}/{len(mask)} ({100*count/len(mask):.0f}%)")

    # Normalize inputs with StandardScaler
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std < 1e-8] = 1.0  # Avoid division by zero
    X_norm = (X - X_mean) / X_std

    return X_norm, Y, mask, X_mean, X_std


# ============================================================================
# Loss Function
# ============================================================================

def masked_loss(pred, target, mask):
    """Masked MSE with physical constraint penalties."""
    # Core MSE only on valid (non-NaN) outputs
    diff_sq = (pred - target) ** 2 * mask
    mse = diff_sq.sum() / mask.sum().clamp(min=1)

    # Soft constraint: Gas + Liquid + Solid ≈ 100%
    phase_sum = pred[:, 0] + pred[:, 1] + pred[:, 2]  # Liquid + Gas + Solid
    phase_penalty = ((phase_sum - 100.0) ** 2).mean()

    # Soft constraint: BTX ≤ Total aromatics
    btx_violation = F.relu(pred[:, 6] - pred[:, 5])
    btx_penalty = (btx_violation ** 2).mean()

    return mse + 0.01 * phase_penalty + 0.01 * btx_penalty


# ============================================================================
# Training
# ============================================================================

def train():
    """Full training pipeline."""
    X_norm, Y, mask, X_mean, X_std = load_and_preprocess()

    # Train/test split
    n = len(X_norm)
    indices = np.random.permutation(n)
    n_test = int(n * TEST_FRAC)
    test_idx = indices[:n_test]
    train_idx = indices[n_test:]

    X_train = torch.tensor(X_norm[train_idx], dtype=torch.float32)
    Y_train = torch.tensor(Y[train_idx], dtype=torch.float32)
    M_train = torch.tensor(mask[train_idx], dtype=torch.float32)

    X_test = torch.tensor(X_norm[test_idx], dtype=torch.float32)
    Y_test = torch.tensor(Y[test_idx], dtype=torch.float32)
    M_test = torch.tensor(mask[test_idx], dtype=torch.float32)

    print(f"\n  Train: {len(X_train)}, Test: {len(X_test)}")

    # DataLoader
    train_ds = TensorDataset(X_train, Y_train, M_train)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              drop_last=False)

    # Model, optimizer, scheduler
    model = PyrolysisNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, patience=SCHEDULER_PATIENCE, factor=SCHEDULER_FACTOR
    )

    best_val_loss = float('inf')
    best_state = None
    patience_counter = 0

    print("\nTraining...")
    for epoch in range(1, MAX_EPOCHS + 1):
        # Train
        model.train()
        train_loss_sum = 0.0
        train_batches = 0
        for xb, yb, mb in train_loader:
            optimizer.zero_grad()
            pred = model(xb)
            loss = masked_loss(pred, yb, mb)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item()
            train_batches += 1

        # Validate
        model.eval()
        with torch.no_grad():
            val_pred = model(X_test)
            val_loss = masked_loss(val_pred, Y_test, M_test).item()

        train_loss_avg = train_loss_sum / max(train_batches, 1)
        scheduler.step(val_loss)

        if epoch % 50 == 0 or epoch == 1:
            lr = optimizer.param_groups[0]['lr']
            print(f"  Epoch {epoch:4d} | Train: {train_loss_avg:.4f} | Val: {val_loss:.4f} | LR: {lr:.2e}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= EARLY_STOP_PATIENCE:
                print(f"  Early stopping at epoch {epoch} (patience={EARLY_STOP_PATIENCE})")
                break

    # Load best model
    model.load_state_dict(best_state)

    # Save model and scaler
    torch.save(best_state, MODEL_SAVE_PATH)
    torch.save({
        'mean': torch.tensor(X_mean, dtype=torch.float32),
        'scale': torch.tensor(X_std, dtype=torch.float32),
    }, SCALER_SAVE_PATH)
    print(f"\n  Model saved to {MODEL_SAVE_PATH}")
    print(f"  Scaler saved to {SCALER_SAVE_PATH}")

    # Evaluate
    evaluate(model, X_test, Y_test, M_test)


# ============================================================================
# Evaluation
# ============================================================================

def evaluate(model, X_test, Y_test, M_test):
    """Compute per-output metrics and generate parity plots."""
    model.eval()
    with torch.no_grad():
        pred = model(X_test).numpy()

    actual = Y_test.numpy()
    mask = M_test.numpy().astype(bool)

    os.makedirs(PLOT_DIR, exist_ok=True)

    print("\n" + "=" * 70)
    print(f"{'Output':<35} {'R²':>8} {'MAE':>8} {'RMSE':>8} {'N':>6}")
    print("-" * 70)

    r2_values = []
    parity_rows = []
    metrics_rows = []
    for i, name in enumerate(OUTPUT_COLS):
        valid = mask[:, i]
        n_valid = valid.sum()
        if n_valid < 2:
            print(f"  {name:<35} {'N/A':>8} {'N/A':>8} {'N/A':>8} {n_valid:>6}")
            continue

        y_true = actual[valid, i]
        y_pred = pred[valid, i]

        ss_res = ((y_true - y_pred) ** 2).sum()
        ss_tot = ((y_true - y_true.mean()) ** 2).sum()
        r2 = 1 - ss_res / max(ss_tot, 1e-10) if ss_tot > 1e-10 else 0.0
        mae = np.abs(y_true - y_pred).mean()
        rmse = np.sqrt(((y_true - y_pred) ** 2).mean())

        r2_values.append(r2)
        metrics_rows.append([name, r2, mae, rmse, int(n_valid)])
        print(f"  {name:<35} {r2:>8.3f} {mae:>8.2f} {rmse:>8.2f} {n_valid:>6}")

        for a, p in zip(y_true, y_pred):
            parity_rows.append([name, float(a), float(p)])

        # Parity plot
        fig, ax = plt.subplots(1, 1, figsize=figsize('single', aspect=1.0))
        ax.scatter(y_true, y_pred, alpha=0.6, s=20, edgecolors='k', linewidths=0.3)
        lims = [0, max(y_true.max(), y_pred.max()) * 1.1 + 1]
        ax.plot(lims, lims, '--', color=COLORS[0], linewidth=0.8)
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_xlabel('Actual (wt%)')
        ax.set_ylabel('Predicted (wt%)')
        ax.set_title(f'{name}\nR\u00b2={r2:.3f}, MAE={mae:.2f}, N={n_valid}')
        ax.set_aspect('equal')
        fig.tight_layout()
        safe_name = name.replace(' ', '_').replace('(', '').replace(')', '').replace('>', 'gt').replace('%', 'pct')
        savefig(fig, os.path.join(PLOT_DIR, f'parity_{safe_name}'))
        plt.close(fig)

    print("-" * 70)
    if r2_values:
        print(f"  {'Mean R²':<35} {np.mean(r2_values):>8.3f}")
    print("=" * 70)
    print(f"\n  Parity plots saved to {PLOT_DIR}/")

    # Save parity data (actual vs predicted for each output on test set)
    csv_path = os.path.join(DATA_DIR, 'parity_actual_vs_predicted_test_set.csv')
    pd.DataFrame(parity_rows, columns=['Output', 'Actual_wt%', 'Predicted_wt%']).to_csv(csv_path, index=False)
    print(f"  Saved {csv_path}")

    # Save per-output metrics summary
    csv_path = os.path.join(DATA_DIR, 'model_test_metrics_per_output.csv')
    pd.DataFrame(metrics_rows, columns=['Output', 'R2', 'MAE', 'RMSE', 'N']).to_csv(csv_path, index=False)
    print(f"  Saved {csv_path}")


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    train()
