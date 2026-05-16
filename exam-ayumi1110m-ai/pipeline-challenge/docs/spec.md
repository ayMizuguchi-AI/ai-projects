# 詳細仕様

## 概要

本ドキュメントでは、異常検知タスクの入出力フォーマット・検知対象・評価方法を定義します。パイプラインは `data/input/` からデータを読み込み、`output/` に結果を出力してください。

## 基準日

日付に関するすべての相対計算は **2025-01-31** を基準日とします。

## データ期間

入力データは **2024-10-01 〜 2025-01-31**（4ヶ月間）を対象としています。

---

## 異常検知

### 入力
- `data/input/orders.csv`
- `data/input/access_logs.jsonl`
- `data/input/products.json`
- `data/input/users.json`
- `data/input/labeled_anomalies_sample.json`（学習用：ラベル付き異常データの約30%）

### 出力
- `output/anomalies.json`

### 概要

注文データおよびアクセスログから**異常なイベント**を検知する。

**検知手法は自由です。** ルールベース（統計的閾値）、Isolation Forest、Local Outlier Factor、Autoencoder、アンサンブル手法など、どのようなアプローチでも構いません。

### ラベル付き学習データ（`labeled_anomalies_sample.json`）

検知すべき異常の約30%がラベル付きデータとして提供されます。これを教師あり/半教師あり学習や、ルール設計の参考に使用できます。

```json
[
  {
    "type": "suspicious_order",
    "entity_id": "U045",
    "timestamp": "2025-01-15T14:23:00Z",
    "severity": "high",
    "details": {
      "metric": "order_amount",
      "value": 980000.00
    }
  }
]
```

> **注意**: ラベル付きデータには `threshold` や `deviation_factor` は含まれません。これらは受験者が独自に設計する部分です。

### 異常タイプ

検知すべき異常は以下の4カテゴリです。各カテゴリの特徴を参考情報として示します。

| 異常タイプ | 概要 | 特徴の目安 |
|------------|------|-----------|
| `suspicious_order` | 通常とかけ離れた高額注文 | ユーザーの購買パターンから大きく逸脱する注文額 |
| `rapid_orders` | 短時間に集中する連続注文 | 同一ユーザーによる短時間内の異常な注文頻度 |
| `unusual_access` | 異常なアクセスパターン | 同一IPからの短時間内の大量アクセス |
| `price_mismatch` | 価格の不整合 | 注文時の単価と商品マスタ価格の有意な乖離 |

> **注意**: 上記はカテゴリの概要説明です。具体的な閾値・検知条件は規定しません。ラベル付きデータからパターンを学習するか、独自の統計的/ML手法で検知ロジックを設計してください。

### 推奨アプローチ（参考）

以下は参考となるアプローチ例です。これらに限定する必要はありません。

1. **統計的手法** — 平均・標準偏差に基づく閾値設定（Zスコア、IQR法等）
2. **教師あり学習** — ラベル付きデータで分類モデルを学習（Random Forest, XGBoost等）
3. **教師なし学習** — Isolation Forest, DBSCAN, Local Outlier Factor等
4. **時系列分析** — スライディングウィンドウによる頻度ベースの検知
5. **ハイブリッド手法** — ルールベースとMLの組み合わせ

### 重大度（severity）の分類

検知した各異常に対して、以下の3段階で重大度を分類してください。

| 重大度 | 意味 |
|--------|------|
| `high` | ビジネスに重大な影響を与えうる異常 |
| `medium` | 注意が必要な異常 |
| `low` | 軽微な異常 |

重大度の判定基準は自由です。ラベル付きデータのパターンを参考に設計してください。

### 出力ルール

- `anomaly_id` は連番: `A001`, `A002`, `A003`, ...
- `timestamp` 昇順でソート
- 1つのイベントが複数の異常タイプに該当する場合、それぞれ個別の異常として出力
- `details.metric` — 検知に使用した主要指標名（自由記述）
- `details.value` — 観測値（小数第2位まで）
- `details.threshold` — 使用した閾値（小数第2位まで）。ML手法など閾値が明確でない場合は異常スコアの判定境界値を記載
- `details.deviation_factor` — 逸脱の程度を示す係数（小数第2位まで）。算出方法は自由

### 評価方法（概要）

非公開の完全な異常ラベルデータに対して、**F1スコア**（Precision × Recall の調和平均）で評価されます。

- マッチング条件: `type` + `entity_id` + `timestamp`（完全一致）
- Precision = TP / (TP + FP), Recall = TP / (TP + FN)
- F1 = 2 × Precision × Recall / (Precision + Recall)

### 出力フォーマット

```json
[
  {
    "anomaly_id": "A001",
    "type": "suspicious_order",
    "entity_id": "U045",
    "timestamp": "2025-01-15T14:23:00Z",
    "severity": "high",
    "details": {
      "metric": "order_amount",
      "value": 980000.00,
      "threshold": 150000.00,
      "deviation_factor": 6.53
    }
  }
]
```

---

## 共通事項

- 金額はすべて日本円（JPY）。通貨記号は不要
- 浮動小数点値は特に指定がない限り小数第2位まで
- 出力のタイムスタンプは ISO 8601 形式（`Z` サフィックス付き、UTC）
- JSON 出力は有効な JSON であること（文字列の適切なエスケープ、末尾カンマ禁止）
- 結果が空の場合、JSON は空配列 `[]` を出力
