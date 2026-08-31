import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string tag: "NEWS"
    property string title: "News-Anbindung vorbereitet"
    property string body: "Marktnachrichten werden später live geladen."
    property string meta: "—"
    height: 66
    radius: 10
    color: "#081d2e"
    border.width: 1
    border.color: "#163a56"
    RowLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10
        Rectangle {
            width: 48; height: 42; radius: 8; color: "#0a3153"
            Text { anchors.centerIn: parent; text: root.tag; color: "#55aaff"; font.pixelSize: 10; font.weight: Font.Bold }
        }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 2
            Text { text: root.title; color: "#f5f8fb"; font.pixelSize: 11; font.weight: Font.Medium; elide: Text.ElideRight; Layout.fillWidth: true }
            Text { text: root.body; color: "#8598ad"; font.pixelSize: 10; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        Text { text: root.meta; color: root.meta === "live" ? "#35df8a" : "#8194aa"; font.pixelSize: 10 }
    }
}
