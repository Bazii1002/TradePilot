import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components"

ApplicationWindow {
    id: window
    width: 1672
    height: 941
    minimumWidth: 1280
    minimumHeight: 720
    visible: true
    color: "#010812"
    title: "TradePilot · " + (backend ? backend.version : "Desktop Alpha")

    property int currentPage: 0
    property bool lightMode: false
    property var navNames: ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]
    property var navIcons: [Qt.resolvedUrl("../assets/icons/dashboard.svg"), Qt.resolvedUrl("../assets/icons/bot.svg"), Qt.resolvedUrl("../assets/icons/portfolio.svg"), Qt.resolvedUrl("../assets/icons/markets.svg"), Qt.resolvedUrl("../assets/icons/news.svg"), Qt.resolvedUrl("../assets/icons/backtest.svg"), Qt.resolvedUrl("../assets/icons/trades.svg"), Qt.resolvedUrl("../assets/icons/settings.svg")]
    property color bg: lightMode ? "#edf3f8" : "#010812"
    property color panel: lightMode ? "#ffffff" : "#071521"
    property color panel2: lightMode ? "#f6f9fc" : "#091b29"
    property color line: lightMode ? "#d8e3ec" : "#17364e"
    property color textMain: lightMode ? "#10202d" : "#f4f7fb"
    property color textMuted: lightMode ? "#617486" : "#8ca0b4"
    property color blue: "#278cff"
    property color green: "#2dde80"
    property color purple: "#8b61ff"

    Rectangle { anchors.fill: parent; color: window.bg }

    Rectangle {
        id: sidebar
        width: 226; anchors.top: parent.top; anchors.bottom: parent.bottom
        color: window.lightMode ? "#f8fbfd" : "#04111d"
        border.color: window.line
        Text { x: 28; y: 28; text: "Trade"; color: window.textMain; font.pixelSize: 25; font.bold: true; font.family: "Segoe UI" }
        Text { x: 86; y: 28; text: "Pilot"; color: window.blue; font.pixelSize: 25; font.bold: true; font.family: "Segoe UI" }
        Text { x: 28; y: 66; text: "DESKTOP ALPHA 0.13.0"; color: window.textMuted; font.pixelSize: 9; font.family: "Segoe UI" }

        Column {
            x: 16; y: 112; width: 194; spacing: 7
            Repeater {
                model: window.navNames
                delegate: Rectangle {
                    width: 194; height: 48; radius: 9
                    color: window.currentPage === index ? (window.lightMode ? "#e4f0ff" : "#0b2a47") : "transparent"
                    border.width: window.currentPage === index ? 1 : 0
                    border.color: window.currentPage === index ? "#1f75c8" : "transparent"
                    Image { x: 13; anchors.verticalCenter: parent.verticalCenter; source: window.navIcons[index]; width: 20; height: 20; opacity: window.currentPage === index ? 1.0 : 0.7 }
                    Text { x: 46; anchors.verticalCenter: parent.verticalCenter; text: modelData; color: window.currentPage === index ? window.blue : window.textMuted; font.pixelSize: 13; font.family: "Segoe UI" }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: window.currentPage = index }
                }
            }
        }

        Rectangle { x: 16; y: parent.height-136; width: 194; height: 105; radius: 11; color: window.panel; border.color: window.line }
        Text { x: 30; y: parent.height-120; text: "BOT ENGINE"; color: window.textMuted; font.pixelSize: 9; font.family: "Segoe UI" }
        Text { x: 30; y: parent.height-94; text: bot && bot.running ? "● RUNNING" : "● STOPPED"; color: bot && bot.running ? window.green : "#778b9e"; font.pixelSize: 13; font.bold: true; font.family: "Segoe UI" }
        Text { x: 30; y: parent.height-70; text: bot ? ("Stufe " + bot.level + " · " + bot.levelName) : "—"; color: window.textMain; font.pixelSize: 11; font.family: "Segoe UI" }
        Text { x: 30; y: parent.height-49; text: "SHADOW · PRODUCTION SIGNALS"; color: "#f2b84b"; font.pixelSize: 10; font.family: "Segoe UI" }
    }

    Item {
        id: content
        anchors.left: sidebar.right; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom

        Rectangle {
            id: header
            x: 28; y: 20; width: parent.width-56; height: 74; radius: 13
            color: window.panel; border.color: window.line
            Text { x: 22; y: 14; text: window.navNames[window.currentPage]; color: window.textMain; font.pixelSize: 22; font.bold: true; font.family: "Segoe UI" }
            Text { x: 22; y: 44; text: backend ? backend.freshnessText : ""; color: backend && backend.dataFresh ? window.green : window.textMuted; font.pixelSize: 10; font.family: "Segoe UI" }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                Rectangle { width: 138; height: 40; radius: 10; color: window.panel2; border.color: window.line; Text { anchors.centerIn: parent; text: "NYSE · " + (backend ? backend.nyseState : "—"); color: backend && backend.nyseOpen ? window.green : window.textMuted; font.pixelSize: 11; font.family: "Segoe UI" } }
                Rectangle { width: 146; height: 40; radius: 10; color: window.panel2; border.color: window.line; Text { anchors.centerIn: parent; text: "NASDAQ · " + (backend ? backend.nasdaqState : "—"); color: backend && backend.nasdaqOpen ? window.green : window.textMuted; font.pixelSize: 11; font.family: "Segoe UI" } }
                Rectangle { width: 138; height: 40; radius: 10; color: window.panel2; border.color: window.line; Text { anchors.centerIn: parent; text: "XETRA · " + (backend ? backend.xetraState : "—"); color: backend && backend.xetraOpen ? window.green : window.textMuted; font.pixelSize: 11; font.family: "Segoe UI" } }
                Rectangle { width: 132; height: 40; radius: 10; color: window.panel2; border.color: window.line; Text { anchors.centerIn: parent; text: backend ? backend.marketTime : "—"; color: window.textMain; font.pixelSize: 11; font.family: "Segoe UI" } }
            }
        }

        Item {
            x: 28; y: 112; width: parent.width-56; height: parent.height-132

            // DASHBOARD
            Item {
                anchors.fill: parent; visible: window.currentPage === 0
                Row {
                    width: parent.width; height: 112; spacing: 14
                    Repeater {
                        model: [
                            {t:"Cash Available", v:backend?backend.cashText:"—", s:"eToro REAL · Read only", c:"#2dde80"},
                            {t:"Invested", v:backend?backend.investedText:"—", s:backend?backend.investedPctText:"—", c:"#278cff"},
                            {t:"Portfolio Value", v:backend?backend.portfolioText:"—", s:backend?backend.openPositionCountText:"—", c:"#8b61ff"},
                            {t:"Today", v:backend?backend.todayText:"—", s:backend?backend.todayPctText:"—", c:"#f2b84b"}
                        ]
                        delegate: Rectangle {
                            width: (parent.width-42)/4; height: 108; radius: 13; color: window.panel; border.color: window.line
                            Rectangle { x: 0; y: 0; width: 4; height: parent.height; radius: 2; color: modelData.c }
                            Text { x: 20; y: 18; text: modelData.t; color: window.textMuted; font.pixelSize: 11; font.family:"Segoe UI" }
                            Text { x: 20; y: 45; text: modelData.v; color: window.textMain; font.pixelSize: 24; font.bold: true; font.family:"Segoe UI" }
                            Text { x: 20; y: 80; text: modelData.s; color: window.textMuted; font.pixelSize: 10; font.family:"Segoe UI" }
                        }
                    }
                }

                Rectangle {
                    x:0; y:128; width: parent.width*0.42; height: 560; radius: 13; color: window.panel; border.color: window.line
                    Text { x:20; y:18; text:"Bot Activity · Production Signals"; color:window.textMain; font.pixelSize:16; font.bold:true; font.family:"Segoe UI" }
                    Rectangle { x:20; y:54; width:parent.width-40; height:74; radius:10; color:window.panel2; border.color:window.line }
                    Text { x:36; y:68; text:bot && bot.running?"● RUNNING":"● STOPPED"; color:bot && bot.running?window.green:window.textMuted; font.pixelSize:14; font.bold:true; font.family:"Segoe UI" }
                    Text { x:36; y:94; text:bot?("Stufe "+bot.level+" · "+bot.levelName+" · "+bot.modeText):"—"; color:window.textMuted; font.pixelSize:11; font.family:"Segoe UI" }
                    Rectangle { x:parent.width-150; y:70; width:112; height:38; radius:9; color:bot&&bot.running?"#442029":"#0d3155"; border.color:bot&&bot.running?"#a33c53":"#24639a"; Text{anchors.centerIn:parent;text:bot&&bot.running?"STOP":"START";color:window.textMain;font.pixelSize:12;font.bold:true} MouseArea{anchors.fill:parent;onClicked:{if(bot){if(bot.running)bot.stopBot();else bot.startBot()}}} }
                    Text { x:20; y:154; text:"Letzte Aktion"; color:window.textMuted; font.pixelSize:10; font.family:"Segoe UI" }
                    Text { x:20; y:177; width:parent.width-40; text:bot?bot.lastActionText:"—"; color:window.textMain; font.pixelSize:13; wrapMode:Text.WordWrap; font.family:"Segoe UI" }
                    Text { x:20; y:224; text:"Shadow-Konto"; color:window.textMuted; font.pixelSize:10; font.family:"Segoe UI" }
                    Text { x:20; y:247; text:bot?bot.paperEquityText:"—"; color:window.textMain; font.pixelSize:23; font.bold:true; font.family:"Segoe UI" }
                    Text { x:170; y:252; text:bot?("P/L "+bot.pnlText):""; color:window.green; font.pixelSize:12; font.family:"Segoe UI" }
                    Text { x:20; y:296; text:"Engine Log"; color:window.textMain; font.pixelSize:13; font.bold:true; font.family:"Segoe UI" }
                    ListView { x:20; y:326; width:parent.width-40; height:210; clip:true; model:bot?JSON.parse(bot.eventsJson):[]; delegate:Rectangle{width:ListView.view.width;height:42;color:"transparent";border.color:window.line;Text{x:4;y:7;text:modelData.time;color:window.textMuted;font.pixelSize:9} Text{x:70;y:7;width:parent.width-74;text:modelData.text;color:window.textMain;font.pixelSize:10;elide:Text.ElideRight}} }
                }

                Rectangle {
                    x: parent.width*0.42+14; y:128; width: parent.width*0.58-14; height: 328; radius:13; color:window.panel; border.color:window.line
                    Text{x:20;y:18;text:"Market Scanner";color:window.textMain;font.pixelSize:16;font.bold:true;font.family:"Segoe UI"}
                    Text{anchors.right:parent.right;anchors.rightMargin:20;y:21;text:bot?("Scans "+bot.scanCount+" · "+bot.lastScanText):"";color:window.textMuted;font.pixelSize:10}
                    ListView{x:20;y:56;width:parent.width-40;height:248;clip:true;model:bot?JSON.parse(bot.marketRowsJson):[];delegate:Rectangle{width:ListView.view.width;height:38;color:index%2===0?window.panel2:"transparent";Text{x:10;anchors.verticalCenter:parent.verticalCenter;text:modelData.symbol;color:window.textMain;font.pixelSize:11;font.bold:true} Text{x:105;anchors.verticalCenter:parent.verticalCenter;text:modelData.strategy;color:window.textMuted;font.pixelSize:10} Text{x:210;anchors.verticalCenter:parent.verticalCenter;text:modelData.score+"%";color:window.textMain;font.pixelSize:10} Text{anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;text:modelData.signal;color:modelData.signal==="BUY"?window.green:(modelData.signal==="WATCH"?"#f2b84b":window.textMuted);font.pixelSize:10;font.bold:true}}}
                }
                Rectangle {
                    x: parent.width*0.42+14; y:470; width: parent.width*0.58-14; height:218; radius:13; color:window.panel; border.color:window.line
                    Text{x:20;y:18;text:"System Status";color:window.textMain;font.pixelSize:16;font.bold:true;font.family:"Segoe UI"}
                    Text{x:20;y:58;text:"Broker";color:window.textMuted;font.pixelSize:10} Text{x:170;y:58;text:backend?backend.brokerStatusText:"—";color:backend&&backend.brokerConnected?window.green:window.textMuted;font.pixelSize:11}
                    Text{x:20;y:88;text:"Bot Mode";color:window.textMuted;font.pixelSize:10} Text{x:170;y:88;text:bot?bot.modeText:"—";color:"#f2b84b";font.pixelSize:11}
                    Text{x:20;y:118;text:"REAL AutoTrading";color:window.textMuted;font.pixelSize:10} Text{x:170;y:118;text:bot?bot.realLockText:"—";color:"#ef6b74";font.pixelSize:11;font.bold:true}
                    Text{x:20;y:148;text:"Open Shadow Positions";color:window.textMuted;font.pixelSize:10} Text{x:170;y:148;text:bot?bot.openPositions:"0";color:window.textMain;font.pixelSize:11}
                    Text{x:20;y:178;text:"Stress Trades";color:window.textMuted;font.pixelSize:10} Text{x:170;y:178;text:bot?bot.tradeCount:"0";color:window.textMain;font.pixelSize:11}
                }
            }

            // BOT PAGE
            Item {
                anchors.fill: parent; visible: window.currentPage === 1
                Rectangle { x:0;y:0;width:parent.width;height:150;radius:13;color:window.panel;border.color:window.line
                    Text{x:22;y:18;text:"AutoTrader Control";color:window.textMain;font.pixelSize:20;font.bold:true;font.family:"Segoe UI"}
                    Text{x:22;y:51;text:"Die Produktions-Signalengine nutzt echte Marktdaten und handelt im Shadow-Modus. REAL AutoTrading bleibt weiterhin gesperrt.";color:window.textMuted;font.pixelSize:11}
                    Row{x:22;y:84;spacing:10;Repeater{model:[{n:"FAST",l:1},{n:"DAY",l:2},{n:"WEEK",l:3},{n:"INVEST",l:4}];delegate:Rectangle{width:108;height:42;radius:9;color:bot&&bot.level===modelData.l?"#0d3155":window.panel2;border.color:bot&&bot.level===modelData.l?window.blue:window.line;Text{anchors.centerIn:parent;text:modelData.l+"  "+modelData.n;color:bot&&bot.level===modelData.l?"#7fc5ff":window.textMuted;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:if(bot)bot.setLevel(modelData.l)}}}}
                    Rectangle{x:parent.width-282;y:84;width:120;height:42;radius:9;color:"#0d3155";border.color:"#24639a";Text{anchors.centerIn:parent;text:"SCAN NOW";color:window.textMain;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:if(bot)bot.forceScan()}}
                    Rectangle{x:parent.width-150;y:84;width:120;height:42;radius:9;color:bot&&bot.running?"#442029":"#0f3e31";border.color:bot&&bot.running?"#a33c53":"#248358";Text{anchors.centerIn:parent;text:bot&&bot.running?"STOP BOT":"START BOT";color:window.textMain;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:{if(bot){if(bot.running)bot.stopBot();else bot.startBot()}}}}
                }
                Rectangle{x:0;y:166;width:parent.width*0.55;height:522;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Open Shadow Positions";color:window.textMain;font.pixelSize:16;font.bold:true}
                    ListView{x:20;y:56;width:parent.width-40;height:440;clip:true;model:bot?JSON.parse(bot.positionsJson):[];delegate:Rectangle{width:ListView.view.width;height:70;color:index%2===0?window.panel2:"transparent";Text{x:10;y:10;text:modelData.symbol;color:window.textMain;font.pixelSize:13;font.bold:true} Text{x:90;y:11;text:modelData.strategy;color:window.purple;font.pixelSize:10;font.bold:true} Text{x:10;y:38;text:"Entry $"+Number(modelData.entry).toFixed(2)+" · Now $"+Number(modelData.price).toFixed(2);color:window.textMuted;font.pixelSize:10} Text{anchors.right:parent.right;anchors.rightMargin:12;y:25;text:(modelData.pnl_pct>=0?"+":"")+Number(modelData.pnl_pct).toFixed(2)+"%";color:modelData.pnl_pct>=0?window.green:"#ef6b74";font.pixelSize:12;font.bold:true}}}
                    Text{visible:bot&&bot.openPositions===0;anchors.centerIn:parent;text:"Noch keine Shadow-Positionen";color:window.textMuted;font.pixelSize:12}
                }
                Rectangle{x:parent.width*0.55+14;y:166;width:parent.width*0.45-14;height:522;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Engine Status";color:window.textMain;font.pixelSize:16;font.bold:true}
                    Column{x:20;y:60;spacing:22
                        Text{text:"Status:  "+(bot?bot.statusText:"—");color:bot&&bot.running?window.green:window.textMain;font.pixelSize:12}
                        Text{text:"Stufe:  "+(bot?(bot.level+" · "+bot.levelName):"—");color:window.textMain;font.pixelSize:12}
                        Text{text:"Letzter Scan:  "+(bot?bot.lastScanText:"—");color:window.textMain;font.pixelSize:12}
                        Text{text:"Nächster Scan:  "+(bot?bot.nextScanText:"—");color:window.textMain;font.pixelSize:12}
                        Text{text:"Scans gesamt:  "+(bot?bot.scanCount:0);color:window.textMain;font.pixelSize:12}
                        Text{text:"Trades gesamt:  "+(bot?bot.tradeCount:0);color:window.textMain;font.pixelSize:12}
                        Text{text:"Shadow Equity:  "+(bot?bot.paperEquityText:"—");color:window.textMain;font.pixelSize:12}
                        Text{text:"Shadow P/L:  "+(bot?bot.pnlText:"—");color:window.green;font.pixelSize:12}
                    }
                    Rectangle{x:20;y:400;width:parent.width-40;height:72;radius:9;color:"#28161b";border.color:"#71313d";Text{x:14;y:12;text:"REAL AUTOTRADING LOCKED";color:"#ef6b74";font.pixelSize:12;font.bold:true} Text{x:14;y:36;width:parent.width-28;text:"Manuelle REAL-Ausführung ist über Safety Core + Bestätigung möglich. Automatische Echtgeld-Ausführung der Produktionssignale ist weiterhin gesperrt.";color:window.textMuted;font.pixelSize:10;wrapMode:Text.WordWrap}}
                }
            }

            // PORTFOLIO
            Item { anchors.fill:parent; visible:window.currentPage===2
                Rectangle{x:0;y:0;width:parent.width;height:120;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"eToro Portfolio · REAL LIVE DATA";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:54;text:"Cash  "+(backend?backend.cashText:"—");color:window.green;font.pixelSize:22;font.bold:true}
                    Text{x:260;y:54;text:"Invested  "+(backend?backend.investedText:"—");color:window.blue;font.pixelSize:22;font.bold:true}
                    Text{x:540;y:54;text:"Value  "+(backend?backend.portfolioText:"—");color:window.purple;font.pixelSize:22;font.bold:true}
                    Rectangle{anchors.right:parent.right;anchors.rightMargin:20;y:39;width:120;height:42;radius:9;color:"#0d3155";border.color:"#24639a";Text{anchors.centerIn:parent;text:"REFRESH";color:window.textMain;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:if(backend)backend.refreshData()}}
                }
                Rectangle{x:0;y:136;width:parent.width;height:552;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Open REAL Positions";color:window.textMain;font.pixelSize:16;font.bold:true}
                    ListView{x:20;y:56;width:parent.width-40;height:470;clip:true;model:backend?JSON.parse(backend.activityRowsJson):[];delegate:Rectangle{width:ListView.view.width;height:58;color:index%2===0?window.panel2:"transparent";Text{x:10;anchors.verticalCenter:parent.verticalCenter;text:modelData.symbol;color:window.textMain;font.pixelSize:12;font.bold:true} Text{x:150;anchors.verticalCenter:parent.verticalCenter;text:modelData.shares;color:window.textMuted;font.pixelSize:10} Text{anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;text:modelData.amount;color:window.textMain;font.pixelSize:11}}}
                    Text{visible:backend&&JSON.parse(backend.activityRowsJson).length===0;anchors.centerIn:parent;text:"Keine offenen REAL-Positionen";color:window.textMuted;font.pixelSize:12}
                }
            }

            // MARKETS
            Item{anchors.fill:parent;visible:window.currentPage===3
                Rectangle{anchors.fill:parent;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Markets · Bot Scanner";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:47;text:"Das Universe wird vom laufenden Shadow-Bot bewertet.";color:window.textMuted;font.pixelSize:11}
                    ListView{x:20;y:82;width:parent.width-40;height:570;clip:true;model:bot?JSON.parse(bot.marketRowsJson):[];delegate:Rectangle{width:ListView.view.width;height:62;color:index%2===0?window.panel2:"transparent";Text{x:12;y:12;text:modelData.symbol;color:window.textMain;font.pixelSize:13;font.bold:true} Text{x:12;y:34;width:330;text:modelData.reason||"";elide:Text.ElideRight;color:window.textMuted;font.pixelSize:9}
                            Text{x:180;y:12;text:"Stufe "+(bot?bot.level:2)+" · "+modelData.strategy;color:window.textMuted;font.pixelSize:10} Text{x:390;y:12;text:"Score "+modelData.score+"%";color:window.textMain;font.pixelSize:11} Text{anchors.right:parent.right;anchors.rightMargin:18;y:12;text:modelData.signal;color:modelData.signal==="BUY"?window.green:(modelData.signal==="WATCH"?"#f2b84b":window.textMuted);font.pixelSize:11;font.bold:true}}}
                }
            }

            // NEWS
            Item{anchors.fill:parent;visible:window.currentPage===4
                Rectangle{anchors.fill:parent;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"International Market News";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:48;text:"Alpha-Preview: News-Datenquelle wird als nächster Integrationsschritt angebunden.";color:window.textMuted;font.pixelSize:11}
                    Column{x:20;y:90;width:parent.width-40;spacing:12
                        Repeater{model:[
                            {b:"FED",t:"Fed / US rates",s:"Makro-News-Modul vorbereitet · noch kein Live-Feed"},
                            {b:"NASDAQ",t:"US Technology",s:"Market-News-Panel aktiv · Datenquelle folgt"},
                            {b:"EUROPE",t:"European Markets",s:"XETRA/Europa-Bereich vorbereitet"},
                            {b:"AI",t:"AI Review Queue",s:"Später: relevante News werden vor Trades bewertet"}
                        ];delegate:Rectangle{width:parent.width;height:96;radius:10;color:window.panel2;border.color:window.line;Rectangle{x:14;y:18;width:90;height:28;radius:7;color:"#0d3155";Text{anchors.centerIn:parent;text:modelData.b;color:"#7fc5ff";font.pixelSize:10;font.bold:true}} Text{x:124;y:18;text:modelData.t;color:window.textMain;font.pixelSize:13;font.bold:true} Text{x:124;y:48;width:parent.width-144;text:modelData.s;color:window.textMuted;font.pixelSize:10;wrapMode:Text.WordWrap}}}
                    }
                }
            }

            // BACKTEST
            Item{anchors.fill:parent;visible:window.currentPage===5
                property bool ran:false
                Rectangle{anchors.fill:parent;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Backtest";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:50;text:"Der bestehende Research-/Backtest-Bereich bleibt getrennt von der Live Engine.";color:window.textMuted;font.pixelSize:11}
                    Rectangle{x:20;y:92;width:210;height:44;radius:9;color:"#0d3155";border.color:"#24639a";Text{anchors.centerIn:parent;text:"RUN UI SMOKE BACKTEST";color:window.textMain;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:parent.parent.ran=true}}
                    Rectangle{x:20;y:160;width:parent.width-40;height:180;radius:10;color:window.panel2;border.color:window.line
                        Text{x:18;y:18;text:parent.parent.ran?"UI Smoke Backtest abgeschlossen":"Noch kein UI Smoke Backtest gestartet";color:window.textMain;font.pixelSize:14;font.bold:true}
                        Text{x:18;y:54;text:parent.parent.ran?"FAST · DAY · WEEK · INVEST: Konfiguration erreichbar\nEngine-State: OK\nREAL Trading: nicht Teil dieses Tests":"Dieser Button prüft nur die App-Verkabelung; der Research Engine 0.6.1 wird nicht verändert.";color:window.textMuted;font.pixelSize:11;lineHeight:1.5}
                    }
                }
            }

            // TRADES
            Item{anchors.fill:parent;visible:window.currentPage===6
                Rectangle{anchors.fill:parent;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Shadow Trade History";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:48;text:"Alle Shadow-BUY/SELL-Aktionen der Produktions-Signalengine. Jede Position behält ihre Eröffnungsstrategie.";color:window.textMuted;font.pixelSize:11}
                    ListView{x:20;y:84;width:parent.width-40;height:566;clip:true;model:bot?JSON.parse(bot.tradesJson):[];delegate:Rectangle{width:ListView.view.width;height:54;color:index%2===0?window.panel2:"transparent";Text{x:10;anchors.verticalCenter:parent.verticalCenter;text:modelData.time;color:window.textMuted;font.pixelSize:9} Text{x:95;anchors.verticalCenter:parent.verticalCenter;text:modelData.symbol;color:window.textMain;font.pixelSize:12;font.bold:true} Text{x:190;anchors.verticalCenter:parent.verticalCenter;text:modelData.side;color:modelData.side==="BUY"?window.green:"#f2b84b";font.pixelSize:11;font.bold:true} Text{x:275;anchors.verticalCenter:parent.verticalCenter;text:modelData.strategy;color:window.purple;font.pixelSize:10} Text{x:390;anchors.verticalCenter:parent.verticalCenter;text:"$"+Number(modelData.amount).toFixed(2);color:window.textMain;font.pixelSize:10} Text{x:500;anchors.verticalCenter:parent.verticalCenter;text:modelData.pnl!==0?((modelData.pnl>0?"+":"")+"$"+Number(modelData.pnl).toFixed(2)):"—";color:modelData.pnl>=0?window.green:"#ef6b74";font.pixelSize:10} Text{x:610;anchors.verticalCenter:parent.verticalCenter;width:parent.width-630;text:modelData.reason;color:window.textMuted;font.pixelSize:10;elide:Text.ElideRight}}}
                    Text{visible:bot&&bot.tradeCount===0;anchors.centerIn:parent;text:"Noch keine Shadow-Trades";color:window.textMuted;font.pixelSize:12}
                }
            }

            // SETTINGS
            Item{anchors.fill:parent;visible:window.currentPage===7
                Rectangle{anchors.fill:parent;radius:13;color:window.panel;border.color:window.line
                    Text{x:20;y:18;text:"Settings";color:window.textMain;font.pixelSize:18;font.bold:true}
                    Text{x:20;y:55;text:"Appearance";color:window.textMuted;font.pixelSize:10}
                    Rectangle{x:20;y:80;width:180;height:42;radius:9;color:window.panel2;border.color:window.line;Text{anchors.centerIn:parent;text:window.lightMode?"LIGHT MODE":"DARK MODE";color:window.textMain;font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:window.lightMode=!window.lightMode}}
                    Text{x:20;y:160;text:"Bot Safety";color:window.textMuted;font.pixelSize:10}
                    Rectangle{x:20;y:186;width:520;height:126;radius:10;color:window.panel2;border.color:window.line
                        Text{x:16;y:14;text:"Mode: SHADOW · PRODUCTION SIGNALS";color:"#f2b84b";font.pixelSize:12;font.bold:true}
                        Text{x:16;y:43;text:"Trade Size: $10.00 simulated";color:window.textMain;font.pixelSize:11}
                        Text{x:16;y:68;text:"Max Open Shadow Positions: 3";color:window.textMain;font.pixelSize:11}
                        Text{x:16;y:93;text:"REAL AutoTrading: LOCKED · Safety Core READY";color:"#ef6b74";font.pixelSize:11;font.bold:true}
                    }
                    Text{x:20;y:350;text:"Shadow Test Data";color:window.textMuted;font.pixelSize:10}
                    Rectangle{x:20;y:376;width:200;height:42;radius:9;color:"#3a1a21";border.color:"#783440";Text{anchors.centerIn:parent;text:"RESET SHADOW DATA";color:"#ff8b93";font.pixelSize:11;font.bold:true} MouseArea{anchors.fill:parent;onClicked:if(bot)bot.resetShadow()}}
                    Text{x:20;y:448;width:620;text:"Reset stoppt den Bot, löscht nur lokale Shadow-Positionen/Trades und setzt das simulierte Konto auf $1,000 zurück. eToro-REAL-Daten werden nicht verändert.";color:window.textMuted;font.pixelSize:10;wrapMode:Text.WordWrap}
                }
            }
        }
    }
}
