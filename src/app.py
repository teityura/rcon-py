#!/usr/bin/env python3
import asyncio
import csv
import fileinput
import logging
import os
import subprocess
from datetime import datetime

import discord
from discord.ext import commands
from dotenv import load_dotenv

# base directories
SRC_DIR = os.path.dirname(__file__)
STEAM_DIR = "/home/steam"
INSTALL_DIR = f"{STEAM_DIR}/dedicated-server/palworld"

# logging settings
LOG_PATH = f"{SRC_DIR}/logs/app.log"
DEBUG_LOG_PATH = f"{SRC_DIR}/logs/debug-app.log"

# server settings
BANLIST_PATH = f"{INSTALL_DIR}/Pal/Saved/SaveGames/banlist.txt"
CONFIG_PATH = f"{INSTALL_DIR}/Pal/Saved/Config/LinuxServer/PalWorldSettings.ini"
DEFAULT_CONFIG_PATH = f"{INSTALL_DIR}/DefaultPalWorldSettings.ini"

# backup settings
SAVE_DIR = f"{INSTALL_DIR}/Pal/Saved"
BACKUP_DIR = f"{STEAM_DIR}/backup/palworld"
BACKUP_BASE_NAME = "backup-palworld"
MAX_BACKUPS = 120

# rcon settings
RCON_PATH = "/usr/local/bin/rcon"
RCON_PROFILE = "palworld"
RCON_CONFIG_PATH = f"{SRC_DIR}/config/rcon.yaml"

# discord settings
load_dotenv(f"{SRC_DIR}/config/.env")
print(f"{SRC_DIR}/config/.env")
ALLOWED_USERS = [str(id) for id in os.getenv("ALLOWED_USERS").split(",")]
ALLOWED_ROLES = [str(id) for id in os.getenv("ALLOWED_ROLES").split(",")]
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_WEBHOOK_ID = os.getenv("DISCORD_WEBHOOK_ID")

# set bot
intents = discord.Intents.default()
intents.message_content = True
help_command = commands.DefaultHelpCommand(no_category="Commands")
bot = commands.Bot(command_prefix="/", intents=intents, help_command=help_command)


def setup_file_handler(log_path, level, formatter):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def setup_stream_handler(level, formatter):
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def setup_logger(name, level, handler, propagate=True):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = propagate
    return logger


