#include "ical_service.h"
#include "note.h" // for isoToTimestamp
#include <fstream>
#include <sstream>
#include <ctime>
#include <algorithm>
#include <cctype>

namespace gnote {

std::string IcalService::formatIcalDate(int64_t ts) {
    std::time_t t = (std::time_t)ts;
    std::tm tm{}; gmtime_r(&t,&tm);
    char buf[32];
    strftime(buf,sizeof(buf),"%Y%m%dT%H%M%SZ",&tm);
    return buf;
}

int64_t IcalService::parseIcalDate(const std::string& s) {
    // s: 20260824T100000Z o 20260824
    if (s.empty()) return 0;
    std::string v=s;
    // trim
    v.erase(std::remove_if(v.begin(), v.end(), ::isspace), v.end());
    // remove TZID prefix not handled
    if (v.size()>=8) {
        int y,m,d,H=0,M=0,S=0;
        if (v.find('T')!=std::string::npos) {
            if (sscanf(v.c_str(), "%4d%2d%2dT%2d%2d%2d", &y,&m,&d,&H,&M,&S)>=3) {
                std::tm tm{}; tm.tm_year=y-1900; tm.tm_mon=m-1; tm.tm_mday=d;
                tm.tm_hour=H; tm.tm_min=M; tm.tm_sec=S; tm.tm_isdst=-1;
                return (int64_t)timegm(&tm);
            }
        } else {
            if (sscanf(v.c_str(), "%4d%2d%2d", &y,&m,&d)==3) {
                std::tm tm{}; tm.tm_year=y-1900; tm.tm_mon=m-1; tm.tm_mday=d;
                tm.tm_hour=0; tm.tm_min=0; tm.tm_sec=0; tm.tm_isdst=-1;
                return (int64_t)timegm(&tm);
            }
        }
    }
    // fallback intentar iso
    return isoToTimestamp(v);
}

std::string IcalService::exportToString(const std::vector<Event>& events) {
    std::ostringstream out;
    out << "BEGIN:VCALENDAR\r\n";
    out << "VERSION:2.0\r\n";
    out << "PRODID:-//gnote-calendar//ES\r\n";
    out << "CALSCALE:GREGORIAN\r\n";
    for (auto &e: events) {
        out << "BEGIN:VEVENT\r\n";
        out << "UID:" << (e.uid.empty() ? generateUid() : e.uid) << "\r\n";
        out << "DTSTAMP:" << formatIcalDate(e.created_at ? e.created_at : nowTimestamp()) << "\r\n";
        out << "DTSTART:" << formatIcalDate(e.start_ts) << "\r\n";
        out << "DTEND:" << formatIcalDate(e.end_ts) << "\r\n";
        // escapar comas y saltos en SUMMARY/DESCRIPTION
        auto esc = [](std::string s){
            std::string r; for(char c: s){ if(c=='\n') r+="\\n"; else if(c==','||c==';') {r+='\\'; r+=c;} else r+=c; } return r;
        };
        out << "SUMMARY:" << esc(e.title) << "\r\n";
        if (!e.description.empty()) out << "DESCRIPTION:" << esc(e.description) << "\r\n";
        if (!e.location.empty()) out << "LOCATION:" << esc(e.location) << "\r\n";
        if (!e.rrule.empty()) out << "RRULE:" << e.rrule << "\r\n";
        out << "END:VEVENT\r\n";
    }
    out << "END:VCALENDAR\r\n";
    return out.str();
}

bool IcalService::exportToFile(const std::vector<Event>& events, const std::string& path, std::string& err) {
    std::string content = exportToString(events);
    std::ofstream f(path, std::ios::binary);
    if (!f) { err="No se pudo abrir archivo para escritura: "+path; return false; }
    f << content;
    return true;
}

static std::string unfoldIcal(const std::string& content) {
    // líneas plegadas: "\r\n " -> ""
    std::string out; out.reserve(content.size());
    for (size_t i=0;i<content.size();++i) {
        if (content[i]=='\r' && i+1<content.size() && content[i+1]=='\n') {
            if (i+2<content.size() && (content[i+2]==' ' || content[i+2]=='\t')) {
                i+=2; continue; // saltar CRLF + espacio
            }
        }
        out.push_back(content[i]);
    }
    return out;
}

static std::string trim(const std::string& s) {
    size_t a=0; while(a<s.size() && isspace((unsigned char)s[a])) a++;
    size_t b=s.size(); while(b>a && isspace((unsigned char)s[b-1])) b--;
    return s.substr(a,b-a);
}

IcalResult IcalService::importFromString(const std::string& content, std::vector<Event>& out) {
    IcalResult res;
    std::string unfolded = unfoldIcal(content);
    std::istringstream ss(unfolded);
    std::string line;
    Event cur; bool inEvent=false;
    while (std::getline(ss, line)) {
        // remover \r
        if (!line.empty() && line.back()=='\r') line.pop_back();
        if (line=="BEGIN:VEVENT") { cur=Event(); cur.source="imported_ics"; cur.created_at=nowTimestamp(); inEvent=true; continue; }
        if (line=="END:VEVENT" && inEvent) {
            if (cur.title.empty()) cur.title="(Sin título)";
            if (cur.start_ts && cur.end_ts) {
                if (cur.uid.empty()) cur.uid=generateUid();
                out.push_back(cur);
                res.imported++;
            } else { res.errors++; }
            inEvent=false; continue;
        }
        if (!inEvent) continue;
        auto pos=line.find(':');
        if (pos==std::string::npos) continue;
        std::string key=line.substr(0,pos);
        std::string val=line.substr(pos+1);
        // key puede tener parámetros: DTSTART;TZID=... -> extraer key base
        auto semi=key.find(';'); if (semi!=std::string::npos) key=key.substr(0,semi);
        // unescape
        // reemplazar \n -> \n real, \, -> ,
        std::string unesc; for(size_t i=0;i<val.size();++i){ if(val[i]=='\\' && i+1<val.size()){ if(val[i+1]=='n' || val[i+1]=='N'){unesc+='\n'; i++;} else if(val[i+1]==','||val[i+1]==';'||val[i+1]=='\\'){unesc+=val[i+1]; i++;} else unesc+=val[i]; } else unesc+=val[i]; }
        val=unesc;
        if (key=="SUMMARY") cur.title=val;
        else if (key=="DESCRIPTION") cur.description=val;
        else if (key=="LOCATION") cur.location=val;
        else if (key=="UID") cur.uid=val;
        else if (key=="DTSTART") cur.start_ts=parseIcalDate(val);
        else if (key=="DTEND") cur.end_ts=parseIcalDate(val);
        else if (key=="RRULE") cur.rrule=val;
        else if (key=="DTSTAMP") { /* ignorar */ }
    }
    // Si evento sin DTEND pero con duración 1h por defecto
    for (auto &e: out) if (e.end_ts==0 && e.start_ts) e.end_ts=e.start_ts+3600;
    return res;
}

IcalResult IcalService::importFromFile(const std::string& path, std::vector<Event>& out, std::string& err) {
    std::ifstream f(path, std::ios::binary);
    if (!f) { err="No se pudo abrir archivo: "+path; return {}; }
    std::ostringstream ss; ss<<f.rdbuf();
    return importFromString(ss.str(), out);
}

}
