import json
import argparse
import sys
from pathlib import Path

def calculate_mae(verdict, ground_truth):
    """
    Calculates Mean Absolute Error (MAE) between simulation midpoint
    and ground truth values.
    """
    errors = []
    comparison_table = []
    
    predictions = verdict.get("predictions", {})
    
    # We expect these 4 deltas for S2 Argentina IPC
    deltas = ["delta_1_feb", "delta_2_apr", "delta_3_jul", "delta_4_dec"]
    
    for delta in deltas:
        if delta not in predictions:
            print(f"Warning: {delta} missing from predictions.")
            continue
        if delta not in ground_truth:
            print(f"Warning: {delta} missing from ground truth.")
            continue
            
        pred = predictions[delta]
        gt_val = ground_truth[delta]
        
        # Midpoint calculation
        mid_point = (pred["min_pct"] + pred["max_pct"]) / 2.0
        abs_error = abs(mid_point - gt_val)
        
        errors.append(abs_error)
        comparison_table.append({
            "Delta": delta,
            "Truth": f"{gt_val:.2f}%",
            "Range": f"[{pred['min_pct']:.1f}% - {pred['max_pct']:.1f}%]",
            "Mid": f"{mid_point:.2f}%",
            "Error": f"{abs_error:.2f}%"
        })
    
    mae = sum(errors) / len(errors) if errors else 0.0
    return mae, comparison_table

def main():
    parser = argparse.ArgumentParser(description="MiroFish IPC Quantitative Evaluator")
    parser.add_argument("verdict", type=str, help="Path to verdict.json")
    parser.add_argument("--ground_truth", type=str, default="ground_truth.json", help="Path to ground_truth.json (default: root)")
    args = parser.parse_args()

    verdict_path = Path(args.verdict)
    # The user specifically requested to look for ground_truth.json in the project root
    gt_path = Path(args.ground_truth)

    if not verdict_path.exists():
        print(f"Error: Verdict file {verdict_path} not found.")
        sys.exit(1)
    
    if not gt_path.exists():
        # Try root as fallback if not absolute and current dir fails
        root_gt = Path(__file__).parent.parent.parent / "ground_truth.json"
        if root_gt.exists():
            gt_path = root_gt
        else:
            print(f"Error: Ground truth file {gt_path} not found.")
            sys.exit(1)

    try:
        with open(verdict_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Robust JSON extraction using regex to handle markdown fences or extra text
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            v_data = json.loads(json_match.group(0))
        else:
            v_data = json.loads(content) # Fallback
            
        with open(gt_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
    except Exception as e:
        print(f"Error parsing JSON files: {e}")
        sys.exit(1)

    mae, table = calculate_mae(v_data, gt_data)

    # UI Output
    print("\n" + "="*80)
    print(f"{'MiroFish Phase 2 (S2) - Argentina IPC Evaluation':^80}")
    print("="*80)
    print(f"{'Period/Delta':<15} | {'Truth':<10} | {'Sim Range':<18} | {'Sim Mid':<10} | {'Abs Err':<10}")
    print("-" * 80)
    for row in table:
        print(f"{row['Delta']:<15} | {row['Truth']:<10} | {row['Range']:<18} | {row['Mid']:<10} | {row['Error']:<10}")
    print("-" * 80)
    print(f"{'TOTAL MEAN ABSOLUTE ERROR (MAE):':<67} {mae:.4f}%")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
