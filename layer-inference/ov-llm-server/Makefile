PREFIX ?= $(HOME)/.local
BIN_DIR := $(PREFIX)/bin

.PHONY: install

install:
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(CURDIR)/scripts/ov-convert-model" "$(BIN_DIR)/ov-convert-model"
	@ln -sf "$(CURDIR)/scripts/ov-warm-models" "$(BIN_DIR)/ov-warm-models"
	@echo "Installed ov-convert-model to $(BIN_DIR)"
	@echo "Installed ov-warm-models to $(BIN_DIR)"
