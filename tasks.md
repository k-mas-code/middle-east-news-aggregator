# 実装計画：中東ニュース集約・比較分析システム

## 概要

設計書に基づき、Collector → Filter → Clusterer → Analyzer → Repository → API → Frontendの順に段階的に実装します。**Googleサービス（Firestore・Cloud Run・Firebase Hosting）を活用した完全無料構成**で運用します。

## タスク

- [ ] 1. GCPプロジェクトのセットアップ（初回のみ）
  - [ ] 1.1 GCPプロジェクトの作成と設定
    - Google Cloud Console（https://console.cloud.google.com）でアカウント作成
    - 新規プロジェクトを作成（例: `middle-east-news-aggregator`）
    - 請求先アカウントを設定（無料枠のみ使用・課金は発生しない）
  - [ ] 1.2 必要なAPIの有効化
    - Firestore API を有効化
    - Cloud Run API を有効化
    - Cloud Build API を有効化
    - Firebase を有効化（Firebase Console でプロジェクトを追加）
  - [ ] 1.3 Firestore データベースの作成
    - Firestore をネイティブモードで作成
    - リージョン: `asia-northeast1`（東京）を選択
  - [ ] 1.4 サービスアカウントの作成と権限設定
    - サービスアカウントを作成（例: `github-actions-sa`）
    - 以下のロールを付与:
      - `Cloud Datastore User`（Firestore 読み書き）
      - `Cloud Run Developer`（Cloud Run デプロイ）
      - `Storage Object Admin`（Cloud Storage 操作）
    - JSON キーファイルをダウンロード
  - [ ] 1.5 GitHub Secrets の設定
    - リポジトリの Settings → Secrets and variables → Actions で以下を設定:
      - `GCP_PROJECT_ID`: GCPプロジェクトID
      - `GCP_SA_KEY`: サービスアカウントJSONキー（Base64エンコード）
  - [ ] 1.6 Firebase Hosting の初期化
    - `npm install -g firebase-tools` でFirebase CLIをインストール
    - `firebase login` でログイン
    - `firebase init hosting` でHostingを初期化
    - `firebase.json` と `.firebaserc` をリポジトリにコミット

- [ ] 2. プロジェクト構造とコアデータモデルのセットアップ
  - `middle_east_aggregator/` ディレクトリ構造を作成する
  - `models.py` に RawArticle・Article・SentimentResult・Entity・Cluster・ComparisonResult・Report の dataclass を定義する
  - `requirements.txt` に feedparser・httpx・spacy・textblob・scikit-learn・google-cloud-firestore・fastapi・uvicorn・hypothesis・pytest を追加する
  - _Requirements: 1.5, 4.1_

- [ ] 3. Firestore データベース層の実装
  - [ ] 3.1 Firestore クライアントと ArticleRepository を実装する
    - `database.py` に Firestore クライアント初期化を実装する
    - `save`・`find_by_url`・`find_by_date_range`・`delete_older_than` メソッドを実装する
    - 重複URLの場合は既存ドキュメントを更新するupsertロジックを実装する
    - _Requirements: 1.2, 1.3, 6.1, 6.4_
  - [ ]* 3.2 ArticleRepository のプロパティテストを書く
    - **Property 2: 記事保存ラウンドトリップ**
    - **Property 3: 重複保存の冪等性**
    - **Property 11: データ保持期間**
    - **Property 12: 書き込み失敗時のロールバック**
    - **Validates: Requirements 1.2, 1.3, 6.1, 6.3, 6.4**
  - [ ] 3.3 ReportRepository を実装する
    - `save`・`find_all`・`find_by_id`・`search` メソッドを実装する
    - _Requirements: 6.2_
  - [ ]* 3.4 ReportRepository のプロパティテストを書く
    - **Property 9: レポート保存ラウンドトリップ**
    - **Validates: Requirements 6.2**

- [ ] 4. Collector（収集器）の実装
  - [ ] 4.1 BaseCollector と各メディアの Collector を実装する
    - `collectors.py` に BaseCollector・AlJazeeraCollector・ReutersCollector・BBCCollector を実装する
    - feedparser で RSS フィードを解析し RawArticle に変換するロジックを実装する
    - httpx のタイムアウト設定（30秒）とリトライロジック（3回失敗で60分スキップ）を実装する
    - _Requirements: 1.1, 1.2, 1.5, 7.1, 7.2_
  - [ ]* 4.2 Collector のプロパティテストを書く
    - **Property 1: 記事フィールド完全性**
    - **Property 4: 部分障害時の継続性**
    - **Validates: Requirements 1.4, 1.5**
  - [ ]* 4.3 Collector のユニットテストを書く
    - モック RSS フィード XML を使った解析テスト
    - タイムアウト・接続失敗・パースエラーのエラー条件テスト
    - _Requirements: 1.4, 7.1, 7.2_

- [ ] 5. チェックポイント — 全テストが通ることを確認する
  - 全テストが通ることを確認し、疑問点があればユーザーに確認する。

- [ ] 6. Filter（フィルタ）の実装
  - [ ] 6.1 MiddleEastFilter を実装する
    - `filters.py` に中東関連キーワードリストと `filter`・`is_relevant` メソッドを実装する
    - タイトルと本文の両方をキーワード検索（大文字小文字を区別しない）する
    - フィルタリング結果のログ出力（対象件数・除外件数）を実装する
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [ ]* 6.2 Filter のプロパティテストを書く
    - **Property 5: フィルタリング正確性**
    - **Validates: Requirements 2.1, 2.2**
  - [ ]* 6.3 Filter のユニットテストを書く
    - 大文字小文字の境界値テスト
    - 0件フィルタリング時の警告ログテスト（エッジケース）
    - _Requirements: 2.4_

