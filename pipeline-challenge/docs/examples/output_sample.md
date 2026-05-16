# 出力データスキーマ

## 異常検知（`anomalies.json`）— アルゴリズム自由

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

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `anomaly_id` | string | 異常ID（連番: A001, A002, ...） |
| `type` | string | 異常タイプ（4種類のいずれか） |
| `entity_id` | string | 関連するユーザーIDまたはIPアドレス |
| `timestamp` | string | 異常発生日時（ISO 8601） |
| `severity` | string | 重大度（`high`、`medium`、`low`） |
| `details.metric` | string | 検知に使用した主要指標名（自由記述） |
| `details.value` | float | 観測値（小数第2位まで） |
| `details.threshold` | float | 使用した閾値（小数第2位まで）。ML手法の場合は判定境界値 |
| `details.deviation_factor` | float | 逸脱の程度を示す係数（小数第2位まで）。算出方法は自由 |

### タスク概要

注文データおよびアクセスログから異常なイベントを検知します。検知手法は自由です。

### ラベル付き学習データ

`labeled_anomalies_sample.json` に全異常の約30%がラベル付きで提供されます。教師あり学習やルール設計の参考に使用できます。

### 異常タイプ（4カテゴリ）

| タイプ | 概要 | 検知のヒント |
|--------|------|-------------|
| `suspicious_order` | 通常とかけ離れた高額注文 | ユーザーの過去の注文額の統計から逸脱する注文を検知 |
| `rapid_orders` | 短時間に集中する連続注文 | 同一ユーザーの注文タイムスタンプの時間間隔を分析 |
| `unusual_access` | 同一IPからの異常アクセスパターン | IPアドレス別のアクセス頻度をウィンドウで分析 |
| `price_mismatch` | 注文時単価と商品マスタ価格の不整合 | 注文の `unit_price` と商品マスタの `price` を比較 |

> 具体的な閾値・検知条件は規定しません。ラベル付きデータからパターンを学習するか、独自の手法で設計してください。

### 重大度の分類

| 重大度 | 意味 |
|--------|------|
| `high` | ビジネスに重大な影響を与えうる異常 |
| `medium` | 注意が必要な異常 |
| `low` | 軽微な異常 |

判定基準は自由です。ラベル付きデータのパターンを参考に設計してください。

### 評価指標
- **検知F1スコア** — type + entity_id + timestamp（完全一致）でマッチング
- F1 = 2 × Precision × Recall / (Precision + Recall)

### 出力ルール
- `timestamp` 昇順でソート
- 異常IDはタイムスタンプ順に連番（A001, A002, ...）
- 1つのイベントが複数の異常タイプに該当する場合、それぞれ個別の異常として出力

### 出力例

```json
[
  {
    "anomaly_id": "A001",
    "type": "price_mismatch",
    "entity_id": "U032",
    "timestamp": "2024-10-05T08:12:00Z",
    "severity": "low",
    "details": {
      "metric": "price_difference_pct",
      "value": 8.50,
      "threshold": 5.00,
      "deviation_factor": 1.70
    }
  },
  {
    "anomaly_id": "A002",
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
  },
  {
    "anomaly_id": "A003",
    "type": "rapid_orders",
    "entity_id": "U078",
    "timestamp": "2025-01-20T11:05:00Z",
    "severity": "medium",
    "details": {
      "metric": "order_count_10min",
      "value": 5.00,
      "threshold": 3.00,
      "deviation_factor": 1.67
    }
  },
  {
    "anomaly_id": "A004",
    "type": "unusual_access",
    "entity_id": "10.0.1.50",
    "timestamp": "2025-01-22T03:00:00Z",
    "severity": "high",
    "details": {
      "metric": "access_count_1h",
      "value": 520.00,
      "threshold": 100.00,
      "deviation_factor": 5.20
    }
  }
]
```
