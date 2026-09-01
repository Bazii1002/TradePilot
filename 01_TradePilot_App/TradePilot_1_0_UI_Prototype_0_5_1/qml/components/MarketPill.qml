import QtQuick

Item {
    id: root
    property string market: "NYSE"
    property string stateText: "Open"
    property string subText: ""
    property bool open: true
    width: 150; height: 58

    Rectangle {
        x: -3; y: -3; width: parent.width+6; height: parent.height+6; radius: 13
        color: "transparent"; border.width: 3
        border.color: root.open ? "#051d18" : "#231014"
    }
    Rectangle {
        anchors.fill: parent; radius: 11
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.open ? "#061b1b" : "#170d14" }
            GradientStop { position: 1.0; color: "#06131d" }
        }
        border.width: 1
        border.color: root.open ? "#0a7b59" : "#702b3b"

        Rectangle { x: 14; y: 16; width: 12; height: 12; radius: 6; color: root.open ? "#2fe58c" : "#ff4f63"; opacity: 0.14 }
        Rectangle { x: 17; y: 19; width: 6; height: 6; radius: 3; color: root.open ? "#35ec91" : "#ff5368" }
        Text { x: 36; y: 9; text: root.market; color: "#f4f8fc"; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: "Segoe UI" }
        Text { x: 36; y: 31; text: root.stateText; color: root.open ? "#31e48b" : "#ff6271"; font.pixelSize: 12; font.family: "Segoe UI" }
        Text { visible: root.subText.length>0; anchors.right: parent.right; anchors.rightMargin: 9; y: 32; text: root.subText; color: "#8fa2b6"; font.pixelSize: 9; font.family: "Segoe UI" }
    }
}
