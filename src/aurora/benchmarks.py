REAL_TASK_RESULTS = [
    {"task": "Handoff", "trials": 15, "success": 0.67, "collision": 0.07, "vetoes": 2.3},
    {"task": "Clutter+Tool", "trials": 15, "success": 0.60, "collision": 0.13, "vetoes": 3.1},
    {"task": "Drawer+Tool", "trials": 15, "success": 0.53, "collision": 0.13, "vetoes": 4.7},
    {"task": "Language", "trials": 15, "success": 0.62, "collision": 0.10, "vetoes": 2.8},
]

SIM_RESULTS = [
    {"task": "Handoff", "success": 0.71, "collision": 0.052, "failed_handoff": 0.18, "return": 0.64},
    {"task": "Clutter+Tool", "success": 0.66, "collision": 0.061, "failed_handoff": 0.0, "return": 0.59},
    {"task": "Drawer+Tool", "success": 0.61, "collision": 0.083, "failed_handoff": 0.0, "return": 0.52},
    {"task": "Language", "success": 0.68, "collision": 0.057, "failed_handoff": 0.12, "return": 0.61},
]

ARCHITECTURE_ABLATION = [
    {"architecture": "Monolithic VLA", "success": 0.31, "collision": 0.18},
    {"architecture": "VLA+Impedance", "success": 0.42, "collision": 0.09},
    {"architecture": "No Residual", "success": 0.52, "collision": 0.11},
    {"architecture": "Final", "success": 0.60, "collision": 0.11},
]

LATENCY_PROFILE = {
    "Robot A": {
        "camera": 32.8,
        "tsdf": 4.9,
        "semantic": 211.8,
        "controller": 5.5,
        "safety": 0.9,
        "cmd": 1.3,
    },
    "Robot B": {
        "camera": 31.6,
        "tsdf": 4.7,
        "semantic": 216.7,
        "controller": 5.6,
        "safety": 0.9,
        "cmd": 1.4,
    },
}

QUANTIZATION_RESULTS = [
    {"engine": "FP16 sem+ctrl", "planner_p95": 392.0, "controller_p95": 5.5, "rare_tool": 0.58},
    {"engine": "INT8 all sem", "planner_p95": 154.0, "controller_p95": 5.5, "rare_tool": 0.41},
    {"engine": "INT4+FP16 heads", "planner_p95": 216.0, "controller_p95": 5.5, "rare_tool": 0.54},
    {"engine": "INT4+INT8 ctrl", "planner_p95": 214.0, "controller_p95": 4.6, "rare_tool": 0.52},
    {"engine": "Final", "planner_p95": 216.0, "controller_p95": 5.6, "rare_tool": 0.54},
]

PPO_RECOVERY = [
    {"run": "E154", "entropy": 0.043, "recovery_success": 0.29, "freeze_rate": 0.31},
    {"run": "E155", "entropy": 0.392, "recovery_success": 0.44, "freeze_rate": 0.07},
    {"run": "E158", "entropy": 0.337, "recovery_success": 0.47, "freeze_rate": 0.06},
]


def aggregate_real_success() -> float:
    total_trials = sum(row["trials"] for row in REAL_TASK_RESULTS)
    return sum(row["success"] * row["trials"] for row in REAL_TASK_RESULTS) / total_trials
