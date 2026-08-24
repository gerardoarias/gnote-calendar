cmake_minimum_required(VERSION 3.10)
project(gnote-calendar VERSION 2.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release)

# Opciones
option(WITH_GTK "Compilar con GUI GTK3" OFF)
option(WITH_GTK4 "GUI GTK4 Python (PyGObject, auto-detect)" OFF)
option(WITH_QT "GUI Qt6 C++ (Qt Widgets) - opcional, Python PySide6 por defecto" OFF)

# SQLite vendorizado (siempre)
add_library(sqlite3 STATIC third_party/sqlite3.c)
target_include_directories(sqlite3 PUBLIC third_party)
target_compile_definitions(sqlite3 PUBLIC SQLITE_ENABLE_FTS5)
target_link_libraries(sqlite3 PUBLIC pthread dl)

# Core
set(CORE_SRC
    src/core/utils.cpp
    src/core/storage.cpp
    src/core/ical_service.cpp
    src/core/search.cpp
    src/core/sync_service.cpp
)
set(PLATFORM_SRC
    src/platform/config.cpp
    src/platform/notifier.cpp
)

add_library(gnotecore STATIC ${CORE_SRC} ${PLATFORM_SRC})
target_include_directories(gnotecore PUBLIC src third_party)
target_link_libraries(gnotecore PUBLIC sqlite3)

# UI opcional
if(WITH_GTK)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(GTKMM REQUIRED gtkmm-3.0)
    add_library(gnoteui STATIC src/ui/main_window.cpp)
    target_include_directories(gnoteui PUBLIC ${GTKMM_INCLUDE_DIRS})
    target_compile_definitions(gnoteui PUBLIC HAVE_GTKMM)
    target_compile_options(gnoteui PUBLIC ${GTKMM_CFLAGS_OTHER})
    target_link_libraries(gnoteui PUBLIC gnotecore ${GTKMM_LIBRARIES})
endif()
if(WITH_QT)
    find_package(Qt6 COMPONENTS Widgets QUIET)
    if(Qt6_FOUND)
        add_library(gnoteui_qt STATIC src/ui/qt/main_window.cpp)
        target_link_libraries(gnoteui_qt PUBLIC gnotecore Qt6::Widgets)
        target_compile_definitions(gnoteui_qt PUBLIC HAVE_QT)
    else()
        message(WARNING "Qt6 no encontrado, WITH_QT ignorado - usa gui_qt.py PySide6")
    endif()
endif()

# App
add_executable(gnote-calendar src/app/main.cpp)
target_link_libraries(gnote-calendar PRIVATE gnotecore)
if(WITH_GTK)
    target_compile_definitions(gnote-calendar PRIVATE HAVE_GTKMM)
    target_include_directories(gnote-calendar PRIVATE ${GTKMM_INCLUDE_DIRS})
    target_link_libraries(gnote-calendar PRIVATE gnoteui ${GTKMM_LIBRARIES})
    target_compile_options(gnote-calendar PRIVATE ${GTKMM_CFLAGS_OTHER})
endif()

# Tests
add_executable(gnote-tests tests/test_core.cpp)
target_link_libraries(gnote-tests PRIVATE gnotecore)

# Instalación GUI Python Qt (principal) + Tk fallback + legacy GTK4
install(PROGRAMS gui_qt.py gui.py DESTINATION share/gnote-calendar)
install(PROGRAMS gui_gtk4.py DESTINATION share/gnote-calendar OPTIONAL)
install(FILES packaging/gnote-calendar.desktop packaging/gnote-calendar.svg DESTINATION share/gnote-calendar/packaging)
install(FILES requirements.txt DESTINATION share/gnote-calendar OPTIONAL)

# Instalación core
install(TARGETS gnote-calendar DESTINATION bin)
install(FILES data/schema.sql DESTINATION share/gnote-calendar)

enable_testing()
add_test(NAME core_tests COMMAND gnote-tests)
