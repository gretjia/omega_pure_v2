import os
import shutil
import subprocess
from pathlib import Path

# Base directories
BASE_DIR = Path("/home/zephryj/projects/omega_pure_v2")
REPORTS_DIR = BASE_DIR / "reports"

# Create phase directories
phase_dirs = {
    "phase3": REPORTS_DIR / "phase3",
    "phase6": REPORTS_DIR / "phase6",
    "phase7": REPORTS_DIR / "phase7",
    "phase8": REPORTS_DIR / "phase8",
    "phase9": REPORTS_DIR / "phase9",
    "phase10": REPORTS_DIR / "phase10",
    "audits_and_insights": REPORTS_DIR / "audits_and_insights",
    "general": REPORTS_DIR / "general"
}

for d in phase_dirs.values():
    d.mkdir(parents=True, exist_ok=True)

def safe_move(src, dest_dir):
    if not src.exists():
        return
    dest_path = dest_dir / src.name
    if src.resolve() != dest_path.resolve():
        shutil.move(str(src), str(dest_path))

# 1. Move existing reports
safe_move(REPORTS_DIR / "PHASE3_V15_TRAINING_REPORT.md", phase_dirs["phase3"])
safe_move(REPORTS_DIR / "phase6_results", phase_dirs["phase6"])
safe_move(REPORTS_DIR / "PHASE7_REPORT.md", phase_dirs["phase7"])
safe_move(REPORTS_DIR / "PHASE8_REPORT.md", phase_dirs["phase8"])
safe_move(REPORTS_DIR / "phase8_sweep", phase_dirs["phase8"])
safe_move(REPORTS_DIR / "PHASE9_EVIDENCE.md", phase_dirs["phase9"])
safe_move(REPORTS_DIR / "phase10_results", phase_dirs["phase10"])
safe_move(REPORTS_DIR / "phase10_gated_results", phase_dirs["phase10"])

# 2. Move audits
safe_move(BASE_DIR / "audit" / "gemini_bitter_lessons.md", phase_dirs["audits_and_insights"])
safe_move(BASE_DIR / "architect" / "audit" / "2026-03-30_gemini_gcs_io_optimization_audit.md", phase_dirs["audits_and_insights"])
safe_move(BASE_DIR / "architect" / "audit" / "2026-03-30_gemini_softmax_portfolio_loss_audit.md", phase_dirs["audits_and_insights"])

# 3. Move existing gdocs
for doc in ["id1_math_verification.md", "id2_engineering_audit.md", "id3_fix_recommendations.md", "id4_srl_friction_calibration.md", "id5_mae_vs_intent_prediction.md", "id6_vd_physics_ruling.md"]:
    safe_move(BASE_DIR / "architect" / "gdocs" / doc, phase_dirs["audits_and_insights"])

# 4. Download and organize new gdocs
docs_to_download = [
    ("1HsowI7MIjmrRtGVlPURF0ChC6ulFV4642hFxGX0hOi4", "Epiplexity.md", "general"),
    ("1fSJ_iJcQdCnIW8x6XyzO1kIWKpmck8gEMyd-7S1NL8c", "Phase_10_Vanguard_V5_Report.md", "phase10"),
    ("1LLwHMtbZIfDUcEpbxWJvuA-7649fJcYVZRtfBoMArvc", "run_9_math.md", "phase9"),
    ("1iVKw9UTI3wBmgHk3dw8kr19KLltgF8g4fUw4wt7jguE", "run_9_econ.md", "phase9"),
    ("1NMUgCo3RjhrIHiXZXhGXM-M-IZJLX8HbMLTSucY9jS8", "Phase_9_Evidence_Package.md", "phase9"),
    ("13RJY0QnfJtphwB49YmT-n4fXZQlj6z7OmpqG1IGBx6w", "omega_core_insights.md", "audits_and_insights"),
    ("1gHDPPLCu26sUWDNoCvDsbHJYp_V8MXduk9OZGmxAeLg", "Phase_8_Comprehensive_Report.md", "phase8"),
    ("1gzy7PDaQChmMYBjolhegUTHVIvz45RxFwiyd5dTUYWM", "Phase_7_Comprehensive_Report.md", "phase7"),
    ("1RREV0WM54RXQZsexbeJH4zrXOstgtYzzTNy7vd_yjhc", "Phase_7_Full_Simulation.md", "phase7"),
    ("1lmkg8qYD77QIWan-FD5_jGgt4NQPrTV8FkKx1Gjgr9A", "Phase_7_Historical_Data.md", "phase7"),
]

for doc_id, filename, phase_key in docs_to_download:
    dest_path = phase_dirs[phase_key] / filename
    if not dest_path.exists():
        print(f"Downloading {filename}...")
        try:
            # use subprocess to run gdocs read
            result = subprocess.run(["gdocs", "read", doc_id], capture_output=True, text=True, check=True)
            with open(dest_path, "w") as f:
                f.write(result.stdout)
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

print("Reorganization complete.")
