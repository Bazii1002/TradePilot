import QtQuick

Item {
    id: root
    property color accentColor: "#168CFF"
    property color fillColor: "#06131F"
    property color fillColor2: "#0A1927"
    property color borderColor: "#18364C"
    property real cornerRadius: 15
    property bool glow: true
    property bool ambient: true
    default property alias content: contentLayer.data

    Rectangle {
        visible: root.glow
        x: -3; y: -2; width: parent.width + 6; height: parent.height + 6
        radius: root.cornerRadius + 5
        color: "transparent"
        border.width: 4
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.018)
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        border.width: 1
        border.color: root.borderColor
        clip: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.fillColor2 }
            GradientStop { position: 0.42; color: root.fillColor }
            GradientStop { position: 1.0; color: "#04101A" }
        }

        // Restrained glass sheen: no visible circles/blobs.
        Rectangle {
            visible: root.ambient
            x: 1; y: 1; width: parent.width - 2; height: Math.max(38, parent.height * 0.26)
            radius: root.cornerRadius - 1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#102437" }
                GradientStop { position: 0.72; color: "#081724" }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.28
        }

        Rectangle {
            x: 15; y: 1; width: parent.width - 30; height: 1
            color: "#D9F0FF"; opacity: 0.045
        }

        Rectangle {
            visible: root.glow
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.leftMargin: 18; anchors.rightMargin: 18
            height: 14
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.14) }
            }
        }
        Rectangle {
            visible: root.glow
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.leftMargin: 18; anchors.rightMargin: 18
            height: 2; radius: 1
            color: root.accentColor; opacity: 0.82
        }

        Item { id: contentLayer; anchors.fill: parent }
    }
}
