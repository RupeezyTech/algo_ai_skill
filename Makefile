SKILL_NAME := indian-algo-trading
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "dev")
BUILD_DIR := build
SKILL_FILE := $(BUILD_DIR)/$(SKILL_NAME)-$(VERSION).skill
PLUGIN_FILE := $(BUILD_DIR)/$(SKILL_NAME)-$(VERSION).plugin

# Files that go into the skill package
SKILL_FILES := SKILL.md \
	$(wildcard references/*.md) \
	$(wildcard references/brokers/rupeezy-vortex.md) \
	$(wildcard references/brokers/BROKER_TEMPLATE.md) \
	scripts/validate_strategy.py \
	scripts/scaffold_strategy.py

# Plugin adds MCP configs + plugin manifest on top of skill files
PLUGIN_EXTRA := .claude-plugin/plugin.json .claude-plugin/marketplace.json .mcp.json

.PHONY: skill plugin all clean list validate test-scaffold release

all: skill plugin

# --- Skill package (just the skill, no MCP) ---

skill: $(SKILL_FILE)
	@echo ""
	@echo "Built: $(SKILL_FILE)"
	@echo "Files: $$(unzip -l $(SKILL_FILE) | grep -c '  [0-9]') entries"
	@echo "Size:  $$(du -h $(SKILL_FILE) | cut -f1)"

$(SKILL_FILE): $(SKILL_FILES)
	@mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/references/brokers
	@mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/scripts
	cp SKILL.md $(BUILD_DIR)/$(SKILL_NAME)/
	cp references/*.md $(BUILD_DIR)/$(SKILL_NAME)/references/
	cp references/brokers/rupeezy-vortex.md $(BUILD_DIR)/$(SKILL_NAME)/references/brokers/
	cp references/brokers/BROKER_TEMPLATE.md $(BUILD_DIR)/$(SKILL_NAME)/references/brokers/
	cp scripts/validate_strategy.py $(BUILD_DIR)/$(SKILL_NAME)/scripts/
	cp scripts/scaffold_strategy.py $(BUILD_DIR)/$(SKILL_NAME)/scripts/
	@cd $(BUILD_DIR) && zip -r ../$(SKILL_FILE) $(SKILL_NAME)/
	@rm -rf $(BUILD_DIR)/$(SKILL_NAME)

# --- Plugin package (skill + MCP servers) ---

plugin: $(PLUGIN_FILE)
	@echo ""
	@echo "Built: $(PLUGIN_FILE)"
	@echo "Files: $$(unzip -l $(PLUGIN_FILE) | grep -c '  [0-9]') entries"
	@echo "Size:  $$(du -h $(PLUGIN_FILE) | cut -f1)"

$(PLUGIN_FILE): $(SKILL_FILES) $(PLUGIN_EXTRA)
	@mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/.claude-plugin
	@mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/references/brokers
	@mkdir -p $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/scripts
	cp .claude-plugin/plugin.json $(BUILD_DIR)/$(SKILL_NAME)/.claude-plugin/
	cp .claude-plugin/marketplace.json $(BUILD_DIR)/$(SKILL_NAME)/.claude-plugin/
	cp .mcp.json $(BUILD_DIR)/$(SKILL_NAME)/
	cp SKILL.md $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/
	cp references/*.md $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/references/
	cp references/brokers/rupeezy-vortex.md $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/references/brokers/
	cp references/brokers/BROKER_TEMPLATE.md $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/references/brokers/
	cp scripts/validate_strategy.py $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/scripts/
	cp scripts/scaffold_strategy.py $(BUILD_DIR)/$(SKILL_NAME)/skills/$(SKILL_NAME)/scripts/
	@cd $(BUILD_DIR) && zip -r ../$(PLUGIN_FILE) $(SKILL_NAME)/
	@rm -rf $(BUILD_DIR)/$(SKILL_NAME)

# --- Utilities ---

list:
	@echo "=== Skill contents ($(VERSION)) ==="
	@echo ""
	@for f in $(SKILL_FILES); do echo "  $$f"; done
	@echo ""
	@echo "Total: $$(echo $(SKILL_FILES) | wc -w | tr -d ' ') files"
	@echo ""
	@echo "=== Plugin adds ==="
	@echo ""
	@for f in $(PLUGIN_EXTRA); do echo "  $$f"; done
	@echo "  + skill nested under skills/$(SKILL_NAME)/"

validate:
	@echo "Validating strategy template..."
	@python3 scripts/validate_strategy.py assets/strategy_template/strategy.py
	@echo ""
	@echo "Validating broker template..."
	@python3 scripts/validate_broker_adapter.py references/brokers/BROKER_TEMPLATE.md
	@echo ""
	@echo "Validating SKILL.md frontmatter..."
	@head -1 SKILL.md | grep -q "^---" && echo "PASS: YAML frontmatter present" || echo "FAIL: Missing YAML frontmatter"
	@grep -q "^name:" SKILL.md && echo "PASS: name field present" || echo "FAIL: Missing name field"
	@grep -q "^description:" SKILL.md && echo "PASS: description field present" || echo "FAIL: Missing description field"
	@echo ""
	@echo "Validating plugin manifest..."
	@python3 -m json.tool .claude-plugin/plugin.json > /dev/null 2>&1 && echo "PASS: plugin.json valid JSON" || echo "FAIL: plugin.json invalid"
	@python3 -m json.tool .mcp.json > /dev/null 2>&1 && echo "PASS: .mcp.json valid JSON" || echo "FAIL: .mcp.json invalid"
	@python3 -m json.tool .claude-plugin/marketplace.json > /dev/null 2>&1 && echo "PASS: marketplace.json valid JSON" || echo "FAIL: marketplace.json invalid"

test-scaffold:
	@echo "Testing scaffold script..."
	@cd /tmp && python3 $(CURDIR)/scripts/scaffold_strategy.py _makefile_test --type live > /dev/null 2>&1
	@test -f /tmp/_makefile_test/main.py && echo "PASS: scaffold generates files" || echo "FAIL: scaffold broken"
	@rm -rf /tmp/_makefile_test

release: all
	@test "$(VERSION)" != "dev" || (echo "Error: no git tag found. Run: git tag -a vX.Y.Z -m 'Release vX.Y.Z'" && exit 1)
	gh release create $(VERSION) $(SKILL_FILE) $(PLUGIN_FILE) \
		--title "$(SKILL_NAME) $(VERSION)" \
		--notes-file CHANGELOG.md

clean:
	rm -rf $(BUILD_DIR)
