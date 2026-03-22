# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## プロジェクト概要

**Middle East News Aggregator（中東ニュース集約システム）** は、Al Jazeera・Reuters・BBCの3大メディアから中東関連ニュースを自動収集し、分析・比較を行うPythonベースのシステムです。NLPによるトピッククラスタリング、感情分析、バイアス検出を行い、FastAPIバックエンドとReactフロントエンドを通じて英語/日本語のバイリンガルレポートを提供します。

### アーキテクチャ

```
Collector (RSS) → Filter → Translator → Clusterer → Analyzer → Firestore
                                                               ↓
                                      FastAPI (Cloud Run) ← ← ←
                                              ↓
                                      React Frontend (Firebase Hosting)
```

**主要コンポーネント:**
- **Collectors**: 各メディアソース（Al Jazeera、Reuters、BBC）のRSSフィードパーサー
- **Filter**: 中東関連性のキーワードベースフィルタリング
- **Translator**: クォータ管理付きGoogle Translate API統合
- **Clusterer**: TF-IDF + KMeansによるトピックグルーピング
- **Analyzer**: 感情分析（TextBlob）とエンティティ抽出（spaCy）
- **Repositories**: 記事とレポートのFirestoreベース永続化
- **Pipeline**: 完全なワークフローのオーケストレーション（middle_east_aggregator/pipeline.py）

## 開発コマンド

### テストの実行

```bash
# カバレッジ付きで全テストを実行
pytest

# 特定のテストタイプを実行
pytest -m unit          # ユニットテストのみ
pytest -m property      # プロパティベーステスト（Hypothesis）
pytest -m integration   # 統合テスト

# 単一のテストファイルを実行
pytest tests/test_pipeline.py

# 詳細出力で実行
pytest -v

# カバレッジレポートを生成
pytest --cov=middle_east_aggregator --cov-report=html
```

### ローカル開発

```bash
# 依存関係をインストール（Python 3.11+が必要）
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# GCP認証情報を設定
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 収集パイプラインを手動実行
python -m middle_east_aggregator.cli collect

# FastAPIサーバーをローカルで起動
uvicorn middle_east_aggregator.api:app --reload --port 8000

# APIドキュメントにアクセス
# http://localhost:8000/docs
```

### Docker

```bash
# Dockerイメージをビルド
docker build -t middle-east-aggregator .

# コンテナをローカルで実行
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
  middle-east-aggregator

# ヘルスエンドポイントをテスト
curl http://localhost:8080/api/status
```

### フロントエンド開発

```bash
cd frontend

# 依存関係をインストール
npm install

# 開発サーバーを起動
npm run dev

# 本番用ビルド
npm run build

# 本番ビルドをプレビュー
npm run preview
```

### デプロイ

**バックエンド (Cloud Run):**
- `.github/workflows/deploy.yml`を通じて`main`ブランチへのプッシュで自動デプロイ
- 手動デプロイ: mainにプッシュするか、ワークフローを手動トリガー

**フロントエンド (Firebase Hosting):**
- `.github/workflows/deploy.yml`を通じてバックエンド後に自動デプロイ
- `FIREBASE_SERVICE_ACCOUNT` Secretが必要

**定期収集:**
- `.github/workflows/collect.yml`を通じて6時間ごとに実行
- 手動トリガー: GitHub Actions → Run workflow

## コアアーキテクチャパターン

### パイプラインフロー

`NewsPipeline`クラス（`pipeline.py`）は完全なワークフローをオーケストレーションします：

1. **収集 (Collection)**: RSSフィードから記事を取得（全コレクターが実行され、失敗は分離される）
2. **変換 (Conversion)**: RawArticle → Article にUUID生成を伴い変換
3. **フィルタリング (Filtering)**: 中東キーワードフィルターを適用
4. **翻訳 (Translation)**: 日本語に翻訳（クォータを考慮、翻訳システムの項を参照）
5. **保存 (Storage)**: Firestoreに記事を保存（URLによるupsert）
6. **クラスタリング (Clustering)**: トピック類似度で記事をグループ化（TF-IDFコサイン距離）
7. **分析 (Analysis)**: 感情スコア、エンティティを抽出し、メディア間で比較
8. **レポート生成 (Reporting)**: 比較レポートを生成して保存

