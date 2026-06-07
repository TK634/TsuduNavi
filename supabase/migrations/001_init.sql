-- ============================================================
-- 塾AIエージェント 初期スキーマ（オールインワンモード）
-- ============================================================

-- students: 生徒情報テーブル（Supabaseで一元管理）
CREATE TABLE IF NOT EXISTS students (
    id           UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    line_user_id TEXT        NOT NULL UNIQUE,
    name         TEXT,
    grade        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- conversations: 会話状態テーブル
-- stage は ConversationStage enum の値に対応
-- collected_data: ヒアリング済みデータ（JSONB）
-- messages: 会話ログ全体（JSONB配列）
CREATE TABLE IF NOT EXISTS conversations (
    id             UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    line_user_id   TEXT        NOT NULL UNIQUE,
    stage          TEXT        NOT NULL DEFAULT 'greeting'
                               CHECK (stage IN (
                                   'greeting', 'collect_grade', 'collect_subject',
                                   'collect_schedule', 'show_slots',
                                   'confirm_booking', 'completed'
                               )),
    collected_data JSONB       NOT NULL DEFAULT '{}',
    messages       JSONB       NOT NULL DEFAULT '[]',
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- bookings: 予約テーブル
-- status: 'confirmed'（確定）/ 'cancelled'（キャンセル）/ 'completed'（受講済み）
CREATE TABLE IF NOT EXISTS bookings (
    id                UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    line_user_id      TEXT        NOT NULL,
    student_name      TEXT        NOT NULL,
    grade             TEXT        NOT NULL,
    subject           TEXT        NOT NULL,
    scheduled_at      TIMESTAMPTZ NOT NULL,
    calendar_event_id TEXT,
    status            TEXT        NOT NULL DEFAULT 'confirmed'
                                  CHECK (status IN ('confirmed', 'cancelled', 'completed')),
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── インデックス ──────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_conversations_line_user_id
    ON conversations (line_user_id);

CREATE INDEX IF NOT EXISTS idx_bookings_line_user_id
    ON bookings (line_user_id);

CREATE INDEX IF NOT EXISTS idx_bookings_scheduled_at
    ON bookings (scheduled_at);

-- ── Row Level Security ────────────────────────────────────────────────────
-- バックエンドは SERVICE_ROLE キーを使用するため RLS はオフにしています。
-- 必要に応じてポリシーを追加してください。

ALTER TABLE students      DISABLE ROW LEVEL SECURITY;
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE bookings      DISABLE ROW LEVEL SECURITY;