- [ ] 7. Clusterer（クラスタリング器）の実装
  - [ ] 7.1 TopicClusterer を実装する
    - `clusterer.py` に TF-IDF ベクトル化とコサイン類似度ベースのクラスタリングを実装する
    - 各 Cluster に topic_name を自動生成するロジック（上位 TF-IDF 語を使用）を実装する
    - 単一記事の場合は単独 Cluster として扱うロジックを実装する
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 7.2 Clusterer のプロパティテストを書く
    - **Property 6: クラスタリング不変条件**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
  - [ ]* 7.3 Clusterer のユニットテストを書く
    - 単一記事のエッジケーステスト（単独 Cluster）
    - 同一メディア複数記事のクラスタリングテスト
    - _Requirements: 3.4_

- [ ] 8. BiasAnalyzer（バイアス分析器）の実装
  - [ ] 8.1 BiasAnalyzer を実装する
    - `analyzer.py` に TextBlob を使った感情分析（polarity・subjectivity）を実装する
    - spaCy を使ったエンティティ抽出（PERSON・GPE・ORG・LOC）を実装する
    - Cluster 内の全 Article を比較して ComparisonResult を生成するロジックを実装する
    - 単一メディア Cluster の場合は比較なしの単独 Report を生成するロジックを実装する
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ]* 8.2 BiasAnalyzer のプロパティテストを書く
    - **Property 7: Bias_Score 範囲不変条件**
    - **Property 8: 比較分析生成完全性**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [ ]* 8.3 BiasAnalyzer のユニットテストを書く
    - 感情分析の具体的な例テスト（明確にポジティブ・ネガティブなテキスト）
    - 単一メディア Cluster の単独 Report 生成テスト
    - _Requirements: 4.4, 4.5_

- [ ] 9. チェックポイント — 全テストが通ることを確認する
  - 全テストが通ることを確認し、疑問点があればユーザーに確認する。

- [ ] 10. FastAPI バックエンドの実装
  - [ ] 10.1 FastAPI アプリケーションと全エンドポイントを実装する
    - `api.py` に GET `/api/reports`・GET `/api/reports/{id}`・GET `/api/reports/search`・GET `/api/articles`・GET `/api/status`・POST `/api/collect` を実装する
    - Pydantic レスポンスモデルを定義する
    - CORS 設定を追加する
    - _Requirements: 5.1, 5.2, 5.4, 5.5, 5.6_
  - [ ]* 10.2 API エンドポイントのプロパティテストを書く
    - **Property 10: 検索結果関連性**
    - **Validates: Requirements 5.5**
  - [ ]* 10.3 API エンドポイントのユニットテストを書く
    - TestClient を使った各エンドポイントの例テスト
    - `/api/status` の最終更新日時レスポンステスト
    - _Requirements: 5.1, 5.6_

- [ ] 11. GitHub Actions による定期収集の実装
  - `.github/workflows/collect.yml` に6時間間隔のCronジョブを実装する
  - Collector → Filter → Clusterer → Analyzer → Firestore の処理パイプラインを実装する
  - 収集サマリーログ（収集件数・エラー件数）の出力を実装する
  - GitHub Secrets に GCP サービスアカウントキーを設定する
  - _Requirements: 1.2, 1.6, 7.3, 7.4_

- [ ] 12. React フロントエンドの実装
  - [ ] 12.1 React + TypeScript プロジェクトをセットアップし、レポート一覧画面を実装する
    - `frontend/` ディレクトリに Vite + React + TypeScript プロジェクトを作成する
    - API クライアント関数（fetch wrapper）を実装する
    - レポート一覧コンポーネントを実装する（最終更新日時表示を含む）
    - _Requirements: 5.1, 5.6_
  - [ ] 12.2 レポート詳細画面とバイアス比較チャートを実装する
    - レポート詳細コンポーネントを実装する（メディア別 Article・原文リンクを含む）
    - Recharts を使った Bias_Score 比較チャートを実装する
    - _Requirements: 5.2, 5.3, 5.4_
  - [ ] 12.3 キーワード検索機能を実装する
    - 検索入力コンポーネントと検索結果表示を実装する
    - _Requirements: 5.5_

- [ ] 13. Cloud Run と Firebase Hosting へのデプロイ設定
  - `Dockerfile` を作成し Cloud Run 用コンテナをビルドする
  - `cloudbuild.yaml` で Cloud Run への自動デプロイを設定する
  - Firebase Hosting に React フロントエンドをデプロイする
  - GitHub Actions に CD パイプラインを追加する
  - _Requirements: 全要件_

- [ ] 14. 最終チェックポイント — 全テストが通ることを確認する
  - 全テストが通ることを確認し、疑問点があればユーザーに確認する。

## 注意事項

- `*` が付いたタスクはオプションであり、MVP を優先する場合はスキップ可能
- 各タスクは対応する要件番号を参照しており、トレーサビリティを確保
- プロパティテストは Hypothesis ライブラリを使用し、最低100回のイテレーションを実行
- チェックポイントで段階的に動作確認を行う

## Googleサービス設定メモ

| 設定項目 | 値 |
|---|---|
| 定期実行 | GitHub Actions Cron（6時間間隔） |
| データベース | Firestore（GCPプロジェクト内） |
| バックエンド | Cloud Run（us-central1リージョン） |
| フロントエンド | Firebase Hosting |
| 認証情報 | GitHub Secrets に GCP サービスアカウントキーを保存 |
