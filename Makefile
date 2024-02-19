.PHONY: all venv unit rcon clean

CUR_USER := $(shell id -un)
UNIT_PATH := /etc/systemd/system/rcon-py.service
CRON_PATH := /etc/cron.d/rcon-py
RCON_PATH := /usr/local/bin/rcon

all: venv unit cron rcon start

venv:
	@if [ ! -d venv ]; then \
		echo "[venv] initializing ..."; \
		python3 -m venv venv; \
		. venv/bin/activate; \
		pip install -r requirements.txt; \
		ls -al venv/; \
	else \
		echo "[venv] already initialized."; \
		ls -al venv/; \
	fi

unit:
	@if [ ! -f $(UNIT_PATH) ]; then \
		echo "[unit] creating ..."; \
		cp etc/systemd/system/rcon-py.service $(UNIT_PATH); \
		sed -i 's|@@CURDIR@@|$(CURDIR)|g' $(UNIT_PATH); \
		sed -i 's|@@CUR_USER@@|$(CUR_USER)|g' $(UNIT_PATH); \
		systemctl daemon-reload; \
		ls -l $(UNIT_PATH); \
	else \
		echo "[unit] already created."; \
		ls -l $(UNIT_PATH); \
	fi

cron:
	@if [ -f "$(CURDIR)/etc/cron.d/rcon-py" ] && [ ! -f $(CRON_PATH) ]; then \
		echo "[cron] creating ..."; \
		cp "$(CURDIR)/etc/cron.d/rcon-py" $(CRON_PATH); \
		sed -i 's|@@CURDIR@@|$(CURDIR)|g' $(CRON_PATH); \
		sed -i 's|@@CUR_USER@@|$(CUR_USER)|g' $(CRON_PATH); \
		ls -l $(CRON_PATH); \
	elif [ -f $(CRON_PATH) ]; then \
		echo "[cron] already created."; \
		ls -l $(CRON_PATH); \
	else \
		echo "[cron] not exists."; \
	fi

rcon:
	@if [ ! -f $(RCON_PATH) ]; then \
		echo "[rcon] installing ..."; \
		mkdir -p tmp; \
		curl -o tmp/rcon.tar.gz -sLO https://github.com/gorcon/rcon-cli/releases/download/v0.10.3/rcon-0.10.3-amd64_linux.tar.gz; \
		tar -xzf tmp/rcon.tar.gz -C tmp --strip-components=1 --no-same-owner; \
		chmod +x tmp/rcon; \
		mv tmp/rcon $(RCON_PATH); \
		rm -rf tmp; \
		ls -l $(RCON_PATH); \
	else \
		echo "[rcon] already installed."; \
		ls -l $(RCON_PATH); \
	fi

start: venv unit rcon
	systemctl is-active --quiet rcon-py || systemctl start rcon-py
	systemctl status rcon-py

clean:
	systemctl is-active --quiet rcon-py && systemctl stop rcon-py || true
	test -d venv && rm -rf venv || true
	test -f $(UNIT_PATH) && rm -f $(UNIT_PATH) || true
	test -f $(CRON_PATH) && rm -f $(CRON_PATH) || true
	test -f $(RCON_PATH) && rm -f $(RCON_PATH) || true
