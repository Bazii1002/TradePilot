import QtQuick

Rectangle {
    id: root
    property string label: "Metric"
    property string value: "—"
    property string detail: ""
    property color accentColor: "#2aa8ff"
    radius: 9
    color: "#071827"
    border.width: 1
    border.color: "#173a54"

    Rectangle { x: 0; y: 0; width: 3; height: parent.height; radius: 2; color: root.accentColor }
    Text { x: 14; y: 9; text: root.label; color: "#71879b"; font.pixelSize: 9; font.family: "Segoe UI"; font.weight: Font.DemiBold }
    Text { x: 14; y: 27; text: root.value; color: "#f4f7fb"; font.pixelSize: 17; font.family: "Segoe UI"; font.weight: Font.DemiBold }
    Text { anchors.right: parent.right; anchors.rightMargin: 10; y: 31; text: root.detail; color: root.accentColor; font.pixelSize: 8; font.family: "Segoe UI" }
}
