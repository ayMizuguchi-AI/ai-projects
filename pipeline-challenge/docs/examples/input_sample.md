# 入力データスキーマ

## orders.csv

| カラム | 型 | 説明 | 例 |
|--------|-----|------|-----|
| `order_id` | string | 注文ID（一意） | `ORD-00001` |
| `user_id` | string | ユーザーID | `U001` |
| `product_id` | string | 商品ID | `P042` |
| `quantity` | integer | 注文数量 | `2` |
| `unit_price` | float | 注文時の単価 | `1500.00` |
| `total_amount` | float | 注文合計額（quantity × unit_price） | `3000.00` |
| `order_date` | string | 注文日時（ISO 8601） | `2024-11-15T10:30:00Z` |
| `status` | string | 注文ステータス | `completed` |
| `payment_method` | string | 支払い方法 | `credit_card` |

### 注文ステータスの値
- `completed` : 注文完了（出荷済み）
- `cancelled` : 注文キャンセル（出荷前）
- `refunded`  : 返金済み（出荷後）

### 支払い方法
- `credit_card`（クレジットカード）
- `debit_card`（デビットカード）
- `bank_transfer`（銀行振込）
- `convenience_store`（コンビニ決済）
- `e_wallet`（電子マネー）

### 注意事項
- 一部のレコードに NULL 値や空値が含まれる場合があります
- 日付フォーマットが若干異なるケースがあります
- `total_amount` が `quantity × unit_price` と一致しない場合があります（異常の可能性）

---

## users.json

```json
[
  {
    "user_id": "U001",
    "name": "Tanaka Taro",
    "email": "tanaka@example.com",
    "registration_date": "2024-06-15",
    "prefecture": "Tokyo",
    "age": 32,
    "gender": "M"
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `user_id` | string | ユーザーID（一意、U001〜U200） |
| `name` | string | ユーザー名 |
| `email` | string | メールアドレス |
| `registration_date` | string | アカウント作成日（YYYY-MM-DD） |
| `prefecture` | string | 都道府県 |
| `age` | integer | 年齢 |
| `gender` | string | `M`（男性）、`F`（女性）、`other`（その他） |

---

## products.json

```json
[
  {
    "product_id": "P001",
    "name": "Wireless Headphones",
    "category": "electronics",
    "price": 12800.00,
    "stock": 150,
    "created_at": "2024-01-10"
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `product_id` | string | 商品ID（一意、P001〜P100） |
| `name` | string | 商品名 |
| `category` | string | 商品カテゴリ |
| `price` | float | 現在の定価 |
| `stock` | integer | 現在の在庫数 |
| `created_at` | string | 商品登録日（YYYY-MM-DD） |

### カテゴリ一覧
- `electronics`（家電・電子機器）
- `clothing`（衣料品）
- `food`（食品）
- `books`（書籍）
- `home`（ホーム・インテリア）
- `sports`（スポーツ）
- `beauty`（美容・コスメ）

---

## access_logs.jsonl

各行が1つの JSON オブジェクトです。

```json
{"timestamp": "2024-11-15T10:28:00Z", "user_id": "U001", "ip_address": "192.168.1.100", "endpoint": "/products/P042", "method": "GET", "status_code": 200, "session_id": "sess_abc123", "duration_ms": 145}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `timestamp` | string | アクセス日時（ISO 8601） |
| `user_id` | string | ユーザーID（匿名アクセスの場合は null） |
| `ip_address` | string | クライアントIPアドレス |
| `endpoint` | string | アクセスしたURLパス |
| `method` | string | HTTPメソッド（GET、POST 等） |
| `status_code` | integer | HTTPレスポンスステータスコード |
| `session_id` | string | セッションID |
| `duration_ms` | integer | レスポンス時間（ミリ秒） |

### エンドポイントパターン
- `/products/{product_id}` : 商品詳細ページ
- `/products` : 商品一覧ページ
- `/cart` : ショッピングカート
- `/checkout` : 決済ページ
- `/orders` : 注文履歴
- `/search?q={query}` : 検索

---

## labeled_anomalies_sample.json（学習用）

異常検知の学習用ラベル付きデータです。全異常の**約30%**が含まれます。

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
  },
  {
    "type": "unusual_access",
    "entity_id": "192.168.1.50",
    "timestamp": "2025-01-10T09:15:00Z",
    "severity": "medium",
    "details": {
      "metric": "access_count_1h",
      "value": 350.00
    }
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `type` | string | 異常タイプ（`suspicious_order`, `rapid_orders`, `unusual_access`, `price_mismatch`） |
| `entity_id` | string | 関連するユーザーIDまたはIPアドレス |
| `timestamp` | string | 異常発生日時（ISO 8601） |
| `severity` | string | 重大度（`high`, `medium`, `low`） |
| `details.metric` | string | 検知に使用された指標名 |
| `details.value` | float | 観測値 |

### 注意事項
- 全異常の約30%のみが含まれます（残り約70%は非公開・採点用）
- 教師あり/半教師あり学習やルール設計の参考に使用できます
- `details` にはラベル付け時の参考情報が含まれますが、`threshold` や `deviation_factor` は含まれません（受験者が独自に設計する部分）
