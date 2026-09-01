import QtQuick

Item {
    id: root
    property string symbol: "AAPL"
    property string company: "Apple Inc."
    property string side: "BUY"
    property string amount: "$5,320.00"
    property string shares: "20 Shares"
    property string time: "10:31:22 AM"
    property string logoSource: ""
    height: 72

    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#143149"; opacity: 0.82 }

    Image {
        x: 0; y: 10; width: 46; height: 46
        source: root.logoSource
        fillMode: Image.PreserveAspectCrop
        smooth: true; mipmap: true
    }

    Text { x: 57; y: 10; text: root.symbol; color: "#F4F7FB"; font.pixelSize: 14; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 57; y: 34; width: 105; elide: Text.ElideRight; text: root.company; color: "#8FA2B5"; font.pixelSize: 10; font.family: "Segoe UI" }
    Text { x: 164; y: 20; text: root.side; color: root.side === "BUY" ? "#2EE890" : "#FF5666"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 220; y: 9; text: root.amount; color: "#F4F7FB"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 220; y: 34; text: root.shares; color: "#8498AB"; font.pixelSize: 9; font.family: "Segoe UI" }
    Text { anchors.right: parent.right; anchors.rightMargin: 1; y: 22; text: root.time; color: "#879AAD"; font.pixelSize: 9; font.family: "Segoe UI" }
}
