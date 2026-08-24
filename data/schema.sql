-- Esquema SQLite para gnote-calendar
-- Compatible SQLite 3.7+ (desde Ubuntu 14.04)

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    location TEXT DEFAULT '',
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    rrule TEXT DEFAULT '',
    note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
    uid TEXT UNIQUE,
    source TEXT DEFAULT 'local',
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
CREATE INDEX IF NOT EXISTS idx_events_uid ON events(uid);

CREATE TABLE IF NOT EXISTS tags(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS note_tags(
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY(note_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);

-- Backlinks para Knowledge OS (Etapa 2)
CREATE TABLE IF NOT EXISTS backlinks(
    src_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    dst_title TEXT NOT NULL,
    PRIMARY KEY(src_id, dst_title)
);
CREATE INDEX IF NOT EXISTS idx_backlinks_src ON backlinks(src_id);
CREATE INDEX IF NOT EXISTS idx_backlinks_dst ON backlinks(dst_title);

-- FTS5 para búsqueda instantánea (si no disponible, fallback a LIKE)
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, body, content='notes', content_rowid='id', tokenize='unicode61');
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
