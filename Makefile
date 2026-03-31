SKILL_NAME := indian-algo-trading
VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "dev")
BUILD_DIR := build
SKILL_FILE := $(BUILD_DIR)/$(SKILL_NAME)-$(VERSION).skill

# Files that go into the skill package
SKILL_FILES := SKILL.md \
	$(wildcard references/*.md) \
	$(wildcard references/brokers/rupeezy-vortex.md) \
	$(wildcard references/brokers/BROKER_TEMPLATE.md) \
	scripts/validate_strategy.py \
	scripts/scaffold_strategy.py

.PHONY: skill clean list validate test-scaffold release

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

list:
	@echo "Skill contents ($(VERSION)):"
	@echo ""
	@for f in $(SKILL_FILES); do echo "  $$f"; done
	@echo ""
	@echo "Total: $$(echo $(SKILL_FILES) | wc -w | tr -d ' ') files"

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

test-scaffold:
	@echo "Testing scaffold script..."
	@cd /tmp && python3 $(CURDIR)/scripts/scaffold_strategy.py _makefile_test --type live > /dev/null 2>&1
	@test -f /tmp/_makefile_test/main.py && echo "PASS: scaffold generates files" || echo "FAIL: scaffold broken"
	@rm -rf /tmp/_makefile_test

release: skill
	@test "$(VERSION)" != "dev" || (echo "Error: no git tag found. Run: git tag -a vX.Y.Z -m 'Release vX.Y.Z'" && exit 1)
	gh release create $(VERSION) $(SKILL_FILE) \
		--title "$(SKILL_NAME) $(VERSION)" \
		--notes-file CHANGELOG.md

clean:
	rm -rf $(BUILD_DIR)
