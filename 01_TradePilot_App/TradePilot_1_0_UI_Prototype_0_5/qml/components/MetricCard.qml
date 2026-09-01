import QtQuick

NeonCard {
    id: root
    property string title: "Cash Available"
    property string value: "$18,742.63"
    property string subtitleLeft: "Buying Power"
    property string subtitleRight: "$18,742.63"
    property string iconSource: ""
    property color valueColor: "#F5F8FC"
    property bool sparkline: false

    Text {
        x: 24; y: 22
        text: root.title
        color: "#F0F5FA"
        font.pixelSize: 16
        font.weight: Font.Medium
        font.family: "Segoe UI"
    }

    Rectangle {
        width: 50; height: 50
        anchors.right: parent.right; anchors.rightMargin: 18
        y: 17; radius: 11
        color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.075)
        border.width: 1
        border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.33)
        Image {
            anchors.centerIn: parent
            width: 27; height: 27
            source: root.iconSource
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
    }

    Text {
        x: 24; y: 69
        text: root.value
        color: root.valueColor
        font.pixelSize: 31
        font.weight: Font.DemiBold
        font.family: "Segoe UI"
    }

    Text {
        x: 24; y: 132
        text: root.subtitleLeft
        color: root.valueColor === "#35DF8B" ? "#31DC87" : "#8EA2B5"
        font.pixelSize: 12
        font.family: "Segoe UI"
    }
    Text {
        anchors.right: parent.right; anchors.rightMargin: 24
        y: 132
        text: root.subtitleRight
        color: "#C4D0DB"
        font.pixelSize: 12
        font.family: "Segoe UI"
    }

    Canvas {
        visible: root.sparkline
        x: 178; y: 103; width: 136; height: 52
        property var pts: [0.12,0.18,0.23,0.20,0.29,0.34,0.31,0.40,0.46,0.43,0.52,0.49,0.57,0.61,0.58,0.66,0.72,0.68,0.79,0.76,0.84,0.89,0.86,0.95]
        onPaint: {
            var c=getContext("2d"); c.reset();
            var grad=c.createLinearGradient(0,0,0,height); grad.addColorStop(0,"rgba(46,225,137,0.25)"); grad.addColorStop(1,"rgba(46,225,137,0)");
            c.beginPath();
            for(var i=0;i<pts.length;i++) { var xx=i*(width-2)/(pts.length-1); var yy=height-4-pts[i]*(height-9); if(i===0)c.moveTo(xx,yy);else c.lineTo(xx,yy); }
            c.lineTo(width-2,height); c.lineTo(0,height); c.closePath(); c.fillStyle=grad; c.fill();
            c.beginPath();
            for(var j=0;j<pts.length;j++) { var x2=j*(width-2)/(pts.length-1); var y2=height-4-pts[j]*(height-9); if(j===0)c.moveTo(x2,y2);else c.lineTo(x2,y2); }
            c.strokeStyle="rgba(43,229,139,0.14)"; c.lineWidth=5; c.stroke();
            c.beginPath();
            for(var k=0;k<pts.length;k++) { var x3=k*(width-2)/(pts.length-1); var y3=height-4-pts[k]*(height-9); if(k===0)c.moveTo(x3,y3);else c.lineTo(x3,y3); }
            c.strokeStyle="#38DF8D"; c.lineWidth=1.7; c.stroke();
        }
    }
}
