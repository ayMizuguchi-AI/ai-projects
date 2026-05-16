# 入力データスキーマ

## 注文データ（`orders.csv`）

```csv
order_id,user_id,product_id,quantity,unit_price,total_amount,order_date,status,payment_method
ORD-00001,U109,P019,2,17700.0,35400.0,2024-11-19T16:53:54Z,completed,e_wallet
ORD-00002,U109,P020,1,2300.0,2300.0,2025-01-30T22:27:12Z,completed,e_wallet
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `order_id` | string | 注文ID（一意） |
| `user_id` | string | ユーザーID |
| `product_id` | string | 商品ID |
| `quantity` | int | 数量 |
| `unit_price` | float | 単価 |
| `total_amount` | float | 合計金額 |
| `order_date` | string | 注文日時（ISO 8601） |
| `status` | string | ステータス（`completed`, `refunded`, `cancelled`） |
| `payment_method` | string | 支払い方法 |

> **推薦には `completed` ステータスの注文のみ**を使用してください。

---

## ユーザー情報（`users.json`）

```json
[
  {
    "user_id": "U001",
    "name": "Nakajima Yuki",
    "email": "nakajima.yuki1@example.com",
    "registration_date": "2025-01-27",
    "prefecture": "Kagawa",
    "age": 33,
    "gender": "M"
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `user_id` | string | ユーザーID（一意） |
| `name` | string | 氏名 |
| `email` | string | メールアドレス |
| `registration_date` | string | 登録日（YYYY-MM-DD） |
| `prefecture` | string | 都道府県 |
| `age` | int | 年齢 |
| `gender` | string | 性別（`M`, `F`） |

---

## 商品マスタ（`products.json`）

```json
[
  {
    "product_id": "P001",
    "name": "Wireless Headphones",
    "category": "electronics",
    "price": 51500.0,
    "stock": 22,
    "created_at": "2024-04-14"
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `product_id` | string | 商品ID（一意） |
| `name` | string | 商品名 |
| `category` | string | カテゴリ |
| `price` | float | 定価 |
| `stock` | int | 在庫数 |
| `created_at` | string | 登録日 |

> `category` フィールドはカテゴリベースの推薦に活用できます。

---

## アクセスログ（`access_logs.jsonl`）

```json
{"timestamp": "2024-10-01T00:02:39Z", "user_id": "U003", "ip_address": "192.168.116.221", "endpoint": "/products/P049", "method": "GET", "status_code": 200, "session_id": "sess_000702", "duration_ms": 1998}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `timestamp` | string | アクセス日時（ISO 8601） |
| `user_id` | string/null | ユーザーID（未ログイン時は null） |
| `ip_address` | string | IPアドレス |
| `endpoint` | string | アクセスURL |
| `method` | string | HTTPメソッド |
| `status_code` | int | HTTPステータスコード |
| `session_id` | string | セッションID |
| `duration_ms` | int | レスポンス時間（ミリ秒） |

> `/products/Pxxx` 形式のエンドポイントは商品閲覧を示します。閲覧行動ベースの推薦に活用できます。

---

## ラベル付きレコメンデーションデータ（`labeled_recommendations_sample.json`）

```json
[
  {
    "user_id": "U001",
    "recommendations": [
      {
        "product_id": "P045",
        "reason": "frequently_bought_together"
      }
    ]
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `user_id` | string | 推薦対象ユーザーID |
| `recommendations[].product_id` | string | 推薦商品ID |
| `recommendations[].reason` | string | 推薦理由 |

> 全推薦の約30%がラベル付きで提供されます。`score` は含まれません（受験者が独自に設計する部分）。
