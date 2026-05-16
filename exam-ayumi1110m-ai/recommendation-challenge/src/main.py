#!/usr/bin/env python3
"""
Recommendation Pipeline Challenge - Solution
Generates product recommendations based on purchase history.
Basic approach: co-purchase analysis only.
"""

import csv
import json
import os
from collections import defaultdict
from itertools import combinations

INPUT_DIR = os.environ.get("INPUT_DIR", "data/input")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

MAX_RECOMMENDATIONS = 10


# =============================================================================
# Data Loading
# =============================================================================

def load_orders():
    orders = []
    with open(os.path.join(INPUT_DIR, "orders.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            orders.append(row)
    return orders


def load_products():
    with open(os.path.join(INPUT_DIR, "products.json"), "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Recommendation Generation (Co-Purchase Only)
# =============================================================================

def generate_recommendations(orders, products):
    print("  Generating recommendations (co-purchase analysis)...")
    products_map = {p["product_id"]: p for p in products}

    # Filter to completed orders with valid product
    completed = []
    for o in orders:
        if o.get("status") != "completed":
            continue
        if not o.get("user_id") or not o.get("product_id"):
            continue
        if o["product_id"] in products_map:
            completed.append(o)

    # Build user purchase history
    user_purchased = defaultdict(set)
    for o in completed:
        user_purchased[o["user_id"]].add(o["product_id"])

    # Build co-purchase matrix
    copurchase = defaultdict(lambda: defaultdict(int))
    for uid, products_bought in user_purchased.items():
        product_list = list(products_bought)
        for p1, p2 in combinations(product_list, 2):
            copurchase[p1][p2] += 1
            copurchase[p2][p1] += 1

    # Generate recommendations per user
    results = []
    for uid in sorted(user_purchased.keys()):
        purchased = user_purchased[uid]

        # Score unpurchased products by co-occurrence with purchased products
        scores = defaultdict(float)
        for owned_pid in purchased:
            for candidate_pid, count in copurchase[owned_pid].items():
                if candidate_pid not in purchased:
                    scores[candidate_pid] += count

        if not scores:
            continue

        # Normalize to 0-1
        max_score = max(scores.values())
        if max_score <= 0:
            continue

        # Sort by score, take top N
        sorted_candidates = sorted(
            scores.items(),
            key=lambda x: (-x[1], x[0])
        )[:MAX_RECOMMENDATIONS]

        recommendations = []
        for pid, raw_score in sorted_candidates:
            normalized_score = round(raw_score / max_score, 2)
            recommendations.append({
                "product_id": pid,
                "score": normalized_score,
                "reason": "frequently_bought_together"
            })

        if recommendations:
            results.append({
                "user_id": uid,
                "recommendations": recommendations
            })

    return results


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Recommendation Pipeline - Starting")
    print(f"  Input:  {INPUT_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\nLoading data...")
    orders = load_orders()
    products = load_products()
    print(f"  Orders: {len(orders)}, Products: {len(products)}")

    print("\nProcessing...")
    recommendations = generate_recommendations(orders, products)
    total_pairs = sum(len(u["recommendations"]) for u in recommendations)

    filepath = os.path.join(OUTPUT_DIR, "recommendations.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)

    print(f"    -> {len(recommendations)} users, {total_pairs} recommendations written")

    # Write completion marker
    with open(os.path.join(OUTPUT_DIR, ".done"), "w") as f:
        f.write("done\n")

    print("\n" + "=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
