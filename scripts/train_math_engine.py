import pandas as pd
import numpy as np
import xgboost as xgb
import optuna
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, mean_absolute_error

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "processed", "atmospheric_impact_matrix.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")

os.makedirs(MODEL_DIR, exist_ok=True)

def train_math_engine():
    print("==================================================")
    print("  CALAMITY AI: XGBoost Math Engine (Optuna)       ")
    print("==================================================")
    
    # 1. Load Data
    df = pd.read_csv(DATA_PATH)
    
    target_affected = 'Total Affected' if 'Total Affected' in df.columns else df.columns[df.columns.str.contains('Affected')][0]
    target_damage = "Total Damage ('000 US$)" if "Total Damage ('000 US$)" in df.columns else df.columns[df.columns.str.contains('Damage')][0]
    
    # Apply log1p normalizations
    df['log_total_affected'] = np.log1p(df[target_affected].fillna(0))
    df['log_total_damage'] = np.log1p(df[target_damage].fillna(0))
    
    # 2. Feature Engineering
    features = ['Country', 'Disaster Type', 'Start Month', 'Start Year']
    
    actual_features = []
    for f in features:
        if f in df.columns:
            actual_features.append(f)
        else:
            match = df.columns[df.columns.str.contains(f, case=False)]
            if len(match) > 0:
                actual_features.append(match[0])
                
    X = df[actual_features].copy()
    
    # CONSTRAINT 2: Native Categoricals (No Label/One-Hot Encoding)
    for col in X.columns:
        if X[col].dtype == 'object' or str(X[col].dtype).startswith('string') or 'Country' in col or 'Type' in col:
            X[col] = X[col].astype('category')
            
    # Fill numeric NAs (Categoricals inherently handle NaNs in XGBoost)
    for col in X.columns:
        if X[col].dtype != 'category':
            X[col] = X[col].fillna(-1)
            
    y_affected = df['log_total_affected']
    y_damage = df['log_total_damage']
    
    print(f"[*] Engineered {X.shape[1]} features: {list(X.columns)}")
    print("[*] Performing 3-Way Split (Train / Validation / Holdout-Test)...")
    
    # CONSTRAINT 1: Strict Data Leakage Prevention
    # 15% Holdout exactly sequestered
    X_temp, X_test, y_aff_temp, y_aff_test, y_dam_temp, y_dam_test = train_test_split(
        X, y_affected, y_damage, test_size=0.15, random_state=42
    )
    
    # Of the remaining 85%, take 20% for Optuna validation
    X_train, X_val, y_aff_train, y_aff_val, y_dam_train, y_dam_val = train_test_split(
        X_temp, y_aff_temp, y_dam_temp, test_size=0.20, random_state=42
    )
    
    print("[*] Initiating Optuna Study A: Affected Population (50 Trials)...")
    
    # 4. Optuna Study A
    def objective_affected(trial):
        param = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'enable_categorical': True,
            'tree_method': 'hist'
        }
        model = xgb.XGBRegressor(**param, random_state=42)
        model.fit(X_train, y_aff_train)
        preds = model.predict(X_val)
        return root_mean_squared_error(y_aff_val, preds)

    study_a = optuna.create_study(direction='minimize')
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study_a.optimize(objective_affected, n_trials=50)
    
    print(f"  [+] Optuna Validated Log-RMSE for affected: {study_a.best_value:.4f}")
    
    print("\n[*] Initiating Optuna Study B: Economic Damage (50 Trials)...")
    
    # 5. Optuna Study B
    def objective_damage(trial):
        param = {
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'enable_categorical': True,
            'tree_method': 'hist'
        }
        model = xgb.XGBRegressor(**param, random_state=42)
        model.fit(X_train, y_dam_train)
        preds = model.predict(X_val)
        return root_mean_squared_error(y_dam_val, preds)

    study_b = optuna.create_study(direction='minimize')
    study_b.optimize(objective_damage, n_trials=50)
    
    print(f"  [+] Optuna Validated Log-RMSE for damage: {study_b.best_value:.4f}")
    
    # 6. Inverse Transform Holdout Evaluation
    print("\n[*] Training Best Models & Evaluating on Sequestered Holdout Set...")
    
    # Model A
    best_params_a = study_a.best_params.copy()
    best_params_a['enable_categorical'] = True
    best_params_a['tree_method'] = 'hist'
    
    model_a = xgb.XGBRegressor(**best_params_a, random_state=42)
    model_a.fit(X_temp, y_aff_temp)
    
    preds_aff_log = model_a.predict(X_test)
    # CONSTRAINT 3: Inverse Transform
    preds_aff_real = np.expm1(preds_aff_log)
    true_aff_real = np.expm1(y_aff_test)
    
    rmse_aff = root_mean_squared_error(true_aff_real, preds_aff_real)
    mae_aff = mean_absolute_error(true_aff_real, preds_aff_real)
    
    # Model B
    best_params_b = study_b.best_params.copy()
    best_params_b['enable_categorical'] = True
    best_params_b['tree_method'] = 'hist'
    
    model_b = xgb.XGBRegressor(**best_params_b, random_state=42)
    model_b.fit(X_temp, y_dam_temp)
    
    preds_dam_log = model_b.predict(X_test)
    # CONSTRAINT 3: Inverse Transform
    preds_dam_real = np.expm1(preds_dam_log)
    true_dam_real = np.expm1(y_dam_test)
    
    rmse_dam = root_mean_squared_error(true_dam_real, preds_dam_real)
    mae_dam = mean_absolute_error(true_dam_real, preds_dam_real)
    
    print("\n==================================================")
    print("  REAL-WORLD HOLDOUT METRICS (INVERSE TRANSFORMED) ")
    print("==================================================")
    print("  [MODEL A] TARGET: Affected Population")
    print(f"    RMSE : {rmse_aff:,.2f} people")
    print(f"    MAE  : {mae_aff:,.2f} people")
    print("\n  [MODEL B] TARGET: Economic Damage ('000 USD)")
    print(f"    RMSE : ${rmse_dam:,.2f}K USD")
    print(f"    MAE  : ${mae_dam:,.2f}K USD")
    print("==================================================")
    
    print("\n[*] Exporting finalized production XGBoost artifacts...")
    # Final retrain on the complete dataset (Train + Val + Holdout) for optimal production weights
    model_a.fit(X, y_affected)
    model_a.save_model(os.path.join(MODEL_DIR, "xgb_log_affected.json"))
    
    model_b.fit(X, y_damage)
    model_b.save_model(os.path.join(MODEL_DIR, "xgb_log_damage.json"))
    
    print("==================================================")
    print("  MODELS EXPORTED SUCCESSFULLY                    ")
    print("==================================================")

if __name__ == "__main__":
    train_math_engine()
