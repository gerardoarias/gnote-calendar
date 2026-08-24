#include "storage.h"
#include "../../third_party/sqlite3.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>

namespace gnote {

std::string defaultDbPath() {
    const char* home = getenv("HOME");
    if (!home) home = "/tmp";
    std::string dir = std::string(home) + "/.local/share/gnote-calendar";
    std::filesystem::create_directories(dir);
    return dir + "/notes.db";
}

Storage::Storage(const std::string& dbPath) : dbPath_(dbPath), db_(nullptr) {}
Storage::~Storage() { close(); }

void Storage::close() {
    if (db_) { sqlite3_close(db_); db_=nullptr; }
}

bool Storage::open() {
    if (db_) return true;
    // asegurar directorio
    auto pos = dbPath_.find_last_of('/');
    if (pos != std::string::npos) {
        std::filesystem::create_directories(dbPath_.substr(0,pos));
    }
    int rc = sqlite3_open(dbPath_.c_str(), &db_);
    if (rc != SQLITE_OK) {
        lastError_ = sqlite3_errmsg(db_);
        db_=nullptr;
        return false;
    }
    exec("PRAGMA journal_mode=WAL;");
    exec("PRAGMA foreign_keys=ON;");
    exec("PRAGMA synchronous=NORMAL;");
    return true;
}

bool Storage::exec(const std::string& sql) const {
    char* err=nullptr;
    int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &err);
    if (rc!=SQLITE_OK) {
        // lastError mutable
        const_cast<Storage*>(this)->lastError_ = err ? err : sqlite3_errmsg(db_);
        if (err) sqlite3_free(err);
        return false;
    }
    return true;
}

bool Storage::initSchema() {
    if (!isOpen() && !open()) return false;
    // Intenta leer data/schema.sql relativo al binario o inline fallback
    std::string schemaPath = "data/schema.sql";
    std::ifstream f(schemaPath);
    std::string sql;
    if (f.good()) {
        std::ostringstream ss; ss << f.rdbuf(); sql = ss.str();
    } else {
        // fallback inline (copia de data/schema.sql)
        sql = R"(
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', location TEXT DEFAULT '', start_ts INTEGER NOT NULL, end_ts INTEGER NOT NULL, rrule TEXT DEFAULT '', note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL, uid TEXT UNIQUE, source TEXT DEFAULT 'local', created_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
        CREATE INDEX IF NOT EXISTS idx_events_uid ON events(uid);
        CREATE TABLE IF NOT EXISTS tags(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS note_tags(note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE, tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE, PRIMARY KEY(note_id, tag_id));
        CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
        CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at);
        CREATE TABLE IF NOT EXISTS backlinks(src_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE, dst_title TEXT NOT NULL, PRIMARY KEY(src_id, dst_title));
        CREATE INDEX IF NOT EXISTS idx_backlinks_src ON backlinks(src_id);
        CREATE INDEX IF NOT EXISTS idx_backlinks_dst ON backlinks(dst_title);
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(title, body, content='notes', content_rowid='id', tokenize='unicode61');
        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body); END;
        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body); END;
        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN INSERT INTO notes_fts(notes_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body); INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body); END;
        )";
    }
    char* err=nullptr;
    int rc = sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &err);
    if (rc!=SQLITE_OK) {
        lastError_ = err ? err : sqlite3_errmsg(db_);
        if (err) sqlite3_free(err);
        // Si FTS5 no existe, reintentar sin FTS
        if (lastError_.find("fts5")!=std::string::npos || lastError_.find("no such module")!=std::string::npos) {
            // crear sin FTS
            exec("DROP TRIGGER IF EXISTS notes_ai; DROP TRIGGER IF EXISTS notes_ad; DROP TRIGGER IF EXISTS notes_au; DROP TABLE IF EXISTS notes_fts;");
            std::string fallback = R"(
            CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT DEFAULT '', location TEXT DEFAULT '', start_ts INTEGER NOT NULL, end_ts INTEGER NOT NULL, rrule TEXT DEFAULT '', note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL, uid TEXT UNIQUE, source TEXT DEFAULT 'local', created_at INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
            )";
            return exec(fallback);
        }
        return false;
    }
    return true;
}

bool Storage::needsMigration() const { return false; }

// Helpers internos
static void bindText(sqlite3_stmt* s, int idx, const std::string& v) {
    sqlite3_bind_text(s, idx, v.c_str(), -1, SQLITE_TRANSIENT);
}

