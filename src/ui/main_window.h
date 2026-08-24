#pragma once

// Este header solo se incluye si HAVE_GTKMM está definido.
// Proporciona MainWindow GTK ligera.
// Si no hay gtkmm, el build usa solo CLI.

#ifdef HAVE_GTKMM
#include <gtkmm.h>
#include "../core/storage.h"

namespace gnote {

class MainWindow : public Gtk::Window {
public:
    explicit MainWindow(Storage& storage);
    virtual ~MainWindow();

private:
    Storage& storage_;
    Gtk::Box mainBox_{Gtk::ORIENTATION_HORIZONTAL};
    Gtk::Box leftBox_{Gtk::ORIENTATION_VERTICAL};
    Gtk::Box rightBox_{Gtk::ORIENTATION_VERTICAL};
    Gtk::Calendar calendar_;
    Gtk::SearchEntry searchEntry_;
    Gtk::ScrolledWindow noteScroll_;
    Gtk::ListBox noteList_;
    Gtk::ScrolledWindow editorScroll_;
    Gtk::TextView editor_;
    Gtk::Label statusLabel_;
    Gtk::Button newNoteBtn_{"Nueva Nota"};
    Gtk::Button newEventBtn_{"Nuevo Evento"};
    Gtk::Button exportBtn_{"Exportar .ics"};
    Gtk::Button importBtn_{"Importar .ics"};

    void setupUI();
    void refreshNotes();
    void onNewNote();
    void onNewEvent();
    void onExport();
    void onImport();
    void onSearchChanged();
    void onCalendarDaySelected();
};

}
#endif
