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
    title: "TradePilot · " + (backend ? backend.version : "UI Prototype 0.6")

    property int currentPage: 0
    property var navNames: ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]
    property var navIcons: [Qt.resolvedUrl("../assets/icons/dashboard.svg"), Qt.resolvedUrl("../assets/icons/bot.svg"), Qt.resolvedUrl("../assets/icons/portfolio.svg"), Qt.resolvedUrl("../assets/icons/markets.svg"), Qt.resolvedUrl("../assets/icons/news.svg"), Qt.resolvedUrl("../assets/icons/backtest.svg"), Qt.resolvedUrl("../assets/icons/trades.svg"), Qt.resolvedUrl("../assets/icons/settings.svg")]
    property real designW: 1672
    property real designH: 941

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
        Rectangle { x: 1030; y: -130; width: 720; height: 270; radius: 135; color: "#0b4d91"; opacity: 0.025 }
        Rectangle { x: 1150; y: 700; width: 570; height: 260; radius: 130; color: "#0b684e"; opacity: 0.035 }
        Rectangle { x: 420; y: 260; width: 650; height: 300; radius: 150; color: "#33256c"; opacity: 0.010 }

        // SIDEBAR -----------------------------------------------------------------
        Rectangle {
            x: 0; y: 0; width: 240; height: 941
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#04121f" }
                GradientStop { position: 1.0; color: "#020e18" }
            }
            border.width: 1; border.color: "#123248"

            Image {
                x: 28; y: 22; width: 48; height: 43
                source: Qt.resolvedUrl("../assets/ui/logo.png")
                fillMode: Image.PreserveAspectFit
                smooth: true; mipmap: true
            }
            Text { x: 84; y: 31; text: "TradePilot"; color: "#f7f9fc"; font.pixelSize: 24; font.weight: Font.DemiBold; font.family: "Segoe UI" }
            Text { x: 84; y: 62; text: "1.0 · UI Prototype 0.6.5"; color: "#6f8498"; font.pixelSize: 10; font.family: "Segoe UI" }

            Column {
                x: 12; y: 114; width: 216; spacing: 5
                Repeater {
                    model: 8
                    NavItem {
                        width: 216
                        label: window.navNames[index]
                        iconSource: window.navIcons[index]
                        selected: window.currentPage === index
                        onClicked: { window.currentPage=index; if (backend) backend.navigationClicked(label) }
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
            Text { x: 27; y: 894; width: 186; text: "Live Dashboard · eToro READ ONLY"; color: "#4f687c"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.family: "Segoe UI" }
        }

        // TOP BAR -----------------------------------------------------------------
        Rectangle {
            x: 240; y: 0; width: 1432; height: 96
            color: "#020b15"
            border.width: 1; border.color: "#123047"
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#17415c"; opacity: 0.52 }

            MarketPill { x: 688; y: 18; width: 158; market: "NYSE"; stateText: backend ? backend.nyseState : "—"; subText: backend ? backend.nyseSub : ""; open: backend ? backend.nyseOpen : false }
            MarketPill { x: 858; y: 18; width: 158; market: "NASDAQ"; stateText: backend ? backend.nasdaqState : "—"; subText: backend ? backend.nasdaqSub : ""; open: backend ? backend.nasdaqOpen : false }
            MarketPill { x: 1028; y: 18; width: 184; market: "XETRA"; stateText: backend ? backend.xetraState : "—"; subText: backend ? backend.xetraSub : ""; open: backend ? backend.xetraOpen : false }

            Image { x: 1245; y: 28; width: 30; height: 30; source: Qt.resolvedUrl("../assets/icons/bell.svg"); fillMode: Image.PreserveAspectFit; smooth: true }
            Rectangle { x: 1268; y: 24; width: 6; height: 6; radius: 3; color: "#2F96FF" }

            Rectangle {
                x: 1302; y: 17; width: 54; height: 54; radius: 27
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#0A2033" }
                    GradientStop { position: 1.0; color: "#06131F" }
                }
                border.width: 1; border.color: "#38556E"
                Image { anchors.centerIn: parent; width: 31; height: 31; source: Qt.resolvedUrl("../assets/icons/profile.svg"); fillMode: Image.PreserveAspectFit; smooth: true }
            }
        }

        // Placeholder pages until dashboard is frozen.
        Item {
            visible: window.currentPage !== 0
            x: 240; y: 96; width: 1432; height: 821
            Text { anchors.centerIn: parent; text: window.navNames[window.currentPage] + " · wird nach Freigabe des Dashboard-Designs gebaut"; color: "#8ba0b5"; font.pixelSize: 20; font.family: "Segoe UI" }
        }

        // DASHBOARD ---------------------------------------------------------------
        Item {
            visible: window.currentPage === 0
            x: 262; y: 116; width: 1388; height: 764

            MetricCard { x: 0; y: 0; width: 335; height: 174; title: "Cash Available"; value: backend ? backend.cashText : "—"; subtitleLeft: "Buying Power"; subtitleRight: backend ? backend.cashText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/cash.svg"); accentColor: "#29a9ff" }
            MetricCard { x: 351; y: 0; width: 335; height: 174; title: "Invested"; value: backend ? backend.investedText : "—"; subtitleLeft: backend ? backend.openPositionCountText : "Open Positions"; subtitleRight: backend ? backend.investedPctText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/invested.svg"); accentColor: "#2de487" }
            MetricCard { x: 702; y: 0; width: 335; height: 174; title: "Portfolio Value"; value: backend ? backend.portfolioText : "—"; subtitleLeft: backend && backend.dataFresh ? "eToro REAL · LIVE" : "eToro REAL · STALE"; subtitleRight: backend ? backend.portfolioText : "—"; iconSource: Qt.resolvedUrl("../assets/icons/value.svg"); accentColor: "#8d64ff" }
            MetricCard { x: 1053; y: 0; width: 335; height: 174; title: "Today"; value: backend ? backend.todayText : "—"; subtitleLeft: backend ? backend.todayPctText : "—"; subtitleRight: ""; iconSource: Qt.resolvedUrl("../assets/icons/today.svg"); accentColor: "#25aaff"; valueColor: backend && backend.todayAvailable ? "#35df8b" : "#91a4b7"; sparkline: backend ? backend.todayAvailable : false }

            // Recent Trades --------------------------------------------------------
            NeonCard {
                x: 0; y: 190; width: 380; height: 574
                glow: false; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: backend ? backend.activityTitle : "Open Positions"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 18; y: 20; text: "View All  ›"; color: "#52a9ff"; font.pixelSize: 11; font.family: "Segoe UI" }
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
                glow: false; accentColor: "#685cff"
                Text { x: 20; y: 18; text: "Portfolio Overview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 364; y: 14; width: 74; height: 34; radius: 8; color: "#071521"; border.width: 1; border.color: "#203f59"; Text { anchors.centerIn: parent; text: "1D   ⌄"; color: "#dce6ef"; font.pixelSize: 11; font.family: "Segoe UI" } }
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
                            width: 53; height: 34; radius: 7
                            color: index===0 ? "#0d3155" : "#071521"
                            border.width: 1; border.color: index===0 ? "#24639a" : "#19384f"
                            Text { anchors.centerIn: parent; text: modelData; color: index===0 ? "#7fc5ff" : "#93a5b7"; font.pixelSize: 10; font.family: "Segoe UI" }
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
                glow: false; accentColor: "#278fff"
                Text { x: 20; y: 18; text: "International Market News · Preview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 18; y: 20; text: "View All  ›"; color: "#52a9ff"; font.pixelSize: 11; font.family: "Segoe UI" }
                Column {
                    x: 20; y: 54; width: 476
                    NewsRow { width: 476; imageSource: Qt.resolvedUrl("../assets/news/fed.png"); badge: "FED"; titleText: "Fed Minutes Signal Caution on Rate Cuts"; subtitle: "Officials emphasize data dependency amid persistent inflation risks."; timeText: "7m ago"; badgeColor: "#0e3b69" }
                    NewsRow { width: 476; imageSource: Qt.resolvedUrl("../assets/news/nasdaq.png"); badge: "NASDAQ"; titleText: "NASDAQ Rallies on Tech Earnings Beat"; subtitle: "Strong results from AI and cloud giants fuel market optimism."; timeText: "29m ago"; badgeColor: "#39206f" }
                    NewsRow { width: 476; imageSource: Qt.resolvedUrl("../assets/news/btc.png"); badge: "BTC"; titleText: "Bitcoin Holds Above $67K as ETF Inflows Rise"; subtitle: "Institutional demand continues to support bullish momentum."; timeText: "46m ago"; badgeColor: "#5a3507" }
                    NewsRow { width: 476; imageSource: Qt.resolvedUrl("../assets/news/europe.png"); badge: "EUROPE"; titleText: "European Markets Mixed Ahead of ECB Meet"; subtitle: "Investors await guidance as growth outlook remains uncertain."; timeText: "1h ago"; badgeColor: "#083f73" }
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
                Text { x: 143; y: 108; text: "🔒  AutoTrader → REAL gesperrt"; color: "#b4c0cc"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 135; text: "Strategie:"; color: "#93a4b6"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 199; y: 135; text: "Research Engine 0.6.1"; color: "#4aa7ff"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 160; text: backend ? ("◷  " + backend.lastRefreshText + " · " + backend.freshnessText) : "◷  Noch nicht aktualisiert"; color: "#8ea2b5"; font.pixelSize: 10; font.family: "Segoe UI" }
                Rectangle {
                    x: 392; y: 135; width: 101; height: 38; radius: 9
                    color: liveMouse.containsMouse ? "#18354a" : "#081722"; border.width: 1; border.color: "#2f6b8d"
                    Text { anchors.centerIn: parent; text: "LIVE Test"; color: "#8fd3ff"; font.pixelSize: 10; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                    MouseArea { id: liveMouse; anchors.fill: parent; hoverEnabled: true; onClicked: liveDialog.open() }
                }
            }
        }

        // FOOTER ------------------------------------------------------------------
        Rectangle {
            x: 240; y: 917; width: 1432; height: 24
            color: "#020b14"; border.width: 1; border.color: "#123047"
            Text { x: 17; anchors.verticalCenter: parent.verticalCenter; text: "ⓘ  Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse."; color: "#698095"; font.pixelSize: 9; font.family: "Segoe UI" }
            Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "UI Prototype 0.6.6 · Manual LIVE Execution Bridge"; color: "#536d83"; font.pixelSize: 9; font.family: "Segoe UI" }
        }
    }

    Dialog {
        id: liveDialog
        modal: true
        anchors.centerIn: parent
        width: 560
        height: 650
        padding: 0
        closePolicy: Popup.NoAutoClose
        background: Rectangle {
            radius: 18
            color: "#06111c"
            border.width: 1
            border.color: "#24577a"
        }
        contentItem: Item {
            anchors.fill: parent
            Text { x: 28; y: 24; text: "eToro REAL · Manueller LIVE-Test"; color: "#f4f7fb"; font.pixelSize: 22; font.weight: Font.DemiBold; font.family: "Segoe UI" }
            Text { x: 28; y: 62; width: 500; wrapMode: Text.WordWrap; text: "ECHTGELD. Maximal 10 EUR · BUY only · Hebel 1x · AutoTrader bleibt gesperrt."; color: "#ffba6a"; font.pixelSize: 12; font.family: "Segoe UI" }

            Text { x: 28; y: 110; text: "Ticker"; color: "#91a7ba"; font.pixelSize: 11; font.family: "Segoe UI" }
            TextField { id: liveSymbol; x: 28; y: 130; width: 180; height: 42; text: "AAPL"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI"; background: Rectangle { radius: 8; color: "#091a27"; border.color: "#23475f" } }
            Text { x: 230; y: 110; text: "Budget EUR"; color: "#91a7ba"; font.pixelSize: 11; font.family: "Segoe UI" }
            TextField { id: liveAmount; x: 230; y: 130; width: 140; height: 42; text: "10"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI"; validator: DoubleValidator { bottom: 0.01; top: 10.0; decimals: 2 }; background: Rectangle { radius: 8; color: "#091a27"; border.color: "#23475f" } }
            Button { x: 390; y: 130; width: 140; height: 42; text: "Vorbereiten"; enabled: backend && !backend.liveBusy; onClicked: backend.prepareLiveBuy(liveSymbol.text, Number(liveAmount.text.replace(",","."))) }

            Rectangle { x: 28; y: 195; width: 502; height: 270; radius: 12; color: "#04101a"; border.width: 1; border.color: "#173950" }
            Text { x: 46; y: 214; width: 466; height: 230; wrapMode: Text.WordWrap; text: backend ? backend.liveReviewText : "—"; color: "#dbe8f3"; font.pixelSize: 13; lineHeight: 1.2; font.family: "Segoe UI" }

            Text { x: 28; y: 486; text: "Finale Bestätigung"; color: "#91a7ba"; font.pixelSize: 11; font.family: "Segoe UI" }
            TextField { id: liveConfirm; x: 28; y: 507; width: 240; height: 42; placeholderText: "LIVE eintippen"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI"; background: Rectangle { radius: 8; color: "#091a27"; border.color: "#6c3b3b" } }
            Button { x: 286; y: 507; width: 244; height: 42; text: "ECHTGELDORDER SENDEN"; enabled: backend && backend.livePrepared && !backend.liveBusy && liveConfirm.text.toUpperCase() === "LIVE"; onClicked: { if (backend.executePreparedLiveBuy(liveConfirm.text)) liveConfirm.text = "" } }

            Text { x: 28; y: 566; width: 502; wrapMode: Text.WordWrap; text: backend ? backend.liveStatusText : "—"; color: "#8fc8ea"; font.pixelSize: 11; font.family: "Segoe UI" }
            Button { x: 28; y: 605; width: 120; height: 34; text: "Abbrechen"; onClicked: { if (backend) backend.cancelPreparedLiveBuy(); liveConfirm.text=""; liveDialog.close() } }
        }
    }

}
