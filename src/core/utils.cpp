#include "note.h"
#include "event.h"
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <regex>
#include <random>

namespace gnote {

int64_t nowTimestamp() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

std::string timestampToISO(int64_t ts) {
    std::time_t t = static_cast<std::time_t>(ts);
    std::tm tm{};
    gmtime_r(&t, &tm);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm);
    return buf;
}

static bool parseDateTime(const std::string& s, std::tm& tm) {
    // Intenta varios formatos: "2026-08-24 10:00", "2026-08-24T10:00:00Z", "20260824T100000Z"
    std::istringstream ss(s);
    ss >> std::get_time(&tm, "%Y-%m-%d %H:%M");
    if (!ss.fail()) return true;
    ss.clear(); ss.str(s);
    ss >> std::get_time(&tm, "%Y-%m-%dT%H:%M:%S");
    if (!ss.fail()) return true;
    ss.clear(); ss.str(s);
    ss >> std::get_time(&tm, "%Y-%m-%d");
    if (!ss.fail()) { tm.tm_hour=0; tm.tm_min=0; tm.tm_sec=0; return true; }
    // ICS format: 20260824T100000Z
    if (s.size() >= 15) {
        char buf[20];
        // 20260824T100000Z -> 2026-08-24 10:00:00
        int y,m,d,H,M,S;
        if (sscanf(s.c_str(), "%4d%2d%2dT%2d%2d%2d", &y,&m,&d,&H,&M,&S)==6) {
            tm.tm_year=y-1900; tm.tm_mon=m-1; tm.tm_mday=d;
            tm.tm_hour=H; tm.tm_min=M; tm.tm_sec=S; tm.tm_isdst=-1;
            return true;
        }
        if (sscanf(s.c_str(), "%4d%2d%2d", &y,&m,&d)==3) {
            tm.tm_year=y-1900; tm.tm_mon=m-1; tm.tm_mday=d;
            tm.tm_hour=0; tm.tm_min=0; tm.tm_sec=0; tm.tm_isdst=-1;
            return true;
        }
    }
    return false;
}

int64_t isoToTimestamp(const std::string& iso) {
    if (iso.empty()) return 0;
    std::tm tm{};
    tm.tm_isdst = -1;
    if (!parseDateTime(iso, tm)) return 0;
    // Usamos timegm si disponible, fallback a mktime con TZ UTC
#if defined(__linux__)
    return static_cast<int64_t>(timegm(&tm));
#else
    return static_cast<int64_t>(mktime(&tm));
#endif
}

std::vector<std::string> extractTags(const std::string& text) {
    std::regex re(R"(#([A-Za-z0-9_\-]+))");
    std::sregex_iterator it(text.begin(), text.end(), re), end;
    std::vector<std::string> out;
    for (; it!=end; ++it) out.push_back((*it)[1].str());
    return out;
}

std::vector<std::string> extractBacklinks(const std::string& text) {
    std::regex re(R"(\[\[([^\]]+)\]\])");
    std::sregex_iterator it(text.begin(), text.end(), re), end;
    std::vector<std::string> out;
    for (; it!=end; ++it) out.push_back((*it)[1].str());
    return out;
}

std::vector<std::string> extractTasks(const std::string& text) {
    std::regex re(R"(- \[( |x|X)\] (.+))");
    std::sregex_iterator it(text.begin(), text.end(), re), end;
    std::vector<std::string> out;
    for (; it!=end; ++it) out.push_back((*it)[0].str());
    return out;
}

std::string generateUid() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    std::ostringstream ss;
    ss << std::hex;
    for (int i=0;i<32;i++) ss << dis(gen);
    ss << "@gnote-calendar.local";
    return ss.str();
}

bool Event::isAllDay() const {
    // Si duration es múltiplo de 86400 y empieza a medianoche
    if (durationSeconds() % 86400 != 0) return false;
    std::time_t t = static_cast<std::time_t>(start_ts);
    std::tm tm{}; gmtime_r(&t,&tm);
    return tm.tm_hour==0 && tm.tm_min==0 && tm.tm_sec==0;
}

}
