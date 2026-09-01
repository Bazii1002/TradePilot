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
        id: bg
        x: root.selected ? -4 : 0; y: 0
        width: parent.width + (root.selected ? 4 : 0); height: parent.height
        radius: 12
        color: root.selected ? "#0B2946" : (root.hovered ? "#071C2E" : "transparent")
        border.width: root.selected ? 1 : (root.hovered ? 1 : 0)
        border.color: root.selected ? "#2577AE" : (root.hovered ? "#173C57" : "transparent")
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on border.color { ColorAnimation { duration: 130 } }

        Rectangle {
            visible: root.selected
            width: 4; anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
            radius: 2; color: "#38AEFF"
        }
        Rectangle {
            visible: root.selected
            x: 0; y: 5; width: 23; height: parent.height-10; radius: 10
            color: "#159BFF"; opacity: 0.10
        }
        Rectangle {
            visible: root.selected
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.leftMargin: 14; anchors.rightMargin: 14; height: 1
            color: "#36AFFF"; opacity: 0.36
        }

        Image {
            x: 27; width: 24; height: 24; anchors.verticalCenter: parent.verticalCenter
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
            opacity: root.selected ? 1.0 : (root.hovered ? 0.92 : 0.72)
            scale: root.hovered ? 1.05 : 1.0
            Behavior on scale { NumberAnimation { duration: 120 } }
        }
        Text {
            x: 68; anchors.verticalCenter: parent.verticalCenter
            text: root.label
            color: root.selected ? "#F7FAFD" : (root.hovered ? "#E6EDF4" : "#C2CEDA")
            font.pixelSize: 15; font.weight: root.selected ? Font.DemiBold : Font.Normal
            font.family: "Segoe UI"
        }
    }

    MouseArea {
        id: mouse; anchors.fill: parent; hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
