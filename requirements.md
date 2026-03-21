# 要件定義書

## はじめに

本システムは、Al Jazeera・Reuters・BBCの3大メディアから中東情勢に関する報道を自動収集し、各メディアの視点・バイアス・差異を比較分析することで、ユーザーが多角的かつ正確な情報を把握できるようにするニュース集約・比較分析プラットフォームです。

## 用語集

- **Aggregator（集約システム）**: 複数のニュースソースからコンテンツを自動収集するシステム
- **Article（記事）**: 各メディアが公開したニュース記事（タイトル・本文・公開日時・URL・著者を含む）
- **Collector（収集器）**: 特定メディアのRSSフィードまたはAPIからArticleを取得するコンポーネント
- **Analyzer（分析器）**: 収集したArticleを比較・分析し、バイアスや差異を検出するコンポーネント
- **Report（レポート）**: 同一トピックに関する複数メディアの報道を比較した分析結果
- **Bias_Score（バイアススコア）**: 記事の感情的傾向や語彙選択の偏りを数値化したスコア
- **Topic（トピック）**: 複数の記事が共通して扱う中東情勢の特定の出来事や事象
- **Cluster（クラスター）**: 同一Topicに関連する記事のグループ
- **Dashboard（ダッシュボード）**: 収集・分析結果をユーザーに提示するWebインターフェース

---

## 要件

### 要件1：ニュース記事の自動収集

**ユーザーストーリー：** 開発者として、Al Jazeera・Reuters・BBCの3メディアから中東関連記事を自動収集したい。そうすることで、常に最新の報道情報をシステムに取り込める。

#### 受け入れ基準

1. THE Collector SHALL 各メディア（Al Jazeera・Reuters・BBC）のRSSフィードまたは公開APIから記事を取得する
2. WHEN 収集スケジュールが起動したとき、THE Collector SHALL 各メディアから最新記事を取得し、Articleとしてデータストアに保存する
3. WHEN 同一URLの記事が既にデータストアに存在するとき、THE Collector SHALL 重複保存を行わず既存レコードを更新する
4. IF メディアのエンドポイントへの接続が失敗したとき、THEN THE Collector SHALL エラーをログに記録し、他のメディアの収集処理を継続する
5. THE Collector SHALL 各Articleに対して、タイトル・本文・公開日時・ソースURL・メディア名を保存する
6. WHEN 収集処理が完了したとき、THE Collector SHALL 収集件数・エラー件数を含む収集サマリーをログに出力する

---

### 要件2：中東関連記事のフィルタリング

**ユーザーストーリー：** アナリストとして、収集した記事の中から中東情勢に関連するものだけを抽出したい。そうすることで、無関係な記事を除外して分析精度を高められる。

#### 受け入れ基準

1. THE Analyzer SHALL 収集したArticleに対して、中東関連キーワード（例：Israel、Palestine、Gaza、Lebanon、Syria、Iran、Iraq、Yemen、Saudi Arabia、Egypt、Jordan、Middle East）を用いてフィルタリングを行う
2. WHEN Articleのタイトルまたは本文に中東関連キーワードが含まれるとき、THE Analyzer SHALL そのArticleを分析対象としてマークする
3. THE Analyzer SHALL フィルタリング結果として、対象記事数と除外記事数をログに記録する
4. IF フィルタリング後に対象記事が0件のとき、THEN THE Analyzer SHALL 警告をログに出力し処理を終了する

---

### 要件3：トピッククラスタリング

**ユーザーストーリー：** アナリストとして、複数メディアが同一の出来事を報道している記事をグループ化したい。そうすることで、同じトピックに対する各メディアの報道を横断的に比較できる。

#### 受け入れ基準

