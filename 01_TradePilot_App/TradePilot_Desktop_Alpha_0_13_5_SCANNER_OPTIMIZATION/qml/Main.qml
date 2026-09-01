import QtQuick
import QtQuick.Controls
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
    title: "TradePilot · " + (backend ? backend.version : "Desktop Alpha 0.13.5")

    property int currentPage: 0
    property var navNames: ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]
    property var navIcons: [Qt.resolvedUrl("../assets/icons/dashboard.svg"), Qt.resolvedUrl("../assets/icons/bot.svg"), Qt.resolvedUrl("../assets/icons/portfolio.svg"), Qt.resolvedUrl("../assets/icons/markets.svg"), Qt.resolvedUrl("../assets/icons/news.svg"), Qt.resolvedUrl("../assets/icons/backtest.svg"), Qt.resolvedUrl("../assets/icons/trades.svg"), Qt.resolvedUrl("../assets/icons/settings.svg")]
    property real designW: 1672
    property real designH: 941
    property string dashboardRange: "1D"
    property var dashboardRanges: ["1D","1W","1M","3M","YTD","1Y","All"]

    function goPage(index) {
        currentPage = index
        if (backend) backend.navigationClicked(navNames[index])
    }

    function cycleDashboardRange() {
        var i = dashboardRanges.indexOf(dashboardRange)
        dashboardRange = dashboardRanges[(i + 1) % dashboardRanges.length]
    }

    function logoFor(symbol) {
        var s = String(symbol || "").toUpperCase()
        if (["AAPL","NVDA","MSFT","TSLA","SPY"].indexOf(s) >= 0)
            return Qt.resolvedUrl("../assets/company/" + s.toLowerCase() + ".png")
        return ""
    }

    Rectangle { anchors.fill: parent; color: "#010812" }

    Item {
        id: stage
        width: window.designW
        height: window.designH
        transformOrigin: Item.TopLeft
        // 0.4 uses the full client area. This removes the visible letterbox bars on the Surface.
        transform: Scale {
            origin.x: 0; origin.y: 0
            xScale: window.width / window.designW
            yScale: window.height / window.designH
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#010812" }
                GradientStop { position: 0.50; color: "#03101c" }
                GradientStop { position: 1.0; color: "#020912" }
            }
        }
        Rectangle { x: 1030; y: -130; width: 720; height: 270; radius: 135; color: "#0b4d91"; opacity: 0.045 }
        Rectangle { x: 1150; y: 700; width: 570; height: 260; radius: 130; color: "#0b684e"; opacity: 0.055 }
        Rectangle { x: 420; y: 260; width: 650; height: 300; radius: 150; color: "#33256c"; opacity: 0.025 }

        // SIDEBAR -----------------------------------------------------------------
        Rectangle {
            x: 0; y: 0; width: 240; height: 941
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#051522" }
                GradientStop { position: 0.55; color: "#03111C" }
                GradientStop { position: 1.0; color: "#020C15" }
            }
            border.width: 1; border.color: "#123248"

            Image {
                x: 28; y: 22; width: 48; height: 43
                source: Qt.resolvedUrl("../assets/ui/logo.png")
                fillMode: Image.PreserveAspectFit
                smooth: true; mipmap: true
            }
            Text { x: 84; y: 31; text: "TradePilot"; color: "#f7f9fc"; font.pixelSize: 24; font.weight: Font.DemiBold; font.family: "Segoe UI" }
            Text { x: 84; y: 62; text: "Desktop Alpha 0.13.5"; color: "#6f8498"; font.pixelSize: 10; font.family: "Segoe UI" }

            Column {
                x: 12; y: 114; width: 216; spacing: 5
                Repeater {
                    model: 8
                    NavItem {
                        width: 216
                        label: window.navNames[index]
                        iconSource: window.navIcons[index]
                        selected: window.currentPage === index
                        onClicked: window.goPage(index)
                    }
                }
            }

            NeonCard {
                x: 20; y: 742; width: 200; height: 121
                glow: false; ambient: false
                fillColor: "#061522"; fillColor2: "#081b2a"; borderColor: "#183b54"
                Text { x: 17; y: 15; text: "◉  Market Time (ET)"; color: "#91a4b7"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 17; y: 43; text: backend ? backend.marketTime : "--:--:--"; color: "#f6f8fb"; font.pixelSize: 23; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 17; y: 75; text: backend ? backend.dateText : "--"; color: "#748a9e"; font.pixelSize: 11; font.family: "Segoe UI" }
                Rectangle { x: 17; y: 99; width: 6; height: 6; radius: 3; color: "#2ee58c" }
                Text { x: 29; y: 96; text: "System Status: Online"; color: "#2cd986"; font.pixelSize: 9; font.family: "Segoe UI" }
            }
            Text { x: 27; y: 894; width: 186; text: "Production Engine · eToro REAL READ ONLY"; color: "#4f687c"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.family: "Segoe UI" }
        }

        // TOP BAR -----------------------------------------------------------------
        Rectangle {
            x: 240; y: 0; width: 1432; height: 96
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#03101D" }
                GradientStop { position: 1.0; color: "#020A13" }
            }
            border.width: 1; border.color: "#15364E"
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#17415c"; opacity: 0.52 }

            MarketPill { x: 688; y: 18; width: 158; market: "NYSE"; stateText: backend ? backend.nyseState : "—"; subText: backend ? backend.nyseSub : ""; open: backend ? backend.nyseOpen : false }
            MarketPill { x: 858; y: 18; width: 158; market: "NASDAQ"; stateText: backend ? backend.nasdaqState : "—"; subText: backend ? backend.nasdaqSub : ""; open: backend ? backend.nasdaqOpen : false }
            MarketPill { x: 1028; y: 18; width: 184; market: "XETRA"; stateText: backend ? backend.xetraState : "—"; subText: backend ? backend.xetraSub : ""; open: backend ? backend.xetraOpen : false }

            Rectangle {
                id: bellButton
                x: 1236; y: 18; width: 52; height: 52; radius: 14
                color: bellMouse.containsMouse ? "#0B2235" : "transparent"
                border.width: bellMouse.containsMouse ? 1 : 0
                border.color: "#24577A"
                Behavior on color { ColorAnimation { duration: 120 } }
                Image { anchors.centerIn: parent; width: 30; height: 30; source: Qt.resolvedUrl("../assets/icons/bell.svg"); fillMode: Image.PreserveAspectFit; smooth: true }
                Rectangle { x: 35; y: 6; width: 7; height: 7; radius: 3.5; color: "#2F96FF" }
                MouseArea { id: bellMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.goPage(4) }
            }

            Rectangle {
                id: profileButton
                x: 1302; y: 17; width: 54; height: 54; radius: 27
                gradient: Gradient {
                    GradientStop { position: 0.0; color: profileMouse.containsMouse ? "#123552" : "#0A2033" }
                    GradientStop { position: 1.0; color: "#06131F" }
                }
                border.width: 1; border.color: profileMouse.containsMouse ? "#52A9FF" : "#38556E"
                Image { anchors.centerIn: parent; width: 31; height: 31; source: Qt.resolvedUrl("../assets/icons/profile.svg"); fillMode: Image.PreserveAspectFit; smooth: true }
                MouseArea { id: profileMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.goPage(7) }
            }
        }

        // PREMIUM VISUAL POLISH 0.13.2: frozen geometry, upgraded surfaces/interactions
        // PREMIUM VISUAL POLISH II 0.13.4 + SCANNER OPTIMIZATION 0.13.5: functional dashboard actions + upgraded surfaces/interactions
        // FUNCTIONAL PAGES ---------------------------------------------------------
        // The dashboard below is the frozen/approved TradePilot design. All other
        // pages use the exact same shell, card, spacing and accent language.

        // BOT --------------------------------------------------------------------
        Item {
            visible: window.currentPage === 1
            x: 262; y: 116; width: 1388; height: 764

            NeonCard {
                x: 0; y: 0; width: 1388; height: 150
                glow: true; accentColor: "#2aa8ff"; fillColor: "#061522"; fillColor2: "#0A1C2D"; borderColor: "#1C405A"
                Text { x: 20; y: 18; text: "AutoTrader Control"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "Produktionssignale mit echten Marktdaten · SHADOW aktiv · REAL AutoTrading gesperrt"; color: "#8da2b6"; font.pixelSize: 11; font.family: "Segoe UI" }

                Row {
                    x: 20; y: 82; spacing: 10
                    Repeater {
                        model: [{n:"FAST",l:1},{n:"DAY",l:2},{n:"WEEK",l:3},{n:"INVEST",l:4}]
                        Rectangle {
                            id: strategyButton
                            width: 116; height: 42; radius: 9
                            property bool active: bot && bot.level === modelData.l
                            property bool hovered: strategyMouse.containsMouse
                            gradient: Gradient {
                                GradientStop { position: 0.0; color: strategyButton.active ? "#123D72" : (strategyButton.hovered ? "#0B2439" : "#071521") }
                                GradientStop { position: 1.0; color: strategyButton.active ? "#082747" : "#06121D" }
                            }
                            border.width: 1
                            border.color: strategyButton.active ? "#2EA8FF" : (strategyButton.hovered ? "#285878" : "#1A3B53")
                            Rectangle { visible: strategyButton.active; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.leftMargin: 10; anchors.rightMargin: 10; height: 2; radius: 1; color: "#30AAFF" }
                            Text { anchors.centerIn: parent; text: modelData.l + "  " + modelData.n; color: strategyButton.active ? "#DDF2FF" : (strategyButton.hovered ? "#C7D8E6" : "#91A5B8"); font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                            MouseArea { id: strategyMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: if (bot) bot.setLevel(modelData.l) }
                        }
                    }
                }

                Rectangle {
                    id: scanButton
                    x: 1084; y: 82; width: 130; height: 42; radius: 9
                    property bool hovered: scanMouse.containsMouse
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: scanButton.hovered ? "#174D88" : "#103C6B" }
                        GradientStop { position: 1.0; color: scanButton.hovered ? "#092C50" : "#08233E" }
                    }
                    border.width: 1; border.color: scanButton.hovered ? "#39B6FF" : "#2A79B6"
                    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.leftMargin: 12; anchors.rightMargin: 12; height: 2; radius: 1; color: "#33B3FF"; opacity: 0.72 }
                    Text { anchors.centerIn: parent; text: "SCAN NOW"; color: "#D9F1FF"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: scanMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: if (bot) bot.forceScan() }
                }
                Rectangle {
                    id: botToggleButton
                    x: 1228; y: 82; width: 140; height: 42; radius: 9
                    property bool hovered: botToggleMouse.containsMouse
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: bot && bot.running ? (botToggleButton.hovered ? "#57202B" : "#431A24") : (botToggleButton.hovered ? "#104D39" : "#0B392D") }
                        GradientStop { position: 1.0; color: bot && bot.running ? "#281219" : "#071F19" }
                    }
                    border.width: 1; border.color: bot && bot.running ? (botToggleButton.hovered ? "#FF5F70" : "#A33A4D") : (botToggleButton.hovered ? "#39D990" : "#1D7452")
                    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.leftMargin: 12; anchors.rightMargin: 12; height: 2; radius: 1; color: bot && bot.running ? "#FF5E70" : "#31DF8B"; opacity: 0.75 }
                    Text { anchors.centerIn: parent; text: bot && bot.running ? "STOP BOT" : "START BOT"; color: bot && bot.running ? "#FFA3AA" : "#5BEAA4"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: botToggleMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { if (bot) { if (bot.running) bot.stopBot(); else bot.startBot() } } }
                }
            }

            NeonCard {
                x: 0; y: 166; width: 824; height: 598
                glow: true; accentColor: "#8d64ff"; fillColor2: "#0A172A"; borderColor: "#1A3A54"
                Text { x: 20; y: 18; text: "Open Shadow Positions"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 20; text: bot ? (bot.openPositions + " offen") : "0 offen"; color: "#8ea2b5"; font.pixelSize: 11; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 54; width: 784; height: 1; color: "#16344c" }
                Text { x: 22; y: 67; text: "SYMBOL"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 142; y: 67; text: "STRATEGY"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 300; y: 67; text: "ENTRY / NOW"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 30; y: 67; text: "P/L"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                ListView {
                    x: 20; y: 90; width: 784; height: 475; clip: true
                    model: bot ? JSON.parse(bot.positionsJson) : []
                    delegate: Rectangle {
                        width: ListView.view.width; height: 68
                        radius: 8
                        color: rowHover.containsMouse ? "#0A2032" : (index % 2 === 0 ? "#071827" : "transparent")
                        border.width: rowHover.containsMouse ? 1 : 0
                        border.color: "#214B68"
                        Text { x: 10; y: 14; text: modelData.symbol; color: modelData.is_finalist ? "#8fcbff" : "#f4f7fb"; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 122; y: 14; text: modelData.strategy + (modelData.is_finalist ? "  · FINAL" : ""); color: modelData.is_finalist ? "#c78cff" : "#9d7dff"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 280; y: 14; text: "$" + Number(modelData.entry).toFixed(2) + "  →  $" + Number(modelData.price).toFixed(2); color: "#b7c5d1"; font.pixelSize: 11; font.family: "Segoe UI" }
                        Text { anchors.right: parent.right; anchors.rightMargin: 12; y: 14; text: (modelData.pnl_pct >= 0 ? "+" : "") + Number(modelData.pnl_pct).toFixed(2) + "%"; color: modelData.pnl_pct >= 0 ? "#31e28b" : "#ff7782"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 10; y: 40; width: 730; text: modelData.reason || "Position wird nach der beim Einstieg gespeicherten Strategie verwaltet"; color: "#748a9e"; font.pixelSize: 9; elide: Text.ElideRight; font.family: "Segoe UI" }
                        MouseArea { id: rowHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                    }
                }
                Text { visible: bot && bot.openPositions === 0; anchors.centerIn: parent; text: "Noch keine Shadow-Positionen"; color: "#7d91a5"; font.pixelSize: 12; font.family: "Segoe UI" }
            }

            NeonCard {
                x: 840; y: 166; width: 548; height: 598
                accentColor: "#2dde80"; fillColor: "#061823"; fillColor2: "#092720"; borderColor: "#18704D"
                Text { x: 20; y: 18; text: "Engine Status"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 55; width: 330; height: 76; radius: 10; color: "#071B21"; border.width: 1; border.color: "#1B5948" }
                Rectangle { x: 390; y: 38; width: 118; height: 118; radius: 59; color: "transparent"; border.width: 1; border.color: "#125B49"; opacity: 0.75 }
                Rectangle { x: 401; y: 49; width: 96; height: 96; radius: 48; color: "transparent"; border.width: 2; border.color: "#20C878"; opacity: 0.55 }
                Rectangle { x: 410; y: 58; width: 78; height: 78; radius: 39; color: "#08251F"; border.width: 1; border.color: "#2DE487"; opacity: 0.95 }
                Image { x: 419; y: 67; width: 60; height: 60; source: Qt.resolvedUrl("../assets/ui/bot.png"); fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true }
                Rectangle { x: 445; y: 52; width: 7; height: 7; radius: 3.5; color: "#2DEB8E"; SequentialAnimation on opacity {
                    running: bot && bot.running
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.25; duration: 650 }
                    NumberAnimation { to: 1.0; duration: 650 }
                } }
                Rectangle { x: 36; y: 77; width: 9; height: 9; radius: 4.5; color: bot && bot.running ? "#31e28b" : "#74899d" }
                Text { x: 55; y: 68; text: bot && bot.running ? "RUNNING" : "STOPPED"; color: bot && bot.running ? "#31e28b" : "#9aacba"; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 55; y: 94; text: bot ? ("Stufe " + bot.level + " · " + bot.levelName + " · " + bot.modeText) : "—"; color: "#8398aa"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 20; y: 158; text: "Letzter Scan"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 158; text: bot ? bot.lastScanText : "—"; color: "#edf3f8"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 190; text: "Nächster Scan"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 190; text: bot ? bot.nextScanText : "—"; color: "#edf3f8"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 222; text: "Scans gesamt"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 222; text: bot ? bot.scanCount : "0"; color: "#edf3f8"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 254; text: "Trades gesamt"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 254; text: bot ? bot.tradeCount : "0"; color: "#edf3f8"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 286; text: "Shadow Equity"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 286; text: bot ? bot.paperEquityText : "—"; color: "#edf3f8"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 318; text: "Shadow P/L"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 198; y: 318; text: bot ? bot.pnlText : "—"; color: "#31e28b"; font.pixelSize: 11; font.family: "Segoe UI" }

                Rectangle { x: 20; y: 372; width: 508; height: 102; radius: 10; color: "#2A151D"; border.width: 1; border.color: "#91384A" }
                Rectangle { x: 34; y: 393; width: 42; height: 42; radius: 10; color: "#431923"; border.width: 1; border.color: "#7F3242" }
                Text { x: 34; y: 393; width: 42; height: 42; text: "⌑"; color: "#FF7180"; font.pixelSize: 25; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Segoe UI" }
                Text { x: 90; y: 388; text: "REAL AUTOTRADING LOCKED"; color: "#FF7F89"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 90; y: 416; width: 414; text: "Produktionssignale laufen im Shadow-Modus. Der REAL Execution Safety Core bleibt getrennt und gesperrt."; color: "#AFC0CD"; font.pixelSize: 10; wrapMode: Text.WordWrap; font.family: "Segoe UI" }

                Text { x: 20; y: 505; text: "Letzte Aktion"; color: "#71879b"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 20; y: 529; width: 508; height: 48; text: bot ? bot.lastActionText : "—"; color: "#e5edf4"; font.pixelSize: 10; wrapMode: Text.WordWrap; font.family: "Segoe UI" }
            }
        }

        // PORTFOLIO ---------------------------------------------------------------
        Item {
            visible: window.currentPage === 2
            x: 262; y: 116; width: 1388; height: 764

            MetricCard { x: 0; y: 0; width: 335; height: 174; title: "Cash Available"; onClicked: window.goPage(2); value: backend ? backend.cashText : "—"; subtitleLeft: "Buying Power"; subtitleRight: backend ? backend.cashText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/cash.svg"); accentColor: "#29a9ff" }
            MetricCard { x: 351; y: 0; width: 335; height: 174; title: "Invested"; onClicked: window.goPage(2); value: backend ? backend.investedText : "—"; subtitleLeft: backend ? backend.openPositionCountText : "Open Positions"; subtitleRight: backend ? backend.investedPctText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/invested.svg"); accentColor: "#2de487" }
            MetricCard { x: 702; y: 0; width: 335; height: 174; title: "Portfolio Value"; onClicked: window.goPage(2); value: backend ? backend.portfolioText : "—"; subtitleLeft: backend && backend.dataFresh ? "eToro REAL · LIVE" : "eToro REAL · STALE"; subtitleRight: backend ? backend.portfolioText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/value.svg"); accentColor: "#8d64ff" }
            NeonCard {
                x: 1053; y: 0; width: 335; height: 174; glow: false; accentColor: "#25aaff"
                Text { x: 20; y: 18; text: "Broker Sync"; color: "#dce5ed"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 20; y: 57; text: backend ? backend.brokerStatusText : "—"; color: backend && backend.brokerConnected ? "#31e28b" : "#91a4b7"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 112; width: 130; height: 38; radius: 8; color: "#0d3155"; border.width: 1; border.color: "#24639a" }
                Text { x: 20; y: 112; width: 130; height: 38; text: "REFRESH"; color: "#8fd2ff"; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Segoe UI" }
                MouseArea { x: 20; y: 112; width: 130; height: 38; cursorShape: Qt.PointingHandCursor; onClicked: if (backend) backend.refreshData() }
            }

            NeonCard {
                x: 0; y: 190; width: 600; height: 574; glow: false; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: "Open REAL Positions"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 55; width: 560; height: 1; color: "#16344c" }
                ListView {
                    x: 20; y: 70; width: 560; height: 470; clip: true
                    model: backend ? JSON.parse(backend.activityRowsJson) : []
                    delegate: Rectangle {
                        width: ListView.view.width; height: 64; color: index % 2 === 0 ? "#071827" : "transparent"
                        Text { x: 10; y: 12; text: modelData.symbol; color: modelData.is_finalist ? "#8fcbff" : "#f4f7fb"; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 10; y: 36; text: modelData.shares; color: "#758b9f"; font.pixelSize: 9; font.family: "Segoe UI" }
                        Text { anchors.right: parent.right; anchors.rightMargin: 12; y: 19; text: modelData.amount; color: "#dce6ef"; font.pixelSize: 12; font.family: "Segoe UI" }
                    }
                }
                Text { visible: backend && JSON.parse(backend.activityRowsJson).length === 0; anchors.centerIn: parent; text: "Keine offenen eToro-Positionen"; color: "#8296a9"; font.pixelSize: 12; font.family: "Segoe UI" }
            }

            NeonCard {
                x: 616; y: 190; width: 772; height: 574; glow: false; accentColor: "#8d64ff"
                Text { x: 20; y: 18; text: "Portfolio Overview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 56; text: backend ? backend.portfolioText : "—"; color: "#f4f7fb"; font.pixelSize: 27; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 91; text: backend && backend.todayAvailable ? (backend.todayText + "  " + backend.todayPctText) : "Today P/L: —"; color: "#31e28b"; font.pixelSize: 12; font.family: "Segoe UI" }
                Item {
                    x: 20; y: 126; width: 732; height: 300
                    PortfolioChart { anchors.fill: parent; points: backend && backend.chartReady ? JSON.parse(backend.portfolioChartJson) : [0.5,0.5] }
                    Text { anchors.centerIn: parent; visible: !(backend && backend.chartReady); text: "Portfolio-Verlauf wird lokal aufgezeichnet"; color: "#71879a"; font.pixelSize: 11; font.family: "Segoe UI" }
                }
                Rectangle { x: 20; y: 446; width: 732; height: 1; color: "#153149" }
                Text { x: 20; y: 466; text: "Invested"; color: "#93a5b7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 20; y: 490; text: backend ? backend.allocationInvestedValue : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 265; y: 466; text: "Positions"; color: "#93a5b7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 265; y: 490; text: backend ? backend.openPositionCountText : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 500; y: 466; text: "Cash"; color: "#93a5b7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 500; y: 490; text: backend ? backend.allocationCashValue : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 535; width: 732; height: 14; radius: 5; color: "#11283b" }
                Rectangle { x: 20; y: 535; width: backend ? 732 * backend.allocationInvestedFraction : 0; height: 14; radius: 5; color: "#2d78ff" }
            }
        }

        // MARKETS -----------------------------------------------------------------
        Item {
            visible: window.currentPage === 3
            x: 262; y: 116; width: 1388; height: 764
            NeonCard {
                anchors.fill: parent; glow: false; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: "Markets · Production Scanner"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "~1.000 Aktien → Fast Top 50 → Deep Analysis → Final Top 12 · Retry + Quarantine Cache"; color: "#8398ab"; font.pixelSize: 11; font.family: "Segoe UI" }

                Row {
                    x: 20; y: 78; spacing: 9
                    ScannerMetric { width: 180; height: 58; label: "UNIVERSE"; value: bot ? String(bot.universeCount) : "—"; detail: bot ? bot.scannerSourceText : ""; accentColor: "#2aa8ff" }
                    ScannerMetric { width: 180; height: 58; label: "SCANNED"; value: bot ? String(bot.scannerScanned) : "—"; detail: bot ? bot.scannerCacheText : ""; accentColor: "#24c9db" }
                    ScannerMetric { width: 180; height: 58; label: "CANDIDATES"; value: bot ? String(bot.scannerCandidates) : "—"; detail: "Fast Top 50"; accentColor: "#8d64ff" }
                    ScannerMetric { width: 180; height: 58; label: "DEEP"; value: bot ? String(bot.scannerDeep) : "—"; detail: "Production"; accentColor: "#5f8dff" }
                    ScannerMetric { width: 180; height: 58; label: "FINALISTS"; value: bot ? String(bot.scannerFinalists) : "—"; detail: "Final Top 12"; accentColor: "#b26cff" }
                    ScannerMetric { width: 180; height: 58; label: "BUY SIGNALS"; value: bot ? String(bot.scannerSignals) : "—"; detail: "Shadow"; accentColor: "#2de487" }
                    ScannerMetric { width: 180; height: 58; label: "DURATION"; value: bot ? bot.scannerDurationText : "—"; detail: bot && bot.scannerErrors > 0 ? (bot.scannerErrors + " errors") : "OK"; accentColor: bot && bot.scannerErrors > 0 ? "#ff727d" : "#2de487" }
                }

                Text { x: 22; y: 154; text: "SYMBOL"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 170; y: 154; text: "STRATEGY"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 355; y: 154; text: "SCORE"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 485; y: 154; text: "REASON"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 34; y: 154; text: "SIGNAL"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 174; width: 1348; height: 1; color: "#16344c" }
                ListView {
                    x: 20; y: 184; width: 1348; height: 549; clip: true
                    model: bot ? JSON.parse(bot.marketRowsJson) : []
                    delegate: Rectangle {
                        width: ListView.view.width; height: 62; color: index % 2 === 0 ? "#071827" : "transparent"
                        Text { x: 10; y: 13; text: modelData.symbol; color: modelData.is_finalist ? "#8fcbff" : "#f4f7fb"; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 150; y: 13; text: modelData.strategy + (modelData.is_finalist ? "  · FINAL" : ""); color: modelData.is_finalist ? "#c78cff" : "#9d7dff"; font.pixelSize: 11; font.family: "Segoe UI" }
                        Text { x: 335; y: 13; text: modelData.score + "%"; color: "#dce5ed"; font.pixelSize: 11; font.family: "Segoe UI" }
                        Text { x: 465; y: 13; width: 720; text: modelData.reason || ""; color: "#8da2b5"; font.pixelSize: 10; elide: Text.ElideRight; font.family: "Segoe UI" }
                        Rectangle { anchors.right: parent.right; anchors.rightMargin: 12; y: 10; width: 92; height: 30; radius: 7; color: modelData.signal === "BUY" ? "#0b392d" : (modelData.signal === "WATCH" ? "#3a2b0c" : "#0a1b29"); border.width: 1; border.color: modelData.signal === "BUY" ? "#1d7452" : (modelData.signal === "WATCH" ? "#785c20" : "#19384f") }
                        Text { anchors.right: parent.right; anchors.rightMargin: 12; y: 10; width: 92; height: 30; text: modelData.signal; color: modelData.signal === "BUY" ? "#31e28b" : (modelData.signal === "WATCH" ? "#f2c45b" : "#8ca0b4"); font.pixelSize: 10; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Segoe UI" }
                    }
                }
            }
        }

        // NEWS --------------------------------------------------------------------
        Item {
            visible: window.currentPage === 4
            x: 262; y: 116; width: 1388; height: 764
            NeonCard {
                anchors.fill: parent; glow: false; accentColor: "#278fff"
                Text { x: 20; y: 18; text: "International Market News"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "News-Layout ist aktiv. Die Live-Newsquelle wird separat angebunden."; color: "#8398ab"; font.pixelSize: 11; font.family: "Segoe UI" }
                Column {
                    x: 20; y: 86; width: 1348
                    NewsRow { width: 1348; imageSource: Qt.resolvedUrl("../assets/news/fed.png"); badge: "FED"; titleText: "Fed Minutes Signal Caution on Rate Cuts"; subtitle: "Officials emphasize data dependency amid persistent inflation risks."; timeText: "Preview"; badgeColor: "#0e3b69" }
                    NewsRow { width: 1348; imageSource: Qt.resolvedUrl("../assets/news/nasdaq.png"); badge: "NASDAQ"; titleText: "NASDAQ Rallies on Tech Earnings Beat"; subtitle: "Strong results from AI and cloud giants fuel market optimism."; timeText: "Preview"; badgeColor: "#39206f" }
                    NewsRow { width: 1348; imageSource: Qt.resolvedUrl("../assets/news/btc.png"); badge: "BTC"; titleText: "Bitcoin Holds Above $67K as ETF Inflows Rise"; subtitle: "Institutional demand continues to support bullish momentum."; timeText: "Preview"; badgeColor: "#5a3507" }
                    NewsRow { width: 1348; imageSource: Qt.resolvedUrl("../assets/news/europe.png"); badge: "EUROPE"; titleText: "European Markets Mixed Ahead of ECB Meet"; subtitle: "Investors await guidance as growth outlook remains uncertain."; timeText: "Preview"; badgeColor: "#083f73" }
                }
                Rectangle { x: 20; y: 485; width: 1348; height: 1; color: "#153149" }
                Text { x: 20; y: 515; text: "AI News Review"; color: "#f4f7fb"; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 552; width: 1348; height: 138; radius: 10; color: "#071827"; border.width: 1; border.color: "#17364e" }
                Text { x: 38; y: 573; text: "Vorbereitet"; color: "#8d64ff"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 38; y: 605; width: 1308; text: "Später werden relevante Unternehmens- und Makro-News vor einem Trade gefiltert und der jeweiligen Bot-Stufe zugeordnet. Dieser Build erfindet keine Live-News."; color: "#8da2b5"; font.pixelSize: 11; wrapMode: Text.WordWrap; font.family: "Segoe UI" }
            }
        }

        // BACKTEST ----------------------------------------------------------------
        Item {
            id: backtestPage
            property bool ran: false
            visible: window.currentPage === 5
            x: 262; y: 116; width: 1388; height: 764
            NeonCard {
                anchors.fill: parent; glow: false; accentColor: "#8d64ff"
                Text { x: 20; y: 18; text: "Backtest"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "Research Engine 0.6.1 bleibt getrennt von der laufenden Bot-Engine."; color: "#8398ab"; font.pixelSize: 11; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 90; width: 230; height: 44; radius: 8; color: "#0d3155"; border.width: 1; border.color: "#24639a" }
                Text { x: 20; y: 90; width: 230; height: 44; text: "RUN UI SMOKE BACKTEST"; color: "#8fd2ff"; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Segoe UI" }
                MouseArea { x: 20; y: 90; width: 230; height: 44; cursorShape: Qt.PointingHandCursor; onClicked: backtestPage.ran = true }
                NeonCard { x: 20; y: 164; width: 650; height: 270; glow: false; ambient: false; fillColor: "#061522"; fillColor2: "#081b2a"; borderColor: "#183b54" }
                Text { x: 42; y: 190; text: backtestPage.ran ? "UI Smoke Backtest abgeschlossen" : "Noch kein UI Smoke Backtest gestartet"; color: "#f4f7fb"; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 42; y: 232; width: 605; text: backtestPage.ran ? "FAST · DAY · WEEK · INVEST: erreichbar\nEngine State: OK\nREAL Trading: nicht Teil dieses UI-Tests" : "Der UI-Smoke-Test prüft die Verkabelung der Oberfläche. Die Research-Produktion wird dabei nicht verändert."; color: "#8da2b5"; font.pixelSize: 11; lineHeight: 1.5; wrapMode: Text.WordWrap; font.family: "Segoe UI" }
            }
        }

        // TRADES ------------------------------------------------------------------
        Item {
            visible: window.currentPage === 6
            x: 262; y: 116; width: 1388; height: 764
            NeonCard {
                anchors.fill: parent; glow: false; accentColor: "#2dde80"
                Text { x: 20; y: 18; text: "Trade History · Shadow Production Signals"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "Jede Position behält die Strategie, mit der sie eröffnet wurde."; color: "#8398ab"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 22; y: 88; text: "TIME"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 135; y: 88; text: "SYMBOL"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 260; y: 88; text: "SIDE"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 365; y: 88; text: "STRATEGY"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 515; y: 88; text: "AMOUNT"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 650; y: 88; text: "P/L"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Text { x: 790; y: 88; text: "REASON"; color: "#6f879c"; font.pixelSize: 9; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 108; width: 1348; height: 1; color: "#16344c" }
                ListView {
                    x: 20; y: 118; width: 1348; height: 615; clip: true
                    model: bot ? JSON.parse(bot.tradesJson) : []
                    delegate: Rectangle {
                        width: ListView.view.width; height: 58; color: index % 2 === 0 ? "#071827" : "transparent"
                        Text { x: 10; y: 18; text: modelData.time; color: "#74899d"; font.pixelSize: 9; font.family: "Segoe UI" }
                        Text { x: 115; y: 16; text: modelData.symbol; color: modelData.is_finalist ? "#8fcbff" : "#f4f7fb"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 240; y: 16; text: modelData.side; color: modelData.side === "BUY" ? "#31e28b" : "#f2b84b"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                        Text { x: 345; y: 16; text: modelData.strategy + (modelData.is_finalist ? "  · FINAL" : ""); color: modelData.is_finalist ? "#c78cff" : "#9d7dff"; font.pixelSize: 10; font.family: "Segoe UI" }
                        Text { x: 495; y: 16; text: "$" + Number(modelData.amount).toFixed(2); color: "#dce5ed"; font.pixelSize: 10; font.family: "Segoe UI" }
                        Text { x: 630; y: 16; text: modelData.pnl !== 0 ? ((modelData.pnl > 0 ? "+" : "") + "$" + Number(modelData.pnl).toFixed(2)) : "—"; color: modelData.pnl >= 0 ? "#31e28b" : "#ff7782"; font.pixelSize: 10; font.family: "Segoe UI" }
                        Text { x: 770; y: 16; width: 560; text: modelData.reason || ""; color: "#8398ab"; font.pixelSize: 10; elide: Text.ElideRight; font.family: "Segoe UI" }
                    }
                }
                Text { visible: bot && bot.tradeCount === 0; anchors.centerIn: parent; text: "Noch keine Shadow-Trades"; color: "#7d91a5"; font.pixelSize: 12; font.family: "Segoe UI" }
            }
        }

        // SETTINGS ----------------------------------------------------------------
        Item {
            visible: window.currentPage === 7
            x: 262; y: 116; width: 1388; height: 764
            NeonCard {
                anchors.fill: parent; glow: false; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: "Settings"; color: "#f4f7fb"; font.pixelSize: 18; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 49; text: "TradePilot Desktop · lokaler Entwicklungsstand"; color: "#8398ab"; font.pixelSize: 11; font.family: "Segoe UI" }

                Text { x: 20; y: 95; text: "DESIGN"; color: "#6f879c"; font.pixelSize: 9; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                NeonCard { x: 20; y: 120; width: 650; height: 118; glow: false; ambient: false; fillColor: "#061522"; fillColor2: "#081b2a"; borderColor: "#183b54" }
                Text { x: 42; y: 143; text: "TradePilot Finished Dark Design"; color: "#f4f7fb"; font.pixelSize: 14; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 42; y: 174; text: "Feste Designbasis · keine freie Neuinterpretation"; color: "#8da2b5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 20; y: 278; text: "BOT SAFETY"; color: "#6f879c"; font.pixelSize: 9; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                NeonCard { x: 20; y: 303; width: 650; height: 180; glow: false; ambient: false; fillColor: "#061522"; fillColor2: "#081b2a"; borderColor: "#183b54" }
                Text { x: 42; y: 328; text: "Mode"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 210; y: 328; text: bot ? bot.modeText : "—"; color: "#f2c45b"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 42; y: 360; text: "REAL AutoTrading"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 210; y: 360; text: bot ? bot.realLockText : "—"; color: "#ff7782"; font.pixelSize: 11; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 42; y: 392; text: "Shadow Equity"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 210; y: 392; text: bot ? bot.paperEquityText : "—"; color: "#f4f7fb"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 42; y: 424; text: "Strategy"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 210; y: 424; text: bot ? (bot.level + " · " + bot.levelName) : "—"; color: "#8fd2ff"; font.pixelSize: 11; font.family: "Segoe UI" }

                Text { x: 20; y: 530; text: "SHADOW TEST DATA"; color: "#6f879c"; font.pixelSize: 9; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 556; width: 210; height: 44; radius: 8; color: "#391921"; border.width: 1; border.color: "#7c3543" }
                Text { x: 20; y: 556; width: 210; height: 44; text: "RESET SHADOW DATA"; color: "#ff9299"; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.family: "Segoe UI" }
                MouseArea { x: 20; y: 556; width: 210; height: 44; cursorShape: Qt.PointingHandCursor; onClicked: if (bot) bot.resetShadow() }
                Text { x: 20; y: 622; width: 650; text: "Löscht ausschließlich lokale Shadow-Positionen und Shadow-Trades. eToro-REAL-Daten werden nicht verändert."; color: "#8398ab"; font.pixelSize: 10; wrapMode: Text.WordWrap; font.family: "Segoe UI" }
            }
        }

        // DASHBOARD ---------------------------------------------------------------
        Item {
            visible: window.currentPage === 0
            x: 262; y: 116; width: 1388; height: 764

            MetricCard { x: 0; y: 0; width: 335; height: 174; title: "Cash Available"; onClicked: window.goPage(2); value: backend ? backend.cashText : "—"; subtitleLeft: "Buying Power"; subtitleRight: backend ? backend.cashText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/cash.svg"); accentColor: "#29a9ff" }
            MetricCard { x: 351; y: 0; width: 335; height: 174; title: "Invested"; onClicked: window.goPage(2); value: backend ? backend.investedText : "—"; subtitleLeft: backend ? backend.openPositionCountText : "Open Positions"; subtitleRight: backend ? backend.investedPctText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/invested.svg"); accentColor: "#2de487" }
            MetricCard { x: 702; y: 0; width: 335; height: 174; title: "Portfolio Value"; onClicked: window.goPage(2); value: backend ? backend.portfolioText : "—"; subtitleLeft: backend && backend.dataFresh ? "eToro REAL · LIVE" : "eToro REAL · STALE"; subtitleRight: backend ? backend.portfolioText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/value.svg"); accentColor: "#8d64ff" }
            MetricCard { x: 1053; y: 0; width: 335; height: 174; title: "Today"; onClicked: window.goPage(6); value: backend ? backend.todayText : "—"; subtitleLeft: backend ? backend.todayPctText : "—"; subtitleRight: ""; iconSource: Qt.resolvedUrl("../assets/icons/today.svg"); accentColor: "#25aaff"; valueColor: backend && backend.todayAvailable ? "#35df8b" : "#91a4b7"; sparkline: backend ? backend.todayAvailable : false }

            // Recent Trades --------------------------------------------------------
            NeonCard {
                x: 0; y: 190; width: 380; height: 574
                glow: true; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: backend ? backend.activityTitle : "Open Positions"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle {
                    id: positionsViewAll
                    x: 286; y: 12; width: 74; height: 32; radius: 8
                    color: positionsViewMouse.containsMouse ? "#0D2C48" : "#071A29"
                    border.width: 1; border.color: positionsViewMouse.containsMouse ? "#3CAEFF" : "#214C6A"
                    Text { anchors.centerIn: parent; text: "View All  ›"; color: "#71C0FF"; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: positionsViewMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.goPage(2) }
                }
                Text { x: 20; y: 55; text: "Symbol"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 184; y: 55; text: "Side"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 242; y: 55; text: "Amount"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 55; text: "Time"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 75; width: 340; height: 1; color: "#16344c" }

                Column {
                    id: activityColumn
                    x: 20; y: 82; width: 340
                    property var rows: backend ? JSON.parse(backend.activityRowsJson) : []
                    Repeater {
                        model: activityColumn.rows
                        TradeRow {
                            width: 340
                            symbol: modelData.symbol || "POSITION"
                            company: modelData.company || ""
                            side: modelData.side || "OPEN"
                            amount: modelData.amount || "—"
                            shares: modelData.shares || ""
                            time: modelData.time || ""
                            logoSource: window.logoFor(symbol)
                        }
                    }
                }
                Text { visible: activityColumn.rows.length === 0; x: 20; y: 112; width: 340; text: backend && backend.brokerConnected ? "Keine offenen eToro-Positionen." : "Noch keine eToro-Daten. Keys einrichten und Verbindung testen."; color: "#8296a9"; font.pixelSize: 11; wrapMode: Text.WordWrap; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 530; width: 340; height: 1; color: "#143149" }
                Text { x: 20; y: 544; text: "Alle Zeiten in ET"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
            }

            // Portfolio Overview ---------------------------------------------------
            NeonCard {
                x: 396; y: 190; width: 460; height: 574
                glow: true; accentColor: "#685cff"
                Text { x: 20; y: 18; text: "Portfolio Overview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle {
                    id: rangeCycleButton
                    x: 364; y: 14; width: 74; height: 34; radius: 8
                    color: rangeCycleMouse.containsMouse ? "#0D2C48" : "#071521"
                    border.width: 1; border.color: rangeCycleMouse.containsMouse ? "#438FC1" : "#203f59"
                    Text { anchors.centerIn: parent; text: window.dashboardRange + "   ⌄"; color: "#dce6ef"; font.pixelSize: 11; font.family: "Segoe UI" }
                    MouseArea { id: rangeCycleMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.cycleDashboardRange() }
                }
                Text { x: 20; y: 59; text: backend ? backend.portfolioText : "—"; color: "#f4f7fb"; font.pixelSize: 26; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 93; text: backend && backend.todayAvailable ? (backend.todayText + " (" + backend.todayPctText + ")") : "Today P/L: —"; color: "#31e28b"; font.pixelSize: 12; font.family: "Segoe UI" }

                Item {
                    x: 20; y: 124; width: 420; height: 248
                    PortfolioChart { anchors.fill: parent; points: backend && backend.chartReady ? JSON.parse(backend.portfolioChartJson) : [0.5, 0.5] }
                    Text { anchors.centerIn: parent; visible: !(backend && backend.chartReady); text: backend && backend.brokerConnected ? "Portfolio-Verlauf wird ab jetzt lokal aufgezeichnet" : "Warte auf eToro-Daten"; color: "#71879a"; font.pixelSize: 11; font.family: "Segoe UI" }
                    Column {
                        anchors.right: parent.right; anchors.top: parent.top; anchors.topMargin: 11; spacing: 45
                        Repeater { model: ["103K", "101K", "99K", "97K"]
                            Text { text: modelData; color: "#8396a9"; font.pixelSize: 9; font.family: "Segoe UI" }
                        }
                    }
                    Row {
                        x: 4; y: 225; width: 370; spacing: 34
                        Repeater { model: ["09:30 AM", "11:00 AM", "12:30 PM", "02:00 PM", "04:00 PM"]
                            Text { text: modelData; color: "#7d91a5"; font.pixelSize: 8; font.family: "Segoe UI" }
                        }
                    }
                }

                Row {
                    x: 20; y: 389; spacing: 7
                    Repeater {
                        model: ["1D","1W","1M","3M","YTD","1Y","All"]
                        Rectangle {
                            id: rangeButton
                            width: 53; height: 34; radius: 7
                            property bool selected: window.dashboardRange === modelData
                            color: selected ? "#0D3A61" : (rangeMouse.containsMouse ? "#0A2235" : "#071521")
                            border.width: 1; border.color: selected ? "#399BDB" : (rangeMouse.containsMouse ? "#315F7D" : "#19384f")
                            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.leftMargin: 8; anchors.rightMargin: 8; height: 2; radius: 1; color: "#42B7FF"; opacity: selected ? 0.9 : 0.0 }
                            Text { anchors.centerIn: parent; text: modelData; color: selected ? "#A6DDFF" : "#93a5b7"; font.pixelSize: 10; font.weight: selected ? Font.DemiBold : Font.Normal; font.family: "Segoe UI" }
                            MouseArea { id: rangeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.dashboardRange = modelData }
                        }
                    }
                }
                Rectangle { x: 20; y: 435; width: 420; height: 1; color: "#153149" }

                Text { x: 20; y: 447; text: "●"; color: "#2c83ff"; font.pixelSize: 13 }
                Text { x: 38; y: 447; text: "Invested"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 38; y: 471; text: backend ? backend.allocationInvestedValue : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 38; y: 493; text: backend ? backend.allocationInvestedPct : "—"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 176; y: 447; text: "●"; color: "#8b61ff"; font.pixelSize: 13 }
                Text { x: 194; y: 447; text: "Positions"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 194; y: 471; text: backend ? backend.openPositionCountText : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 194; y: 493; text: "READ ONLY"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 326; y: 447; text: "●"; color: "#2cc6d8"; font.pixelSize: 13 }
                Text { x: 344; y: 447; text: "Cash"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 344; y: 471; text: backend ? backend.allocationCashValue : "—"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 344; y: 493; text: backend ? backend.allocationCashPct : "—"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Rectangle {
                    x: 20; y: 531; width: 420; height: 16; radius: 5; color: "#11283b"
                    Rectangle { x: 0; y: 0; width: backend ? 420 * backend.allocationInvestedFraction : 0; height: 16; radius: 5; color: "#2d78ff" }
                    Rectangle { x: backend ? 420 * backend.allocationInvestedFraction : 0; y: 0; width: backend ? 420 * (1.0 - backend.allocationInvestedFraction) : 0; height: 16; radius: 5; color: "#26c7d3" }
                }
            }

            // News ----------------------------------------------------------------
            NeonCard {
                x: 872; y: 190; width: 516; height: 350
                glow: true; accentColor: "#278fff"
                Text { x: 20; y: 18; text: "International Market News · Preview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle {
                    id: newsViewAll
                    x: 422; y: 12; width: 74; height: 32; radius: 8
                    color: newsViewMouse.containsMouse ? "#0D2C48" : "#071A29"
                    border.width: 1; border.color: newsViewMouse.containsMouse ? "#3CAEFF" : "#214C6A"
                    Text { anchors.centerIn: parent; text: "View All  ›"; color: "#71C0FF"; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: newsViewMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.goPage(4) }
                }
                Column {
                    x: 20; y: 54; width: 476
                    NewsRow { width: 476; onClicked: window.goPage(4); imageSource: Qt.resolvedUrl("../assets/news/fed.png"); badge: "FED"; titleText: "Fed Minutes Signal Caution on Rate Cuts"; subtitle: "Officials emphasize data dependency amid persistent inflation risks."; timeText: "7m ago"; badgeColor: "#0e3b69" }
                    NewsRow { width: 476; onClicked: window.goPage(4); imageSource: Qt.resolvedUrl("../assets/news/nasdaq.png"); badge: "NASDAQ"; titleText: "NASDAQ Rallies on Tech Earnings Beat"; subtitle: "Strong results from AI and cloud giants fuel market optimism."; timeText: "29m ago"; badgeColor: "#39206f" }
                    NewsRow { width: 476; onClicked: window.goPage(4); imageSource: Qt.resolvedUrl("../assets/news/btc.png"); badge: "BTC"; titleText: "Bitcoin Holds Above $67K as ETF Inflows Rise"; subtitle: "Institutional demand continues to support bullish momentum."; timeText: "46m ago"; badgeColor: "#5a3507" }
                    NewsRow { width: 476; onClicked: window.goPage(4); imageSource: Qt.resolvedUrl("../assets/news/europe.png"); badge: "EUROPE"; titleText: "European Markets Mixed Ahead of ECB Meet"; subtitle: "Investors await guidance as growth outlook remains uncertain."; timeText: "1h ago"; badgeColor: "#083f73" }
                }
            }

            // Bot Status -----------------------------------------------------------
            NeonCard {
                x: 872; y: 556; width: 516; height: 208
                accentColor: "#2dde80"; fillColor: "#061823"; fillColor2: "#09231f"; borderColor: "#18533d"
                Text { x: 20; y: 18; text: "Bot Status"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }

                Rectangle { x: 23; y: 54; width: 100; height: 100; radius: 50; color: "transparent"; border.width: 8; border.color: "#0b2f29" }
                Rectangle { x: 29; y: 60; width: 88; height: 88; radius: 44; color: "transparent"; border.width: 2; border.color: "#2de487"; opacity: 0.64 }
                Image { x: 35; y: 66; width: 76; height: 76; source: Qt.resolvedUrl("../assets/ui/bot.png"); fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true }

                Rectangle { x: 143; y: 59; width: 163; height: 34; radius: 8; color: "#0b392d"; border.width: 1; border.color: "#1d7452" }
                Rectangle { x: 157; y: 72; width: 7; height: 7; radius: 3.5; color: "#31e28b" }
                Text { x: 172; y: 69; text: backend ? backend.brokerStatusText : "eToro"; color: "#31e28b"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 143; y: 108; text: "🔒  REAL AutoTrading gesperrt"; color: "#b4c0cc"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 135; text: "Strategie:"; color: "#93a4b6"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 199; y: 135; text: bot ? ("Stufe " + bot.level + " · " + bot.levelName) : "Production Strategy"; color: "#4aa7ff"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 160; text: backend ? ("◷  " + backend.lastRefreshText + " · " + backend.freshnessText) : "◷  Noch nicht aktualisiert"; color: "#8ea2b5"; font.pixelSize: 10; font.family: "Segoe UI" }
                Rectangle {
                    x: 392; y: 135; width: 101; height: 38; radius: 9
                    color: viewBotMouse.containsMouse ? "#18354a" : "#081722"; border.width: 1; border.color: "#2f6b8d"
                    Text { anchors.centerIn: parent; text: "View Bot  ›"; color: "#8fd3ff"; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: viewBotMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: window.goPage(1) }
                }
            }
        }

        // FOOTER ------------------------------------------------------------------
        Rectangle {
            x: 240; y: 917; width: 1432; height: 24
            color: "#020b14"; border.width: 1; border.color: "#123047"
            Text { x: 17; anchors.verticalCenter: parent.verticalCenter; text: "ⓘ  Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse."; color: "#698095"; font.pixelSize: 9; font.family: "Segoe UI" }
            Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "Desktop Alpha 0.13.5 · Scanner Optimization · Visual Polish II · 1000 Stocks"; color: "#536d83"; font.pixelSize: 9; font.family: "Segoe UI" }
        }
    }

}
