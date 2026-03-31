SKILL_NAME := indian-algo-trading
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "dev")
BUILD_DIR := build
PLUGIN_DIR := plugins/$(SKILL_NAME)
SKILL_DIR := $(PLUGIN_DIR)/skills/$(SKILL_NAME)
SKILL_FILE := $(BUILD_DIR)/$(SKILL_NAME)-$(VERSION).skill
PLUGIN_FILE := $(BUILD_DIR)/$(SKILL_NAME)-$(VERSION).plugin

# Skill content (lives under skills/indian-algo-trading/)
SKILL_FILES := $(SKILL_DIR)/SKILL.md \
	$(wildcard $(SKILL_DIR)/references/*.md) \
	$(wildcard $(SKILL_DIR)/references/brokers/*.md) \
	$(SKILL_DIR)/scripts/validate_strategy.py \
	$(SKILL_DIR)/scripts/scaffold_strategy.py

# Plugin manifest + MCP (lives under plugins/indian-algo-trading/)
# marketplace.json stays in repo (for GitHub marketplace sync) but NOT in .plugin zip
PLUGIN_EXTRA := $(PLUGIN_DIR)/.claude-plugin/plugin.json $(PLUGIN_DIR)/.mcp.json

.PHONY: skill plugin all clean list validate test-scaffold bump release

all: skill plugin

# --- Skill package (just the skill, no MCP) ---

skill: $(SKILL_FILE)
	@echo ""
	@echo "Built: $(SKILL_FILE)"
	@echo "Files: $$(unzip -l $(SKILL_FILE) | grep -c '  [0-9]') entries"
	@echo "Size:  $$(du -h $(SKILL_FILE) | cut -f1)"

$(SKILL_FILE): $(SKILL_FILES)
	@mkdir -p $(BUILD_DIR)
	@rm -f $(SKILL_FILE)
	@cd $(SKILL_DIR) && zip -r $(CURDIR)/$(SKILL_FILE) .

# --- Plugin package (skill + MCP servers + manifest) ---
# The repo IS the plugin layout, so we cherry-pick what goes in

plugin: $(PLUGIN_FILE)
	@echo ""
	@echo "Built: $(PLUGIN_FILE)"
	@echo "Files: $$(unzip -l $(PLUGIN_FILE) | grep -c '  [0-9]') entries"
	@echo "Size:  $$(du -h $(PLUGIN_FILE) | cut -f1)"

$(PLUGIN_FILE): $(SKILL_FILES) $(PLUGIN_EXTRA)
	@rm -f $(PLUGIN_FILE)
	@rm -rf $(BUILD_DIR)/plugin-staging
	@mkdir -p $(BUILD_DIR)/plugin-staging/.claude-plugin
	@mkdir -p $(BUILD_DIR)/plugin-staging/skills/$(SKILL_NAME)/references/brokers
	# Copy SKILL.md
	cp $(SKILL_DIR)/SKILL.md $(BUILD_DIR)/plugin-staging/skills/$(SKILL_NAME)/
	# Copy references (preserve brokers/ subdirectory so SKILL.md paths work)
	cp $(SKILL_DIR)/references/*.md $(BUILD_DIR)/plugin-staging/skills/$(SKILL_NAME)/references/
	cp $(SKILL_DIR)/references/brokers/*.md $(BUILD_DIR)/plugin-staging/skills/$(SKILL_NAME)/references/brokers/
	# Copy plugin manifest + MCP
	cp $(PLUGIN_DIR)/.claude-plugin/plugin.json $(BUILD_DIR)/plugin-staging/.claude-plugin/
	cp $(PLUGIN_DIR)/.mcp.json $(BUILD_DIR)/plugin-staging/
	@cd $(BUILD_DIR)/plugin-staging && zip -r ../../$(PLUGIN_FILE) .
	@rm -rf $(BUILD_DIR)/plugin-staging

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

validate:
	@echo "Validating SKILL.md frontmatter..."
	@head -1 $(SKILL_DIR)/SKILL.md | grep -q "^---" && echo "PASS: YAML frontmatter present" || echo "FAIL: Missing YAML frontmatter"
	@grep -q "^name:" $(SKILL_DIR)/SKILL.md && echo "PASS: name field present" || echo "FAIL: Missing name field"
	@grep -q "^description:" $(SKILL_DIR)/SKILL.md && echo "PASS: description field present" || echo "FAIL: Missing description field"
	@echo ""
	@echo "Validating plugin manifest..."
	@python3 -m json.tool $(PLUGIN_DIR)/.claude-plugin/plugin.json > /dev/null 2>&1 && echo "PASS: plugin.json valid JSON" || echo "FAIL: plugin.json invalid"
	@python3 -m json.tool $(PLUGIN_DIR)/.mcp.json > /dev/null 2>&1 && echo "PASS: .mcp.json valid JSON" || echo "FAIL: .mcp.json invalid"
	@python3 -m json.tool .claude-plugin/marketplace.json > /dev/null 2>&1 && echo "PASS: marketplace.json valid JSON" || echo "FAIL: marketplace.json invalid"

test-scaffold:
	@echo "Testing scaffold script..."
	@cd /tmp && python3 $(CURDIR)/$(SKILL_DIR)/scripts/scaffold_strategy.py _makefile_test --type live > /dev/null 2>&1
	@test -f /tmp/_makefile_test/main.py && echo "PASS: scaffold generates files" || echo "FAIL: scaffold broken"
	@rm -rf /tmp/_makefile_test

bump:
	@test -n "$(NEW_VERSION)" || (echo "Usage: make bump NEW_VERSION=1.2.0" && exit 1)
	@echo "Bumping to $(NEW_VERSION)..."
	@sed -i '' 's/"version": "[^"]*"/"version": "$(NEW_VERSION)"/g' .claude-plugin/marketplace.json
	@sed -i '' 's/"version": "[^"]*"/"version": "$(NEW_VERSION)"/g' $(PLUGIN_DIR)/.claude-plugin/plugin.json
	@sed -i '' 's/^version: .*/version: $(NEW_VERSION)/' $(SKILL_DIR)/SKILL.md
	@git add .claude-plugin/marketplace.json $(PLUGIN_DIR)/.claude-plugin/plugin.json $(SKILL_DIR)/SKILL.md
	@git commit -m "chore: bump version to $(NEW_VERSION)"
	@git tag -a v$(NEW_VERSION) -m "Release v$(NEW_VERSION)"
	@echo ""
	@echo "Done. Run 'make release' to build and publish."

release: all
	@test "$(VERSION)" != "dev" || (echo "Error: no git tag found. Run: git tag -a vX.Y.Z -m 'Release vX.Y.Z'" && exit 1)
	gh release create $(VERSION) $(SKILL_FILE) $(PLUGIN_FILE) \
		--title "$(SKILL_NAME) $(VERSION)" \
		--notes-file CHANGELOG.md

clean:
	rm -rf $(BUILD_DIR)