**エラーハンドリング**: 各ステップは例外をキャッチして継続します。失敗はログに記録されますが、パイプラインを停止させません。

### 翻訳クォータシステム

システムはGoogle Translate APIの制限内に収まるよう、洗練されたクォータ管理を含んでいます：

**主要ファイル:**
- `translation_config.py`: 設定と制限値（月50万文字）
- `translation_quota.py`: 使用量監視のためのQuotaTracker
- `translator.py`: リトライロジック付き翻訳実行

**翻訳モード**（使用量に基づき自動選択）:
- `FULL`: タイトル + 全文（記事ごとに最大5000文字）
- `TITLES_AND_SUMMARY`: タイトル + 500文字要約（使用量80%以上）
- `TITLES_ONLY`: タイトルのみ（使用量85%以上）
- `DISABLED`: 翻訳なし（使用量90%以上）

**クォータ保存**: Firestoreコレクション `translation_quota` が月次・日次使用量を追跡

**翻訳ロジックを変更する際の注意:**
- 翻訳前に必ず `quota_tracker.can_translate()` を呼び出す
- `quota_tracker.record_translation()` で使用量を記録
- 制限値変更前に `TranslationConfig` の定数を確認

### Firestoreデータモデル

**コレクション:**
- `articles/{article_id}`: メタデータ付き個別記事
- `clusters/{cluster_id}`: 記事参照を含むトピッククラスター
- `reports/{report_id}`: 比較データ付き分析レポート
- `translation_quota/{month}`: 月次翻訳使用量追跡

**重要事項:**
- 記事はURLを自然キーとして使用（重複時はupsert）
- 全てのタイムスタンプはUTC datetime オブジェクト
- リポジトリのFirestoreクエリはインデックス付きフィールドを使用（published_at、collected_at）

### テスト戦略

**デュアルテストアプローチ:**
1. **ユニットテスト**: 具体例、エッジケース、エラー条件
2. **プロパティテスト**: 普遍的プロパティを検証するHypothesisベーステスト

**プロパティテスト** (`tests/test_*_property.py`):
- design.mdの形式的正確性プロパティを検証
- コメントでプロパティ番号を参照（例: "Property 3: 重複保存の冪等性"）
- プロパティごとに最低100イテレーション実行
- `@pytest.mark.property` でタグ付け

**統合テスト** (`conftest.py`):
- ローカルテストでFirestoreエミュレーターを使用
- フィクスチャがテストごとに分離されたデータベースインスタンスを提供

**新機能を追加する際:**
- ユニットテスト（例）とプロパティテスト（不変条件）の両方を書く
- 80%以上のコードカバレッジを確保
- エラー条件を明示的にテスト

## 重要な制約事項

### APIレート制限

**RSSフィード:**
- 明示的なレート制限は文書化されていない
- リクエストごとに30秒のタイムアウト
- 3回連続失敗 → 60分間のバックオフ

**Google Translate API:**
- 月50万文字（無料枠）
- 日10万文字
- `QuotaTracker`で管理 - バイパスしないこと

**Firestore:**
- 日5万読み取り（無料枠）
- 日2万書き込み（無料枠）
- ストレージ1GB制限

### データ保持

- 記事: 30日以上保持
- レポート: 自動削除なし（ストレージ制限を監視）
- 翻訳クォータログ: 月次集約、履歴データは保持

### セキュリティ考慮事項

- GCPサービスアカウントキーはGitHub Secretsに保存
- Firestoreセキュリティルールで認証を強制（本番環境）
- CORSはフロントエンドオリジン用に設定（本番ドメインに合わせて更新）
- Dockerは非rootユーザー（appuser）で実行