1. THE Analyzer SHALL 中東関連Articleを、タイトルおよび本文の類似度に基づいてClusterに分類する
2. WHEN 2つ以上のメディアが同一Topicを報道しているとき、THE Analyzer SHALL それらのArticleを同一Clusterに分類する
3. THE Analyzer SHALL 各Clusterに対して、代表的なトピック名を生成する
4. IF 単一メディアのみが報道しているArticleのとき、THEN THE Analyzer SHALL そのArticleを単独Clusterとして扱う
5. THE Analyzer SHALL Clusterごとに、含まれるArticle数とメディア数を記録する

---

### 要件4：バイアス・差異分析

**ユーザーストーリー：** ユーザーとして、各メディアの報道における語彙選択・感情的傾向・強調点の違いを把握したい。そうすることで、報道バイアスを意識した上で情報を解釈できる。

#### 受け入れ基準

1. THE Analyzer SHALL 各ArticleのBias_Scoreを、感情分析（ポジティブ・ネガティブ・ニュートラル）に基づいて算出する
2. THE Analyzer SHALL 同一Cluster内の各Articleについて、使用語彙・感情スコア・強調されているエンティティ（人物・地名・組織）の差異を抽出する
3. WHEN 同一Topicに対して複数メディアのArticleが存在するとき、THE Analyzer SHALL メディア間のBias_Scoreの差分を計算する
4. THE Analyzer SHALL 各Clusterに対して、メディアごとのBias_Scoreと主要差異点を含むReportを生成する
5. IF 単一メディアのみのClusterのとき、THEN THE Analyzer SHALL 比較なしの単独分析Reportを生成する

---

### 要件5：比較レポートの提供

**ユーザーストーリー：** ユーザーとして、各トピックについてメディア間の比較レポートを閲覧したい。そうすることで、中東情勢を多角的な視点から理解できる。

#### 受け入れ基準

1. THE Dashboard SHALL 収集・分析済みのReportを一覧表示する
2. WHEN ユーザーがReportを選択したとき、THE Dashboard SHALL 対象Clusterの各Article（メディア別）とBias_Score・差異分析を表示する
3. THE Dashboard SHALL 各メディアのBias_Scoreを視覚的に比較できるチャートを表示する
4. THE Dashboard SHALL 各Articleの原文リンクを提供する
5. WHEN ユーザーがキーワードで検索したとき、THE Dashboard SHALL 該当するClusterおよびArticleを返す
6. THE Dashboard SHALL 最終更新日時を表示する

---

### 要件6：データ永続化と管理

**ユーザーストーリー：** 開発者として、収集・分析データを永続化し管理したい。そうすることで、過去の報道履歴を参照・再分析できる。

#### 受け入れ基準

1. THE Aggregator SHALL 収集したArticleをデータストアに永続化する
2. THE Aggregator SHALL 生成したReportをデータストアに永続化する
3. WHEN データストアへの書き込みが失敗したとき、THE Aggregator SHALL エラーをログに記録し、処理をロールバックする
4. THE Aggregator SHALL Articleの保存期間として最低30日間のデータを保持する
5. THE Aggregator SHALL データストアのスキーマバージョンを管理し、マイグレーションをサポートする

---

### 要件7：エラーハンドリングと信頼性

**ユーザーストーリー：** 開発者として、システムが部分的な障害に対して堅牢に動作してほしい。そうすることで、一部のメディアが利用不可でも他のメディアの収集・分析が継続できる。

#### 受け入れ基準

1. IF 外部メディアAPIへのリクエストがタイムアウト（30秒以上）したとき、THEN THE Collector SHALL リクエストを中断し、エラーをログに記録する
2. IF 外部メディアAPIが連続して3回失敗したとき、THEN THE Collector SHALL そのメディアの収集を一時停止し、60分後に再試行する
3. WHEN システムが起動したとき、THE Aggregator SHALL 全コンポーネントの初期化状態を確認し、異常があればログに記録する
4. THE Aggregator SHALL 全ての処理エラーを構造化ログ（タイムスタンプ・エラーコード・メッセージ）として記録する
5. IF 分析処理中に予期しない例外が発生したとき、THEN THE Analyzer SHALL 例外をキャッチしてログに記録し、該当Articleの処理をスキップして次の処理を継続する
