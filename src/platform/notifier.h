#pragma once
#include "../core/event.h"
#include <vector>
#include <string>

namespace gnote {

// Notificador ligero: consulta eventos próximos y dispara libnotify si disponible,
// fallback a stdout.
class Notifier {
public:
    // retorna eventos que empiezan en [now, now+windowSec]
    static std::vector<Event> upcoming(const std::vector<Event>& all, int64_t now, int windowSec=900);

    // intenta notificar (libnotify si existe, si no stdout)
    static bool notify(const Event& e);

private:
    static bool tryLibNotify(const std::string& title, const std::string& body);
};

}
