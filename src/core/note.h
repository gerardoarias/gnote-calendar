#pragma once
#include <string>
#include <vector>
#include <cstdint>

namespace gnote {

struct Note {
    int id = 0; // 0 = no persistido
    std::string title;
    std::string body;
    int64_t created_at = 0; // unix timestamp seconds
    int64_t updated_at = 0;
    std::vector<std::string> tags; // cache, se persiste en note_tags

    bool isPersisted() const { return id != 0; }
};

// Helpers
int64_t nowTimestamp();
std::string timestampToISO(int64_t ts);
int64_t isoToTimestamp(const std::string& iso); // "2026-08-24 10:00" o "2026-08-24T10:00:00Z"
std::vector<std::string> extractTags(const std::string& text); // #tag
std::vector<std::string> extractBacklinks(const std::string& text); // [[link]]
std::vector<std::string> extractTasks(const std::string& text); // - [ ] / - [x]

}
