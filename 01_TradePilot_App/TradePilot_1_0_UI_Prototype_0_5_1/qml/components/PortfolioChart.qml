import QtQuick

Canvas {
    id: root
    property color lineColor: "#6D8CFF"
    property var points: [
        0.12,0.22,0.17,0.29,0.25,0.34,0.31,0.38,0.33,0.37,
        0.43,0.39,0.47,0.44,0.51,0.48,0.55,0.52,0.58,0.54,
        0.62,0.60,0.69,0.64,0.72,0.68,0.74,0.79,0.73,0.82,
        0.77,0.85,0.81,0.88,0.84,0.91,0.89,0.95,0.92,0.98,
        0.94,1.00
    ]

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()

    function xy(i,left,right,top,bottom) {
        return [left + (right-left)*i/(points.length-1), bottom - (bottom-top)*points[i]]
    }

    onPaint: {
        var ctx=getContext("2d"); ctx.reset()
        var left=4, right=width-48, top=16, bottom=height-30

        ctx.strokeStyle="rgba(34,72,101,0.30)"; ctx.lineWidth=1
        for(var g=0;g<4;g++) { var gy=top+(bottom-top)*g/3; ctx.beginPath(); ctx.moveTo(left,gy); ctx.lineTo(right,gy); ctx.stroke() }
        ctx.strokeStyle="rgba(34,64,91,0.10)"
        for(var v=1;v<5;v++) { var gx=left+(right-left)*v/5; ctx.beginPath(); ctx.moveTo(gx,top); ctx.lineTo(gx,bottom); ctx.stroke() }

        var grad=ctx.createLinearGradient(0,top,0,bottom)
        grad.addColorStop(0,"rgba(92,79,255,0.48)")
        grad.addColorStop(0.32,"rgba(48,116,255,0.27)")
        grad.addColorStop(0.74,"rgba(39,104,236,0.09)")
        grad.addColorStop(1,"rgba(28,94,220,0.00)")

        ctx.beginPath()
        for(var i=0;i<points.length;i++) { var p=xy(i,left,right,top,bottom); if(i===0)ctx.moveTo(p[0],p[1]); else ctx.lineTo(p[0],p[1]); }
        ctx.lineTo(right,bottom); ctx.lineTo(left,bottom); ctx.closePath(); ctx.fillStyle=grad; ctx.fill()

        ctx.beginPath()
        for(var j=0;j<points.length;j++) { var p2=xy(j,left,right,top,bottom); if(j===0)ctx.moveTo(p2[0],p2[1]); else ctx.lineTo(p2[0],p2[1]); }
        ctx.strokeStyle="rgba(71,105,255,0.10)"; ctx.lineWidth=8; ctx.stroke()

        ctx.beginPath()
        for(var k=0;k<points.length;k++) { var p3=xy(k,left,right,top,bottom); if(k===0)ctx.moveTo(p3[0],p3[1]); else ctx.lineTo(p3[0],p3[1]); }
        ctx.strokeStyle="#6888FF"; ctx.lineWidth=2.0; ctx.stroke()

        ctx.beginPath()
        for(var m=0;m<points.length;m++) { var p4=xy(m,left,right,top,bottom); if(m===0)ctx.moveTo(p4[0],p4[1]); else ctx.lineTo(p4[0],p4[1]); }
        ctx.strokeStyle="rgba(174,218,255,0.66)"; ctx.lineWidth=0.75; ctx.stroke()
    }
}
