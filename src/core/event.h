#pragma once
#include <string>
#include <cstdint>

namespace gnote {

struct Event {
    int id = 0;
    std::string title;
    std::string description;
    std::string location;
    int64_t start_ts = 0;
    int64_t end_ts = 0;
    std::string rrule; // "FREQ=WEEKLY;BYDAY=MO" o vacío
    int note_id = 0; // 0 = sin nota vinculada
    std::string uid; // para ICS, generado si vacío
    std::string source = "local"; // local | imported_ics
    int64_t created_at = 0;

    bool isAllDay() const;
    int64_t durationSeconds() const { return end_ts - start_ts; }
    bool isValid() const { return !title.empty() && start_ts > 0 && end_ts >= start_ts; }
};

std::string generateUid();

}
