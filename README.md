# Portfolio / Created Projects

SFや近未来の世界観が好きでAIに魅力を感じたことから、AIを取り入れたプログラミングを始めました。  
以下は様々な機械学習をテーマに開発したプロジェクトです。

---

## Projects

### [1. DQN-Learning（強化学習シミュレーション）](./DQN-Learning)
TensorFlow.jsを用いて、AIがブロック崩しを学習する過程を可視化しました。ブラックボックスなAIの脳内（ニューロン）を直感的に見ることができるモニターを実装しました。
> **🔗 [実際にブラウザ上で実行（デモサイト）](https://aymizuguchi-ai.github.io/ai-projects/DQN-Learning/)**  
> ※ダウンロードや環境構築なしで、今すぐブラウザ上でAIの学習シミュレーションを実行できます。
> 現在レスポンシブ非対応のため、Edge以外のブラウザではデザインが崩れる場合があります。

### [2. virtual-chat（AIエージェントシステム）](./virtual-chat)
3Dアバターと音声モデルを使い、実際に会話ができるシステムを制作しました。Three.jsとWeb Audio APIによるリアルタイムな3Dボーン制御とリップシンク（口パク）で人間らしい動きを再現しました。

### [3. Anomaly Detection Pipeline（不正探知データパイプライン）](./anomaly-detection-pipeline)
ECサイトの注文・アクセスログから、Botや不正組織の行動パターンを検知。ルールベースとRandomForestを組み合わせ、ドメイン知識に基づく特徴量エンジニアリングを行いました。
*(※NDAの観点から中核ロジックのみ公開)*

---

## 🛠 Tech Stack
- **Languages:** JavaScript (ES6+ / Vanilla), HTML5/CSS3, Python 3.x
- **AI / ML:** TensorFlow.js, scikit-learn, Gemini API
- **Frontend:** Three.js, @pixiv/three-vrm, Web Audio API, Web Speech API
- **Backend / Data:** Flask, pandas, COEIROINK API