def setup_logging():
    formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{")
    # discord
    info_handler = setup_file_handler(LOG_PATH, logging.INFO, formatter)
    setup_logger("discord", logging.INFO, info_handler)
    # discord.http
    debug_handler = setup_file_handler(DEBUG_LOG_PATH, logging.DEBUG, formatter)
    setup_logger("discord.http", logging.DEBUG, debug_handler, propagate=False)
    # app.py
    stream_handler = setup_stream_handler(logging.INFO, formatter)
    file_name = os.path.basename(__file__)
    app_logger = setup_logger(file_name, logging.INFO, info_handler)
    app_logger.addHandler(stream_handler)
    return app_logger


@bot.event
async def on_ready():
    app_logger.info("[on_ready] rcon-py is ready.")


@bot.event
async def on_message(message):
    app_logger.info(f"[on_message] message.content: {message.content}")
    app_logger.info(f"[on_message] message.webhook_id: {message.webhook_id}")
    if message.webhook_id is not None:
        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
    else:
        await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        app_logger.info(f"[on_command_error] Command not found: {ctx.message.content}")
        return
    app_logger.error(f"[on_command_error] An error occurred: {error}")
    raise error


@bot.before_invoke
async def logging_command(ctx):
    app_logger.info(f"[logging_command] cmd: '{ctx.command}' args: {ctx.args[2:]}")


def is_valid_request():
    def predicate(ctx):
        if str(ctx.message.webhook_id) == str(DISCORD_WEBHOOK_ID):
            return True
        if str(ctx.author) in ALLOWED_USERS:
            return True
        if isinstance(ctx.author, discord.Member):
            if any(str(role.id) in ALLOWED_ROLES for role in ctx.author.roles):
                return True
        return False

    return commands.check(predicate)


def run_rcon_command(command, argument=None):
    command_string = command if argument is None else f"{command} {argument}"
    return subprocess.run([
        RCON_PATH, "-c", RCON_CONFIG_PATH, "-e", RCON_PROFILE, command_string
    ], capture_output=True, text=True)


@bot.command(name="info", brief="サーバーの情報を表示します")
@is_valid_request()
async def info(ctx):
    result = run_rcon_command("Info")
    if result.returncode == 0:
        await ctx.send(f":ok: Info に成功しました\n```{result.stdout}```")
    else:
        await ctx.send(f":warning: Info に失敗しました\n```stdout: {result.stdout}\nstderr: {result.stderr}```")


@bot.command(name="showplayers", brief="ログイン中のプレイヤーを表示します(name,playeruid,steamid)")
@is_valid_request()
async def show_players(ctx):
    result = run_rcon_command("ShowPlayers")
    if result.returncode == 0:
        await ctx.send(f":ok: ShowPlayers に成功しました\n```{result.stdout}```")
    else:
        await ctx.send(f":warning: ShowPlayers に失敗しました\n```stdout: {result.stdout}\nstderr: {result.stderr}```")


@bot.command(name="broadcast", brief="サーバー全体にメッセージを送信します(日本語不可)")
@is_valid_request()
async def broadcast(ctx, *, message: str):
    result = run_rcon_command(f"Broadcast {message}")
    if result.returncode == 0:
        await ctx.send(f":mega: Broadcast に成功しました\n```{result.stdout}```")
    else:
        await ctx.send(f":warning: Broadcast に失敗しました\n```stdout: {result.stdout}\nstderr: {result.stderr}```")


@bot.command(name="kickplayer", brief="プレイヤーをKickします(kickplayer <steamid>)")
@is_valid_request()
async def kick_player(ctx, steam_id: str):
    result = run_rcon_command(f"KickPlayer {steam_id}")
    if result.returncode == 0:
        await ctx.send(f":ok: KickPlayer に成功しました\n```{result.stdout}```")
    else:
        await ctx.send(
            f":warning: KickPlayer に失敗しました\n```[stdout]: {result.stdout}\n[stderr]: {result.stderr}```"
        )


@bot.command(name="banplayer", brief="プレイヤーをBanします(banplayer <steamid>)")
@is_valid_request()
async def ban_player(ctx, steam_id: str):
    result = run_rcon_command(f"BanPlayer {steam_id}")
    if result.returncode == 0:
        await ctx.send(f":construction: BanPlayer を実行します...\n```{result.stdout}```")
    else:
        await ctx.send(
            f":warning: BanPlayer に失敗しました\n```[stdout]: {result.stdout}\n[stderr]: {result.stderr}```"
        )
    await show_banlist(ctx)


@bot.command(name="banlist", brief="Banされたプレイヤーのリストを表示します")
@is_valid_request()
async def show_banlist(ctx):
    try:
        with open(BANLIST_PATH, "r") as file:
            output = file.read()
        if output:
            await ctx.send(f":closed_book: Ban されたプレイヤーリスト```\nsteamid\n{output}```")
        else:
            await ctx.send(":blue_book: Ban されているプレイヤーはいません")
    except FileNotFoundError:
        await ctx.send(":information_source: banlist.txt が見つかりませんでした(先に /banplayer を実行してください)")


@bot.command(name="unbanplayer", brief="プレイヤーのBanを解除します")
@is_valid_request()
async def unban_player(ctx, steam_id: str):
    try:
        with fileinput.FileInput(BANLIST_PATH, inplace=True) as file:
            for line in file:
                if not line.rstrip().endswith(f"steam_{steam_id}"):
                    print(line, end="")
                else:
                    app_logger.info(f"Removed line: {line.rstrip()}")
        await ctx.send(f":construction: banlist.txt から {steam_id} を削除します")
        await show_banlist(ctx)
    except FileNotFoundError:
        await ctx.send(":information_source: banlist.txt が見つかりませんでした(先に /banplayer を実行してください)")


@bot.command(name="backup", brief="サーバーのバックアップを取得します")
@is_valid_request()
async def backup(ctx):
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    result = run_rcon_command("Info")
    # Welcome to Pal Server[v0.1.4.1] Teityura's Palworld Server
    if "Welcome to" in result.stdout:
        version = result.stdout.split("[")[1].split("]")[0]
    else:
        version = "vx.x.x.x"
    # Create backup archive
    BACKUP_PATH = f"{BACKUP_DIR}/{version}_{BACKUP_BASE_NAME}_{current_time}.tar.gz"
    subprocess.run(["tar", "czf", BACKUP_PATH, "-C", SAVE_DIR, "."])
    result = subprocess.run(["ls", "-l", BACKUP_PATH], capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(f":ok: バックアップ に成功しました\n```{result.stdout}```")
        app_logger.info(f"Backup created: {BACKUP_PATH}")
    else:
        await ctx.send(f":warning: バックアップ に失敗しました\n```stdout: {result.stdout}\nstderr: {result.stderr}```")
    # Prune old backups
    backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
    old_backups = backups[MAX_BACKUPS:]
    for backup in old_backups:
        os.remove(os.path.join(BACKUP_DIR, backup))


def truncate_message(msg):
    if len(msg) >= 2000:
        lines = msg.split("\n")
        msg = ""
        for line in lines:
            if len(msg + line + "\n") > 2000:
                break
            msg += line + "\n"
        msg += "..."
    return msg


@bot.command(name="status", brief="サーバーの状態を表示します")
@is_valid_request()
async def status(ctx):
    result = subprocess.run(["systemctl", "status", "palworld"], capture_output=True, text=True)
    msg = truncate_message(result.stdout)
    await ctx.send(f"```# systemctl status palworld\n{msg}```")


@bot.command(name="restart", brief="サーバーを再起動します")
@is_valid_request()
async def restart(ctx, delay: int = 60):
    await ctx.send(
        f":muscle: {delay}秒後にサーバーを再起動します\n"
        f"The server will restart in {delay} seconds.\n"
        "Please prepare to exit the game."
    )
    await broadcast(
        ctx,
        message=f"The-server-will-restart-in-{delay}-seconds.Please-prepare-to-exit-the-game.",
    )
    await asyncio.sleep(delay)
    await ctx.send(":construction: バックアップを取得します...")
    await backup(ctx)
    await ctx.send(":construction: サーバーを再起動しています...")
    result = subprocess.run(["systemctl", "restart", "palworld"], capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(":ok: 再起動が完了しました")
    else:
        await ctx.send(":warning: 再起動が完了しませんでした")
    await status(ctx)


@bot.command(name="stop", brief="サーバーを停止します")
@is_valid_request()
async def stop(ctx, delay: int = 60):
    await ctx.send(
        f":muscle: {delay}秒後にサーバーを停止します\n"
        f"The server will stop in {delay} seconds.\n"
        "Please prepare to exit the game."
    )
    await broadcast(
        ctx,
        message=f"The-server-will-stop-in-{delay}-seconds.Please-prepare-to-exit-the-game.",
    )
    await asyncio.sleep(delay)
    await ctx.send(":construction: バックアップを取得します...")
    await backup(ctx)
    await ctx.send(":construction: サーバーを停止しています...")
    result = subprocess.run(["systemctl", "stop", "palworld"], capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(":ok: 停止が完了しました")
    else:
        await ctx.send(":warning: 停止が完了しませんでした")
    await status(ctx)


@bot.command(name="start", brief="サーバーを起動します")
@is_valid_request()
async def start(ctx, delay: int = 3):
    await ctx.send(
        f":muscle: {delay}秒後にサーバーを起動します\n"
        f"The server will start in {delay} seconds.\n"
        "Please prepare to exit the game."
    )
    await broadcast(
        ctx,
        message=f"The-server-will-start-in-{delay}-seconds.Please-prepare-to-exit-the-game.",
    )
    await asyncio.sleep(delay)
    await ctx.send(":construction: バックアップを取得します...")
    await backup(ctx)
    await ctx.send(":construction: サーバーを起動しています...")
    result = subprocess.run(["systemctl", "start", "palworld"], capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(":ok: 起動が完了しました")
    else:
        await ctx.send(":warning: 起動が完了しませんでした")
    await status(ctx)


@bot.command(name="update", brief="サーバーをアップデートします")
@is_valid_request()
async def update(ctx, delay: int = 60):
    # 告知
    await ctx.send(
        f":muscle: {delay}秒後にサーバーをアップデートします\n"
        f"The server will update in {delay} seconds.\n"
        "Please prepare to exit the game."
    )
    await asyncio.sleep(delay)
    # 停止
    await ctx.send(":construction: サーバーを停止しています...")
    result = subprocess.run(["systemctl", "stop", "palworld"], capture_output=True, text=True)
    if result.returncode == 0:
        msg_subject = ":ok: 停止が完了しました"
    else:
        msg_subject = ":warning: 停止が完了しませんでした"
    result = subprocess.run(["systemctl", "status", "palworld"], capture_output=True, text=True)
    msg_body = truncate_message(result.stdout)
    await ctx.send(f"{msg_subject}\n```# systemctl status palworld\n{msg_body}```")
    # アップデート
    await ctx.send(":construction: バックアップを取得します...")
    await backup(ctx)
    command = [
        "steamcmd",
        "+login",
        "anonymous",
        "+force_install_dir",
        INSTALL_DIR,
        "+app_update",
        "2394010",
        "validate",
        "+quit",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(":ok: サーバーのアップデートが完了しました")
    else:
        await ctx.send(":warning: サーバーのアップデートに失敗しました")
    # 起動
    await ctx.send(":construction: サーバーを起動しています...")
    result = subprocess.run(["systemctl", "start", "palworld"], capture_output=True, text=True)
    if result.returncode == 0:
        await ctx.send(":ok: 起動が完了しました")
    else:
        await ctx.send(":warning: 起動が完了しませんでした")
    await status(ctx)
    # バックアップと完了通知
    await asyncio.sleep(10)  # 起動完了し RCON が使えるようになるまで待機する
    await info(ctx)
    await ctx.send(":construction: バックアップを取得します...")
    await backup(ctx)
    await ctx.send(":tada: 全ての処理が完了しました")


def parse_settings(config_path):
    with open(os.path.expanduser(config_path), "r") as f:
        lines = f.readlines()
    option_line = next(line for line in lines if "OptionSettings=" in line)
    option_settings = option_line.split("OptionSettings=")[1].strip("()\n")
    reader = csv.reader([option_settings], delimiter=",", quotechar='"')
    settings = {}
    for option in next(reader):
        parts = option.split("=", 1)  # 最初の "=" のみで分割
        key = parts[0].strip()
        # 設定が空の場合、空文字列を入れる(ex: ServerPassword="")
        value = parts[1].strip('"') if len(parts) > 1 else ""
        settings[key] = value
    return settings


@bot.command(name="showconfig", brief="PalGameWorldSettings.ini の内容を表示します")
@is_valid_request()
async def showconfig(ctx):
    await ctx.send(":construction: PalGameWorldSettings.ini の内容を取得します...")
    default_settings = parse_settings(DEFAULT_CONFIG_PATH)
    current_settings = parse_settings(CONFIG_PATH)
    changed_settings = {key: value for key, value in current_settings.items() if default_settings.get(key) != value}
    if "AdminPassword" in changed_settings:
        changed_settings["AdminPassword"] = "****"
    rows = [[key, value] for key, value in changed_settings.items()]
    max_key_length = max(len(key) for key in changed_settings.keys())
    max_value_length = max(len(value) for value in changed_settings.values())
    msg = ""
    msg += f"{'Setting':<{max_key_length}} | {'Value':<{max_value_length}}\n"
    msg += f"{'-'*max_key_length} | {'-'*max_value_length}\n"
    for row in rows:
        msg += f"{row[0]:<{max_key_length}} | {row[1]:<{max_value_length}}\n"
    msg = truncate_message(msg)
    await ctx.send(f"```{msg}```")


if __name__ == "__main__":
    app_logger = setup_logging()
    bot.run(DISCORD_BOT_TOKEN)
