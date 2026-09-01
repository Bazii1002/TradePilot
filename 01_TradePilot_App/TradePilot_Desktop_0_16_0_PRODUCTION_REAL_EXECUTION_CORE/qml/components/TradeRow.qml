import QtQuick

Item {
    id: root
    property string symbol: "AAPL"
    property string company: "Apple Inc."
    property string side: "BUY"
    property string amount: "$5,320.00"
    property string shares: "20 Shares"
    property string time: "10:31:22 AM"
    property url logoSource: ""
    property bool hovered: rowMouse.containsMouse
    height: 72

    Rectangle { anchors.fill: parent; radius: 9; color: root.hovered ? "#081B2B" : "transparent"; border.width: root.hovered ? 1 : 0; border.color: "#173B56"; Behavior on color { ColorAnimation { duration: 120 } } }
    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#143149"; opacity: 0.82 }

    Rectangle {
        x: 0; y: 10; width: 46; height: 46; radius: 23
        color: "#0D2232"; border.width: 1; border.color: root.hovered ? "#35769F" : "#23465F"
        Text { anchors.centerIn: parent; visible: !logo.visible; text: root.symbol.length ? root.symbol.charAt(0) : "?"; color: "#DCE8F2"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
        Image { id: logo; anchors.fill: parent; source: root.logoSource; visible: String(root.logoSource).length > 0; fillMode: Image.PreserveAspectCrop; smooth: true; mipmap: true }
    }

    Text { x: 57; y: 10; text: root.symbol; color: "#F4F7FB"; font.pixelSize: 14; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 57; y: 34; width: 105; elide: Text.ElideRight; text: root.company; color: "#8FA2B5"; font.pixelSize: 10; font.family: "Segoe UI" }
    Rectangle { x: 158; y: 17; width: 52; height: 24; radius: 6; color: (root.side === "BUY" || root.side === "OPEN") ? "#0B352A" : "#35161D"; border.width: 1; border.color: (root.side === "BUY" || root.side === "OPEN") ? "#176B4D" : "#78303F" }
    Text { x: 158; y: 17; width: 52; height: 24; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; text: root.side; color: (root.side === "BUY" || root.side === "OPEN") ? "#2EE890" : "#FF6674"; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 220; y: 9; text: root.amount; color: "#F4F7FB"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 220; y: 34; text: root.shares; color: "#8498AB"; font.pixelSize: 9; font.family: "Segoe UI" }
    Text { anchors.right: parent.right; anchors.rightMargin: 4; y: 22; text: root.time; color: "#879AAD"; font.pixelSize: 9; font.family: "Segoe UI" }
    MouseArea { id: rowMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor }
}