int Storage::createNote(Note& note) {
    if (!isOpen()) open();
    note.created_at = note.created_at ? note.created_at : nowTimestamp();
    note.updated_at = nowTimestamp();
    const char* sql = "INSERT INTO notes(title, body, created_at, updated_at) VALUES(?,?,?,?)";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql, -1, &st, nullptr)!=SQLITE_OK) { lastError_=sqlite3_errmsg(db_); return 0; }
    bindText(st,1,note.title); bindText(st,2,note.body);
    sqlite3_bind_int64(st,3,note.created_at); sqlite3_bind_int64(st,4,note.updated_at);
    int rc = sqlite3_step(st); sqlite3_finalize(st);
    if (rc!=SQLITE_DONE) { lastError_=sqlite3_errmsg(db_); return 0; }
    note.id = (int)sqlite3_last_insert_rowid(db_);
    // tags
    if (!note.tags.empty()) setTagsForNote(note.id, note.tags);
    else {
        auto autoTags = extractTags(note.title + " " + note.body);
        if (!autoTags.empty()) setTagsForNote(note.id, autoTags);
    }
    updateBacklinks(note.id, note.body);
    return note.id;
}

bool Storage::updateNote(Note& note) {
    if (!note.isPersisted()) return false;
    note.updated_at = nowTimestamp();
    const char* sql="UPDATE notes SET title=?, body=?, updated_at=? WHERE id=?";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql,-1,&st,nullptr)!=SQLITE_OK) return false;
    bindText(st,1,note.title); bindText(st,2,note.body);
    sqlite3_bind_int64(st,3,note.updated_at); sqlite3_bind_int(st,4,note.id);
    int rc=sqlite3_step(st); sqlite3_finalize(st);
    if (rc!=SQLITE_DONE) return false;
    // actualizar tags si vienen
    if (!note.tags.empty()) setTagsForNote(note.id, note.tags);
    updateBacklinks(note.id, note.body);
    return true;
}

bool Storage::deleteNote(int id) {
    return exec("DELETE FROM notes WHERE id=" + std::to_string(id));
}

std::optional<Note> Storage::getNote(int id) const {
    const char* sql="SELECT id,title,body,created_at,updated_at FROM notes WHERE id=?";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql,-1,&st,nullptr)!=SQLITE_OK) return std::nullopt;
    sqlite3_bind_int(st,1,id);
    std::optional<Note> out;
    if (sqlite3_step(st)==SQLITE_ROW) {
        Note n;
        n.id=sqlite3_column_int(st,0);
        n.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
        n.body= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
        n.created_at=sqlite3_column_int64(st,3);
        n.updated_at=sqlite3_column_int64(st,4);
        n.tags = const_cast<Storage*>(this)->getTagsForNote(n.id);
        out=n;
    }
    sqlite3_finalize(st);
    return out;
}

std::vector<Note> Storage::listNotes(int limit, int offset) const {
    std::vector<Note> out;
    std::string sql="SELECT id,title,body,created_at,updated_at FROM notes ORDER BY updated_at DESC LIMIT "+std::to_string(limit)+" OFFSET "+std::to_string(offset);
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql.c_str(),-1,&st,nullptr)!=SQLITE_OK) return out;
    while (sqlite3_step(st)==SQLITE_ROW) {
        Note n;
        n.id=sqlite3_column_int(st,0);
        n.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
        n.body= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
        n.created_at=sqlite3_column_int64(st,3);
        n.updated_at=sqlite3_column_int64(st,4);
        out.push_back(std::move(n));
    }
    sqlite3_finalize(st);
    // cargar tags lazy
    for (auto& n: out) n.tags = const_cast<Storage*>(this)->getTagsForNote(n.id);
    return out;
}

