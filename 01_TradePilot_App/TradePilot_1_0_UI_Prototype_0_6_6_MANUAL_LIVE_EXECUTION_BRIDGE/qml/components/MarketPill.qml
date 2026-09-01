import QtQuick

Item {
    id: root
    property string market: "NYSE"
    property string stateText: "Open"
    property string subText: ""
    property bool open: true
    width: 158; height: 60

    Rectangle {
        x: -2; y: -2; width: parent.width+4; height: parent.height+4; radius: 13
        color: "transparent"; border.width: 2
        border.color: root.open ? "#06251d" : "#2a1117"
    }
    Rectangle {
        anchors.fill: parent; radius: 11
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.open ? "#061b1b" : "#170d14" }
            GradientStop { position: 1.0; color: "#06131d" }
        }
        border.width: 1
        border.color: root.open ? "#0a7b59" : "#702b3b"

        Rectangle { x: 13; y: 14; width: 11; height: 11; radius: 6; color: root.open ? "#2fe58c" : "#ff4f63"; opacity: 0.14 }
        Rectangle { x: 16; y: 17; width: 5; height: 5; radius: 3; color: root.open ? "#35ec91" : "#ff5368" }
        Text { x: 32; y: 8; text: root.market; color: "#f4f8fc"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
        Text { x: 32; y: 27; text: root.stateText; color: root.open ? "#31e48b" : "#ff6271"; font.pixelSize: 11; font.family: "Segoe UI" }
        Text {
            x: 32; y: 43; width: root.width - 42
            text: root.subText
            color: "#8498ac"; font.pixelSize: 8; font.family: "Segoe UI"
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
        }
    }
}
