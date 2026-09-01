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

    // Soft outer halo. Restrained enough to keep the frozen TradePilot layout professional.
    Rectangle {
        visible: root.glow
        x: -5; y: -4; width: parent.width + 10; height: parent.height + 10
        radius: root.cornerRadius + 8
        color: "transparent"
        border.width: 6
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.025)
        opacity: 0.95
    }
    Rectangle {
        visible: root.glow
        x: -2; y: -2; width: parent.width + 4; height: parent.height + 4
        radius: root.cornerRadius + 3
        color: "transparent"
        border.width: 2
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.08)
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        border.width: 1
        border.color: root.borderColor
        clip: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.fillColor2 }
            GradientStop { position: 0.34; color: root.fillColor }
            GradientStop { position: 1.0; color: "#030D17" }
        }

        // Upper glass reflection.
        Rectangle {
            visible: root.ambient
            x: 1; y: 1; width: parent.width - 2; height: Math.max(52, parent.height * 0.30)
            radius: root.cornerRadius - 1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#183047" }
                GradientStop { position: 0.38; color: "#0C1E2E" }
                GradientStop { position: 1.0; color: "transparent" }
            }
            opacity: 0.24
        }

        // Tiny accent tint in the upper-right corner, visually similar to the approved mockup.
        Rectangle {
            visible: root.ambient
            anchors.right: parent.right; anchors.top: parent.top
            anchors.rightMargin: -70; anchors.topMargin: -54
            width: 260; height: 120; radius: 60
            color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.045)
        }

        Rectangle {
            x: 18; y: 1; width: parent.width - 36; height: 1
            color: "#DDF3FF"; opacity: 0.075
        }

        Rectangle {
            visible: root.glow
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.leftMargin: 18; anchors.rightMargin: 18
            height: 22
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 1.0; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.16) }
            }
        }
        Rectangle {
            visible: root.glow
            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
            anchors.leftMargin: 18; anchors.rightMargin: 18
            height: 2; radius: 1
            color: root.accentColor; opacity: 0.92
        }

        Item { id: contentLayer; anchors.fill: parent }
    }
}
