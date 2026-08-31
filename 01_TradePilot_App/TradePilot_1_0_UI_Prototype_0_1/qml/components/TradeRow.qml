import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property string ticker: "AAPL"
    property string company: "Apple Inc."
    property string side: "BUY"
    property string amount: "$2,250.00"
    property string shares: "10 Shares"
    property string time: "10:31:22 AM"
    property color badgeColor: "#ffffff"
    height: 72

    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#142e43" }
    RowLayout {
        anchors.fill: parent
        spacing: 12
        Rectangle {
            width: 42; height: 42; radius: 21; color: root.badgeColor
            Text { anchors.centerIn: parent; text: root.ticker.substring(0,1); color: "#07111b"; font.pixelSize: 18; font.weight: Font.Bold }
        }
        ColumnLayout {
            Layout.preferredWidth: 102; spacing: 2
            Text { text: root.ticker; color: "#f7f9fc"; font.pixelSize: 14; font.weight: Font.DemiBold }
            Text { text: root.company; color: "#8193a7"; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        Text { text: root.side; color: root.side === "BUY" ? "#30e28a" : "#ff5668"; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.preferredWidth: 48 }
        ColumnLayout {
            Layout.preferredWidth: 92; spacing: 2
            Text { text: root.amount; color: "#f4f7fb"; font.pixelSize: 12; font.weight: Font.Medium }
            Text { text: root.shares; color: "#8b9caf"; font.pixelSize: 10 }
        }
        Item { Layout.fillWidth: true }
        Text { text: root.time; color: "#8b9caf"; font.pixelSize: 10 }
    }
}
