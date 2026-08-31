import QtQuick
import QtQuick.Layouts

GlassCard {
    id: root
    property string title: ""
    property string value: ""
    property string subtitleLeft: ""
    property string subtitleRight: ""
    property string iconText: "◈"
    property color accentColor: "#2d8cff"
    property color valueColor: "#f5f8ff"
    accent: accentColor
    accentBottom: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Text { text: root.title; color: "#f4f7fb"; font.pixelSize: 14; font.weight: Font.Medium }
            Item { Layout.fillWidth: true }
            Rectangle {
                width: 42; height: 42; radius: 10
                color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.10)
                border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.40)
                Text { anchors.centerIn: parent; text: root.iconText; color: root.accentColor; font.pixelSize: 21 }
            }
        }
        Text { text: root.value; color: root.valueColor; font.pixelSize: 28; font.weight: Font.DemiBold }
        RowLayout {
            Layout.fillWidth: true
            Text { text: root.subtitleLeft; color: "#8798ac"; font.pixelSize: 12 }
            Item { Layout.fillWidth: true }
            Text { text: root.subtitleRight; color: "#a7b4c3"; font.pixelSize: 12 }
        }
        Item { Layout.fillHeight: true }
    }
}
