#ifdef HAVE_GTKMM
#include "main_window.h"
#include "../core/ical_service.h"
#include <iostream>

namespace gnote {

MainWindow::MainWindow(Storage& s) : storage_(s) {
    set_title("gnote-calendar - Notas y Calendario");
    set_default_size(1000, 600);
    setupUI();
    refreshNotes();
}

MainWindow::~MainWindow() {}

void MainWindow::setupUI() {
    add(mainBox_);
    // Left panel
    leftBox_.set_size_request(350, -1);
    leftBox_.pack_start(calendar_, Gtk::PACK_SHRINK);
    leftBox_.pack_start(searchEntry_, Gtk::PACK_SHRINK);
    searchEntry_.set_placeholder_text("Buscar notas (Ctrl+K)...");
    searchEntry_.signal_search_changed().connect(sigc::mem_fun(*this, &MainWindow::onSearchChanged));

    noteScroll_.add(noteList_);
    noteScroll_.set_policy(Gtk::POLICY_AUTOMATIC, Gtk::POLICY_AUTOMATIC);
    noteScroll_.set_vexpand(true);
    leftBox_.pack_start(noteScroll_, Gtk::PACK_EXPAND_WIDGET);

    auto* btnBox = Gtk::manage(new Gtk::Box(Gtk::ORIENTATION_HORIZONTAL));
    btnBox->pack_start(newNoteBtn_, Gtk::PACK_SHRINK);
    btnBox->pack_start(newEventBtn_, Gtk::PACK_SHRINK);
    newNoteBtn_.signal_clicked().connect(sigc::mem_fun(*this, &MainWindow::onNewNote));
    newEventBtn_.signal_clicked().connect(sigc::mem_fun(*this, &MainWindow::onNewEvent));
    leftBox_.pack_start(*btnBox, Gtk::PACK_SHRINK);

    auto* ioBox = Gtk::manage(new Gtk::Box(Gtk::ORIENTATION_HORIZONTAL));
    ioBox->pack_start(exportBtn_, Gtk::PACK_SHRINK);
    ioBox->pack_start(importBtn_, Gtk::PACK_SHRINK);
    exportBtn_.signal_clicked().connect(sigc::mem_fun(*this, &MainWindow::onExport));
    importBtn_.signal_clicked().connect(sigc::mem_fun(*this, &MainWindow::onImport));
    leftBox_.pack_start(*ioBox, Gtk::PACK_SHRINK);

    // Right panel
    editorScroll_.add(editor_);
    editorScroll_.set_policy(Gtk::POLICY_AUTOMATIC, Gtk::POLICY_AUTOMATIC);
    editor_.set_wrap_mode(Gtk::WRAP_WORD);
    rightBox_.pack_start(editorScroll_, Gtk::PACK_EXPAND_WIDGET);
    rightBox_.pack_start(statusLabel_, Gtk::PACK_SHRINK);

    mainBox_.pack_start(leftBox_, Gtk::PACK_SHRINK);
    mainBox_.pack_start(rightBox_, Gtk::PACK_EXPAND_WIDGET);

    calendar_.signal_day_selected().connect(sigc::mem_fun(*this, &MainWindow::onCalendarDaySelected));

    show_all_children();
}

void MainWindow::refreshNotes() {
    // limpiar
    auto children = noteList_.get_children();
    for (auto* c: children) noteList_.remove(*c);

    std::string q = searchEntry_.get_text();
    std::vector<Note> notes;
    if (!q.empty()) notes = storage_.searchNotes(q, 100);
    else notes = storage_.listNotes(100);

    for (auto &n: notes) {
        auto* row = Gtk::manage(new Gtk::Box(Gtk::ORIENTATION_VERTICAL));
        auto* title = Gtk::manage(new Gtk::Label(n.title));
        title->set_halign(Gtk::ALIGN_START);
        title->set_markup("<b>" + Glib::Markup::escape_text(n.title) + "</b>");
        auto* snippet = Gtk::manage(new Gtk::Label(n.body.substr(0,80)));
        snippet->set_halign(Gtk::ALIGN_START);
        snippet->set_line_wrap(true);
        snippet->set_opacity(0.7);
        row->pack_start(*title, Gtk::PACK_SHRINK);
        row->pack_start(*snippet, Gtk::PACK_SHRINK);
        row->set_border_width(6);
        auto* listRow = Gtk::manage(new Gtk::ListBoxRow());
        listRow->add(*row);
        // click -> cargar en editor
        listRow->signal_activate().connect([this, n](){
            editor_.get_buffer()->set_text(n.title + "\n\n" + n.body);
            statusLabel_.set_text("Nota #" + std::to_string(n.id) + " - " + std::to_string(n.tags.size()) + " etiquetas");
        });
        noteList_.add(*listRow);
    }
    noteList_.show_all();
    statusLabel_.set_text(std::to_string(notes.size()) + " notas");
}

void MainWindow::onNewNote() {
    Note n; n.title="Nueva nota"; n.body="Escribe aquí... Usa #tag y [[enlace]]";
    storage_.createNote(n);
    refreshNotes();
}

void MainWindow::onNewEvent() {
    guint y,m,d; calendar_.get_date(y,m,d);
    std::tm tm{}; tm.tm_year=y-1900; tm.tm_mon=m; tm.tm_mday=d; tm.tm_hour=10; tm.tm_min=0; tm.tm_isdst=-1;
    int64_t start = (int64_t)timegm(&tm);
    Event e; e.title="Nuevo evento"; e.start_ts=start; e.end_ts=start+3600;
    storage_.createEvent(e);
    statusLabel_.set_text("Evento creado: " + e.title);
}

void MainWindow::onExport() {
    Gtk::FileChooserDialog dlg(*this, "Exportar .ics", Gtk::FILE_CHOOSER_ACTION_SAVE);
    dlg.add_button("_Cancelar", Gtk::RESPONSE_CANCEL);
    dlg.add_button("_Guardar", Gtk::RESPONSE_ACCEPT);
    dlg.set_current_name("calendario.ics");
    if (dlg.run()==Gtk::RESPONSE_ACCEPT) {
        auto path = dlg.get_filename();
        auto events = storage_.listAllEvents();
        std::string err;
        if (IcalService::exportToFile(events, path, err)) statusLabel_.set_text("Exportado: "+path);
        else statusLabel_.set_text("Error export: "+err);
    }
}

void MainWindow::onImport() {
    Gtk::FileChooserDialog dlg(*this, "Importar .ics", Gtk::FILE_CHOOSER_ACTION_OPEN);
    dlg.add_button("_Cancelar", Gtk::RESPONSE_CANCEL);
    dlg.add_button("_Abrir", Gtk::RESPONSE_ACCEPT);
    auto filter = Gtk::FileFilter::create();
    filter->set_name("Calendario ICS"); filter->add_pattern("*.ics");
    dlg.add_filter(filter);
    if (dlg.run()==Gtk::RESPONSE_ACCEPT) {
        auto path = dlg.get_filename();
        std::vector<Event> imported; std::string err;
        auto res = IcalService::importFromFile(path, imported, err);
        if (!err.empty()) { statusLabel_.set_text(err); return; }
        for (auto &e: imported) storage_.createEvent(e);
        statusLabel_.set_text("Importados " + std::to_string(res.imported) + " eventos");
    }
}

void MainWindow::onSearchChanged() { refreshNotes(); }
void MainWindow::onCalendarDaySelected() {
    guint y,m,d; calendar_.get_date(y,m,d);
    auto events = storage_.listEventsForMonth(y, m+1);
    statusLabel_.set_text("Mes " + std::to_string(m+1) + "/" + std::to_string(y) + ": " + std::to_string(events.size()) + " eventos");
}

}
#endif
