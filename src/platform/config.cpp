#include "config.h"
#include <fstream>
#include <filesystem>

namespace gnote {

std::string defaultConfigPath() {
    const char* home = getenv("HOME");
    if (!home) home="/tmp";
    std::string dir = std::string(home)+"/.config/gnote-calendar";
    std::filesystem::create_directories(dir);
    return dir + "/config.ini";
}

Config::Config(const std::string& p) : path_(p.empty()? defaultConfigPath(): p) {}

bool Config::load() {
    std::ifstream f(path_);
    if (!f) return false;
    std::string line;
    while (std::getline(f,line)) {
        if (line.empty() || line[0]=='#' || line[0]==';') continue;
        auto pos=line.find('=');
        if (pos==std::string::npos) continue;
        std::string k=line.substr(0,pos), v=line.substr(pos+1);
        // trim
        auto trim=[](std::string s){
            size_t a=0; while(a<s.size() && isspace((unsigned char)s[a])) a++;
            size_t b=s.size(); while(b>a && isspace((unsigned char)s[b-1])) b--;
            return s.substr(a,b-a);
        };
        data_[trim(k)]=trim(v);
    }
    return true;
}

bool Config::save() const {
    auto pos=path_.find_last_of('/');
    if (pos!=std::string::npos) std::filesystem::create_directories(path_.substr(0,pos));
    std::ofstream f(path_);
    if (!f) return false;
    for (auto &kv: data_) f<<kv.first<<"="<<kv.second<<"\n";
    return true;
}

std::string Config::get(const std::string& key, const std::string& def) const {
    auto it=data_.find(key);
    return it==data_.end()? def : it->second;
}
void Config::set(const std::string& key, const std::string& val){ data_[key]=val; }

}
