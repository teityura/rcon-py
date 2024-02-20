# rcon-py

gorcon x discord.py bot

## Overview

This project is a Chatbot for the Palworld dedicated server.

## Project Structure

```
# tree -aI '.git|venv'
.
├── etc
│   ├── cron.d
│   │   ├── rcon-py
│   │   └── rcon-py.sample
│   └── systemd
│       └── system
│           └── rcon-py.service
├── .gitignore
├── LICENSE
├── Makefile
├── README.md
├── requirements.txt
└── src
    ├── app.py
    ├── config
    │   ├── .env
    │   ├── .env.sample
    │   ├── rcon.yaml
    │   └── rcon.yaml.sample
    ├── hook.py
    └── logs
        ├── app.log
        └── debug-app.log

7 directories, 16 files

# make venv
# ls -l venv/
total 20
drwxr-xr-x 2 root root 4096 Feb 20 11:56 bin
drwxr-xr-x 2 root root 4096 Feb 20 11:56 include
drwxr-xr-x 3 root root 4096 Feb 20 11:56 lib
lrwxrwxrwx 1 root root    3 Feb 20 11:56 lib64 -> lib
-rw-r--r-- 1 root root   70 Feb 20 11:56 pyvenv.cfg
drwxr-xr-x 3 root root 4096 Feb 20 11:56 share
```

## Usage

Set up everything with the make command.

```
make
```

Create a virtual environment in ./venv using python venv, and set up the execution environment for discord.py.

```
make venv
```

Set up the Cron job.

```
make cron
```

Set up the RCON tool.

```
make rcon
```

Start the service.

```
make start
```

## Scripts

- app.py: The main application script.
- hook.py: The script that is regularly called from the Cron job.

## Configs

- rcon.yaml: A file containing settings for RCON and the Discord bot.
- .env: This file is used to set environment variables. These environment variables can include settings that depend on the environment in which the application is run, such as database connection information or API keys.

## Cron Job Details

The cron job is scheduled to execute the hook.py script with the restart command once every day at 6:55 AM. This ensures that the script runs precisely at the specified time without any intervals.

```
55 6 * * * @@CUR_USER@@ @@CURDIR@@/venv/bin/python @@CURDIR@@/src/hook.py restart 300
```

## Cleanup

To remove all files and directories created by the Makefile, run the following command:

```
make clean
```