std::vector<Note> Storage::searchNotes(const std::string& query, int limit) const {
    std::vector<Note> out;
    // intentar FTS5
    {
        std::string sql="SELECT n.id,n.title,n.body,n.created_at,n.updated_at FROM notes n JOIN notes_fts f ON n.id=f.rowid WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?";
        sqlite3_stmt* st=nullptr;
        if (sqlite3_prepare_v2(db_, sql.c_str(),-1,&st,nullptr)==SQLITE_OK) {
            bindText(st,1,query); sqlite3_bind_int(st,2,limit);
            bool hasRows=false;
            while (sqlite3_step(st)==SQLITE_ROW) {
                hasRows=true;
                Note n; n.id=sqlite3_column_int(st,0);
                n.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
                n.body= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
                n.created_at=sqlite3_column_int64(st,3); n.updated_at=sqlite3_column_int64(st,4);
                out.push_back(std::move(n));
            }
            sqlite3_finalize(st);
            if (hasRows || sqlite3_errcode(db_)==SQLITE_OK) {
                // si hubo resultados o no error, devolver (aunque vacío)
                // verificar si tabla fts existe: si no error, ok
                if (!out.empty() || lastError_.empty()) {
                    for (auto& n: out) n.tags = const_cast<Storage*>(this)->getTagsForNote(n.id);
                    // si no hubo resultados pero query no errónea, es simplemente sin matches
                    // comprobamos que no haya sido error de sintaxis FTS
                    if (sqlite3_errcode(db_)==SQLITE_OK) return out;
                }
            } else {
                sqlite3_finalize(st);
            }
        }
    }
    // fallback LIKE
    out.clear();
    std::string like = "%" + query + "%";
    std::string sql="SELECT id,title,body,created_at,updated_at FROM notes WHERE title LIKE ? OR body LIKE ? ORDER BY updated_at DESC LIMIT ?";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql.c_str(),-1,&st,nullptr)!=SQLITE_OK) return out;
    bindText(st,1,like); bindText(st,2,like); sqlite3_bind_int(st,3,limit);
    while (sqlite3_step(st)==SQLITE_ROW) {
        Note n; n.id=sqlite3_column_int(st,0);
        n.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
        n.body= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
        n.created_at=sqlite3_column_int64(st,3); n.updated_at=sqlite3_column_int64(st,4);
        out.push_back(std::move(n));
    }
    sqlite3_finalize(st);
    for (auto& n: out) n.tags = const_cast<Storage*>(this)->getTagsForNote(n.id);
    return out;
}

std::vector<std::string> Storage::getTagsForNote(int noteId) const {
    std::vector<std::string> out;
    const char* sql="SELECT t.name FROM tags t JOIN note_tags nt ON t.id=nt.tag_id WHERE nt.note_id=?";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql,-1,&st,nullptr)!=SQLITE_OK) return out;
    sqlite3_bind_int(st,1,noteId);
    while (sqlite3_step(st)==SQLITE_ROW) {
        out.push_back(reinterpret_cast<const char*>(sqlite3_column_text(st,0)));
    }
    sqlite3_finalize(st);
    return out;
}

bool Storage::setTagsForNote(int noteId, const std::vector<std::string>& tags) {
    exec("DELETE FROM note_tags WHERE note_id=" + std::to_string(noteId));
    for (auto &tag: tags) {
        // insert tag if not exists
        sqlite3_stmt* st=nullptr;
        sqlite3_prepare_v2(db_, "INSERT OR IGNORE INTO tags(name) VALUES(?)", -1, &st, nullptr);
        bindText(st,1,tag); sqlite3_step(st); sqlite3_finalize(st);
        // get tag id
        sqlite3_prepare_v2(db_, "SELECT id FROM tags WHERE name=?", -1, &st, nullptr);
        bindText(st,1,tag);
        int tagId=0;
        if (sqlite3_step(st)==SQLITE_ROW) tagId=sqlite3_column_int(st,0);
        sqlite3_finalize(st);
        if (!tagId) continue;
        sqlite3_prepare_v2(db_, "INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES(?,?)", -1, &st, nullptr);
        sqlite3_bind_int(st,1,noteId); sqlite3_bind_int(st,2,tagId);
        sqlite3_step(st); sqlite3_finalize(st);
    }
    return true;
}

// Events

