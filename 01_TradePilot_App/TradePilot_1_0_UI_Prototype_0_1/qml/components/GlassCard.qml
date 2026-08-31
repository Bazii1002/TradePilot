import QtQuick

Rectangle {
    id: root
    property color accent: "#2d8cff"
    property bool accentBottom: false
    radius: 16
    color: "#071827"
    border.width: 1
    border.color: "#173750"

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: root.accentBottom ? 2 : 0
        radius: 1
        color: root.accent
        opacity: 0.95
    }
}
