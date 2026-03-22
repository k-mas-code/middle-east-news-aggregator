# デプロイメントガイド

Middle East News Aggregator を Google Cloud Platform (無料枠内) にデプロイする手順を説明します。

## 前提条件

1. Google Cloud アカウント（無料枠が有効）
2. Google Cloud SDK (gcloud) のインストール
3. GitHub アカウント
4. git がインストール済み

## 無料枠の制限

このシステムは以下の無料枠内で運用するよう設計されています:

| サービス | 月間制限 | 予想使用量 | 使用率 |
|---------|---------|-----------|-------|
| Google Translate API | 500K文字 | 270K文字 | 54% |
| Firestore 読み取り | 50K回 | 2,400回 | 4.8% |
| Firestore 書き込み | 20K回 | 1,200回 | 6% |
| Cloud Run リクエスト | 2M回 | 500-1000回 | <0.1% |
| Firebase Hosting | 10GB | 50-100MB | 1% |
| GitHub Actions | 2000分 | 60-120分 | 3-6% |

**重要**: デフォルト設定 (`TRANSLATION_MODE=titles_and_summary`) では、タイトルと要約のみを翻訳し、無料枠の54%を使用します。

## Step 1: GCP プロジェクトのセットアップ

### 自動セットアップ（推奨）

```bash
# リポジトリのルートディレクトリで実行
./setup_gcp.sh
```

このスクリプトは以下を自動的に実行します:
1. GCP プロジェクトの作成/選択
2. 必要な API の有効化
3. Firestore データベースの作成
4. サービスアカウントの作成と権限付与
5. サービスアカウントキーのダウンロード (`gcp-key.json`)
6. GitHub Secrets 設定情報の表示

### 手動セットアップ

自動セットアップができない場合、以下の手順で手動設定します:

1. **プロジェクトの作成**
   ```bash
   gcloud projects create middle-east-news-aggregator
   gcloud config set project middle-east-news-aggregator
   ```

