import pandas as pd
import numpy as np
import xgboost as xgb
import optuna
import os
import json
import re

from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, mean_absolute_error

# Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "data", "processed", "atmospheric_impact_matrix.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "models")

os.makedirs(MODEL_DIR, exist_ok=True)

def slugify(text: str) -> str:
    """Converts a string like 'Mass movement (wet)' to 'mass_movement_wet'."""
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')

def train_math_engine_v3():
    print("==================================================")
    print("  CALAMITY AI: XGBoost Math Engine v3 (Multi-Physics)")
    print("==================================================")
    
    # 1. Load Data
    df = pd.read_csv(DATA_PATH)
    
    target_affected = 'Total Affected' if 'Total Affected' in df.columns else df.columns[df.columns.str.contains('Affected')][0]
    target_damage = "Total Damage ('000 US$)" if "Total Damage ('000 US$)" in df.columns else df.columns[df.columns.str.contains('Damage')][0]
    
    df['log_total_affected'] = np.log1p(df[target_affected].fillna(0))
    df['log_total_damage'] = np.log1p(df[target_damage].fillna(0))
    
    # 2. Magnitude/Severity Injection
    severity_col = 'nasa_events_count' if 'nasa_events_count' in df.columns else None
    
    if severity_col:
        df['Severity'] = df[severity_col]
        print(f"[*] Injected '{severity_col}' as core Severity metric.")
    else:
        df['Severity'] = np.nan
        print("[!] Warning: Severity column not found.")
        
    # Intelligent Imputation of missing magnitudes
    df['Severity'] = df.groupby(['Country', 'Disaster Type'])['Severity'].transform(
        lambda x: x.fillna(x.median() if not x.isna().all() else np.nan)
    )
    df['Severity'] = df.groupby('Disaster Type')['Severity'].transform(
        lambda x: x.fillna(x.median() if not x.isna().all() else np.nan)
    )
    df['Severity'] = df['Severity'].fillna(df['Severity'].median())
    
    # 3. Feature Engineering
    features = ['Country', 'Disaster Type', 'Start Month', 'Start Year', 'Severity']
    
    actual_features = []
    for f in features:
        if f in df.columns:
            actual_features.append(f)
        else:
            match = df.columns[df.columns.str.contains(f, case=False)]
            if len(match) > 0:
                actual_features.append(match[0])
                
    cat_cols = ['Country', 'Disaster Type']
    for col in df.columns:
        if col in actual_features:
            if col in cat_cols or df[col].dtype == 'object' or str(df[col].dtype).startswith('string'):
                df[col] = df[col].astype('category')
            elif df[col].dtype != 'category':
                df[col] = df[col].fillna(-1)

    # 4. Disaster-Specific Segregation (Multi-Physics Loop)
    disaster_counts = df['Disaster Type'].value_counts()
    valid_disasters = disaster_counts[disaster_counts >= 100].index.tolist()
    
    print(f"\n[*] Identified {len(valid_disasters)} viable physical domains (N >= 100):")
    for d in valid_disasters:
        print(f"    - {d} ({disaster_counts[d]} records)")
        
    print("\n==================================================")
    print("  INITIATING MULTI-PHYSICS TUNING LOOP")
    print("==================================================")
    
    for disaster_type in valid_disasters:
        slug = slugify(disaster_type)
        print(f"\n>>> DOMAIN: {disaster_type.upper()} [{slug}]")
        
        df_domain = df[df['Disaster Type'] == disaster_type].copy()
        
        X = df_domain[actual_features].copy()
        y_affected = df_domain['log_total_affected']
        y_damage = df_domain['log_total_damage']
        
        # Strict 3-Way Split
        X_temp, X_test, y_aff_temp, y_aff_test, y_dam_temp, y_dam_test = train_test_split(
            X, y_affected, y_damage, test_size=0.15, random_state=42
        )
        
        X_train, X_val, y_aff_train, y_aff_val, y_dam_train, y_dam_val = train_test_split(
            X_temp, y_aff_temp, y_dam_temp, test_size=0.20, random_state=42
        )
        
        # --- Study A: Affected Population ---
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
        
        # --- Study B: Economic Damage ---
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
        
        # Train Best Models & Evaluate
        best_params_a = study_a.best_params.copy()
        best_params_a.update({'enable_categorical': True, 'tree_method': 'hist'})
        model_a = xgb.XGBRegressor(**best_params_a, random_state=42)
        model_a.fit(X_temp, y_aff_temp)
        
        preds_aff_real = np.expm1(model_a.predict(X_test))
        true_aff_real = np.expm1(y_aff_test)
        rmse_aff = root_mean_squared_error(true_aff_real, preds_aff_real)
        mae_aff = mean_absolute_error(true_aff_real, preds_aff_real)
        
        best_params_b = study_b.best_params.copy()
        best_params_b.update({'enable_categorical': True, 'tree_method': 'hist'})
        model_b = xgb.XGBRegressor(**best_params_b, random_state=42)
        model_b.fit(X_temp, y_dam_temp)
        
        preds_dam_real = np.expm1(model_b.predict(X_test))
        true_dam_real = np.expm1(y_dam_test)
        rmse_dam = root_mean_squared_error(true_dam_real, preds_dam_real)
        mae_dam = mean_absolute_error(true_dam_real, preds_dam_real)
        
        print(f"  [+] Affected Population: RMSE = {rmse_aff:,.2f} | Best log-RMSE = {study_a.best_value:.4f}")
        print(f"  [+] Economic Damage    : RMSE = ${rmse_dam:,.2f}K | Best log-RMSE = {study_b.best_value:.4f}")
        
        # Feature Importance
        imp_a = model_a.get_booster().get_score(importance_type='gain')
        imp_b = model_b.get_booster().get_score(importance_type='gain')
        
        # Final Retrain on All Data for Domain
        model_a.fit(X, y_affected)
        model_b.fit(X, y_damage)
        
        # Export
        model_a.save_model(os.path.join(MODEL_DIR, f"{slug}_affected.json"))
        with open(os.path.join(MODEL_DIR, f"{slug}_affected_meta.json"), "w") as f:
            json.dump({"rmse": rmse_aff, "mae": mae_aff, "feature_importance_gain": imp_a, "n_samples": len(df_domain)}, f, indent=4)
            
        model_b.save_model(os.path.join(MODEL_DIR, f"{slug}_damage.json"))
        with open(os.path.join(MODEL_DIR, f"{slug}_damage_meta.json"), "w") as f:
            json.dump({"rmse": rmse_dam, "mae": mae_dam, "feature_importance_gain": imp_b, "n_samples": len(df_domain)}, f, indent=4)

    print("\n==================================================")
    print("  MULTI-PHYSICS EXPORT COMPLETE                    ")
    print("==================================================")

if __name__ == "__main__":
    train_math_engine_v3()
