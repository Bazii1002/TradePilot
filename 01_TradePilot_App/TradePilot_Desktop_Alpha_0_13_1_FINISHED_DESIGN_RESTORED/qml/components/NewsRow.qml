import QtQuick

Item {
    id: root
    property string badge: "FED"
    property string titleText: "Fed Minutes Show Caution on Rate Cuts"
    property string subtitle: "Officials emphasize data dependency amid persistent inflation risks."
    property string timeText: "8m ago"
    property url imageSource: ""
    property color badgeColor: "#1c62a5"
    height: 68

    Rectangle {
        x: 0; y: 7; width: 78; height: 54; radius: 8
        color: "#10283b"; border.width: 1; border.color: "#24465f"; clip: true
        Image { anchors.fill: parent; source: root.imageSource; fillMode: Image.PreserveAspectCrop; smooth: true; mipmap: true }
        Rectangle { anchors.fill: parent; color: "#04101a"; opacity: 0.10 }
    }
    Text { x: 91; y: 7; width: 277; elide: Text.ElideRight; text: root.titleText; color: "#f3f7fb"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 91; y: 28; width: 278; height: 30; wrapMode: Text.WordWrap; text: root.subtitle; color: "#9eafbf"; font.pixelSize: 9; font.family: "Segoe UI"; lineHeight: 1.05 }
    Rectangle {
        anchors.right: parent.right; anchors.rightMargin: 0; y: 7
        width: badge === "NASDAQ" ? 69 : (badge === "EUROPE" ? 64 : 52); height: 23; radius: 6
        color: root.badgeColor; border.width: 1; border.color: Qt.lighter(root.badgeColor,1.18)
        Text { anchors.centerIn: parent; text: root.badge; color: "#e5f2ff"; font.pixelSize: 9; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    }
    Text { anchors.right: parent.right; anchors.rightMargin: 0; y: 41; text: root.timeText; color: "#8599ad"; font.pixelSize: 9; font.family: "Segoe UI" }
    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#143149"; opacity: 0.86 }
}
