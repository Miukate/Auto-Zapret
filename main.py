import sys
import threading
import traceback
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

import backend

class BackendBridge(QObject):
    statusChanged = Signal()
    btnChanged = Signal()
    busyChanged = Signal()
    connectedChanged = Signal()
    versionChanged = Signal()

    def __init__(self):
        super().__init__()
        self._status_text = "Инициализация..."
        self._status_color = "#8E9CAE"
        self._btn_text = "ПОДКЛЮЧИТЬ"
        self._btn_color = "#2D3748"
        self._btn_color_dark = "#1A202C"
        self._version = "v—"
        self._is_busy = False
        self._is_connected = False
        
        self._check_initial_state()

    def _check_initial_state(self):
        try:
            if backend.is_zapret_installed():
                self._version = backend.get_local_version()
                self._status_text = "Готово к подключению"
                self._status_color = "#60A5FA"
            else:
                self._version = "—"
                self._status_text = "Zapret не установлен"
                self._status_color = "#EF4444"
                self._btn_text = "УСТАНОВИТЬ"
                self._btn_color = "#2563EB"
                self._btn_color_dark = "#1D4ED8"
        except Exception as e:
            self._status_text = f"Ошибка: {e}"
            self._status_color = "#EF4444"

    @Property(str, notify=statusChanged)
    def statusText(self): return self._status_text

    @Property(str, notify=statusChanged)
    def statusColor(self): return self._status_color

    @Property(str, notify=btnChanged)
    def btnText(self): return self._btn_text

    @Property(str, notify=btnChanged)
    def btnColor(self): return self._btn_color

    @Property(str, notify=btnChanged)
    def btnColorDark(self): return self._btn_color_dark

    @Property(str, notify=versionChanged)
    def version(self): return self._version

    @Property(bool, notify=busyChanged)
    def isBusy(self): return self._is_busy

    @Property(bool, notify=connectedChanged)
    def isConnected(self): return self._is_connected

    def set_status(self, text, color):
        self._status_text = text
        self._status_color = color
        self.statusChanged.emit()

    def set_button(self, text, color, color_dark):
        self._btn_text = text
        self._btn_color = color
        self._btn_color_dark = color_dark
        self.btnChanged.emit()

    def set_busy(self, busy):
        self._is_busy = busy
        self.busyChanged.emit()

    @Slot()
    def toggle(self):
        if self._is_busy:
            return
        if self._is_connected:
            threading.Thread(target=self._disconnect_thread, daemon=True).start()
        else:
            threading.Thread(target=self._connect_thread, daemon=True).start()

    def _disconnect_thread(self):
        try:
            self.set_busy(True)
            backend.stop_winws()
            self._is_connected = False
            self.connectedChanged.emit()
            self.set_button("ПОДКЛЮЧИТЬ", "#2D3748", "#1A202C")
            self.set_status("Отключено", "#8E9CAE")
        except Exception:
            traceback.print_exc()
        finally:
            self.set_busy(False)

    def _connect_thread(self):
        try:
            self.set_busy(True)
            
            if not backend.is_zapret_installed():
                self.set_status("Загрузка Zapret...", "#60A5FA")
                self.set_button("ЗАГРУЗКА...", "#2D3748", "#1A202C")
                ok, msg = backend.install_latest_zapret()
                if not ok:
                    self.set_status(f"Ошибка: {msg}", "#EF4444")
                    self.set_button("ОШИБКА", "#EF4444", "#B91C1C")
                    return
                self._version = backend.get_local_version()
                self.versionChanged.emit()
            
            configs = backend.find_configs()
            if not configs:
                self.set_status("Нет конфигов", "#EF4444")
                return

            self.set_status("Поиск лучшего конфига...", "#60A5FA")
            self.set_button("ТЕСТ...", "#2D3748", "#1A202C")
            
            def log_cb(msg):
                self.set_status(msg, "#8E9CAE")
                
            best = backend.test_all_configs(configs, log_callback=log_cb)
            
            if not best:
                self.set_status("Не найден рабочий конфиг", "#EF4444")
                self.set_button("ПОДКЛЮЧИТЬ", "#2D3748", "#1A202C")
                return
            
            self.set_status(f"Запуск: {best.name}", "#60A5FA")
            ok, msg = backend.start_config(best)
            
            if ok:
                self._is_connected = True
                self.connectedChanged.emit()
                self.set_button("ОТКЛЮЧИТЬ", "#2563EB", "#1D4ED8")
                self.set_status(f"Защищено: {best.name}", "#60A5FA")
            else:
                self.set_status(f"Ошибка: {msg}", "#EF4444")
                self.set_button("ОШИБКА", "#EF4444", "#B91C1C")
        except Exception as e:
            traceback.print_exc()
            self.set_status(f"Сбой: {e}", "#EF4444")
            self.set_button("ОШИБКА", "#EF4444", "#B91C1C")
        finally:
            self.set_busy(False)


