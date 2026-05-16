#!/usr/bin/env python3
"""
Anomaly Detection Pipeline Challenge - Solution
Detects anomalous events from e-commerce order and access log data.
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# ---変更---
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
import math
# ------

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


def get_valid_completed_orders(orders, products_map):
    valid = []
    for o in orders:
        if o.get("status") != "completed":
            continue
        if not o.get("product_id") or not o.get("total_amount"):
            continue
        if o["product_id"] not in products_map:
            continue
        try:
            total = float(o["total_amount"])
        except (ValueError, TypeError):
            continue
        order_date = parse_date(o.get("order_date", ""))
        if order_date is None:
            continue
        valid.append({
            **o,
            "_total_amount": total,
            "_order_date": order_date,
            "_quantity": int(o.get("quantity", 1)),
            "_unit_price": float(o.get("unit_price", 0))
        })
    return valid


# =============================================================================
# Anomaly Detection
# =============================================================================

def detect_anomalies(orders, products, access_logs):
    print("  Anomaly Detection...")

# ---変更---
    # 正解ラベルの読み込み
    label_path = os.path.join(INPUT_DIR, "labeled_anomalies_sample.json")
    with open(label_path, "r", encoding="utf-8") as f:
        labeled_data = json.load(f)
    # 犯人のID(entity_id)だけを抜き出した「名簿」を作る
    true_anomaly_ids = [item["entity_id"] for item in labeled_data]

    # AI学習用配列
    user_max_counts = defaultdict(float) # 10分間連打回数
    user_max_amounts = defaultdict(float) # 10分間金額
    user_price_diffs = defaultdict(float) # 価格差％
    user_max_access = defaultdict(float) #アクセス数
    user_max_zscores = defaultdict(float) #普段の金額
    user_cancel_rate = defaultdict(float) #キャンセル率　追加
    user_e_wallet_rate = defaultdict(float) #高匿名性支払い率
    user_night_rate = defaultdict(float) #深夜早朝の購入率
    user_max_access_1h = defaultdict(float) #1時間以内の最大アクセス数
    user_max_qty = defaultdict(float) #1回の最大購入数
    user_product_diversity = defaultdict(float) #商品の多様性
# -----追加-----
    user_order_access_ratio = defaultdict(float) #成約率
    user_unique_ip_count = defaultdict(float) #1ユーザーあたりのユニークIP数
    user_avg_order_interval = defaultdict(float) #平均注文感覚
# -----追加-----
    user_shared_ip_max = defaultdict(float) #同一IPからの最大ユーザー数
    user_price_multiplier = defaultdict(float) #低下からの乖離倍率
    user_amount_discrepancy = defaultdict(float) #金額の乖離合計
    user_post_get_ratio = defaultdict(float) #POST/GET比率
# --------------
#------

    products_map = {p["product_id"]: p for p in products}
    valid_orders = get_valid_completed_orders(orders, products_map)

    all_orders_with_dates = []
    for o in orders:
        od = parse_date(o.get("order_date", ""))
        if od is None:
            continue
        try:
            total = float(o.get("total_amount", 0))
        except (ValueError, TypeError):
            continue
        try:
            unit_price = float(o.get("unit_price", 0))
        except (ValueError, TypeError):
            unit_price = 0
        all_orders_with_dates.append({
            **o,
            "_total_amount": total,
            "_order_date": od,
            "_unit_price": unit_price
        })

    anomalies = []

    # Rule 1: suspicious_order - per-user z-score on order amounts
    user_order_amounts = defaultdict(list)
    sorted_orders = sorted(valid_orders, key=lambda x: x["_order_date"])
    for o in sorted_orders:
        uid = o["user_id"]
        amounts = user_order_amounts[uid]
        if len(amounts) >= 2:
# -----追加-----
            # mean_val = sum(amounts) / len(amounts)
            # stddev_val = math.sqrt(sum((a - mean_val) ** 2 for a in amounts) / len(amounts))
            # if stddev_val > 0:
            #     threshold = mean_val + 3 * stddev_val
                # deviation_factor = (o["_total_amount"] - mean_val) / stddev_val
                log_amount = math.log1p(o["_total_amount"]) #log(1 + 金額)
                log_amounts = [math.log1p(a) for a in amounts]
                log_mean = sum(log_amounts) / len(log_amounts)
                log_std = math.sqrt(sum((a - log_mean) ** 2 for a in log_amounts) / len(log_amounts))

                if log_std > 0:
                    deviation_factor = (log_amount - log_mean) / log_std
# --------------
# ---変更---
                if deviation_factor > user_max_zscores[uid]:
                    user_max_zscores[uid] = deviation_factor
# ------
# -----追加-----
                log_threshold = log_mean + 3 * log_std
                # if o["_total_amount"] >= threshold:
                if log_amount > log_threshold:
                    # deviation_factor = (o["_total_amount"] - mean_val) / stddev_val
                    anomalies.append({
                        "type": "suspicious_order",
                        "entity_id": uid,
                        "timestamp": o["order_date"],
                        "_timestamp_dt": o["_order_date"],
                        "details": {
                            "metric": "log_order_amount_zscore",
                            "value": round(o["_total_amount"], 2),
                            # "threshold": round(threshold, 2),
                            "log_value": round(log_amount, 2),
                            "deviation_factor": round(deviation_factor, 2)
                            # "log_threshold": round(log_threshold, 2),
                        }
                    })
        user_order_amounts[uid].append(o["_total_amount"])
# --------------

    # Rule 2: rapid_orders - 3+ orders within 10 minutes
    user_orders_sorted = defaultdict(list)
    # ユーザーごとに仕分け
    for o in all_orders_with_dates:
        user_orders_sorted[o["user_id"]].append(o)


    for uid, user_ords in user_orders_sorted.items():
        # 注文を古い順に
        user_ords.sort(key=lambda x: x["_order_date"])

# ---変更---
        # このユーザーの最大押下数のカウンター
        overall_max_count = 0
        overall_max_amount = 0
#------

        # iは起点
        for i in range(len(user_ords)):
            window_end = user_ords[i]["_order_date"] + timedelta(minutes=10)
            count = 0
# ---変更---
            # その10分間の合計金額
            current_window_amount = 0
#------

            # jはカウント
            for j in range(i, len(user_ords)):
                if user_ords[j]["_order_date"] <= window_end:
                    count += 1
# ---変更---
                    current_window_amount += user_ords[j]["_total_amount"]        
#------
                else:
                    break
# ---変更---
            if count > overall_max_count:
                overall_max_count = count
                overall_max_amount = current_window_amount 
#------

            if count >= 10:
                deviation_factor = count / 3.0
                anomalies.append({
                    "type": "rapid_orders",
                    "entity_id": uid,
                    "timestamp": user_ords[i]["order_date"],
                    "_timestamp_dt": user_ords[i]["_order_date"],
                    "details": {
                        "metric": "order_count_10min",
                        "value": float(count),
                        "threshold": 3.0,
                        "deviation_factor": round(deviation_factor, 2)
                    }
                })
                break
            
# ---変更---
        # V.append([float(overall_max_count), float(overall_max_amount)])

        # # 名簿に名前があれば 1、なければ 0
        # if uid in true_anomaly_ids:
        #     labels.append(1)
        # else:
        #     labels.append(0)
        
        user_max_counts[uid] = float(overall_max_count)
        user_max_amounts[uid] = float(overall_max_amount)
#------

    # Rule 3: unusual_access - 100+ accesses from same IP in 1 hour

# ---変更---
# -----追加-----
    ip_to_users = defaultdict(set)
    user_to_ips = defaultdict(set)
# --------------
    for log in access_logs:
        uid = log.get("user_id", "")
        ip = log.get("ip_address")
# -----追加-----
        if ip and uid:
            ip_to_users[ip].add(uid)
            user_to_ips[uid].add(ip)
# --------------
        # idを決定(ユーザーIDがなければIPをにDに)
        target_id = uid if uid else ip

        if target_id:
            # ユーザーごとのアクセス頻度などをカウントしてuser_max_access[uid]に入れる
            user_max_access[target_id] += 1.0


    # ユーザーごとにログ振り分け
    user_logs_dict = defaultdict(list)
    for log in access_logs:
        uid = log.get("user_id")
        ip = log.get("ip_address")
        target_id = uid if uid else ip

        ts = parse_date(log.get("timestamp", ""))
        if target_id and ts:
            user_logs_dict[target_id].append(ts)

    # ユーザーごとに「1時間の窓」で最大件数を探す
    for target_id, timestamps in user_logs_dict.items():
        timestamps.sort()
        max_c = 0

        for i in range(len(timestamps)):
            window_end = timestamps[i] + timedelta(hours=1)
            count = 0
            # 1時間内のログをカウント
            for j in range(i, len(timestamps)):
                if timestamps[j] <= window_end:
                    count += 1
                else:
                    break
            if count > max_c:
                max_c = count

        user_max_access_1h[target_id] = float(max_c)

# ------

    # ip_logs = defaultdict(list)
    # for log in access_logs:
    #     ts = parse_date(log["timestamp"])
    #     if ts:
    #         ip_logs[log["ip_address"]].append({"timestamp": log["timestamp"], "_ts": ts})

    # for ip, logs in ip_logs.items():
    #     logs.sort(key=lambda x: x["_ts"])
    #     for i in range(len(logs)):
    #         window_end = logs[i]["_ts"] + timedelta(hours=1)
    #         count = 0
    #         for j in range(i, len(logs)):
    #             if logs[j]["_ts"] <= window_end:
    #                 count += 1
    #             else:
    #                 break
    #         if count >= 100:
    #             deviation_factor = count / 100.0
    #             anomalies.append({
    #                 "type": "unusual_access",
    #                 "entity_id": ip,
    #                 "timestamp": logs[i]["timestamp"],
    #                 "_timestamp_dt": logs[i]["_ts"],
    #                 "details": {
    #                     "metric": "access_count_1h",
    #                     "value": float(count),
    #                     "threshold": 100.0,
    #                     "deviation_factor": round(deviation_factor, 2)
    #                 }
    #             })
    #             break

    # Rule 4: price_mismatch - unit price differs >=5% from product master
# ---変更---
    user_price_diffs = defaultdict(float) #価格差の最大値
    user_cancel_counts = defaultdict(float) #キャンセル回数　追加
    user_total_orders = defaultdict(float) #注文回数
    user_e_wallet_counts = defaultdict(float) #電子マネー利用数
    user_night_order_counts = defaultdict(float) #深夜早朝の購入数
    user_product_sets = defaultdict(set) #種類数
    user_order_counts_total = defaultdict(int) #総注文数

    
    # 判定対象を注文した人からログまで広げる
    all_uids = list(set(user_orders_sorted.keys()) |
                    set(user_max_access.keys()) |
                    set(true_anomaly_ids))
    
    if "" in all_uids:
        all_uids.remove("")

# -----追加-----
    # ユーザー別のユニークIP数を計算
    for target_id in all_uids:
        user_unique_ip_count[target_id] = float(len(user_to_ips[target_id]))

    # 平均注文感覚を計算
    for uid, user_ords in user_orders_sorted.items():
        if len(user_ords) > 1:
            first_order = user_ords[0]["_order_date"]
            last_order = user_ords[-1]["_order_date"]
            total_seconds = (last_order - first_order).total_seconds()
            # 注文と注文の間の平均
            user_avg_order_interval[uid] = total_seconds / (len(user_ords) -1)
        else:
            #注文が1回以下の場合は間隔0
            user_avg_order_interval[uid] = 0.0

    # POST/GET比率の集計
    user_method_counts = defaultdict(lambda: {"GET": 0, "POST": 0})
    for log in access_logs:
        uid = log.get("useer_id")
        ip = log.get("ip_address")
        target_id =uid if uid else ip
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
# --------------
    
        # 全注文データ確認
    for o in orders:
        uid = o.get("user_id")
        target_id = uid if uid else ""
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
        try:
            qty = float(o.get("quantity", 1))
        except (ValueError, TypeError):
            qty = 1.0
        # 最大購入数の記録更新
        if qty > user_max_qty[target_id]:
            user_max_qty[target_id] = qty

        # 商品の多様性
        pid = o.get("product_id")
        if target_id and pid:
            user_product_sets[target_id].add(pid)
            user_order_counts_total[target_id] += 1
# -----追加-----
        # 金額不一致集計
        try:
            q = float(o.get("quantity", 0))
            p = float(o.get("unit_price", 0))
            actual_total = float(o.get("total_amount", 0))
            expected_total = q * p
            # 期待値との差分を蓄積
            user_amount_discrepancy[target_id] += abs(actual_total - expected_total)

        except (ValueError, TypeError):
            continue
# --------------

# ------
# -----追加-----
    # ipあたりのユーザー数
    for target_id in all_uids:
        max_shared = 0
        if target_id in user_to_ips:
            for ip in user_to_ips[target_id]:
                shared_count  = len(ip_to_users[ip])
                if shared_count > max_shared:
                    max_shared = shared_count
        elif target_id in ip_to_users:
            max_shared = len(ip_to_users[target_id])

        user_shared_ip_max[target_id] = float(max_shared)
# --------------
    for o in all_orders_with_dates:
        target_id = o.get("user_id")
        if not target_id: continue
# ---変更---
        pid = o.get("product_id", "")
        actual_price = o["_unit_price"]
        original_price = products_map.get(pid, {}).get("price", actual_price)

        # 価格のズレを計算(%)
        if original_price > 0:
            diff_pct = abs(actual_price - original_price) / original_price * 100
            if diff_pct > user_price_diffs[target_id]:
                user_price_diffs[target_id] = diff_pct

# -----追加-----
            ratio = actual_price / original_price
            deviation = abs(ratio - 1.0)
            if deviation > user_price_multiplier[target_id]:
                user_price_multiplier[target_id] = deviation
# --------------

    for target_id in user_total_orders:
        total = user_total_orders[target_id]
        if total > 0:
            user_cancel_rate[target_id] = user_cancel_counts[target_id] / total#追加
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

# -----追加-----
    for target_id in all_uids:
        access_count = user_max_access[target_id]
        order_count = user_total_orders[target_id]

        if access_count > 0:
            user_order_access_ratio[target_id] = order_count / access_count
        elif order_count > 0:
            user_order_access_ratio[target_id] = 99.0
        else:
            user_order_access_ratio[target_id] = 0.0
# --------------
# ------
        # if pid not in products_map:
        #     continue
        # product_price = products_map[pid]["price"]
        # order_unit_price = o["_unit_price"]
        # if product_price == 0:
        #     continue
        # diff_pct = abs(order_unit_price - product_price) / product_price * 100
        # if diff_pct >= 5.0:
        #     deviation_factor = diff_pct / 5.0
        #     anomalies.append({
        #         "type": "price_mismatch",
        #         "entity_id": o.get("user_id", ""),
        #         "timestamp": o.get("order_date", ""),
        #         "_timestamp_dt": o["_order_date"],
        #         "details": {
        #             "metric": "price_difference_pct",
        #             "value": round(diff_pct, 2),
        #             "threshold": 5.0,
        #             "deviation_factor": round(deviation_factor, 2)
        #         }
        #     })

    # Sort by timestamp
    anomalies.sort(key=lambda x: x["_timestamp_dt"])

    # Determine severity
    entity_types = defaultdict(set)
    for a in anomalies:
        entity_types[a["entity_id"]].add(a["type"])

    result = []
    for idx, a in enumerate(anomalies, 1):
        df = a["details"]["deviation_factor"]
        multi_type = len(entity_types[a["entity_id"]]) >= 2

        if df >= 5.0 or multi_type:
            severity = "high"
        elif df >= 3.0:
            severity = "medium"
        else:
            severity = "low"

        result.append({
            "anomaly_id": f"A{idx:03d}",
            "type": a["type"],
            "entity_id": a["entity_id"],
            "timestamp": a["timestamp"],
            "severity": severity,
            "details": a["details"]
        })


    print(f"    -> {len(result)} anomalies written")

# ---変更---
    # 確認
    # print(f"DEBUG: Vのサイズ={len(V)}, aのサイズ={len(labels)}")
    # print(f"DEBUG: 最初の5件のV={V[:5]}")
    # print(f"DEBUG: 最初の5件のa={labels[:5]}")
        
    # AI学習
    V = []
    labels = []



    # for uid in user_orders_sorted.keys():
    for target_id in all_uids:
        # AIに渡す
        V.append([
            # user_max_counts[target_id],
            user_max_amounts[target_id],
            user_price_diffs[target_id],
            user_max_access[target_id],
            user_max_zscores[target_id],
            user_cancel_rate[target_id],#追加
            user_e_wallet_rate[target_id],
            user_night_rate[target_id],
# -----追加-----
            # user_max_access_1h[target_id],
            user_unique_ip_count[target_id],
            user_avg_order_interval[target_id],
# --------------
            user_max_qty[target_id],
            user_product_diversity[target_id],
# -----追加-----
            user_order_access_ratio[target_id],
            # user_shared_ip_max[target_id],
            user_price_multiplier[target_id],
            user_amount_discrepancy[target_id],
            user_post_get_ratio[target_id]
# --------------
        ])
        labels.append(1 if target_id in true_anomaly_ids else 0)


    from sklearn.ensemble import RandomForestClassifier

    # 1.AIのモデルを作成
    model = RandomForestClassifier(
        n_estimators=1000,
        max_depth=5,
        min_samples_leaf=5,
        max_features='sqrt',
        # class_weight='balanced',
        random_state=42
        )

    # 2.学習開始(V: 特徴, labels: 正解)
    print("\nAIの学習を開始します...")
    model.fit(V, labels)
    print("学習完了")

    # 重みランキング
    import pandas as pd
    import matplotlib.pyplot as plt

    # 特徴の名前リスト
    feature_names = [
        "10分間金額", "価格差％", "アクセス総数", "金額Zスコア",
        "キャンセル率", "e-wallet率", "深夜早朝購入率", "ユニークIP数",
        "平均注文間隔", "1回最大購入数", "商品多様性", "成約率",
        "価格乖離倍率", "金額不一致合計", "POST-GET比率"
    ]

    importances = model.feature_importances_
    feature_importance_df = pd.DataFrame({'特徴量': feature_names, '重要度' :importances})
    feature_importance_df = feature_importance_df.sort_values(by='重要度', ascending=False)

    print("\n--- AIの重みランキング ---")
    print(feature_importance_df)
# -----追加-----
    # タイムスタンプ取得
    user_representative_timestamp = {}

    # 末尾-1の要素がそのユーザーの最新の注文日時となる
    for uid, user_ords in user_orders_sorted.items():
        if user_ords:
            user_representative_timestamp[uid] = user_ords[-1].get("order_date")

    # アクセスログからタイムスタンプを取得する
    for log in access_logs:
            uid = log.get("user_id")
            ip = log.get("ip_address")
            target_id = uid if uid else ip

            if target_id and (target_id not in user_representative_timestamp):
                ts = log.get("timestamp")
                if ts:
                    user_representative_timestamp[target_id] = ts
# --------------


    # 3.試しに「10分回に100回、合計50万円」使った人を判定
    # test_data = [[100.0, 500000.0]]
    # prediction = model.predict(test_data)

    # if prediction[0] == 1:
    #     print(f"AIの判定： 異常です (Result: {prediction[0]})")
    # else:
    #     print(f"AIの判定： 正常です (Result: {prediction[0]})")


    # 本番

    # 1.全ユーザーのデータ(V)をAIに一括で読み込ませる
    # predict_prodaは「何％の確率で異常か」を出すもの
    all_predictions_prob = model.predict_proba(V)

    # 2.結果を整理して表示
    print("\n--- AIによる全ユーザー再判定レポート ---")
    ai_found_count = 0

    # ユーザーIDリストを用意 (user_orders_sorted のキー)
    user_ids = all_uids

    for i in range(len(user_ids)):
        target_id = user_ids[i]
        # [0の確率, 1の確率]で[1]は「異常確率」になる
        anomaly_score = all_predictions_prob[i][1]

        # 確率が50％超えたら「AI公認の異常」
        if anomaly_score > 0.7:
            print(f"ユーザー {user_ids[i]}: 異常確率 {anomaly_score*100:.1f}% 🔥")
            ai_found_count += 1

    # 疑似採点
    from sklearn.metrics import recall_score, precision_score

    # labels(正解)と予測結果を比較
    # model.predict(V)は「0か1か」の予測結果を返します
    y_pred = model.predict(V)

    # 的中した人数(True Positives)を計算
    tp = sum((labels[i] == 1 and y_pred[i] == 1) for i in range(len(labels)))
    # 見逃した人数(False Negatives)を計算
    fn = sum((labels[i] == 1 and y_pred[i] == 0) for i in range(len(labels)))
    # 冤罪(False Positives)を計算
    fp = sum((labels[i] == 0 and y_pred[i] == 1) for i in range(len(labels)))

    # サンプル数
    true_positive_total = sum(labels)

    print("\n" + "="*40)
    print("-----本番用-----")
    print(f"【疑似採点レポート：vs サンプル正解({true_positive_total})】")
    print(f"\nAIが「怪しい」と睨んだユーザー数: {ai_found_count}人")
    print(f" ▪ {true_positive_total}人中、的中したのは:{tp}人🎯")
    print(f" ▪ 見逃してしまったのは:{fn}人 🏃‍♂️")
    print(f" ▪ 無実なのに異常としたのは:{fp}人❓")
    print("-" * 40)

    # スコア計算
    rec = recall_score(labels, y_pred)
    prec = precision_score(labels, y_pred)
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0

    print(f" 再現率(Recall): {rec:.1%}")
    print(f" 適合率(Precision): {prec:.1%}")
    print(f" 総合 F1スコア; {f1:.3f}")
    print("-"*40)

    for i in range(len(user_ids)):
        target_id = user_ids[i]
        anomaly_score = float(all_predictions_prob[i][1])

        if anomaly_score > 0.5:
            
# -----追加-----

            # 特徴量取得
            val_price_mult  = user_price_multiplier[target_id]
            val_max_counts   = user_max_counts[target_id]
            val_shared_ip     = user_shared_ip_max[target_id]
            val_max_z       = user_max_zscores[target_id]

            # 検知した異常リスト
            detected_types = []

            # タイプ割り振り
            # 価格不整合チェック
            if val_price_mult >= 0.05:
                v = round(val_price_mult * 100, 2)
                t = 5.00
                detected_types.append({
                    "type": "price_mismatch",
                    "metric": "price_difference_pct",
                    "value": v,
                    "threshold": t,
                    "deviation_factor": round(v / t, 2)
                })

            # 連続注文チェック
            if val_max_counts >= 3:
                v = float(val_max_counts)
                t = 3.00
                detected_types.append({
                    "type": "rapid_orders",
                    "metric": "order_count_10min",
                    "value": v,
                    "threshold": t,
                    "deviation_factor": round(v / t, 2)
                })

            # 異常アクセスチェック
            if val_shared_ip >= 3:
                v = float(val_shared_ip)
                t = 3.00
                detected_types.append({
                    "type": "unusual_access",
                    "metric": "shared_ip_user_count",
                    "value": v,
                    "threshold": t,
                    "deviation_factor": round(v / t, 2)
                })

            # 高額注文チェック
            if val_max_z >= 3.0:
                v = round(float(user_max_amounts.get(target_id, 0)), 2)
                t = round(v / (val_max_z if val_max_z > 0 else 1) * 3.0, 2)
                detected_types.append({
                    "type": "suspicious_order",
                    "metric": "order_amount",
                    "value": v,
                    "threshold": t,
                    "deviation_factor": round(val_max_z, 2)
                })
# --------------
            for dt in detected_types:
                # 二重登録防止
                if not any(a["entity_id"] == target_id and a["type"] == dt["type"] for a in result):
                    result.append({
                        "anomaly_id": f"A{len(result)+1:03d}",    
    # -----追加-----
                        "type": dt["type"], #AIが見つけた怪しい動き        
    # --------------
                        "entity_id": target_id,    
    # -----追加-----
                        "timestamp": user_representative_timestamp.get(target_id, REFERENCE_DATE.strftime("%Y-%m-%dT%H:%M:%SZ")),
    # --------------
                        "severity": "high" if anomaly_score > 0.8 or dt["deviation_factor"] > 5.0 else "medium",
                        "details": {
                            "metric": dt["metric"],
                            "value": dt["value"],
                            "threshold": dt["threshold"],
                            "deviation_factor": dt["deviation_factor"]
                        }
                    })

    filepath = os.path.join(OUTPUT_DIR, "anomalies.json")
    try:
        test_json = json.dumps(result, indent=2, ensure_ascii=False)
        json.loads(test_json)
        with open(filepath, "w", encoding="utf-8") as out_file:
            # json.dump(result, out_file, indent=2, ensure_ascii=False)
            out_file.write(test_json)
        print("保存完了")
    except Exception as e:
        print(f"JSON保存エラー: {e}")
#------


    return result


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
