#include "../core/storage.h"
#include "../core/ical_service.h"
#include "../core/search.h"
#include "../core/sync_service.h"
#include "../platform/config.h"
#include "../platform/notifier.h"
#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <chrono>

#ifdef HAVE_GTKMM
#include "../ui/main_window.h"
#include <gtkmm/main.h>
#endif

using namespace gnote;

void printHelp() {
    std::cout << "gnote-calendar - Gestor ligero de notas y calendario\n\n";
    std::cout << "Uso:\n";
    std::cout << "  gnote-calendar                          # inicia GUI si disponible, sino CLI\n";
    std::cout << "  gnote-calendar --help                   # ayuda\n";
    std::cout << "  gnote-calendar note list                # lista notas\n";
    std::cout << "  gnote-calendar note add \"Titulo\" \"Cuerpo #tag\"\n";
    std::cout << "  gnote-calendar note search \"texto\"\n";
    std::cout << "  gnote-calendar note show <id>\n";
    std::cout << "  gnote-calendar event list [--month YYYY-MM]\n";
    std::cout << "  gnote-calendar event add \"Titulo\" \"2026-08-24 10:00\" \"2026-08-24 11:00\" [--note 1]\n";
    std::cout << "  gnote-calendar ics export --output /tmp/cal.ics [--month YYYY-MM]\n";
    std::cout << "  gnote-calendar ics import <archivo.ics>\n";
    std::cout << "  gnote-calendar sync [--folder ~/Notas] [--watch] [--once]  # folder sync md\n";
    std::cout << "  gnote-calendar check-notify             # muestra recordatorios próximos (15min)\n";
    std::cout << "\nDB: " << defaultDbPath() << "\n";
    std::cout << "Sync folder default: " << FolderSync::defaultFolder() << " (1 .md por nota, frontmatter id/title)\n";
    std::cout << "ICS compatible Gmail: Exportar/Importar .ics desde calendar.google.com\n";
}

