CC := gcc
CXX := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -O2 -Ithird_party -Isrc
CFLAGS := -O0 -Ithird_party -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_FTS3
LDFLAGS := -lpthread -ldl

# Core sources (siempre)
CORE_SRC := src/core/utils.cpp src/core/storage.cpp src/core/ical_service.cpp src/core/search.cpp src/core/sync_service.cpp
PLATFORM_SRC := src/platform/config.cpp src/platform/notifier.cpp
APP_SRC := src/app/main.cpp
SQLITE_SRC := third_party/sqlite3.c

# GTK3 (C++) opcional
WITH_GTK ?= 0
HAVE_GTKMM := 0
ifeq ($(WITH_GTK),1)
  HAVE_GTKMM := 1
endif

ifeq ($(HAVE_GTKMM),1)
  GTK_CXX := $(shell pkg-config --cflags gtkmm-3.0)
  GTK_LD := $(shell pkg-config --libs gtkmm-3.0)
  CXXFLAGS += $(GTK_CXX) -DHAVE_GTKMM
  LDFLAGS += $(GTK_LD)
  UI_SRC := src/ui/main_window.cpp
else
  UI_SRC :=
endif

# GTK4 Python (legacy, Fase 6 depreca)
WITH_GTK4 ?= 0
HAVE_GTK4 := $(shell python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); print('1')" 2>/dev/null || echo 0)
# Qt Python (PySide6) - no requiere build C++, solo runtime
WITH_QT ?= 1
HAVE_QT := $(shell python3 -c "import PySide6" 2>/dev/null && echo 1 || (python3 -c "import PySide2" 2>/dev/null && echo 1 || (python3 -c "import PyQt5" 2>/dev/null && echo 1 || echo 0)))

BUILD_DIR := build
OBJ_DIR := $(BUILD_DIR)/obj

CORE_OBJ := $(patsubst %.cpp,$(OBJ_DIR)/%.o,$(CORE_SRC))
PLATFORM_OBJ := $(patsubst %.cpp,$(OBJ_DIR)/%.o,$(PLATFORM_SRC))
UI_OBJ := $(patsubst %.cpp,$(OBJ_DIR)/%.o,$(UI_SRC))
SQLITE_OBJ := $(OBJ_DIR)/third_party/sqlite3.o
APP_OBJ := $(OBJ_DIR)/src/app/main.o

TEST_SRC := tests/test_core.cpp
TEST_OBJ := $(OBJ_DIR)/tests/test_core.o

TARGET := $(BUILD_DIR)/gnote-calendar
TEST_TARGET := $(BUILD_DIR)/gnote-tests

all: $(TARGET) $(TEST_TARGET)

$(OBJ_DIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJ_DIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@
# sqlite3.c se compila como C
$(SQLITE_OBJ): third_party/sqlite3.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(CORE_OBJ) $(PLATFORM_OBJ) $(UI_OBJ) $(SQLITE_OBJ) $(APP_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $^ -o $@ $(LDFLAGS)
	@echo "==> Binario: $@ (GTK=$(HAVE_GTKMM))"

$(TEST_TARGET): $(CORE_OBJ) $(PLATFORM_OBJ) $(SQLITE_OBJ) $(TEST_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $^ -o $@ $(LDFLAGS)
	@echo "==> Tests: $@"

test: $(TEST_TARGET)
	$(TEST_TARGET)

clean:
	rm -rf $(BUILD_DIR)

install: $(TARGET)
	install -Dm755 $(TARGET) /usr/local/bin/gnote-calendar

help:
	@echo "Targets: all, test, clean, install"
	@echo "  make              # build CLI ligero (sin GTK) + Qt Python"
	@echo "  make WITH_GTK=1   # build con GUI GTK3 (gtkmm) legacy"
	@echo "  make WITH_QT=1    # build con GUI Qt6 C++ (opcional, default Qt Python PySide6, QT_AVAILABLE=$(HAVE_QT))"
	@echo "  make test         # ejecuta tests"

.PHONY: all test clean install help
