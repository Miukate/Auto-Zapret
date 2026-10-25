import os
import re
import subprocess
import time
import psutil
import requests
from packaging import version as pkg_version
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import zipfile
import io
import tempfile
import shutil
import ctypes
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ИСПРАВЛЕНИЕ ДЛЯ .EXE (PYINSTALLER) ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

WINWS_PROCESS = "winws.exe"
CREATE_NO_WINDOW = 0x08000000
GITHUB_API = "https://api.github.com/repos/Flowseal/zapret-discord-youtube/releases/latest"
DEFAULT_VERSION = "0.0.0"
ZAPRET_PREFIX = "zapret"

TEST_TARGETS = [
    "https://discord.com",
    "https://www.youtube.com",
    "https://www.google.com",
]

USER_LIST_FILES = [
    "list-general-user.txt",
    "list-exclude-user.txt",
    "ipset-exclude-user.txt",
]

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def _parse_version_from_name(name: str) -> str:
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", name)
    return m.group(1) if m else DEFAULT_VERSION

def list_zapret_dirs() -> list[Path]:
    if not BASE_DIR.exists():
        return []
    return [
        p for p in BASE_DIR.iterdir()
        if p.is_dir() and p.name.lower().startswith(ZAPRET_PREFIX)
    ]

def get_current_zapret_dir() -> Path | None:
    dirs = list_zapret_dirs()
    if not dirs:
        return None
    try:
        dirs.sort(
            key=lambda p: pkg_version.parse(_parse_version_from_name(p.name)),
            reverse=True,
        )
    except Exception:
        pass
    return dirs[0]

def get_local_version() -> str:
    d = get_current_zapret_dir()
    if not d:
        return DEFAULT_VERSION
    return _parse_version_from_name(d.name)

def is_zapret_installed() -> bool:
    d = get_current_zapret_dir()
    if not d:
        return False
    winws_path = d / "bin" / "winws.exe"
    return winws_path.exists() and len(find_configs()) > 0

def find_configs() -> list[Path]:
    d = get_current_zapret_dir()
    if not d:
        return []
    configs = [
        f for f in d.glob("*.bat")
        if f.name.startswith("general") and "service" not in f.name.lower()
    ]
    def sort_key(p: Path):
        return re.sub(r"(\d+)", lambda m: m.group(1).zfill(8), p.name)
    return sorted(configs, key=sort_key)

def stop_winws():
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and proc.info["name"].lower() == WINWS_PROCESS:
            try:
                proc.kill()
            except Exception:
                pass

def start_config(bat_path: Path) -> tuple[bool, str]:
    if not bat_path.exists():
        return False, f"Файл не найден: {bat_path}"

    bin_dir = bat_path.parent / "bin"
    winws_path = bin_dir / "winws.exe"
    
    if not winws_path.exists():
        return False, f"Критическая ошибка: Файл winws.exe не найден.\nАнтивирус удалил его."
        
    if not (bin_dir / "WinDivert.dll").exists() or not (bin_dir / "WinDivert64.sys").exists():
        return False, "Критическая ошибка: Отсутствуют файлы WinDivert.\nАнтивирус удалил их!"

    stop_winws()
    time.sleep(0.5)

    try:
        proc = subprocess.Popen(
            ["cmd.exe", "/c", bat_path.name],
            cwd=str(bat_path.parent),
            creationflags=CREATE_NO_WINDOW,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="cp866",
            errors="replace"
        )
    except Exception as exc:
        return False, f"Ошибка запуска cmd: {exc}"

    for i in range(30):
        time.sleep(0.5)
        if any(p.info["name"] and p.info["name"].lower() == WINWS_PROCESS
               for p in psutil.process_iter(["name"])):
            return True, bat_path.name
            
        if proc.poll() is not None:
            break

    out, err = proc.communicate()
    error_details = (out + "\n" + err).strip()
    if not error_details:
        error_details = "Консоль не выдала ошибок."
        
    return False, f"winws.exe не запустился.\nЛог:\n{error_details[:600]}"

def _check_target(url: str, timeout: float = 4.0) -> bool:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, timeout=timeout, verify=False, headers=headers)
        return r.status_code in (200, 204, 301, 302, 403)
    except Exception:
        return False

def _score_config() -> int:
    with ThreadPoolExecutor(max_workers=len(TEST_TARGETS)) as pool:
        futures = [pool.submit(_check_target, url) for url in TEST_TARGETS]
        return sum(f.result() for f in futures)

