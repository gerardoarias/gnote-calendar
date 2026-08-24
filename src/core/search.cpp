#include "search.h"
#include <sstream>
#include <algorithm>

namespace gnote {

SearchQuery parseQuery(const std::string& raw) {
    SearchQuery q;
    std::istringstream ss(raw);
    std::string tok;
    std::string textParts;
    while (ss >> tok) {
        auto pos=tok.find(':');
        if (pos!=std::string::npos) {
            std::string k=tok.substr(0,pos), v=tok.substr(pos+1);
            if (k=="tag"||k=="etiqueta") q.tag=v;
            else if (k=="fecha"||k=="date") q.dateFilter=v;
            else textParts += tok + " ";
        } else {
            textParts += tok + " ";
        }
    }
    if (!textParts.empty() && textParts.back()==' ') textParts.pop_back();
    q.text=textParts;
    return q;
}

bool noteMatches(const Note& n, const SearchQuery& q) {
    if (!q.tag.empty()) {
        bool has=false;
        for (auto &t: n.tags) if (t==q.tag) has=true;
        if (!has) return false;
        // también buscar #tag en cuerpo por si no está en tags
        if (n.body.find("#"+q.tag)==std::string::npos && n.title.find("#"+q.tag)==std::string::npos && !has) return false;
    }
    if (!q.text.empty()) {
        std::string hay = n.title + " " + n.body;
        std::string needle=q.text;
        // case insensitive simple
        auto lower = [](std::string s){ std::transform(s.begin(), s.end(), s.begin(), ::tolower); return s; };
        if (lower(hay).find(lower(needle))==std::string::npos) return false;
    }
    return true;
}

}
