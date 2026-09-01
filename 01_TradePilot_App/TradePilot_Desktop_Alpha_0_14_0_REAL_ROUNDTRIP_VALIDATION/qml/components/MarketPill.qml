import QtQuick

Item {
    id: root
    property string market: "NYSE"
    property string stateText: "Open"
    property string subText: ""
    property bool open: true
    width: 158; height: 60

    Rectangle {
        x: -3; y: -3; width: parent.width+6; height: parent.height+6; radius: 14
        color: "transparent"; border.width: 4
        border.color: root.open ? "#07372B" : "#38131B"
        opacity: 0.52
    }
    Rectangle {
        anchors.fill: parent; radius: 11
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.open ? "#07231F" : "#1B0D15" }
            GradientStop { position: 0.52; color: root.open ? "#071A1C" : "#100F17" }
            GradientStop { position: 1.0; color: "#06131D" }
        }
        border.width: 1
        border.color: root.open ? "#118A65" : "#7C3042"

        Rectangle { x: 12; y: 13; width: 13; height: 13; radius: 7; color: root.open ? "#2FE58C" : "#FF4F63"; opacity: 0.10 }
        Rectangle {
            id: dot; x: 16; y: 17; width: 5; height: 5; radius: 3
            color: root.open ? "#35EC91" : "#FF5368"
            SequentialAnimation on opacity {
                running: root.open; loops: Animation.Infinite
                NumberAnimation { to: 0.38; duration: 900 }
                NumberAnimation { to: 1.0; duration: 900 }
            }
        }
        Text { x: 32; y: 8; text: root.market; color: "#F7FAFD"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
        Text { x: 32; y: 27; text: root.stateText; color: root.open ? "#32E58D" : "#FF6877"; font.pixelSize: 11; font.weight: Font.Medium; font.family: "Segoe UI" }
        Text {
            x: 32; y: 43; width: root.width - 42
            text: root.subText
            color: "#8498AC"; font.pixelSize: 8; font.family: "Segoe UI"
            elide: Text.ElideRight
        }
        Rectangle { x: 12; anchors.right: parent.right; anchors.rightMargin: 12; anchors.bottom: parent.bottom; height: 1; color: root.open ? "#26E28D" : "#FF5368"; opacity: 0.24 }
    }
}
