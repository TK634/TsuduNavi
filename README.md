# TsuduNavi

LINE × Claude × Google Calendar を組み合わせた、体験授業の予約を自動化するシステムです。
生徒管理・予約・会話履歴はすべて Supabase で完結するオールインワン構成です。

## 機能概要

| 機能 | 説明 |
|------|------|
| LINEメッセージ受信 | 保護者からのLINEメッセージを署名検証付きで受信 |
| AIヒアリング | Claude APIが学年・科目・希望日程を自然な会話でヒアリング |
| 空き時間確認 | Google Calendarで空きスロットを自動検索 |
| 日程候補提示 | LINEボタンメッセージで最大3件の候補を提示 |
| 予約確定 | 選択されたスロットをカレンダーに登録し確認通知を送信 |

## アーキテクチャ

```
LINE ──→ FastAPI (webhook.py)
              ↓
          agent.py（Claude APIで会話管理）
              ↓
     ┌────────┴────────┐
  calendar.py      database.py
 (Google Calendar)  (Supabase)
```

## フォルダ構成

```
juku-agent/
├── app/
│   ├── main.py        # FastAPI起動・ルーター登録
│   ├── webhook.py     # LINE Webhookエンドポイント（署名検証含む）
│   ├── agent.py       # Claude APIを使った会話ロジック
│   ├── calendar.py    # Google Calendar（空き時間取得・予約作成）
│   ├── line_client.py # LINE Messaging API（メッセージ・ボタン送信）
│   ├── database.py    # Supabase接続・CRUD
│   └── models.py      # Pydanticモデル
├── supabase/
│   └── migrations/
│       └── 001_init.sql  # テーブル定義
├── tests/
│   ├── test_agent.py
│   └── test_webhook.py
├── .env.example
├── requirements.txt
└── README.md
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env を開いて各APIキーを入力してください
```

### 3. Supabaseのテーブル作成

Supabase管理画面の **SQL Editor** で `supabase/migrations/001_init.sql` の内容を実行してください。

### 4. Google Calendarの準備

1. GCPコンソールでサービスアカウントを作成し、JSONキーをダウンロード
2. Google Calendarの **カレンダーの設定 > 特定のユーザーとの共有** にサービスアカウントのメールアドレスを「イベントの編集者」として追加
3. JSONキーの内容を `.env` の `GOOGLE_CALENDAR_CREDENTIALS_JSON` に設定（1行のJSON文字列）

### 5. LINE Developers設定

1. LINE DevelopersでMessaging APIチャネルを作成
2. **Webhook URL** に `https://your-domain.com/line/webhook` を設定
3. **Webhookの利用** をオンにする
4. チャネルアクセストークン（長期）を発行して `.env` に設定

### 6. サーバー起動

```bash
uvicorn app.main:app --reload
```

開発時は ngrok などでローカルサーバーを外部公開します：

```bash
ngrok http 8000
# 発行されたURLをLINE DevelopersのWebhook URLに設定
```

## 会話フロー

```
保護者: こんにちは
  ↓
Claude: いらっしゃいませ！お子様の学年を教えてください。
  ↓
保護者: 中3です
  ↓
Claude: 中3ですね。体験を希望する科目を教えてください。
  ↓
保護者: 数学をお願いします
  ↓
Claude: 数学ですね。希望の曜日と時間帯（午前/午後/夕方）は？
  ↓
保護者: 月曜か水曜の午後がいいです
  ↓
LINE: [ボタン選択]
  ① 6/10(月) 14:00〜15:00
  ② 6/12(水) 14:00〜15:00
  ③ 6/14(金) 15:00〜16:00
  ↓
保護者: ①を希望します
  ↓
LINE: ✅ 予約が確定しました！
      【日時】6月10日(月) 14:00〜15:00
      【科目】数学 / 【学年】中3
      当日お待ちしております。
```

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/line/webhook` | LINE Webhook受信 |

## テスト

```bash
pytest tests/ -v
```

## 環境変数一覧

| 変数名 | 説明 |
|--------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン |
| `LINE_CHANNEL_SECRET` | LINEチャネルシークレット |
| `ANTHROPIC_API_KEY` | Anthropic APIキー |
| `CLAUDE_MODEL` | 使用モデル（デフォルト: `claude-sonnet-4-6`） |
| `SUPABASE_URL` | SupabaseプロジェクトURL |
| `SUPABASE_KEY` | Supabase APIキー（service_role推奨） |
| `GOOGLE_CALENDAR_CREDENTIALS_JSON` | サービスアカウントキー（JSON文字列） |
| `GOOGLE_CALENDAR_ID` | Google CalendarのカレンダーID |
