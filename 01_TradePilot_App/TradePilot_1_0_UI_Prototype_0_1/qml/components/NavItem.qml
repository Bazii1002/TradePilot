import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string label: ""
    property string glyph: "◇"
    property bool selected: false
    signal clicked()
    height: 58
    radius: 12
    color: selected ? "#0c2740" : "transparent"
    border.width: selected ? 1 : 0
    border.color: "#1d4e75"

    Rectangle {
        visible: root.selected
        width: 3; radius: 2
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 8; anchors.bottomMargin: 8
        color: "#38a0ff"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 12
        spacing: 16
        Text { text: root.glyph; color: selected ? "#53adff" : "#dce6f2"; font.pixelSize: 21; Layout.preferredWidth: 22; horizontalAlignment: Text.AlignHCenter }
        Text { text: root.label; color: selected ? "#ffffff" : "#dbe5ef"; font.pixelSize: 15; Layout.fillWidth: true }
    }
    MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
