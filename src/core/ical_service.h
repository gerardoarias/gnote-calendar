#pragma once
#include "event.h"
#include <string>
#include <vector>

namespace gnote {

struct IcalResult {
    int imported = 0;
    int skipped = 0; // duplicados
    int errors = 0;
    std::string message;
};

// Servicio ICS sin dependencia libical (parser propio ligero)
// Compatible con Google Calendar export/import
class IcalService {
public:
    // Exporta eventos a archivo .ics
    static bool exportToFile(const std::vector<Event>& events, const std::string& path, std::string& err);
    static std::string exportToString(const std::vector<Event>& events);

    // Importa desde archivo .ics -> vector<Event>
    static IcalResult importFromFile(const std::string& path, std::vector<Event>& out, std::string& err);
    static IcalResult importFromString(const std::string& content, std::vector<Event>& out);

    // Helpers
    static std::string formatIcalDate(int64_t ts); // UTC YYYYMMDDTHHMMSSZ
    static int64_t parseIcalDate(const std::string& s); // YYYYMMDDTHHMMSSZ o YYYYMMDD
};

}
