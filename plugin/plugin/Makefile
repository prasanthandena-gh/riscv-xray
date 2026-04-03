# plugin/Makefile - Build the QEMU TCG plugin

CC      ?= gcc

# Prefer real QEMU source header over bundled one.
# Override with: QEMU_INCLUDE=/path/to/qemu/include/qemu make plugin
QEMU_INCLUDE ?= $(HOME)/qemu-8.2.2/include/qemu
ifeq ($(wildcard $(QEMU_INCLUDE)/qemu-plugin.h),)
    QEMU_INCLUDE := .
endif

CFLAGS  := -shared -fPIC -O2 -Wall -I$(QEMU_INCLUDE)
LDFLAGS :=

TARGET  := xray_plugin.so
SRC     := xray_plugin.c

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SRC) qemu-plugin.h
	@echo "Building QEMU plugin..."
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)
	@echo "Built: $(TARGET)"

clean:
	rm -f $(TARGET)
