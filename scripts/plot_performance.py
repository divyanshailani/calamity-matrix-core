import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Set up beautiful seaborn style
plt.style.use('dark_background')
sns.set_theme(style="darkgrid", rc={
    "axes.facecolor": "#18181b", 
    "figure.facecolor": "#09090b", 
    "grid.color": "#27272a", 
    "text.color": "#e4e4e7", 
    "axes.labelcolor": "#e4e4e7", 
    "xtick.color": "#a1a1aa", 
    "ytick.color": "#a1a1aa",
    "font.family": "sans-serif"
})

data = []
for f in os.listdir("models"):
    if f.endswith("_meta.json") and not f.startswith("xgb_log"):
        with open(os.path.join("models", f), 'r') as file:
            meta = json.load(file)
            name_parts = f.replace("_meta.json", "").split("_")
            target = name_parts[-1]
            disaster = "_".join(name_parts[:-1]).replace("_", " ").title()
            
            data.append({
                "Disaster": disaster,
                "Target": "Affected Population" if target == "affected" else "Economic Damage",
                "RMSE": meta["rmse"],
                "MAE": meta["mae"],
                "Samples": meta["n_samples"]
            })

df = pd.DataFrame(data)

fig, axes = plt.subplots(2, 1, figsize=(14, 12))
fig.suptitle("Math Engine v3 Performance per Disaster Type", fontsize=22, color="#ffffff", fontweight="bold", y=0.97)

# 1. Affected Population
df_aff = df[df["Target"] == "Affected Population"].sort_values("RMSE", ascending=False)
df_aff_melt = df_aff.melt(id_vars=["Disaster"], value_vars=["RMSE", "MAE"], var_name="Metric", value_name="Value")

sns.barplot(data=df_aff_melt, x="Disaster", y="Value", hue="Metric", ax=axes[0], palette=["#3b82f6", "#10b981"])
axes[0].set_title("Affected Population Error Magnitude", fontsize=16, color="#f4f4f5", pad=15)
axes[0].set_yscale("log")
axes[0].set_ylabel("Error (Log Scale)", fontsize=12)
axes[0].set_xlabel("")
axes[0].tick_params(axis='x', rotation=30, labelsize=12)
axes[0].legend(facecolor="#18181b", edgecolor="#27272a", fontsize=12)

# 2. Economic Damage
df_dam = df[df["Target"] == "Economic Damage"].sort_values("RMSE", ascending=False)
df_dam_melt = df_dam.melt(id_vars=["Disaster"], value_vars=["RMSE", "MAE"], var_name="Metric", value_name="Value")

sns.barplot(data=df_dam_melt, x="Disaster", y="Value", hue="Metric", ax=axes[1], palette=["#ef4444", "#f59e0b"])
axes[1].set_title("Economic Damage in USD Thousands Error Magnitude", fontsize=16, color="#f4f4f5", pad=15)
axes[1].set_yscale("log")
axes[1].set_ylabel("Error (Log Scale)", fontsize=12)
axes[1].set_xlabel("Disaster Type", fontsize=14, labelpad=15)
axes[1].tick_params(axis='x', rotation=30, labelsize=12)
axes[1].legend(facecolor="#18181b", edgecolor="#27272a", fontsize=12)

plt.tight_layout()
plt.subplots_adjust(top=0.9, hspace=0.3)

out_dir = "/Users/divyanshailani/.gemini/antigravity/brain/f18c2b27-d05c-474b-8f60-58bdc6cc3c31"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "disaster_performance.png")
plt.savefig(out_path, dpi=300, bbox_inches="tight")
print(f"Saved chart to {out_path}")
