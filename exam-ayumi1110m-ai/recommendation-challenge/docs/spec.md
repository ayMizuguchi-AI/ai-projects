# 詳細仕様

## 概要

本ドキュメントでは、レコメンデーションタスクの入出力フォーマット・推薦戦略・評価方法を定義します。パイプラインは `data/input/` からデータを読み込み、`output/` に結果を出力してください。

## 基準日

日付に関するすべての相対計算は **2025-01-31** を基準日とします。

## データ期間

入力データは **2024-10-01 〜 2025-01-31**（4ヶ月間）を対象としています。

---

## レコメンデーション

### 入力
- `data/input/orders.csv`
- `data/input/access_logs.jsonl`
- `data/input/products.json`
- `data/input/users.json`
- `data/input/labeled_recommendations_sample.json`（学習用：ラベル付きレコメンデーションデータの約30%）

### 出力
- `output/recommendations.json`

### 概要

注文履歴・商品情報・アクセスログを分析し、各ユーザーに対して**購入する可能性の高い商品**を推薦する。

**推薦手法は自由です。** 協調フィルタリング、コンテンツベースフィルタリング、行列分解、深層学習ベースの推薦など、どのようなアプローチでも構いません。

### ラベル付き学習データ（`labeled_recommendations_sample.json`）

期待される推薦の約30%がラベル付きデータとして提供されます。これを教師あり学習やルール設計の参考に使用できます。

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

> **注意**: ラベル付きデータには `score` は含まれません。スコアの算出方法は受験者が独自に設計する部分です。

### 推薦対象

- `completed` 注文が**1件以上**あるユーザー全員
- 各ユーザーに対し、**未購入の商品**から最大 **10件** を推薦

### 推薦戦略（参考）

以下は参考となる推薦戦略の例です。これらに限定する必要はありません。

| 戦略 | 概要 | データソース |
|------|------|-------------|
| 共起分析 | 同じユーザーが購入した商品ペアの共起頻度に基づく推薦 | `orders.csv` |
| カテゴリ親和性 | ユーザーの購入カテゴリ傾向に基づく推薦 | `orders.csv`, `products.json` |
| 閲覧行動分析 | 閲覧したが未購入の商品を推薦 | `access_logs.jsonl` |
| 協調フィルタリング | 類似ユーザーの購入パターンに基づく推薦 | `orders.csv` |
| コンテンツベース | 商品属性の類似性に基づく推薦 | `products.json` |

### 推薦理由（reason）

各推薦には `reason` フィールドで推薦理由を記述してください。以下はラベル付きデータに含まれる理由の例です:

- `frequently_bought_together` — 共起分析に基づく推薦
- `category_affinity` — カテゴリ親和性に基づく推薦
- `browsing_history` — 閲覧行動に基づく推薦

独自の理由名を使用しても構いません。

### 出力ルール

- `user_id` 昇順でソート
- 各ユーザーの推薦リストは `score` 降順でソート
- 推薦は最大 **10件** まで
- `score` は 0.00〜1.00 の範囲（小数第2位まで）
- 推薦対象は未購入商品のみ（`completed` 注文に含まれる商品は除外）

### 評価方法（概要）

非公開の完全なレコメンデーションデータに対して、**F1スコア**で評価されます。

- マッチング条件: `(user_id, product_id)` ペアの完全一致
- Precision = TP / (TP + FP), Recall = TP / (TP + FN)
- F1 = 2 × Precision × Recall / (Precision + Recall)

### 出力フォーマット

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
      }
    ]
  }
]
```

---

## 共通事項

- 金額はすべて日本円（JPY）。通貨記号は不要
- 浮動小数点値は特に指定がない限り小数第2位まで
- JSON 出力は有効な JSON であること（文字列の適切なエスケープ、末尾カンマ禁止）
- 結果が空の場合、JSON は空配列 `[]` を出力
