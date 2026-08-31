import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string market: "NYSE"
    property string stateText: "Open"
    property string subText: ""
    property bool open: true
    width: 158
    height: 62
    radius: 13
    color: "#061725"
    border.width: 1
    border.color: open ? "#138b62" : "#8b3643"
    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 9
        Rectangle { width: 9; height: 9; radius: 5; color: open ? "#31e089" : "#ff5064" }
        ColumnLayout {
            spacing: 1
            Text { text: root.market; color: "#f7fbff"; font.pixelSize: 12; font.weight: Font.DemiBold }
            Text { text: root.stateText; color: open ? "#36e696" : "#ff6475"; font.pixelSize: 12 }
            Text { visible: root.subText !== ""; text: root.subText; color: "#8b9bae"; font.pixelSize: 9 }
        }
    }
}