int main(int argc, char* argv[]) {
    std::string dbPath = defaultDbPath();
    Storage storage(dbPath);
    if (!storage.open()) {
        std::cerr << "Error abriendo DB: " << storage.lastError() << "\n";
        return 1;
    }
    storage.initSchema();

    // Sin argumentos: intenta GUI, fallback a help
    if (argc == 1) {
#ifdef HAVE_GTKMM
        auto app = Gtk::Application::create(argc, argv, "io.github.gerardoarias.gnote_calendar");
        MainWindow win(storage);
        return app->run(win);
#else
        printHelp();
        std::cout << "\n[Modo CLI] GUI no compilada (falta gtkmm). Compila con WITH_GTK=1 si quieres ventana.\n";
        std::cout << "Notas: " << storage.countNotes() << " | Eventos: " << storage.countEvents() << "\n";
        return 0;
#endif
    }

    std::string cmd = argv[1];
    if (cmd=="--help" || cmd=="-h" || cmd=="help") { printHelp(); return 0; }

    if (cmd=="note") {
        if (argc < 3) { std::cerr << "note requiere subcomando\n"; return 1; }
        std::string sub=argv[2];
        if (sub=="list") {
            auto notes = storage.listNotes(100);
            for (auto &n: notes) {
                std::cout << "#" << n.id << " [" << n.updated_at << "] " << n.title;
                if (!n.tags.empty()) { std::cout << " #"; for (auto &t:n.tags) std::cout<<t<<" "; }
                std::cout << "\n  " << n.body.substr(0,80) << (n.body.size()>80?"...":"") << "\n";
            }
        } else if (sub=="add" && argc>=4) {
            Note n; n.title=argv[3];
            if (argc>=5) n.body=argv[4];
            n.tags = extractTags(n.title+" "+n.body);
            int id = storage.createNote(n);
            if (id) std::cout << "Nota creada #" << id << "\n";
            else std::cerr << "Error: " << storage.lastError() << "\n";
        } else if (sub=="search" && argc>=4) {
            auto res = storage.searchNotes(argv[3], 50);
            for (auto &n: res) std::cout << "#" << n.id << " " << n.title << "\n";
            std::cout << res.size() << " resultados\n";
        } else if (sub=="show" && argc>=4) {
            int id=std::stoi(argv[3]);
            auto n=storage.getNote(id);
            if (n) {
                std::cout << "ID: " << n->id << "\nTítulo: " << n->title << "\nCuerpo:\n" << n->body << "\nTags: ";
                for (auto &t: n->tags) std::cout<<t<<" ";
                std::cout << "\nBacklinks: "; for (auto &b: extractBacklinks(n->body)) std::cout<<b<<" ";
                std::cout << "\nTareas: "; for (auto &t: extractTasks(n->body)) std::cout<<"\n  "<<t;
                std::cout << "\n";
            } else std::cout<<"No encontrada\n";
        } else { std::cerr<<"Subcomando note desconocido\n"; return 1; }
        return 0;
    }

    if (cmd=="event") {
        std::string sub = argc>=3 ? argv[2] : "list";
        if (sub=="list") {
            std::string month;
            for(int i=3;i<argc;i++) if(std::string(argv[i])=="--month" && i+1<argc) month=argv[++i];
            std::vector<Event> evs;
            if (!month.empty()) {
                int y=0,m=0; sscanf(month.c_str(), "%d-%d",&y,&m);
                evs = storage.listEventsForMonth(y,m);
            } else evs = storage.listAllEvents();
            for (auto &e: evs) {
                std::cout << "#" << e.id << " " << e.title << " " << timestampToISO(e.start_ts) << " -> " << timestampToISO(e.end_ts);
                if (e.note_id) std::cout << " (nota #"<<e.note_id<<")";
                std::cout << "\n";
            }
        } else if (sub=="add" && argc>=6) {
            Event e; e.title=argv[3];
            e.start_ts = isoToTimestamp(argv[4]);
            e.end_ts = isoToTimestamp(argv[5]);
            for(int i=6;i<argc;i++) if(std::string(argv[i])=="--note" && i+1<argc) e.note_id=std::stoi(argv[++i]);
            if (!e.isValid()) { std::cerr<<"Evento inválido (título/fecha)\n"; return 1; }
            int id=storage.createEvent(e);
            if (id) std::cout<<"Evento creado #"<<id<<"\n";
            else std::cerr<<"Error: "<<storage.lastError()<<"\n";
        } else { std::cerr<<"Uso: event list|add\n"; return 1; }
        return 0;
    }

    if (cmd=="ics") {
        if (argc<3) { std::cerr<<"ics requiere export|import\n"; return 1; }
        std::string sub=argv[2];
        if (sub=="export") {
            std::string out="/tmp/cal.ics"; std::string month;
            for(int i=3;i<argc;i++){
                std::string a=argv[i];
                if((a=="--output"||a=="-o")&&i+1<argc) out=argv[++i];
                if(a=="--month"&&i+1<argc) month=argv[++i];
            }
            std::vector<Event> evs;
            if(!month.empty()){ int y=0,m=0; sscanf(month.c_str(),"%d-%d",&y,&m); evs=storage.listEventsForMonth(y,m); }
            else evs=storage.listAllEvents();
            std::string err; bool ok=IcalService::exportToFile(evs,out,err);
            if(ok) std::cout<<"Exportado "<<evs.size()<<" eventos a "<<out<<"\n";
            else std::cerr<<"Error: "<<err<<"\n";
        } else if (sub=="import" && argc>=4) {
            std::string path=argv[3];
            std::vector<Event> imported; std::string err;
            auto res=IcalService::importFromFile(path, imported, err);
            if(!err.empty()){ std::cerr<<err<<"\n"; return 1; }
            int ok=0;
            for(auto &e: imported){ if(storage.createEvent(e)) ok++; else std::cerr<<"Skip dup uid "<<e.uid<<" err "<<storage.lastError()<<"\n"; }
            std::cout<<"Importados "<<ok<<"/"<<res.imported<<" eventos desde "<<path<<"\n";
        } else { std::cerr<<"ics export|import\n"; return 1; }
        return 0;
    }

    if (cmd=="sync") {
        std::string folder = FolderSync::defaultFolder();
        bool watch=false;
        for(int i=2;i<argc;i++){
            std::string a=argv[i];
            if((a=="--folder"||a=="-f")&&i+1<argc) folder=argv[++i];
            else if(a=="--watch") watch=true;
            else if(a=="--once") watch=false;
        }
        // expandir ~ ya lo hace FolderSync
        Config cfg;
        cfg.load();
        if (argc==2) {
            // sin args, usa carpeta configurada si existe
            std::string cfgFolder = cfg.get("sync_folder", "");
            if (!cfgFolder.empty()) folder = cfgFolder;
        }
        FolderSync sync(storage, folder);
        if (watch) {
            std::cout << "Watch sync en " << folder << " (Ctrl+C para salir, poll 2s)\n";
            while (true) {
                auto r = sync.sync(true);
                if (r.exported || r.imported) std::cout << "[" << timestampToISO(nowTimestamp()) << "] " << r.message << "\n";
                std::this_thread::sleep_for(std::chrono::seconds(2));
            }
        } else {
            auto r = sync.sync(true);
            std::cout << r.message << " en " << folder << "\n";
            std::cout << "Exportados: " << r.exported << " Importados: " << r.imported << " Omitidos: " << r.skipped << "\n";
            if (r.errors) std::cerr << "Errores: " << r.errors << "\n";
            // guardar carpeta en config
            cfg.set("sync_folder", folder);
            cfg.save();
        }
        return 0;
    }

    if (cmd=="check-notify") {
        auto all = storage.listAllEvents();
        auto ups = Notifier::upcoming(all, nowTimestamp(), 900);
        if (ups.empty()) std::cout<<"Sin eventos próximos (15min)\n";
        for(auto &e: ups) Notifier::notify(e);
        return 0;
    }

    std::cerr<<"Comando desconocido: "<<cmd<<"\n"; printHelp(); return 1;
}
