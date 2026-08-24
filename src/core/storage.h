#pragma once
#include "note.h"
#include "event.h"
#include <string>
#include <vector>
#include <optional>

struct sqlite3;

namespace gnote {

class Storage {
public:
    explicit Storage(const std::string& dbPath);
    ~Storage();

    // No copy
    Storage(const Storage&) = delete;
    Storage& operator=(const Storage&) = delete;

    bool open();
    bool isOpen() const { return db_ != nullptr; }
    void close();

    // Schema
    bool initSchema(); // ejecuta data/schema.sql o inline
    bool needsMigration() const;

    // Notes
    int createNote(Note& note); // asigna id y timestamps
    bool updateNote(Note& note);
    bool deleteNote(int id);
    std::optional<Note> getNote(int id) const;
    std::vector<Note> listNotes(int limit=100, int offset=0) const;
    std::vector<Note> searchNotes(const std::string& query, int limit=50) const;

    // Tags
    std::vector<std::string> getTagsForNote(int noteId) const;
    bool setTagsForNote(int noteId, const std::vector<std::string>& tags);

    // Knowledge OS - Backlinks
    bool updateBacklinks(int noteId, const std::string& body);
    std::vector<std::string> getBacklinksForNote(int noteId) const;
    std::vector<Note> getNotesLinkingTo(const std::string& title) const;
    std::vector<std::pair<int,std::string>> getAllLinks() const; // (src_id, dst_title)

    // Events
    int createEvent(Event& ev);
    bool updateEvent(Event& ev);
    bool deleteEvent(int id);
    std::optional<Event> getEvent(int id) const;
    std::vector<Event> listEvents(int64_t from_ts, int64_t to_ts) const;
    std::vector<Event> listAllEvents() const;
    std::vector<Event> listEventsForMonth(int year, int month) const;

    // Stats
    int countNotes() const;
    int countEvents() const;

    std::string lastError() const { return lastError_; }

private:
    std::string dbPath_;
    sqlite3* db_ = nullptr;
    mutable std::string lastError_;

    bool exec(const std::string& sql) const;
    bool prepareAndExec(const std::string& sql) const;
};

std::string defaultDbPath(); // ~/.local/share/gnote-calendar/notes.db

}
