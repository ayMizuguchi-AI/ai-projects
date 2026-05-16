#!/usr/bin/env python3
"""
Anomaly Detection Pipeline Challenge - Solution
Detects anomalous events from e-commerce order and access log data.
"""

import csv
import json
import math
import os

from collections import defaultdict
from datetime import datetime, timedelta

from sklearn.ensemble import RandomForestClassifier

# 重みランキング
import pandas as pd

INPUT_DIR = os.environ.get("INPUT_DIR", "data/input")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
REFERENCE_DATE = datetime(2025, 1, 31)


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


def load_access_logs():
    logs = []
    with open(os.path.join(INPUT_DIR, "access_logs.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


def parse_date(date_str):
    try:
        if "T" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        else:
            return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
    
def get_target_id(user_id, ip_address):
    return user_id if user_id else ip_address

def get_max_orders_in_window(user_orders, window_minutes=10):
    left = 0
    running_amount = 0.0
    max_count = 0
    max_amount = 0.0
    max_start_idx = 0
    window_delta = timedelta(minutes=window_minutes)

    for right, order in enumerate(user_orders):
        running_amount += order["_total_amount"]
        while user_orders[right]["_order_date"] - user_orders[left]["_order_date"] > window_delta:
            running_amount -= user_orders[left]["_total_amount"]
            left += 1

        current_count = right - left + 1
        if current_count > max_count:
            max_count = current_count
            max_amount = running_amount
            max_start_idx = left

    return max_count, max_amount, max_start_idx


def get_valid_completed_orders(orders, products_map):
    valid = []
    for o in orders:
        if o.get("status") != "completed":
            continue
        if not o.get("product_id") or not o.get("total_amount"):
            continue
        if o["product_id"] not in products_map:
            continue

        total = safe_float(o["total_amount"], None)
        if total is None:
            continue
        order_date = parse_date(o.get("order_date", ""))
        if order_date is None:
            continue
        valid.append({
            **o,
            "_total_amount": total,
            "_order_date": order_date,
            "_quantity": int(safe_float(o.get("quantity", 1), 1.0)),
            "_unit_price": safe_float(o.get("unit_price", 0), 0.0)
        })
    return valid

# 重大度判定
def determine_severity(df, is_multi, ai_score=0):
    if ai_score > 0.9 or df >= 10.0:
        return "high"
    if ai_score > 0.7 or df >= 5.0 or is_multi:
        return "medium"
    return "low"

def normalize_details(details):
    normalized = dict(details)
    for key in ("value", "threshold", "deviation_factor"):
        if key in normalized:
            normalized[key] = round(safe_float(normalized[key], 0.0), 2)
    if "threshold" not in normalized:
        normalized["threshold"] = 0.0
    return normalized

# =============================================================================
# Anomaly Detection
# =============================================================================

def build_features_and_rule_anomalies(orders, products, access_logs, true_anomaly_ids):
    print("  Anomaly Detection...")


    # AI学習用配列
    user_max_counts = defaultdict(float) # 10分間連打回数
    user_max_amounts = defaultdict(float) # 10分間金額
    user_price_diffs = defaultdict(float) # 価格差％
    user_max_access = defaultdict(float) #アクセス数
    user_max_zscores = defaultdict(float) #普段の金額
    user_cancel_rate = defaultdict(float) #キャンセル率　追加
    user_e_wallet_rate = defaultdict(float) #高匿名性支払い率
    user_night_rate = defaultdict(float) #深夜早朝の購入率
    user_max_qty = defaultdict(float) #1回の最大購入数
    user_product_diversity = defaultdict(float) #商品の多様性
    user_order_access_ratio = defaultdict(float) #成約率
    user_unique_ip_count = defaultdict(float) #1ユーザーあたりのユニークIP数
    user_avg_order_interval = defaultdict(float) #平均注文感覚
    user_shared_ip_max = defaultdict(float) #同一IPからの最大ユーザー数
    user_price_multiplier = defaultdict(float) #低下からの乖離倍率
    user_post_get_ratio = defaultdict(float) #POST/GET比率

    products_map = {p["product_id"]: p for p in products}
    valid_orders = get_valid_completed_orders(orders, products_map)

    # ソート用空リスト
    temp_results = []
    anomalies = []

    all_orders_with_dates = []
    for o in orders:
        od = parse_date(o.get("order_date", ""))
        if od is None:
            continue
        total = safe_float(o.get("total_amount", 0), None)
        if total is None:
            continue
        unit_price = safe_float(o.get("unit_price", 0), 0.0)
        all_orders_with_dates.append({
            **o,
            "_total_amount": total,
            "_order_date": od,
            "_unit_price": unit_price
        })


    # Rule 1: suspicious_order - per-user z-score on order amounts
    user_order_amounts = defaultdict(list)
    sorted_orders = sorted(valid_orders, key=lambda x: x["_order_date"])
    for o in sorted_orders:
        uid = o["user_id"]
        amounts = user_order_amounts[uid]
        if len(amounts) >= 2:
            log_amount = math.log1p(o["_total_amount"]) #log(1 + 金額)
            log_amounts = [math.log1p(a) for a in amounts]
            log_mean = sum(log_amounts) / len(log_amounts)
            log_std = math.sqrt(sum((a - log_mean) ** 2 for a in log_amounts) / len(log_amounts))

            deviation_factor = 0.0
            if log_std > 0:
                deviation_factor = (log_amount - log_mean) / log_std
            if deviation_factor > user_max_zscores[uid]:
                user_max_zscores[uid] = deviation_factor
            log_threshold = log_mean + 3 * log_std
            if log_amount > log_threshold:
                anomalies.append({
                    "type": "suspicious_order",
                    "entity_id": uid,
                    "timestamp": o["order_date"],
                    "_timestamp_dt": o["_order_date"],
                    "details": {
                        "metric": "log_order_amount_zscore",
                        "value": round(o["_total_amount"], 2),
                        "log_value": round(log_amount, 2),
                        "threshold": round(log_threshold, 2),
                        "deviation_factor": round(deviation_factor, 2)
                    }
                })
        user_order_amounts[uid].append(o["_total_amount"])

    # Rule 2: rapid_orders
    user_orders_sorted = defaultdict(list)
    # ユーザーごとに仕分け
    for o in all_orders_with_dates:
        user_orders_sorted[o["user_id"]].append(o)


    for uid, user_ords in user_orders_sorted.items():
        # 注文を古い順に
        user_ords.sort(key=lambda x: x["_order_date"])
        overall_max_count, overall_max_amount, max_start_idx = get_max_orders_in_window(user_ords, window_minutes=10)
        if overall_max_count >= 10:
            deviation_factor = overall_max_count / 3.0
            anomalies.append({
                "type": "rapid_orders",
                "entity_id": uid,
                "timestamp": user_ords[max_start_idx]["order_date"],
                "_timestamp_dt": user_ords[max_start_idx]["_order_date"],
                "details": {
                    "metric": "order_count_10min",
                    "value": float(overall_max_count),
                    "threshold": 3.0,
                    "deviation_factor": round(deviation_factor, 2)
                }
            })
            
        
        user_max_counts[uid] = float(overall_max_count)
        user_max_amounts[uid] = float(overall_max_amount)

    # Rule 3: unusual_access - 100+ accesses from same IP in 1 hour

    ip_to_users = defaultdict(set)
    user_to_ips = defaultdict(set)
    for log in access_logs:
        uid = log.get("user_id", "")
        ip = log.get("ip_address")
        if ip and uid:
            ip_to_users[ip].add(uid)
            user_to_ips[uid].add(ip)
        # idを決定(ユーザーIDがなければIPをにDに)
        target_id = get_target_id(uid, ip)

        if target_id:
            # ユーザーごとのアクセス頻度などをカウントしてuser_max_access[uid]に入れる
            user_max_access[target_id] += 1.0

    # ユーザーごとにログ振り分け
    access_timestamps = defaultdict(list)
    for log in access_logs:
        target_id = log.get("ip_address")

        ts = parse_date(log.get("timestamp", ""))
        if target_id and ts:
            access_timestamps[target_id].append(ts)


    # Rule 4: price_mismatch - unit price differs >=5% from product master
    for target_id, timestamps in access_timestamps.items():
        timestamps.sort()
        left = 0
        max_count_1h = 0
        max_idx = 0
        for right in range(len(timestamps)):
            while timestamps[right] - timestamps[left] > timedelta(hours=1):
                left += 1
            current_count = right - left + 1
            if current_count > max_count_1h:
                max_count_1h = current_count
                max_idx = right
        if max_count_1h >= 100:
            anomalies.append({
                "type": "unusual_access",
                "entity_id": target_id,
                "timestamp": timestamps[max_idx].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "_timestamp_dt": timestamps[max_idx],
                "details": {
                    "metric": "access_count_1h",
                    "value": float(max_count_1h),
                    "threshold": 100.0,
                    "deviation_factor": round(max_count_1h / 100.0, 2)
                }
            })
    user_cancel_counts = defaultdict(float) #キャンセル回数　追加
    user_total_orders = defaultdict(float) #注文回数
    user_e_wallet_counts = defaultdict(float) #電子マネー利用数
    user_night_order_counts = defaultdict(float) #深夜早朝の購入数
    user_product_sets = defaultdict(set) #種類数
    user_order_counts_total = defaultdict(int) #総注文数

    
    # 判定対象を注文した人からログまで広げる
    all_uids_set = list(set(user_orders_sorted.keys()) |
                    set(user_max_access.keys()) |
                    set(true_anomaly_ids))
    
    if "" in all_uids_set:
        all_uids_set.remove("")
    all_uids = sorted(list(all_uids_set))

    # ユーザー別のユニークIP数を計算
    for target_id in all_uids:
        user_unique_ip_count[target_id] = float(len(user_to_ips[target_id]))

    # 平均注文感覚を計算
    for uid, user_ords in user_orders_sorted.items():
        if len(user_ords) > 1:
            first_order = user_ords[0]["_order_date"]
            last_order = user_ords[-1]["_order_date"]
            # 注文と注文の間の平均
            user_avg_order_interval[uid] = (last_order - first_order).total_seconds() / (len(user_ords) - 1)
        else:
            #注文が1回以下の場合は間隔0
            user_avg_order_interval[uid] = 0.0

    # POST/GET比率の集計
    user_method_counts = defaultdict(lambda: {"GET": 0, "POST": 0})
    for log in access_logs:
        target_id = get_target_id(log.get("user_id"), log.get("ip_address"))
        method = log.get("method", "GET").upper()
        if method in ["GET", "POST"]:
            user_method_counts[target_id][method] += 1
    # 比率計算
    for target_id in all_uids:
        counts = user_method_counts[target_id]
        if counts["GET"] > 0:
            user_post_get_ratio[target_id] = counts["POST"] / counts["GET"]
        else:
            user_post_get_ratio[target_id] = float(counts["POST"])
    
        # 全注文データ確認
    for o in orders:
        target_id = o.get("user_id") or ""
        if not target_id: continue

        user_total_orders[target_id] += 1.0

        # キャンセルされた注文カウント
        if o.get("status") in ["cancelled", "refunded"]:#追加
            user_cancel_counts[target_id] += 1.0
        
        # 匿名性高い支払いカウント
        if o.get("payment_method") == "e_wallet":
            user_e_wallet_counts[target_id] += 1.0

        # 時間チェック
        dt = parse_date(o.get("order_date", ""))
        if dt and (0 <= dt.hour <= 5):
            user_night_order_counts[target_id] += 1.0

        # 1回の最大購入数カウント
        qty = safe_float(o.get("quantity", 1), 1.0)
        # 最大購入数の記録更新
        if qty > user_max_qty[target_id]:
            user_max_qty[target_id] = qty

        # 商品の多様性
        pid = o.get("product_id")
        if pid:
            user_product_sets[target_id].add(pid)
            user_order_counts_total[target_id] += 1

    # ipあたりのユーザー数
    for target_id in all_uids:
        max_shared = 0
        if target_id in user_to_ips:
            for ip in user_to_ips[target_id]:
                max_shared = max(max_shared, len(ip_to_users[ip]))
        elif target_id in ip_to_users:
            max_shared = len(ip_to_users[target_id])

        user_shared_ip_max[target_id] = float(max_shared)

    for o in all_orders_with_dates:
        target_id = o.get("user_id")
        if not target_id:
            continue
        pid = o.get("product_id", "")
        actual_price = o["_unit_price"]
        original_price = products_map.get(pid, {}).get("price", actual_price)

        # 価格のズレを計算(%)
        if original_price > 0:
            diff_pct = abs(actual_price - original_price) / original_price * 100
            if diff_pct > user_price_diffs[target_id]:
                user_price_diffs[target_id] = diff_pct

            deviation = abs((actual_price / original_price) - 1.0)
            if deviation > user_price_multiplier[target_id]:
                user_price_multiplier[target_id] = deviation
            if diff_pct >= 5.0:
                anomalies.append({
                    "type": "price_mismatch",
                    "entity_id": target_id,
                    "timestamp": o["order_date"],
                    "_timestamp_dt": o["_order_date"],
                    "details": {
                        "metric": "price_difference_pct",
                        "value": round(diff_pct, 2),
                        "threshold": 5.0,
                        "deviation_factor": round(diff_pct / 5.0, 2)
                    }
                })

    for target_id in user_total_orders:
        total = user_total_orders[target_id]
        if total > 0:
            user_cancel_rate[target_id] = user_cancel_counts[target_id] / total
            user_e_wallet_rate[target_id] = user_e_wallet_counts[target_id] / total
            user_night_rate[target_id] = user_night_order_counts[target_id] / total

    # 多様性スコ計算計算
    for target_id in all_uids:
        total = user_order_counts_total[target_id]
        if total > 0:
            # スコア = 種類数 / 総注文数
            user_product_diversity[target_id] = len(user_product_sets[target_id]) / total
        else:
            user_product_diversity[target_id] = 1.0 #注文なしは普通

        access_count = user_max_access[target_id]
        order_count = user_total_orders[target_id]

        if access_count > 0:
            user_order_access_ratio[target_id] = order_count / access_count
        elif order_count > 0:
            user_order_access_ratio[target_id] = 99.0
        else:
            user_order_access_ratio[target_id] = 0.0

    # Sort by timestamp
    anomalies.sort(key=lambda x: x["_timestamp_dt"])

    # Determine severity
    for a in anomalies:
        temp_results.append({
            "type": a["type"],
            "entity_id": a["entity_id"],
            "timestamp": a["timestamp"],
            "severity": a.get("severity", "medium"),
            "details": a["details"],
            "ai_score": 0
        })

    feature_maps = {
        "user_max_amounts": user_max_amounts,
        "user_price_diffs": user_price_diffs,
        "user_max_access": user_max_access,
        "user_max_zscores": user_max_zscores,
        "user_cancel_rate": user_cancel_rate,
        "user_e_wallet_rate": user_e_wallet_rate,
        "user_night_rate": user_night_rate,
        "user_unique_ip_count": user_unique_ip_count,
        "user_avg_order_interval": user_avg_order_interval,
        "user_max_qty": user_max_qty,
        "user_product_diversity": user_product_diversity,
        "user_order_access_ratio": user_order_access_ratio,
        "user_price_multiplier": user_price_multiplier,
        "user_post_get_ratio": user_post_get_ratio,
        "user_max_counts": user_max_counts,
        "user_shared_ip_max": user_shared_ip_max
    }
    return temp_results, feature_maps, all_uids, user_orders_sorted


        
# AI学習
def enrich_with_ai_anomalies(temp_results, feature_maps, all_uids, true_anomaly_ids, user_orders_sorted, access_logs):
    V = []
    labels = []

    for target_id in all_uids:
        # AIに渡す
        V.append([
            feature_maps["user_max_amounts"][target_id],
            feature_maps["user_price_diffs"][target_id],
            feature_maps["user_max_access"][target_id],
            feature_maps["user_max_zscores"][target_id],
            feature_maps["user_cancel_rate"][target_id],
            feature_maps["user_e_wallet_rate"][target_id],
            feature_maps["user_night_rate"][target_id],
            feature_maps["user_unique_ip_count"][target_id],
            feature_maps["user_avg_order_interval"][target_id],
            feature_maps["user_max_qty"][target_id],
            feature_maps["user_product_diversity"][target_id],
            feature_maps["user_order_access_ratio"][target_id],
            feature_maps["user_price_multiplier"][target_id],
            feature_maps["user_post_get_ratio"][target_id]
        ])
        labels.append(1 if target_id in true_anomaly_ids else 0)


    # 1.AIのモデルを作成
    model = RandomForestClassifier(
        n_estimators=1000,
        max_depth=5,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=42
        )

    # 2.学習開始(V: 特徴, labels: 正解)
    print("\nAIの学習を開始します...")
    model.fit(V, labels)
    print("学習完了")


    # 特徴の名前リスト
    feature_names = [
        "10分間金額", "価格差％", "アクセス総数", "金額Zスコア",
        "キャンセル率", "e-wallet率", "深夜早朝購入率", "ユニークIP数",
        "平均注文間隔", "1回最大購入数", "商品多様性", "成約率",
        "価格乖離倍率", "POST-GET比率"
    ]

    # 重みランキング
    importances = model.feature_importances_
    feature_importance_df = pd.DataFrame({"特徴量": feature_names, "重要度": importances})
    feature_importance_df = feature_importance_df.sort_values(by="重要度", ascending=False)

    print("\n--- AIの重みランキング ---")
    print(feature_importance_df)


    # タイムスタンプ取得
    user_representative_timestamp = {}

    # 末尾-1の要素がそのユーザーの最新の注文日時となる
    for uid, user_ords in user_orders_sorted.items():
        if user_ords:
            user_representative_timestamp[uid] = user_ords[-1].get("order_date")

    # アクセスログからタイムスタンプを取得する
    for log in access_logs:
        target_id = get_target_id(log.get("user_id"), log.get("ip_address"))

        if target_id and (target_id not in user_representative_timestamp):
            ts = log.get("timestamp")
            if ts:
                user_representative_timestamp[target_id] = ts


    # 本番
    existing_anomaly_keys = {(item["entity_id"], item["type"], item["timestamp"]) for item in temp_results}

    # 1.全ユーザーのデータ(V)をAIに一括で読み込ませる
    # predict_prodaは「何％の確率で異常か」を出すもの
    all_predictions_prob = model.predict_proba(V)

    # 2.結果を整理して表示
    print("\n--- AIによる全ユーザー再判定レポート ---")

    # ユーザーIDリストを用意 (user_orders_sorted のキー)
    for i, target_id in enumerate(all_uids):
        # [0の確率, 1の確率]で[1]は「異常確率」になる
        anomaly_score = float(all_predictions_prob[i][1])

        # 確率が50％超えたら「AI公認の異常」
        if anomaly_score <= 0.5:
            continue

        # 特徴量取得
        val_price_mult = feature_maps["user_price_multiplier"][target_id]
        val_max_counts = feature_maps["user_max_counts"][target_id]
        val_shared_ip = feature_maps["user_shared_ip_max"][target_id]
        val_max_z = feature_maps["user_max_zscores"][target_id]

        # 検知した異常リスト
        detected_types = []

        # タイプ割り振り
        # 価格不整合チェック
        if val_price_mult >= 0.05:
            v = round(val_price_mult * 100, 2)
            detected_types.append({
                "type": "price_mismatch",
                "metric": "price_difference_pct",
                "value": v,
                "threshold": 5.0,
                "deviation_factor": round(v / 5.0, 2)
            })

        # 連続注文チェック
        if val_max_counts >= 3:
            v = float(val_max_counts)
            detected_types.append({
                "type": "rapid_orders",
                "metric": "order_count_10min",
                "value": v,
                "threshold": 3.0,
                "deviation_factor": round(v / 3.0, 2)
            })

        # 異常アクセスチェック
        if val_shared_ip >= 3:
            v = float(val_shared_ip)
            detected_types.append({
                "type": "unusual_access",
                "metric": "shared_ip_user_count",
                "value": v,
                "threshold": 3.0,
                "deviation_factor": round(v / 3.0, 2)
            })

        # 高額注文チェック
        if val_max_z >= 3.0:
            v = round(float(feature_maps["user_max_amounts"].get(target_id, 0)), 2)
            detected_types.append({
                "type": "suspicious_order",
                "metric": "order_amount",
                "value": v,
                "threshold": 0.0,
                "deviation_factor": round(val_max_z, 2)
            })

        #閾値に届かなかった場合
        if not detected_types:
            ratios = {
                "price_mismatch": val_price_mult / 0.05,
                "rapid_orders": val_max_counts / 3.0,
                "unusual_access": val_shared_ip / 3.0,
                "suspicious_order": val_max_z / 3.0 if val_max_z > 0 else 0
            }
        # 割合が最大のタイプ選出
            likely_type = max(ratios, key=ratios.get)

            # 選出されたタイプに応じて記録
            # 価格不整合チェック
            if likely_type == "price_mismatch":
                v = round(val_price_mult * 100, 2)
                detected_types.append({
                    "type": "price_mismatch",
                    "metric": "price_difference_pct_ai_flagged",
                    "value": v,
                    "threshold": 5.0,
                    "deviation_factor": round(ratios["price_mismatch"], 2)
                })
                
            # 連続注文チェック
            elif likely_type == "rapid_orders":
                v = float(val_max_counts)
                detected_types.append({
                    "type": "rapid_orders",
                    "metric": "order_count_10min_ai_flagged",
                    "value": v,
                    "threshold": 3.0,
                    "deviation_factor": round(ratios["rapid_orders"], 2)
                })


            # 異常アクセスチェック
            elif likely_type == "unusual_access":
                v = float(val_shared_ip)
                detected_types.append({
                    "type": "unusual_access",
                    "metric": "shared_ip_user_count_ai_flagged",
                    "value": v,
                    "threshold": 3.0,
                    "deviation_factor": round(ratios["unusual_access"], 2)
                })

                
            # 高額注文チェック
            else:
                v = round(float(feature_maps["user_max_amounts"].get(target_id, 0)), 2)
                detected_types.append({
                    "type": "suspicious_order",
                    "metric": "order_amount_ai_flagged",
                    "value": v,
                    "threshold": 0.0,
                    "deviation_factor": round(val_max_z, 2)
                })

        for dt in detected_types:
            # 二重登録防止
            candidate_timestamp = user_representative_timestamp.get(
                target_id, REFERENCE_DATE.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            anomaly_key = (target_id, dt["type"], candidate_timestamp)
            if anomaly_key in existing_anomaly_keys:
                continue
            existing_anomaly_keys.add(anomaly_key)
            temp_results.append({
                "type": dt["type"], #AIが見つけた怪しい動き
                "entity_id": target_id,
                "timestamp": candidate_timestamp,
                "details": dt,
                "ai_score": anomaly_score
            })



    # # 疑似採点
    # from sklearn.metrics import recall_score, precision_score

    # # labels(正解)と予測結果を比較
    # # model.predict(V)は「0か1か」の予測結果を返します
    # y_pred = model.predict(V)

    # # 的中した人数(True Positives)を計算
    # tp = sum((labels[i] == 1 and y_pred[i] == 1) for i in range(len(labels)))
    # # 見逃した人数(False Negatives)を計算
    # fn = sum((labels[i] == 1 and y_pred[i] == 0) for i in range(len(labels)))
    # # 冤罪(False Positives)を計算
    # fp = sum((labels[i] == 0 and y_pred[i] == 1) for i in range(len(labels)))

    # # サンプル数
    # true_positive_total = sum(labels)

    # print("\n" + "="*40)
    # print("-----本番用-----")
    # print(f"【疑似採点レポート：vs サンプル正解({true_positive_total})】")
    # print(f"\nAIが「怪しい」と睨んだユーザー数: {ai_found_count}人")
    # print(f" ▪ {true_positive_total}人中、的中したのは:{tp}人🎯")
    # print(f" ▪ 見逃してしまったのは:{fn}人 🏃‍♂️")
    # print(f" ▪ 無実なのに異常としたのは:{fp}人❓")
    # print("-" * 40)

    # # スコア計算
    # rec = recall_score(labels, y_pred)
    # prec = precision_score(labels, y_pred)
    # f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

    # print(f" 再現率(Recall): {rec:.1%}")
    # print(f" 適合率(Precision): {prec:.1%}")
    # print(f" 総合 F1スコア; {f1:.3f}")
    # print("-"*40)


    # 昇順ソート
def build_and_save_final_results(temp_results):
    temp_results.sort(key=lambda x: x["timestamp"])

    current_entity_types = defaultdict(set)
    for item in temp_results:
        current_entity_types[item["entity_id"]].add(item["type"])

    # 最終リストを作成
    final_result = []
    for i, item in enumerate(temp_results, 1):
        df = item["details"].get("deviation_factor", 0)
        score = item.get("ai_score", 0)
        is_multi = len(current_entity_types[item["entity_id"]]) > 1

        final_result.append({
            "anomaly_id": f"A{i:03d}",
            "type": item["type"],
            "entity_id": item["entity_id"],
            "timestamp": item["timestamp"],
            "severity": determine_severity(df, is_multi, score),
            "details": normalize_details(item["details"])
        })
    # JSONに保存
    filepath = os.path.join(OUTPUT_DIR, "anomalies.json")
    try:
        with open(filepath, "w", encoding="utf-8") as out_file:
            json.dump(final_result, out_file, indent=2, ensure_ascii=False)
        print(f"保存完了: {filepath} ({len(final_result)}件)")
    except Exception as e:
        print(f"JSON保存エラー: {e}")

    return final_result

def detect_anomalies(orders, products, access_logs):
    print("  Anomaly Detection...")
    label_path = os.path.join(INPUT_DIR, "labeled_anomalies_sample.json")
    with open(label_path, "r", encoding="utf-8") as f:
        labeled_data = json.load(f)
    true_anomaly_ids = [item["entity_id"] for item in labeled_data]

    temp_results, feature_maps, all_uids, user_orders_sorted = build_features_and_rule_anomalies(
        orders, products, access_logs, true_anomaly_ids
    )
    print(f"    -> {len(temp_results)} anomalies written")

    enrich_with_ai_anomalies(
        temp_results, feature_maps, all_uids, true_anomaly_ids, user_orders_sorted, access_logs
    )
    return build_and_save_final_results(temp_results)


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Anomaly Detection Pipeline - Starting")
    print(f"  Input:  {INPUT_DIR}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("\nLoading data...")
    orders = load_orders()
    products = load_products()
    access_logs = load_access_logs()
    print(f"  Orders: {len(orders)}, Products: {len(products)}, Logs: {len(access_logs)}")

    print("\nProcessing...")
    detect_anomalies(orders, products, access_logs)

    # Write completion marker
    with open(os.path.join(OUTPUT_DIR, ".done"), "w") as f:
        f.write("done\n")

    print("\n" + "=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