int Storage::createEvent(Event& ev) {
    if (!ev.isValid()) return 0;
    ev.created_at = ev.created_at ? ev.created_at : nowTimestamp();
    if (ev.uid.empty()) ev.uid = generateUid();
    const char* sql="INSERT INTO events(title, description, location, start_ts, end_ts, rrule, note_id, uid, source, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql,-1,&st,nullptr)!=SQLITE_OK) { lastError_=sqlite3_errmsg(db_); return 0; }
    bindText(st,1,ev.title); bindText(st,2,ev.description); bindText(st,3,ev.location);
    sqlite3_bind_int64(st,4,ev.start_ts); sqlite3_bind_int64(st,5,ev.end_ts);
    bindText(st,6,ev.rrule);
    if (ev.note_id==0) sqlite3_bind_null(st,7); else sqlite3_bind_int(st,7,ev.note_id);
    bindText(st,8,ev.uid); bindText(st,9,ev.source);
    sqlite3_bind_int64(st,10,ev.created_at);
    int rc=sqlite3_step(st); sqlite3_finalize(st);
    if (rc!=SQLITE_DONE) { lastError_=sqlite3_errmsg(db_); return 0; }
    ev.id=(int)sqlite3_last_insert_rowid(db_);
    return ev.id;
}

bool Storage::updateEvent(Event& ev) {
    if (!ev.id) return false;
    const char* sql="UPDATE events SET title=?, description=?, location=?, start_ts=?, end_ts=?, rrule=?, note_id=?, uid=?, source=? WHERE id=?";
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, sql,-1,&st,nullptr)!=SQLITE_OK) return false;
    bindText(st,1,ev.title); bindText(st,2,ev.description); bindText(st,3,ev.location);
    sqlite3_bind_int64(st,4,ev.start_ts); sqlite3_bind_int64(st,5,ev.end_ts);
    bindText(st,6,ev.rrule);
    if (ev.note_id==0) sqlite3_bind_null(st,7); else sqlite3_bind_int(st,7,ev.note_id);
    bindText(st,8,ev.uid); bindText(st,9,ev.source);
    sqlite3_bind_int(st,10,ev.id);
    int rc=sqlite3_step(st); sqlite3_finalize(st);
    return rc==SQLITE_DONE;
}

bool Storage::deleteEvent(int id) { return exec("DELETE FROM events WHERE id=" + std::to_string(id)); }

static Event rowToEvent(sqlite3_stmt* st) {
    Event e;
    e.id=sqlite3_column_int(st,0);
    e.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
    e.description= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
    e.location= reinterpret_cast<const char*>(sqlite3_column_text(st,3) ? sqlite3_column_text(st,3) : (const unsigned char*)"");
    e.start_ts=sqlite3_column_int64(st,4); e.end_ts=sqlite3_column_int64(st,5);
    e.rrule= reinterpret_cast<const char*>(sqlite3_column_text(st,6) ? sqlite3_column_text(st,6) : (const unsigned char*)"");
    e.note_id=sqlite3_column_int(st,7);
    e.uid= reinterpret_cast<const char*>(sqlite3_column_text(st,8) ? sqlite3_column_text(st,8) : (const unsigned char*)"");
    e.source= reinterpret_cast<const char*>(sqlite3_column_text(st,9) ? sqlite3_column_text(st,9) : (const unsigned char*)"");
    e.created_at=sqlite3_column_int64(st,10);
    return e;
}

std::optional<Event> Storage::getEvent(int id) const {
    sqlite3_stmt* st=nullptr;
    sqlite3_prepare_v2(db_, "SELECT id,title,description,location,start_ts,end_ts,rrule,note_id,uid,source,created_at FROM events WHERE id=?", -1, &st, nullptr);
    sqlite3_bind_int(st,1,id);
    std::optional<Event> out;
    if (sqlite3_step(st)==SQLITE_ROW) out=rowToEvent(st);
    sqlite3_finalize(st);
    return out;
}

std::vector<Event> Storage::listEvents(int64_t from_ts, int64_t to_ts) const {
    std::vector<Event> out;
    sqlite3_stmt* st=nullptr;
    sqlite3_prepare_v2(db_, "SELECT id,title,description,location,start_ts,end_ts,rrule,note_id,uid,source,created_at FROM events WHERE start_ts>=? AND start_ts<=? ORDER BY start_ts ASC", -1, &st, nullptr);
    sqlite3_bind_int64(st,1,from_ts); sqlite3_bind_int64(st,2,to_ts);
    while (sqlite3_step(st)==SQLITE_ROW) out.push_back(rowToEvent(st));
    sqlite3_finalize(st);
    return out;
}

std::vector<Event> Storage::listAllEvents() const {
    std::vector<Event> out;
    sqlite3_stmt* st=nullptr;
    sqlite3_prepare_v2(db_, "SELECT id,title,description,location,start_ts,end_ts,rrule,note_id,uid,source,created_at FROM events ORDER BY start_ts ASC", -1, &st, nullptr);
    while (sqlite3_step(st)==SQLITE_ROW) out.push_back(rowToEvent(st));
    sqlite3_finalize(st);
    return out;
}