# --- QML ДИЗАЙН ---
qml_code = """
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt5Compat.GraphicalEffects

Window {
    id: root
    width: 400
    height: 680
    visible: true
    title: "Auto Zapret"
    color: "#09090B"

    Item {
        anchors.fill: parent
        clip: true
        
        Rectangle {
            width: 300; height: 300; radius: 150
            x: -50; y: 50
            color: "#2563EB"
            opacity: 0.2
            SequentialAnimation on scale {
                loops: Animation.Infinite
                NumberAnimation { to: 1.2; duration: 4000; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 4000; easing.type: Easing.InOutSine }
            }
            layer.enabled: true
            layer.effect: GaussianBlur { radius: 64; samples: 16 }
        }

        Rectangle {
            width: 250; height: 250; radius: 125
            x: 200; y: 400
            color: "#7E22CE"
            opacity: 0.15
            SequentialAnimation on scale {
                loops: Animation.Infinite
                NumberAnimation { to: 1.3; duration: 5000; easing.type: Easing.InOutSine }
                NumberAnimation { to: 1.0; duration: 5000; easing.type: Easing.InOutSine }
            }
            layer.enabled: true
            layer.effect: GaussianBlur { radius: 64; samples: 16 }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.topMargin: 15
            height: 130

            Column {
                anchors.centerIn: parent
                spacing: 8
                
                Image {
                    source: iconPath
                    width: 64
                    height: 64
                    anchors.horizontalCenter: parent.horizontalCenter
                    fillMode: Image.PreserveAspectFit
                }
                
                Text {
                    text: "Auto Zapret"
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.family: "Segoe UI Variable Display", "Segoe UI"
                    font.pixelSize: 22
                    font.weight: Font.Bold
                    font.letterSpacing: 0.5
                    color: "#FAFAFA"
                }
                
                Text {
                    text: "SECURE TUNNEL"
                    anchors.horizontalCenter: parent.horizontalCenter
                    font.family: "Segoe UI Variable Text", "Segoe UI"
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.5
                    color: "#52525B"
                }
            }
        }

        Item { Layout.fillHeight: true }

        Item {
            Layout.alignment: Qt.AlignHCenter
            width: 200
            height: 200

            Rectangle {
                anchors.centerIn: parent
                width: 140; height: 140; radius: 70
                color: backendBridge.isConnected ? "#3B82F6" : "transparent"
                opacity: backendBridge.isConnected ? 0.4 : 0.0
                scale: backendBridge.isConnected ? 1.8 : 1.0
                
                Behavior on scale { NumberAnimation { duration: 1000; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: 1000 } }
                
                layer.enabled: true
                layer.effect: GaussianBlur { radius: 32; samples: 16 }
            }

            Rectangle {
                id: mainButton
                anchors.centerIn: parent
                width: 130
                height: 130
                radius: 38
                
                gradient: Gradient {
                    GradientStop { position: 0.0; color: backendBridge.btnColor }
                    GradientStop { position: 1.0; color: Qt.darker(backendBridge.btnColor, 1.5) }
                }
                
                Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuad } }

                Rectangle {
                    anchors.fill: parent
                    radius: parent.radius
                    color: "transparent"
                    border.color: "#33FFFFFF"
                    border.width: 1.5
                }

                scale: mouseArea.pressed ? 0.92 : (mouseArea.containsMouse ? 1.05 : 1.0)
                Behavior on scale { NumberAnimation { duration: 300; easing.type: Easing.OutBack } }

                Text {
                    anchors.centerIn: parent
                    text: backendBridge.btnText
                    font.family: "Segoe UI Variable Text", "Segoe UI"
                    font.pixelSize: 15
                    font.weight: Font.Bold
                    color: "#FFFFFF"
                }

                SequentialAnimation on opacity {
                    running: backendBridge.isBusy
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.5; duration: 800; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1.0; duration: 800; easing.type: Easing.InOutSine }
                }
                Behavior on opacity { enabled: !backendBridge.isBusy; NumberAnimation { duration: 200 } }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: backendBridge.toggle()
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            radius: 24
            color: "#14FFFFFF"
            border.color: "#1FFFFFFF"
            border.width: 1

            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                horizontalOffset: 0
                verticalOffset: 8
                radius: 20
                samples: 25
                color: "#80000000"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 12
                
                Rectangle {
                    width: 10; height: 10; radius: 5
                    color: backendBridge.statusColor
                    
                    SequentialAnimation on opacity {
                        running: backendBridge.isBusy
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.2; duration: 600; easing.type: Easing.InOutSine }
                        NumberAnimation { to: 1.0; duration: 600; easing.type: Easing.InOutSine }
                    }
                }

                Text {
                    text: backendBridge.statusText
                    font.family: "Segoe UI Variable Text", "Segoe UI"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    color: "#E4E4E7"
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    Behavior on color { ColorAnimation { duration: 300 } }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                
                Text {
                    text: backendBridge.version
                    font.family: "Segoe UI Variable Text", "Segoe UI"
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    color: "#52525B"
                }
                
                Item { Layout.fillWidth: true }
                
                Text {
                    text: "by Miukate"
                    font.family: "Segoe UI Variable Text", "Segoe UI"
                    font.pixelSize: 11
                    font.weight: Font.Medium
                    color: "#52525B"
                }
            }
        }
    }
}
"""

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    
    icon_file = Path("icon.png")
    icon_url = ""
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))
        icon_url = QUrl.fromLocalFile(str(icon_file.resolve())).toString()

    bridge = BackendBridge()
    
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("iconPath", icon_url)
    engine.rootContext().setContextProperty("backendBridge", bridge)
    engine.loadData(qml_code.encode('utf-8'))
    
    if not engine.rootObjects():
        sys.exit(-1)
        
    sys.exit(app.exec())