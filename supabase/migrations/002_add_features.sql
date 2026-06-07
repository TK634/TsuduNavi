-- ============================================================
-- 002: 各エージェント機能に必要なテーブル・カラム追加
-- ============================================================

-- ── 既存テーブルへのカラム追加 ────────────────────────────────────────────

-- students: リスクスコア管理カラム
ALTER TABLE students ADD COLUMN IF NOT EXISTS risk_score  NUMERIC(5,2) DEFAULT 0;
ALTER TABLE students ADD COLUMN IF NOT EXISTS risk_level  TEXT         DEFAULT 'low'
    CHECK (risk_level IN ('low', 'medium', 'high'));

-- bookings: 体験授業フォローアップ用カラム
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS trial_notes        TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS trial_completed_at TIMESTAMPTZ;

-- ── 新規テーブル ──────────────────────────────────────────────────────────

-- teachers: 講師アカウント管理
-- LINE IDで講師を識別し、保護者との Webhook ルーティングに使う
CREATE TABLE IF NOT EXISTS teachers (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    line_user_id TEXT NOT NULL UNIQUE,
    name         TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- attendances: 出席記録（退塾リスク検知の入力データ）
CREATE TABLE IF NOT EXISTS attendances (
    id                  UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id          UUID    NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_date         DATE    NOT NULL,
    attended            BOOLEAN NOT NULL DEFAULT true,
    subject             TEXT,
    teacher_line_user_id TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- grades: 成績記録（退塾リスク検知の入力データ）
CREATE TABLE IF NOT EXISTS grades (
    id         UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID         NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject    TEXT         NOT NULL,
    score      NUMERIC(5,2) NOT NULL,
    test_date  DATE         NOT NULL,
    test_type  TEXT,        -- '定期テスト', '模試', '小テスト' など
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

-- contact_logs: 保護者への連絡記録（退塾リスク検知の入力データ）
CREATE TABLE IF NOT EXISTS contact_logs (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id    UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    contacted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    contact_type  TEXT        DEFAULT 'line',  -- 'line', 'phone', 'face_to_face'
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- lesson_reports: 授業報告（講師→保護者の連絡帳）
-- status: draft（下書き）→ confirmed（講師確認済み）→ sent（保護者送信済み）
CREATE TABLE IF NOT EXISTS lesson_reports (
    id                   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id           UUID REFERENCES students(id) ON DELETE SET NULL,
    teacher_line_user_id TEXT NOT NULL,
    raw_content          TEXT NOT NULL,   -- 講師の生メモ
    generated_content    TEXT,            -- Claude生成の丁寧な文章
    status               TEXT NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft', 'sent', 'cancelled')),
    parent_line_user_id  TEXT,            -- 送信先保護者の LINE ID
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- invoices: 請求テーブル（月謝リマインドの対象）
CREATE TABLE IF NOT EXISTS invoices (
    id           UUID         DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id   UUID         NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    line_user_id TEXT         NOT NULL,  -- 保護者の LINE ID（JOIN不要のため非正規化）
    amount       INTEGER      NOT NULL,  -- 円
    due_date     DATE         NOT NULL,
    paid_at      TIMESTAMPTZ,
    status       TEXT         NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'paid', 'overdue')),
    month        TEXT         NOT NULL,  -- '2026-06' 形式
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- reminder_logs: リマインド送信履歴（重複送信防止）
CREATE TABLE IF NOT EXISTS reminder_logs (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id    UUID        NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    sent_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reminder_type TEXT        NOT NULL
                  CHECK (reminder_type IN ('3days_before', 'due_day', '3days_after'))
);

-- followup_logs: 体験後フォローアップ送信履歴（重複送信防止）
CREATE TABLE IF NOT EXISTS followup_logs (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    booking_id    UUID        NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    followup_type TEXT        NOT NULL CHECK (followup_type IN ('3day', '1week')),
    sent_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── インデックス ──────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_attendances_student_id
    ON attendances (student_id, lesson_date DESC);

CREATE INDEX IF NOT EXISTS idx_grades_student_id
    ON grades (student_id, test_date DESC);

CREATE INDEX IF NOT EXISTS idx_contact_logs_student_id
    ON contact_logs (student_id, contacted_at DESC);

CREATE INDEX IF NOT EXISTS idx_lesson_reports_teacher
    ON lesson_reports (teacher_line_user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_invoices_status_due
    ON invoices (status, due_date);

CREATE INDEX IF NOT EXISTS idx_reminder_logs_invoice
    ON reminder_logs (invoice_id, reminder_type);

CREATE INDEX IF NOT EXISTS idx_followup_logs_booking
    ON followup_logs (booking_id, followup_type);

CREATE INDEX IF NOT EXISTS idx_bookings_trial_completed
    ON bookings (trial_completed_at)
    WHERE trial_completed_at IS NOT NULL;

-- ── RLS（バックエンド専用のため無効化）────────────────────────────────────

ALTER TABLE teachers       DISABLE ROW LEVEL SECURITY;
ALTER TABLE attendances    DISABLE ROW LEVEL SECURITY;
ALTER TABLE grades         DISABLE ROW LEVEL SECURITY;
ALTER TABLE contact_logs   DISABLE ROW LEVEL SECURITY;
ALTER TABLE lesson_reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE invoices       DISABLE ROW LEVEL SECURITY;
ALTER TABLE reminder_logs  DISABLE ROW LEVEL SECURITY;
ALTER TABLE followup_logs  DISABLE ROW LEVEL SECURITY;