std::vector<Event> Storage::listEventsForMonth(int year, int month) const {
    std::tm tm{}; tm.tm_year=year-1900; tm.tm_mon=month-1; tm.tm_mday=1; tm.tm_isdst=-1;
    int64_t start = (int64_t)timegm(&tm);
    tm.tm_mon+=1; if (tm.tm_mon>11){tm.tm_mon=0; tm.tm_year++;}
    int64_t end = (int64_t)timegm(&tm)-1;
    return listEvents(start,end);
}

int Storage::countNotes() const {
    sqlite3_stmt* st=nullptr; sqlite3_prepare_v2(db_, "SELECT COUNT(*) FROM notes", -1,&st,nullptr);
    int c=0; if (sqlite3_step(st)==SQLITE_ROW) c=sqlite3_column_int(st,0);
    sqlite3_finalize(st); return c;
}
int Storage::countEvents() const {
    sqlite3_stmt* st=nullptr; sqlite3_prepare_v2(db_, "SELECT COUNT(*) FROM events", -1,&st,nullptr);
    int c=0; if (sqlite3_step(st)==SQLITE_ROW) c=sqlite3_column_int(st,0);
    sqlite3_finalize(st); return c;
}

// Knowledge OS - Backlinks
bool Storage::updateBacklinks(int noteId, const std::string& body) {
    exec("DELETE FROM backlinks WHERE src_id=" + std::to_string(noteId));
    auto links = extractBacklinks(body);
    for (auto &dst: links) {
        sqlite3_stmt* st=nullptr;
        if (sqlite3_prepare_v2(db_, "INSERT OR IGNORE INTO backlinks(src_id, dst_title) VALUES(?,?)", -1, &st, nullptr)!=SQLITE_OK) continue;
        sqlite3_bind_int(st,1,noteId); bindText(st,2,dst);
        sqlite3_step(st); sqlite3_finalize(st);
    }
    return true;
}
std::vector<std::string> Storage::getBacklinksForNote(int noteId) const {
    std::vector<std::string> out;
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, "SELECT dst_title FROM backlinks WHERE src_id=?", -1, &st, nullptr)!=SQLITE_OK) return out;
    sqlite3_bind_int(st,1,noteId);
    while (sqlite3_step(st)==SQLITE_ROW) out.push_back(reinterpret_cast<const char*>(sqlite3_column_text(st,0)));
    sqlite3_finalize(st); return out;
}
std::vector<Note> Storage::getNotesLinkingTo(const std::string& title) const {
    std::vector<Note> out;
    sqlite3_stmt* st=nullptr;
    const char* sql="SELECT n.id,n.title,n.body,n.created_at,n.updated_at FROM notes n JOIN backlinks b ON n.id=b.src_id WHERE b.dst_title=? ORDER BY n.updated_at DESC";
    if (sqlite3_prepare_v2(db_, sql, -1, &st, nullptr)!=SQLITE_OK) return out;
    bindText(st,1,title);
    while (sqlite3_step(st)==SQLITE_ROW) {
        Note n; n.id=sqlite3_column_int(st,0);
        n.title= reinterpret_cast<const char*>(sqlite3_column_text(st,1) ? sqlite3_column_text(st,1) : (const unsigned char*)"");
        n.body= reinterpret_cast<const char*>(sqlite3_column_text(st,2) ? sqlite3_column_text(st,2) : (const unsigned char*)"");
        n.created_at=sqlite3_column_int64(st,3); n.updated_at=sqlite3_column_int64(st,4);
        out.push_back(std::move(n));
    }
    sqlite3_finalize(st); return out;
}
std::vector<std::pair<int,std::string>> Storage::getAllLinks() const {
    std::vector<std::pair<int,std::string>> out;
    sqlite3_stmt* st=nullptr;
    if (sqlite3_prepare_v2(db_, "SELECT src_id, dst_title FROM backlinks", -1, &st, nullptr)!=SQLITE_OK) return out;
    while (sqlite3_step(st)==SQLITE_ROW) out.emplace_back(sqlite3_column_int(st,0), reinterpret_cast<const char*>(sqlite3_column_text(st,1)));
    sqlite3_finalize(st); return out;
}

}