## よくあるパターン

### 新しいメディアソースの追加

1. `collectors.py`で`BaseCollector`を継承したコレクタークラスを作成
2. RSSフィード解析付きの`fetch()`メソッドを実装
3. `NewsPipeline.__init__()`のコレクターリストに追加
4. `models.py`の`media_name` Literal型を更新
5. モックRSSフィード付きのユニットテストを追加

### クラスタリングアルゴリズムの変更

- `clusterer.py`の`TopicClusterer`を編集
- プロパティを維持: 全記事は必ず1つのクラスターに属する
- `tests/test_clusterer_property.py`のプロパティテストを更新
- クラスター粒度調整のため`similarity_threshold`パラメータをチューニング

### APIエンドポイントの追加

1. `api.py`でPydanticレスポンスモデルを定義
2. リポジトリクエリを使用してエンドポイントを実装
3. エラーハンドリングを追加（適切なステータスコード付きHTTPException）
4. docstringでドキュメント化（/docsに表示される）
5. ルートエンドポイントのエンドポイントリストを更新

## ファイル構造リファレンス

```
middle_east_aggregator/
├── models.py              # コアデータモデル（dataclasses）
├── pipeline.py            # メインオーケストレーションロジック
├── collectors.py          # RSSフィードコレクター
├── filters.py             # 中東キーワードフィルター
├── translator.py          # Google Translate統合
├── translation_config.py  # 翻訳設定
├── translation_quota.py   # クォータ追跡
├── clusterer.py           # トピッククラスタリング（TF-IDF）
├── analyzer.py            # 感情分析とエンティティ抽出
├── database.py            # Firestoreリポジトリ
├── api.py                 # FastAPIエンドポイント
└── cli.py                 # コマンドラインインターフェース

tests/
├── conftest.py            # Pytestフィクスチャ（Firestoreエミュレーター）
├── test_*_unit.py         # ユニットテスト
├── test_*_property.py     # プロパティベーステスト
└── test_*_integration.py  # 統合テスト

docs/
├── requirements.md        # 日本語要件定義書
├── design.md             # アーキテクチャと形式的プロパティ
└── tasks.md              # 実装ロードマップ
```

## 主要な依存関係

- **feedparser**: RSSフィード解析
- **httpx**: APIリクエスト用非同期HTTPクライアント
- **spacy** (en_core_web_sm): NLPエンティティ抽出
- **textblob**: 感情分析
- **scikit-learn**: TF-IDFベクトル化とクラスタリング
- **google-cloud-firestore**: データベース永続化
- **google-cloud-translate**: 翻訳API
- **fastapi + uvicorn**: REST APIサーバー
- **hypothesis**: プロパティベーステスト
- **pytest + pytest-asyncio**: テストフレームワーク

## トラブルシューティング

**パイプラインが "No articles collected" で失敗する:**
- RSSフィードURLがアクセス可能か確認
- ネットワーク接続を検証
- HTTPエラーについてコレクターログを確認

**翻訳クォータ超過:**
- `/api/admin/quota-status` エンドポイントを確認
- `TranslationConfig.MONTHLY_LIMIT_CHARS` を見直し
- パイプラインはクォータが満たされるとモードを自動的に劣化させる

**Firestore接続エラー:**
- `GOOGLE_CLOUD_PROJECT` 環境変数を確認
- サービスアカウントにFirestoreパーミッションがあるか確認
- ローカル開発の場合、Firestoreエミュレーターが動作しているか確認

**テストが "Firestore unavailable" で失敗する:**
- 統合テストにはFirestoreエミュレーターが必要
- インストール: `gcloud components install cloud-firestore-emulator`
- 起動: `gcloud beta emulators firestore start`

**Dockerヘルスチェック失敗:**
- ポート8080が公開されアクセス可能か確認
- `/api/status` エンドポイントが応答するか確認
- 起動エラーについてuvicornログを確認
