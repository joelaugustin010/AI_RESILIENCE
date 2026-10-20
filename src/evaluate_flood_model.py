"""Audit candidate flood labels and evaluate only if readiness checks pass."""

try:
    from src.flood_model import audit_flood_dataset, evaluate_flood_model, load_flood_data
except ModuleNotFoundError:  # Support `python src/evaluate_flood_model.py` as well as `-m`.
    from flood_model import audit_flood_dataset, evaluate_flood_model, load_flood_data


def main() -> None:
    frame, metadata = load_flood_data()
    report = audit_flood_dataset(frame, metadata)
    print("=== FLOOD MODEL READINESS AUDIT ===")
    print(f"Rows: {report['rows']}")
    print(f"Features present: {report['feature_count']}")
    print(f"Target counts (0=no flood, 1=flood): {report['target_counts']}")
    print(f"Exact duplicate rows: {report['exact_duplicates']}")
    print(f"Observation dates: {report['date_min']} to {report['date_max']} ({report['distinct_dates']} distinct)")
    print(f"Missing values: {report['missing_values']}")
    print(f"Readiness: {'READY FOR RESEARCH EVALUATION' if report['ready'] else 'BLOCKED'}")
    if report["blockers"]:
        print("\nBlocking issues:")
        for item in report["blockers"]:
            print(f"- {item}")
    if report["warnings"]:
        print("\nReview warnings:")
        for item in report["warnings"]:
            print(f"- {item}")

    if not report["ready"]:
        print("\nNo model was fitted; no performance metrics or prediction were generated.")
        return

    result = evaluate_flood_model(frame, metadata)
    print("\nChronological, event-separated holdout:", result["split"])
    print("Logistic-regression metrics:", result["model_metrics"])
    print("Prior-baseline metrics:", result["baseline_metrics"])
    print("These research metrics do not establish operational forecasting skill.")


if __name__ == "__main__":
    main()