2. **課金の有効化**
   - [GCP Console](https://console.cloud.google.com/billing) で課金を有効化
   - 無料枠のみ使用する場合でも課金アカウントの登録が必要

3. **API の有効化**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable translate.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

4. **Firestore の作成**
   ```bash
   gcloud firestore databases create --region=us-central1
   ```

5. **サービスアカウントの作成**
   ```bash
   gcloud iam service-accounts create news-aggregator-sa \
       --display-name="News Aggregator Service Account"

   # 権限の付与
   gcloud projects add-iam-policy-binding middle-east-news-aggregator \
       --member="serviceAccount:news-aggregator-sa@middle-east-news-aggregator.iam.gserviceaccount.com" \
       --role="roles/datastore.user"

   gcloud projects add-iam-policy-binding middle-east-news-aggregator \
       --member="serviceAccount:news-aggregator-sa@middle-east-news-aggregator.iam.gserviceaccount.com" \
       --role="roles/cloudtranslate.user"

   gcloud projects add-iam-policy-binding middle-east-news-aggregator \
       --member="serviceAccount:news-aggregator-sa@middle-east-news-aggregator.iam.gserviceaccount.com" \
       --role="roles/run.admin"

   # キーの作成
   gcloud iam service-accounts keys create gcp-key.json \
       --iam-account=news-aggregator-sa@middle-east-news-aggregator.iam.gserviceaccount.com
   ```

## Step 2: GitHub Secrets の設定

GitHub リポジトリの Settings → Secrets and variables → Actions で以下のシークレットを追加:

1. **GCP_PROJECT_ID**
   ```
   middle-east-news-aggregator
   ```

2. **GCP_SA_KEY**
   ```
   # gcp-key.json の全内容をコピー
   cat gcp-key.json
   ```

3. **FIREBASE_SERVICE_ACCOUNT**
   ```
   # gcp-key.json と同じ内容
   cat gcp-key.json
   ```

## Step 3: ローカル開発環境の設定

```bash
# .env ファイルの作成
cp .env.example .env

# 環境変数の設定
cat > .env << EOF
# GCP Configuration
GCP_PROJECT_ID=middle-east-news-aggregator
GOOGLE_APPLICATION_CREDENTIALS=./gcp-key.json

# Translation API Configuration
TRANSLATION_MODE=titles_and_summary
TRANSLATION_MONTHLY_LIMIT=500000
TRANSLATION_SAFE_MARGIN=0.80
TRANSLATION_DISABLE_THRESHOLD=0.95
TRANSLATION_DAILY_LIMIT=20000
TRANSLATION_MAX_PER_ARTICLE=5000

# Cloud Run Configuration
PORT=8080
EOF
```

## Step 4: ローカルテスト

```bash
# 依存関係のインストール
pip install -r requirements.txt

# spaCy モデルのダウンロード
python -m spacy download en_core_web_sm

# テストの実行
pytest tests/ -v

# ローカルサーバーの起動
python -m uvicorn middle_east_aggregator.api:app --reload --port 8080
```

ブラウザで http://localhost:8080 にアクセスして動作確認。

## Step 5: デプロイ

```bash
# main ブランチにプッシュ（自動デプロイが実行される）
git push origin main
```

GitHub Actions が自動的に以下を実行します:
1. バックエンド (FastAPI) を Cloud Run にデプロイ
2. フロントエンド (React) を Firebase Hosting にデプロイ
3. 6時間ごとに記事収集を自動実行

## Step 6: デプロイ確認

1. **Cloud Run URL の確認**
   ```bash
   gcloud run services describe news-aggregator-api \
       --region=us-central1 \
       --format='value(status.url)'
   ```

2. **動作確認**
   ```bash
   # ヘルスチェック
   curl https://YOUR_CLOUD_RUN_URL/api/status

   # 手動収集のトリガー
   curl -X POST https://YOUR_CLOUD_RUN_URL/api/collect
   ```

3. **使用量の確認**
   ```bash
   # ブラウザで開く
   open https://YOUR_CLOUD_RUN_URL/api/admin/quota-status
   open https://YOUR_CLOUD_RUN_URL/api/admin/quota-forecast
   ```

## 使用量の監視

### リアルタイム監視

- **Quota Status**: `GET /api/admin/quota-status`
  - 現在の使用量、記事数、残り文字数
  - ステータス: SAFE / WARNING / CRITICAL

- **Quota Forecast**: `GET /api/admin/quota-forecast`
  - 月末までの使用量予測
  - リスクレベル: LOW / MEDIUM / HIGH

### GCP Console での監視

1. [Translation API Quotas](https://console.cloud.google.com/apis/api/translate.googleapis.com/quotas)
2. [Firestore Usage](https://console.cloud.google.com/firestore/usage)
3. [Cloud Run Metrics](https://console.cloud.google.com/run)

## 翻訳モードの調整

使用量が多い場合は環境変数で翻訳モードを変更:

```bash
# Cloud Run の環境変数を更新
gcloud run services update news-aggregator-api \
    --region=us-central1 \
    --set-env-vars TRANSLATION_MODE=titles_only
```

### 翻訳モード一覧

| モード | 文字数/記事 | 月間記事数 | 用途 |
|-------|-----------|----------|------|
| `disabled` | 0 | - | テスト環境 |
| `titles_only` | 100 | 5000記事 | 高頻度収集 |
| `titles_and_summary` | 300 | 1666記事 | **推奨 (デフォルト)** |
| `full` | 2000 | 250記事 | 詳細分析 |

## トラブルシューティング

### 翻訳が無効化される

**原因**: 使用量が95%を超えた

**対処**:
1. 翻訳モードを下げる: `titles_only` または `disabled`
2. 収集頻度を下げる (GitHub Actions の cron 設定を変更)
3. 翌月まで待つ（1日で自動リセット）

### Cloud Run のデプロイが失敗

**原因**: サービスアカウントの権限不足

**対処**:
```bash
# Service Account User ロールを追加
gcloud projects add-iam-policy-binding middle-east-news-aggregator \
    --member="serviceAccount:news-aggregator-sa@middle-east-news-aggregator.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
```

### Firestore の読み書きが失敗

**原因**: データベースが作成されていない、または権限不足

**対処**:
```bash
# Firestore データベースの作成
gcloud firestore databases create --region=us-central1

# データベースユーザー権限の確認
gcloud projects get-iam-policy middle-east-news-aggregator \
    --flatten="bindings[].members" \
    --filter="bindings.role:roles/datastore.user"
```

## 無料枠を超えないためのベストプラクティス

1. **デフォルト設定を使用**: `TRANSLATION_MODE=titles_and_summary` (270K chars/月)
2. **使用量を定期監視**: `/api/admin/quota-forecast` で予測を確認
3. **自動縮退を信頼**: 80%で自動的にモードダウン、95%で無効化
4. **収集頻度を調整**: 6時間ごと → 12時間ごとに変更可能
5. **アラート設定**: GCP Console で予算アラートを設定

## コスト試算

無料枠を超えた場合の従量課金:

- **Translation API**: $20 / 1M文字
- **Firestore 読み取り**: $0.06 / 100K回
- **Firestore 書き込み**: $0.18 / 100K回
- **Cloud Run**: $0.24 / 100万リクエスト

デフォルト設定（titles_and_summary）では月額 $0 で運用可能です。

## 次のステップ

- [CLAUDE.md](../CLAUDE.md): 開発ガイド
- [design.md](./design.md): システム設計
- [GitHub Actions](.github/workflows/): CI/CD 設定
