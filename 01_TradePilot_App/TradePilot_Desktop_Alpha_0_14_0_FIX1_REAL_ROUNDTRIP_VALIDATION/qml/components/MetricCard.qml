import QtQuick

NeonCard {
    id: root
    property string title: "Cash Available"
    property string value: "$18,742.63"
    property string subtitleLeft: "Buying Power"
    property string subtitleRight: "$18,742.63"
    property url iconSource: ""
    property color valueColor: "#F5F8FC"
    property bool sparkline: false
    property bool hovered: cardMouse.containsMouse
    signal clicked()

    borderColor: hovered ? Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.58) : "#18364C"

    Text { x: 24; y: 22; text: root.title; color: "#EAF1F7"; font.pixelSize: 16; font.weight: Font.Medium; font.family: "Segoe UI" }

    Rectangle {
        x: parent.width - 73; y: 14; width: 56; height: 56; radius: 15
        color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.035)
    }
    Rectangle {
        width: 48; height: 48
        anchors.right: parent.right; anchors.rightMargin: 21
        y: 18; radius: 12
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.15) }
            GradientStop { position: 1.0; color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.055) }
        }
        border.width: 1
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.42)
        Image { anchors.centerIn: parent; width: 26; height: 26; source: root.iconSource; fillMode: Image.PreserveAspectFit; smooth: true }
    }

    Text { x: 24; y: 69; text: root.value; color: root.valueColor; font.pixelSize: 31; font.weight: Font.DemiBold; font.family: "Segoe UI" }
    Text { x: 24; y: 132; text: root.subtitleLeft; color: root.valueColor === "#35DF8B" ? "#31DC87" : "#8EA2B5"; font.pixelSize: 12; font.family: "Segoe UI" }
    Text { anchors.right: parent.right; anchors.rightMargin: 24; y: 132; text: root.subtitleRight; color: "#C4D0DB"; font.pixelSize: 12; font.family: "Segoe UI" }

    Canvas {
        visible: root.sparkline
        x: 178; y: 103; width: 136; height: 52
        property var pts: [0.12,0.18,0.23,0.20,0.29,0.34,0.31,0.40,0.46,0.43,0.52,0.49,0.57,0.61,0.58,0.66,0.72,0.68,0.79,0.76,0.84,0.89,0.86,0.95]
        onPaint: {
            var c=getContext("2d"); c.reset();
            var grad=c.createLinearGradient(0,0,0,height); grad.addColorStop(0,"rgba(46,225,137,0.28)"); grad.addColorStop(1,"rgba(46,225,137,0)");
            c.beginPath();
            for(var i=0;i<pts.length;i++) { var xx=i*(width-2)/(pts.length-1); var yy=height-4-pts[i]*(height-9); if(i===0)c.moveTo(xx,yy);else c.lineTo(xx,yy); }
            c.lineTo(width-2,height); c.lineTo(0,height); c.closePath(); c.fillStyle=grad; c.fill();
            c.beginPath();
            for(var j=0;j<pts.length;j++) { var x2=j*(width-2)/(pts.length-1); var y2=height-4-pts[j]*(height-9); if(j===0)c.moveTo(x2,y2);else c.lineTo(x2,y2); }
            c.strokeStyle="rgba(43,229,139,0.16)"; c.lineWidth=6; c.stroke();
            c.beginPath();
            for(var k=0;k<pts.length;k++) { var x3=k*(width-2)/(pts.length-1); var y3=height-4-pts[k]*(height-9); if(k===0)c.moveTo(x3,y3);else c.lineTo(x3,y3); }
            c.strokeStyle="#38DF8D"; c.lineWidth=1.8; c.stroke();
        }
    }

    Rectangle {
        anchors.fill: parent; radius: root.cornerRadius
        color: "transparent"
        border.width: root.hovered ? 1 : 0
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.28)
    }
    Rectangle {
        visible: root.hovered
        x: 18; y: 1; width: parent.width - 36; height: 2; radius: 1
        color: root.accentColor; opacity: 0.42
    }
    MouseArea { id: cardMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
