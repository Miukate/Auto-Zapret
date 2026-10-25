<div align="center">
  <img src="icon.png" width="120" alt="Auto Zapret Logo">
  <h1>Auto Zapret</h1>
  <p><b>Автоматический обход DPI-блокировок для Windows с современным интерфейсом.</b></p>
  
  [![Latest Release](https://img.shields.io/github/v/release/ТВОЙ_НИК/Auto-Zapret?style=for-the-badge&color=2563EB)](../../releases/latest)
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
  [![PySide6](https://img.shields.io/badge/PySide6-QML-green?style=for-the-badge&logo=qt)](https://pypi.org/project/PySide6/)
</div>

---

## 📥 Скачать (Для обычных пользователей)
Вам не нужно быть программистом, чтобы пользоваться программой. 
1. Перейдите в раздел **[Releases (Релизы)](../../releases/latest)**.
2. Скачайте установщик **`AutoZapret_Setup.exe`**.
3. Запустите его, установите и пользуйтесь! 

*Примечание: при первом запуске обязательно разрешите программе доступ в брандмауэре и добавьте в исключения антивируса.*

---

## 💻 Для разработчиков
Программа написана на Python с использованием `PySide6` (QML) для интерфейса.

*   `main.py` — точка входа, интерфейс и связка с логикой (QML).
*   `backend.py` — скрипт скачивания Zapret, тестирования пинга и запуска конфигов.
*   `setup.iss` — скрипт сборки установщика для Inno Setup.

### Как собрать самому?
```bash
# Установка зависимостей
python -m pip install PySide6 requests psutil packaging pyinstaller

# Сборка .exe (с правами администратора)
python -m PyInstaller --noconsole --onefile --uac-admin --name="AutoZapret" --icon="icon.ico" --add-data "icon.png;." main.py
