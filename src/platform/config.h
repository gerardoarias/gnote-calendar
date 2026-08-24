#pragma once
#include <string>
#include <map>

namespace gnote {

class Config {
public:
    explicit Config(const std::string& path = "");
    bool load();
    bool save() const;
    std::string get(const std::string& key, const std::string& def="") const;
    void set(const std::string& key, const std::string& val);
    std::string path() const { return path_; }
private:
    std::string path_;
    std::map<std::string,std::string> data_;
};

std::string defaultConfigPath(); // ~/.config/gnote-calendar/config.ini

}
