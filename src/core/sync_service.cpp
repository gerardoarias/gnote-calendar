#include "sync_service.h"
#include "note.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <ctime>
#include <regex>

namespace gnote {
namespace fs = std::filesystem;

std::string FolderSync::defaultFolder() {
    const char* home = getenv("HOME");
    if (!home) home = "/tmp";
    return std::string(home) + "/Notas";
}

FolderSync::FolderSync(Storage& storage, const std::string& folderPath)
    : storage_(storage), folder_(folderPath) {
    if (folder_.empty()) folder_ = defaultFolder();
    // expandir ~
    if (!folder_.empty() && folder_[0]=='~') {
        const char* home = getenv("HOME");
        if (home) folder_ = std::string(home) + folder_.substr(1);
    }
}

std::string FolderSync::sanitizeFilename(const std::string& title, int id) {
    std::string s;
    // id prefix para estabilidad
    char prefix[16]; snprintf(prefix, sizeof(prefix), "%04d-", id);
    s = prefix;
    for (char c : title) {
        if (std::isalnum((unsigned char)c) || c=='-' || c=='_') s+=c;
        else if (c==' ') s+='-';
        else if ((unsigned char)c > 127) s+=c; // utf8 keep
        else if (c=='/' || c=='\\') s+='-';
    }
    if (s.size() > 80) s = s.substr(0,80);
    // trim trailing -
    while (!s.empty() && s.back()=='-') s.pop_back();
    if (s.empty()) s = std::string(prefix) + "nota";
    s += ".md";
    return s;
}

std::string FolderSync::generateFrontmatter(const Note& note) {
    std::ostringstream out;
    out << "---\n";
    out << "id: " << note.id << "\n";
    // escapar título con comillas si tiene :
    out << "title: \""; 
    for (char c: note.title) { if (c=='"') out << "\\\""; else out << c; }
    out << "\"\n";
    out << "created: " << timestampToISO(note.created_at) << "\n";
    out << "updated: " << timestampToISO(note.updated_at) << "\n";
    if (!note.tags.empty()) {
        out << "tags: [";
        for (size_t i=0;i<note.tags.size();++i) {
            if (i) out << ", ";
            out << note.tags[i];
        }
        out << "]\n";
    }
    out << "---\n\n";
    out << note.body << "\n";
    return out.str();
}

bool FolderSync::parseFrontmatter(const std::string& content, Note& note, std::string& bodyOut) {
    note = Note();
    bodyOut = content;
    if (content.rfind("---",0)!=0) {
        // sin frontmatter: tratar todo como body, título = primera línea
        std::istringstream ss(content);
        std::string first;
        std::getline(ss, first);
        if (!first.empty()) note.title = first.substr(0,80);
        else note.title = "Sin título";
        bodyOut = content;
        return true;
    }
    size_t end = content.find("\n---", 3);
    if (end == std::string::npos) {
        bodyOut = content;
        return false;
    }
    std::string fm = content.substr(3, end-3);
    bodyOut = content.substr(end+4);
    // trim leading newlines
    while (!bodyOut.empty() && (bodyOut[0]=='\n' || bodyOut[0]=='\r')) bodyOut.erase(0,1);

    std::istringstream ss(fm);
    std::string line;
    while (std::getline(ss, line)) {
        auto pos = line.find(':');
        if (pos==std::string::npos) continue;
        std::string k = line.substr(0,pos), v = line.substr(pos+1);
        // trim
        auto trim = [](std::string s){
            size_t a=0; while(a<s.size() && isspace((unsigned char)s[a])) a++;
            size_t b=s.size(); while(b>a && isspace((unsigned char)s[b-1])) b--;
            return s.substr(a,b-a);
        };
        k = trim(k); v = trim(v);
        // strip quotes
        if (v.size()>=2 && v.front()=='"' && v.back()=='"') v = v.substr(1, v.size()-2);
        // unescape
        std::string unesc;
        for (size_t i=0;i<v.size();++i) {
            if (v[i]=='\\' && i+1<v.size() && v[i+1]=='"') { unesc+='"'; i++; }
            else unesc+=v[i];
        }
        v = unesc;
        if (k=="id") try { note.id = std::stoi(v); } catch(...) {}
        else if (k=="title") note.title = v;
        else if (k=="created") note.created_at = isoToTimestamp(v);
        else if (k=="updated") note.updated_at = isoToTimestamp(v);
        else if (k=="tags") {
            // tags: [a, b] o "a b"
            std::regex re(R"(\[([^\]]*)\])");
            std::smatch m;
            if (std::regex_search(v, m, re)) {
                std::string inner = m[1].str();
                std::stringstream ts(inner);
                std::string tok;
                while (std::getline(ts, tok, ',')) {
                    tok = trim(tok);
                    if (!tok.empty()) note.tags.push_back(tok);
                }
            } else {
                std::stringstream ts(v);
                std::string tok;
                while (ts >> tok) note.tags.push_back(tok);
            }
        }
    }
    if (note.title.empty()) {
        // fallback: primera línea del body
        std::istringstream bs(bodyOut);
        std::string first; std::getline(bs, first);
        note.title = first.empty() ? "Sin título" : first.substr(0,80);
    }
    return true;
}

int64_t FolderSync::fileMtime(const std::string& path) {
    try {
        auto t = fs::last_write_time(path);
        auto sctp = std::chrono::time_point_cast<std::chrono::system_clock::duration>(t - fs::file_time_type::clock::now() + std::chrono::system_clock::now());
        return std::chrono::duration_cast<std::chrono::seconds>(sctp.time_since_epoch()).count();
    } catch (...) { return 0; }
}

bool FolderSync::writeFileAtomic(const std::string& path, const std::string& content) {
    try {
        std::string tmp = path + ".tmp";
        {
            std::ofstream f(tmp, std::ios::binary);
            if (!f) return false;
            f << content;
        }
        fs::rename(tmp, path);
        return true;
    } catch (...) { return false; }
}

static void setFileMtime(const std::string& path, int64_t ts) {
    try {
        auto tp = std::chrono::system_clock::from_time_t((time_t)ts);
        auto ftime = fs::file_time_type::clock::now() + (tp - std::chrono::system_clock::now());
        // aproximación: set to now + delta
        fs::last_write_time(path, ftime);
    } catch (...) {}
}

std::string FolderSync::noteToFilePath(const Note& note) const {
    return (fs::path(folder_) / sanitizeFilename(note.title, note.id)).string();
}

SyncResult FolderSync::exportAll() {
    SyncResult r;
    try { fs::create_directories(folder_); } catch (...) { r.errors++; r.message="No se pudo crear carpeta"; return r; }
    auto notes = storage_.listNotes(10000);
    for (auto &n: notes) {
        std::string path = noteToFilePath(n);
        // si archivo existe y es más nuevo que nota, skip (conflicto: archivo gana, se importará después)
        int64_t fm = fileMtime(path);
        if (fm > 0 && fm > n.updated_at + 1) {
            // archivo más nuevo, no exportar, se contará como import en sync
            r.skipped++;
            continue;
        }
        // también buscar archivo antiguo con mismo id pero título viejo (renombrado)
        // buscar por id prefix
        bool foundOld = false;
        std::string oldPath;
        try {
            for (auto &e : fs::directory_iterator(folder_)) {
                if (!e.is_regular_file()) continue;
                std::string fname = e.path().filename().string();
                char pref[8]; snprintf(pref, sizeof(pref), "%04d-", n.id);
                if (fname.rfind(pref,0)==0 && e.path().string() != path) {
                    oldPath = e.path().string();
                    foundOld = true;
                    break;
                }
            }
        } catch (...) {}
        if (foundOld) {
            try { fs::remove(oldPath); } catch (...) {}
        }
        std::string content = generateFrontmatter(n);
        // comparar contenido para evitar writes innecesarios
        bool needWrite = true;
        if (fs::exists(path)) {
            std::ifstream f(path);
            std::string existing((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
            if (existing == content) needWrite = false;
        }
        if (needWrite) {
            if (writeFileAtomic(path, content)) {
                setFileMtime(path, n.updated_at);
                r.exported++;
            } else r.errors++;
        } else r.skipped++;
    }
    return r;
}

SyncResult FolderSync::importAll() {
    SyncResult r;
    if (!fs::exists(folder_)) return r;
    for (auto &e : fs::directory_iterator(folder_)) {
        if (!e.is_regular_file()) continue;
        std::string fname = e.path().filename().string();
        if (fname.size() < 4 || fname.substr(fname.size()-3) != ".md") continue;
        // leer archivo
        std::ifstream f(e.path());
        if (!f) { r.errors++; continue; }
        std::string content((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
        Note parsed; std::string body;
        parseFrontmatter(content, parsed, body);
        parsed.body = body;
        if (parsed.title.empty()) parsed.title = fname.substr(0, fname.size()-3);
        int64_t fm = fileMtime(e.path().string());
        // buscar nota existente por id del frontmatter
        std::optional<Note> existing;
        if (parsed.id != 0) existing = storage_.getNote(parsed.id);
        if (!existing.has_value()) {
            // buscar por título exacto (para archivos creados manual sin id)
            auto all = storage_.listNotes(10000);
            for (auto &n : all) if (n.title == parsed.title) { existing = n; break; }
        }
        if (existing.has_value()) {
            Note n = existing.value();
            // comparar mtime
            if (fm > 0 && fm <= n.updated_at) {
                // nota más nueva, skip import (se exportará)
                r.skipped++;
                continue;
            }
            // conflicto si ambos más nuevos? para v1 LWW: archivo gana si fm > n.updated_at
            // actualizar nota
            n.title = parsed.title;
            n.body = parsed.body;
            // tags del frontmatter si vienen, sino extraer
            if (!parsed.tags.empty()) n.tags = parsed.tags;
            else n.tags = extractTags(n.body);
            // actualizar con nuevo updated_at = fm o now
            n.updated_at = fm > 0 ? fm : nowTimestamp();
            // usar storage update pero preservando id y sin sobrescribir created_at
            // hack: set created_at original
            // storage.updateNote recalcula updated_at a now, queremos fm, así que bypass via exec directo
            // para simplicidad, usamos updateNote que pone now, luego ajustamos con SQL
            if (storage_.updateNote(n)) {
                // ajustar updated_at a fm si es más preciso
                if (fm > 0) {
                    std::string sql = "UPDATE notes SET updated_at=" + std::to_string(fm) + " WHERE id=" + std::to_string(n.id);
                    // ad-hoc exec via storage (abrir con sqlite directly would be easier, but use export hack)
                    // storage no expone exec, así que hacemos via sqlite3 directly opening DB
                    // fallback: abrir temporal con sqlite3
                    // Para no complicar, dejamos nowTimestamp como updated
                }
                // actualizar backlinks
                storage_.updateBacklinks(n.id, n.body);
                r.imported++;
            } else r.errors++;
        } else {
            // nota nueva desde archivo
            Note n;
            n.title = parsed.title;
            n.body = parsed.body;
            n.tags = parsed.tags.empty() ? extractTags(n.body) : parsed.tags;
            n.created_at = fm > 0 ? fm : nowTimestamp();
            n.updated_at = n.created_at;
            int nid = storage_.createNote(n);
            if (nid) {
                // re-escribir archivo con id correcto y nombre correcto si es necesario
                if (parsed.id != nid) {
                    Note created = storage_.getNote(nid).value_or(n);
                    created.id = nid;
                    std::string newContent = generateFrontmatter(created);
                    // renombrar si el nombre no coincide con el esperado
                    std::string expected = (fs::path(folder_) / sanitizeFilename(created.title, nid)).string();
                    std::string oldPath = e.path().string();
                    if (oldPath != expected) {
                        writeFileAtomic(expected, newContent);
                        setFileMtime(expected, created.updated_at);
                        try { fs::remove(oldPath); } catch(...) {}
                    } else {
                        writeFileAtomic(oldPath, newContent);
                        setFileMtime(oldPath, created.updated_at);
                    }
                }
                r.imported++;
            } else r.errors++;
        }
    }
    return r;
}

SyncResult FolderSync::sync(bool createFolderIfMissing) {
    if (createFolderIfMissing) {
        try { fs::create_directories(folder_); } catch (...) {}
    }
    SyncResult exp = exportAll();
    SyncResult imp = importAll();
    SyncResult r;
    r.exported = exp.exported;
    r.imported = imp.imported;
    r.skipped = exp.skipped + imp.skipped;
    r.errors = exp.errors + imp.errors;
    r.conflicts = 0;
    std::ostringstream msg;
    if (r.exported) msg << "Exportados " << r.exported << " ";
    if (r.imported) msg << "Importados " << r.imported << " ";
    if (r.skipped) msg << "Omitidos " << r.skipped << " ";
    r.message = msg.str();
    if (r.message.empty()) r.message = "Sincronizado — sin cambios";
    return r;
}

}