def test_all_configs(configs: list[Path], log_callback=None) -> Path | None:
    best_path = None
    best_score = -1
    for cfg in configs:
        if log_callback: log_callback(f"Тест: {cfg.name}")
        ok, msg = start_config(cfg)
        if not ok:
            if log_callback: log_callback(f"Ошибка: {msg}")
            continue
        
        time.sleep(1.5)
        score = _score_config()
        
        if log_callback: log_callback(f"Результат: {score}/{len(TEST_TARGETS)}")
        
        if score > best_score:
            best_score = score
            best_path = cfg
            
        stop_winws()
        time.sleep(0.5)
        
        if best_score == len(TEST_TARGETS):
            if log_callback: log_callback(f"Найден идеальный конфиг!")
            break
            
    return best_path

def _download_release_to(url: str, target_dir: Path, progress_cb=None) -> tuple[bool, str]:
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        buf = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                buf.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded / total * 0.7)
    except Exception as exc:
        return False, f"Ошибка скачивания: {exc}"

    buf.seek(0)
    temp_dir = Path(tempfile.mkdtemp(prefix="zapret_install_"))
    try:
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(temp_dir)
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False, f"Ошибка распаковки: {exc}"

    if progress_cb:
        progress_cb(0.85)

    items = list(temp_dir.iterdir())
    source_dir = items[0] if (len(items) == 1 and items[0].is_dir()) else temp_dir

    backup_dir = None
    if target_dir.exists():
        backup_dir = target_dir.with_name(target_dir.name + "_old")
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        target_dir.rename(backup_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        for item in source_dir.iterdir():
            dest = target_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if backup_dir and backup_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            backup_dir.rename(target_dir)
        return False, f"Ошибка копирования: {exc}"

    shutil.rmtree(temp_dir, ignore_errors=True)
    if backup_dir and backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)

    if not target_dir.exists() or not (target_dir / "bin" / "winws.exe").exists():
        return False, "Ошибка: После распаковки папка с winws.exe отсутствует.\nСкорее всего, ваш антивирус удалил файлы."

    if progress_cb:
        progress_cb(1.0)
    return True, "OK"

def install_latest_zapret(progress_cb=None) -> tuple[bool, str]:
    try:
        resp = requests.get(GITHUB_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return False, f"Не удалось получить информацию о релизе: {exc}"

    remote_ver = data.get("tag_name", "").lstrip("v")
    if not remote_ver:
        return False, "GitHub API вернул пустой tag_name."

    zip_asset = next((a for a in data.get("assets", []) if a["name"].endswith(".zip")), None)
    if not zip_asset:
        return False, "В релизе не найден zip-архив"

    target_dir = BASE_DIR / f"{ZAPRET_PREFIX} {remote_ver}"
    ok, msg = _download_release_to(zip_asset["browser_download_url"], target_dir, progress_cb)
    if not ok:
        return False, msg

    return True, f"Установлена версия {remote_ver}"

def check_for_updates() -> dict | None:
    try:
        resp = requests.get(GITHUB_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    remote_ver = data.get("tag_name", "").lstrip("v")
    if not remote_ver:
        return None

    local_ver = get_local_version()
    try:
        if pkg_version.parse(remote_ver) > pkg_version.parse(local_ver):
            zip_asset = next((a for a in data.get("assets", []) if a["name"].endswith(".zip")), None)
            if zip_asset:
                return {
                    "version": remote_ver,
                    "download_url": zip_asset["browser_download_url"],
                    "name": zip_asset["name"],
                }
    except Exception:
        pass
    return None

def update_zapret(progress_cb=None) -> tuple[bool, str]:
    info = check_for_updates()
    if not info:
        return False, "Обновлений нет"

    stop_winws()
    time.sleep(1.0)

    old_dir = get_current_zapret_dir()
    remote_ver = info["version"]
    new_dir = BASE_DIR / f"{ZAPRET_PREFIX} {remote_ver}"

    ok, msg = _download_release_to(info["download_url"], new_dir, progress_cb)
    if not ok:
        return False, msg

    if old_dir and old_dir.exists() and old_dir.resolve() != new_dir.resolve():
        old_lists = old_dir / "lists"
        new_lists = new_dir / "lists"
        new_lists.mkdir(parents=True, exist_ok=True)
        for fname in USER_LIST_FILES:
            src = old_lists / fname
            if src.exists():
                try:
                    shutil.copy2(src, new_lists / fname)
                except Exception:
                    pass
        try:
            shutil.rmtree(old_dir)
        except Exception:
            pass

    return True, f"Обновлено до версии {remote_ver}"