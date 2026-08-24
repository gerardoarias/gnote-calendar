#include "../src/core/storage.h"
#include "../src/core/ical_service.h"
#include "../src/core/search.h"
#include <cassert>
#include <iostream>
#include <filesystem>

using namespace gnote;

void test_notes() {
    std::string db="/tmp/test_gnote_notes.db";
    std::filesystem::remove(db);
    Storage s(db); assert(s.open()); assert(s.initSchema());
    Note n; n.title="Reunión #trabajo"; n.body="Ver [[Proyecto X]] y - [ ] tarea pendiente";
    int id=s.createNote(n); assert(id!=0);
    auto got=s.getNote(id); assert(got.has_value()); assert(got->title=="Reunión #trabajo");
    assert(!got->tags.empty());
    auto list=s.listNotes(); assert(list.size()==1);
    auto search=s.searchNotes("Reunión",10); assert(search.size()==1);
    auto search2=s.searchNotes("inexistente",10); assert(search2.empty());
    // backlinks
    auto links=extractBacklinks(got->body); assert(!links.empty() && links[0]=="Proyecto X");
    s.deleteNote(id); assert(!s.getNote(id).has_value());
    std::filesystem::remove(db);
    std::cout << "[PASS] test_notes\n";
}

void test_events() {
    std::string db="/tmp/test_gnote_events.db";
    std::filesystem::remove(db);
    Storage s(db); assert(s.open()); assert(s.initSchema());
    Event e; e.title="Evento test"; e.start_ts=nowTimestamp()+3600; e.end_ts=e.start_ts+3600;
    int id=s.createEvent(e); assert(id!=0);
    auto got=s.getEvent(id); assert(got.has_value());
    auto all=s.listAllEvents(); assert(all.size()==1);
    // mes
    std::time_t t=(std::time_t)e.start_ts; std::tm tm{}; gmtime_r(&t,&tm);
    auto month=s.listEventsForMonth(tm.tm_year+1900, tm.tm_mon+1); assert(!month.empty());
    s.deleteEvent(id); assert(s.listAllEvents().empty());
    std::filesystem::remove(db);
    std::cout << "[PASS] test_events\n";
}

void test_ical() {
    Event e; e.title="Reunión Gmail"; e.description="Desc\ncon coma, y punto y coma;"; e.start_ts=isoToTimestamp("2026-08-24 10:00"); e.end_ts=isoToTimestamp("2026-08-24 11:00"); e.location="Oficina"; e.uid="test-uid@gtest";
    std::string ics = IcalService::exportToString({e});
    assert(ics.find("BEGIN:VCALENDAR")!=std::string::npos);
    assert(ics.find("SUMMARY:Reunión Gmail")!=std::string::npos);
    std::vector<Event> out; auto res=IcalService::importFromString(ics, out);
    assert(res.imported==1); assert(out[0].title=="Reunión Gmail"); assert(out[0].start_ts==e.start_ts);
    // archivo
    std::string err; assert(IcalService::exportToFile({e}, "/tmp/test_export.ics", err));
    std::vector<Event> out2; std::string err2; auto res2=IcalService::importFromFile("/tmp/test_export.ics", out2, err2);
    assert(res2.imported==1); assert(err2.empty());
    std::filesystem::remove("/tmp/test_export.ics");
    std::cout << "[PASS] test_ical (Gmail compatible)\n";
}

void test_search() {
    Note n; n.title="Compra"; n.body="Leche #casa"; n.tags={"casa"};
    SearchQuery q=parseQuery("tag:casa leche");
    assert(q.tag=="casa" && q.text=="leche");
    assert(noteMatches(n,q));
    q=parseQuery("tag:trabajo");
    assert(!noteMatches(n,q));
    std::cout << "[PASS] test_search\n";
}

void test_link_note_event() {
    std::string db="/tmp/test_gnote_link.db";
    std::filesystem::remove(db);
    Storage s(db); assert(s.open()); assert(s.initSchema());
    Note n; n.title="Nota vinculada"; n.body="contenido"; int nid=s.createNote(n);
    Event e; e.title="Evento vinculado"; e.start_ts=nowTimestamp()+100; e.end_ts=e.start_ts+100; e.note_id=nid;
    int eid=s.createEvent(e); assert(eid!=0);
    auto ge=s.getEvent(eid); assert(ge->note_id==nid);
    std::filesystem::remove(db);
    std::cout << "[PASS] test_link_note_event\n";
}

int main() {
    test_notes();
    test_events();
    test_ical();
    test_search();
    test_link_note_event();
    std::cout << "\n=== TODOS LOS TESTS PASARON ===\n";
    return 0;
}
