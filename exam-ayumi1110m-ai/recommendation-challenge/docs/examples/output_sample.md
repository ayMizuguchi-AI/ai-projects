# 出力データスキーマ

## レコメンデーション（`recommendations.json`）— アルゴリズム自由

```json
[
  {
    "user_id": "U001",
    "recommendations": [
      {
        "product_id": "P045",
        "score": 0.95,
        "reason": "frequently_bought_together"
      }
    ]
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `user_id` | string | 推薦対象ユーザーID |
| `recommendations` | array | 推薦商品リスト（スコア降順、最大10件） |
| `recommendations[].product_id` | string | 推薦商品ID |
| `recommendations[].score` | float | 推薦スコア（0.00-1.00、小数第2位まで）。算出方法は自由 |
| `recommendations[].reason` | string | 推薦理由（自由記述） |

### タスク概要

注文履歴・商品情報・アクセスログを分析し、各ユーザーに購入する可能性の高い商品を推薦します。推薦手法は自由です。

### ラベル付き学習データ

`labeled_recommendations_sample.json` に全推薦の約30%がラベル付きで提供されます。教師あり学習やルール設計の参考に使用できます。

### 推薦対象

- `completed` 注文が1件以上あるユーザー全員
- 未購入の商品から最大10件を推薦

### 推薦理由の例

| 理由 | 概要 | 推薦のヒント |
|------|------|-------------|
| `frequently_bought_together` | 共起分析に基づく推薦 | 同一ユーザーが購入した商品ペアの共起頻度を分析 |
| `category_affinity` | カテゴリ親和性に基づく推薦 | ユーザーの購入カテゴリ傾向と商品カテゴリを比較 |
| `browsing_history` | 閲覧行動に基づく推薦 | アクセスログの商品閲覧パターンを分析 |

> 独自の理由名を使用しても構いません。ラベル付きデータからパターンを学習するか、独自の手法で設計してください。

### 評価指標
- **レコメンデーションF1スコア** — (user_id, product_id)ペアの完全一致でマッチング
- F1 = 2 × Precision × Recall / (Precision + Recall)

### 出力ルール
- `user_id` 昇順でソート
- 各ユーザーの推薦リストは `score` 降順でソート
- 推薦は最大10件まで
- 推薦対象は未購入商品のみ

### 出力例

```json
[
  {
    "user_id": "U001",
    "recommendations": [
      {
        "product_id": "P045",
        "score": 0.95,
        "reason": "frequently_bought_together"
      },
      {
        "product_id": "P012",
        "score": 0.82,
        "reason": "category_affinity"
      },
      {
        "product_id": "P078",
        "score": 0.65,
        "reason": "browsing_history"
      }
    ]
  },
  {
    "user_id": "U002",
    "recommendations": [
      {
        "product_id": "P033",
        "score": 0.91,
        "reason": "frequently_bought_together"
      },
      {
        "product_id": "P055",
        "score": 0.74,
        "reason": "category_affinity"
      }
    ]
  }
]
```
