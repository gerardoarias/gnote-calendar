#pragma once
#include "storage.h"
#include <string>
#include <vector>

namespace gnote {

struct SyncResult {
    int exported = 0; // notas -> archivos
    int imported = 0; // archivos -> notas
    int skipped = 0;
    int conflicts = 0; // archivos más nuevos y notas más nuevas
    int errors = 0;
    std::string message;
};

class FolderSync {
public:
    FolderSync(Storage& storage, const std::string& folderPath);
    std::string folderPath() const { return folder_; }

    // Sincroniza bidireccional: exporta notas nuevas + importa archivos nuevos
    SyncResult sync(bool createFolderIfMissing = true);

    // Solo una dirección
    SyncResult exportAll();
    SyncResult importAll();

    // Helpers
    static std::string sanitizeFilename(const std::string& title, int id);
    static std::string generateFrontmatter(const Note& note);
    static bool parseFrontmatter(const std::string& content, Note& note, std::string& bodyOut);
    static int64_t fileMtime(const std::string& path);
    static bool writeFileAtomic(const std::string& path, const std::string& content);

    // Config helpers
    static std::string defaultFolder(); // ~/Notas

private:
    Storage& storage_;
    std::string folder_;
    std::string noteToFilePath(const Note& note) const;
    Note fileToNote(const std::string& path, bool& ok) const;
};

}
