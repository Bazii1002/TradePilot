import QtQuick

Item {
    id: root
    property string label: "Dashboard"
    property url iconSource: ""
    property bool selected: false
    property bool hovered: mouse.containsMouse
    signal clicked()
    height: 55

    Rectangle {
        x: root.selected ? -4 : 0; y: 0
        width: parent.width + (root.selected ? 4 : 0); height: parent.height
        radius: 12
        color: root.selected ? "#0A2137" : (root.hovered ? "#071A2B" : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? "#1D5277" : "transparent"

        Rectangle {
            visible: root.selected
            width: 4; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
            radius: 2; color: "#3AAEFF"
        }
        Rectangle {
            visible: root.selected
            x: 0; y: 7; width: 15; height: parent.height-14; radius: 7
            color: "#1997FF"; opacity: 0.07
        }

        Image {
            x: 27; width: 24; height: 24; anchors.verticalCenter: parent.verticalCenter
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            opacity: root.selected ? 1.0 : 0.78
        }
        Text {
            x: 68; anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: root.selected ? "#F5F8FC" : "#D0D9E3"
            font.pixelSize: 15; font.weight: root.selected ? Font.Medium : Font.Normal
            font.family: "Segoe UI"
        }
    }

    MouseArea {
        id: mouse; anchors.fill: parent; hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
