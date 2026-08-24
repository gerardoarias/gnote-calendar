#include "notifier.h"
#include <cstdlib>
#include <iostream>

namespace gnote {

std::vector<Event> Notifier::upcoming(const std::vector<Event>& all, int64_t now, int windowSec) {
    std::vector<Event> out;
    for (auto &e: all) {
        if (e.start_ts >= now && e.start_ts <= now + windowSec) out.push_back(e);
    }
    return out;
}

bool Notifier::tryLibNotify(const std::string& title, const std::string& body) {
    // intenta notify-send si existe
    std::string cmd = "which notify-send >/dev/null 2>&1 && notify-send " +
        std::string("'") + title + "' '" + body + "' 2>/dev/null";
    // escapar comillas simples simple
    int rc = system(cmd.c_str());
    return rc==0;
}

bool Notifier::notify(const Event& e) {
    std::string title = "Recordatorio: " + e.title;
    std::string body = e.description;
    if (!e.location.empty()) body += "\nLugar: " + e.location;
    if (tryLibNotify(title, body)) return true;
    std::cout << "[NOTIFY] " << title << " - " << body << "\n";
    return true;
}

}
