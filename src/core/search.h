#pragma once
#include "note.h"
#include "event.h"
#include <string>
#include <vector>

namespace gnote {

// Parseo simple de query con filtros: "tag:trabajo fecha:hoy texto"
// Para ligero, no requiere motor complejo.
struct SearchQuery {
    std::string text; // texto libre
    std::string tag;
    std::string dateFilter; // "hoy", "2026-08-24"
};

SearchQuery parseQuery(const std::string& raw);
bool noteMatches(const Note& n, const SearchQuery& q);

}
