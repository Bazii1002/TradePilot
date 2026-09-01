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
    title: "TradePilot · " + (backend ? backend.version : "UI Prototype 0.5.1")

    property int currentPage: 0
    property var navNames: ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]
    property var navIcons: [Qt.resolvedUrl("../assets/icons/dashboard.svg"), Qt.resolvedUrl("../assets/icons/bot.svg"), Qt.resolvedUrl("../assets/icons/portfolio.svg"), Qt.resolvedUrl("../assets/icons/markets.svg"), Qt.resolvedUrl("../assets/icons/news.svg"), Qt.resolvedUrl("../assets/icons/backtest.svg"), Qt.resolvedUrl("../assets/icons/trades.svg"), Qt.resolvedUrl("../assets/icons/settings.svg")]
    property real designW: 1672
    property real designH: 941

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
            Text { x: 84; y: 62; text: "1.0 · UI Prototype 0.5.1"; color: "#6f8498"; font.pixelSize: 10; font.family: "Segoe UI" }

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
            Text { x: 27; y: 894; width: 186; text: "UI Prototype · keine Broker-Orders"; color: "#4f687c"; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.family: "Segoe UI" }
        }

        // TOP BAR -----------------------------------------------------------------
        Rectangle {
            x: 240; y: 0; width: 1432; height: 96
            color: "#020b15"
            border.width: 1; border.color: "#123047"
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 1; color: "#17415c"; opacity: 0.52 }

            MarketPill { x: 708; y: 19; market: "NYSE"; stateText: "Open"; open: true }
            MarketPill { x: 873; y: 19; market: "NASDAQ"; stateText: "Open"; open: true }
            MarketPill { x: 1038; y: 19; width: 178; market: "XETRA"; stateText: "Closed"; subText: "opens later"; open: false }

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

            MetricCard { x: 0; y: 0; width: 335; height: 174; title: "Cash Available"; value: "$18,742.63"; subtitleLeft: "Buying Power"; subtitleRight: "$18,742.63"; iconSource: Qt.resolvedUrl("../assets/icons/cash.svg"); accentColor: "#29a9ff" }
            MetricCard { x: 351; y: 0; width: 335; height: 174; title: "Invested"; value: "$82,317.58"; subtitleLeft: "In Positions"; subtitleRight: "84.2% of Portfolio"; iconSource: Qt.resolvedUrl("../assets/icons/invested.svg"); accentColor: "#2de487" }
            MetricCard { x: 702; y: 0; width: 335; height: 174; title: "Portfolio Value"; value: "$101,060.21"; subtitleLeft: "Total Value"; subtitleRight: "$101,060.21"; iconSource: Qt.resolvedUrl("../assets/icons/value.svg"); accentColor: "#8d64ff" }
            MetricCard { x: 1053; y: 0; width: 335; height: 174; title: "Today"; value: "+$1,412.63"; subtitleLeft: "+1.41%"; subtitleRight: ""; iconSource: Qt.resolvedUrl("../assets/icons/today.svg"); accentColor: "#25aaff"; valueColor: "#35df8b"; sparkline: true }

            // Recent Trades --------------------------------------------------------
            NeonCard {
                x: 0; y: 190; width: 380; height: 574
                glow: false; accentColor: "#2aa8ff"
                Text { x: 20; y: 18; text: "Recent Trades"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 18; y: 20; text: "View All  ›"; color: "#52a9ff"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 20; y: 55; text: "Symbol"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 184; y: 55; text: "Side"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { x: 242; y: 55; text: "Amount"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 55; text: "Time"; color: "#8294a7"; font.pixelSize: 10; font.family: "Segoe UI" }
                Rectangle { x: 20; y: 75; width: 340; height: 1; color: "#16344c" }

                Column {
                    x: 20; y: 82; width: 340
                    TradeRow { width: 340; symbol: "AAPL"; company: "Apple Inc."; side: "BUY"; amount: "$5,320.00"; shares: "20 Shares"; time: "10:31:22 AM"; logoSource: Qt.resolvedUrl("../assets/company/aapl.png") }
                    TradeRow { width: 340; symbol: "NVDA"; company: "NVIDIA Corp."; side: "SELL"; amount: "$3,850.40"; shares: "10 Shares"; time: "10:22:11 AM"; logoSource: Qt.resolvedUrl("../assets/company/nvda.png") }
                    TradeRow { width: 340; symbol: "MSFT"; company: "Microsoft Corp."; side: "BUY"; amount: "$4,100.00"; shares: "25 Shares"; time: "10:15:08 AM"; logoSource: Qt.resolvedUrl("../assets/company/msft.png") }
                    TradeRow { width: 340; symbol: "TSLA"; company: "Tesla, Inc."; side: "SELL"; amount: "$2,760.00"; shares: "12 Shares"; time: "09:58:47 AM"; logoSource: Qt.resolvedUrl("../assets/company/tsla.png") }
                    TradeRow { width: 340; symbol: "SPY"; company: "SPDR S&P 500 ETF"; side: "BUY"; amount: "$1,875.50"; shares: "15 Shares"; time: "09:41:33 AM"; logoSource: Qt.resolvedUrl("../assets/company/spy.png") }
                }
                Rectangle { x: 20; y: 530; width: 340; height: 1; color: "#143149" }
                Text { x: 20; y: 544; text: "Alle Zeiten in ET"; color: "#74899d"; font.pixelSize: 10; font.family: "Segoe UI" }
            }

            // Portfolio Overview ---------------------------------------------------
            NeonCard {
                x: 396; y: 190; width: 460; height: 574
                glow: false; accentColor: "#685cff"
                Text { x: 20; y: 18; text: "Portfolio Overview"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Rectangle { x: 364; y: 14; width: 74; height: 34; radius: 8; color: "#071521"; border.width: 1; border.color: "#203f59"; Text { anchors.centerIn: parent; text: "1D   ⌄"; color: "#dce6ef"; font.pixelSize: 11; font.family: "Segoe UI" } }
                Text { x: 20; y: 59; text: "$101,060.21"; color: "#f4f7fb"; font.pixelSize: 26; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 20; y: 93; text: "+$1,412.63 (+1.41%)"; color: "#31e28b"; font.pixelSize: 12; font.family: "Segoe UI" }

                Item {
                    x: 20; y: 124; width: 420; height: 248
                    PortfolioChart { anchors.fill: parent }
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
                Text { x: 38; y: 447; text: "Stocks"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 38; y: 471; text: "$72,325.10"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 38; y: 493; text: "71.6%"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 176; y: 447; text: "●"; color: "#8b61ff"; font.pixelSize: 13 }
                Text { x: 194; y: 447; text: "ETFs"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 194; y: 471; text: "$18,430.35"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 194; y: 493; text: "18.2%"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Text { x: 326; y: 447; text: "●"; color: "#2cc6d8"; font.pixelSize: 13 }
                Text { x: 344; y: 447; text: "Cash"; color: "#a8b5c2"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 344; y: 471; text: "$10,304.76"; color: "#f4f7fb"; font.pixelSize: 14; font.family: "Segoe UI" }
                Text { x: 344; y: 493; text: "10.2%"; color: "#7f91a5"; font.pixelSize: 10; font.family: "Segoe UI" }

                Rectangle {
                    x: 20; y: 531; width: 420; height: 16; radius: 5; color: "#11283b"
                    Rectangle { x: 0; y: 0; width: 301; height: 16; radius: 5; color: "#2d78ff" }
                    Rectangle { x: 301; y: 0; width: 76; height: 16; color: "#8b61ff" }
                    Rectangle { x: 377; y: 0; width: 43; height: 16; radius: 5; color: "#26c7d3" }
                }
            }

            // News ----------------------------------------------------------------
            NeonCard {
                x: 872; y: 190; width: 516; height: 350
                glow: false; accentColor: "#278fff"
                Text { x: 20; y: 18; text: "International Market News"; color: "#f4f7fb"; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: "Segoe UI" }
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
                Text { x: 172; y: 69; text: "eToro REAL"; color: "#31e28b"; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: "Segoe UI" }
                Text { x: 143; y: 108; text: "🔒  AutoTrader → REAL gesperrt"; color: "#b4c0cc"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 135; text: "Strategie:"; color: "#93a4b6"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 199; y: 135; text: "Research Engine 0.6.1"; color: "#4aa7ff"; font.pixelSize: 11; font.family: "Segoe UI" }
                Text { x: 143; y: 160; text: "◷  Letzte Analyse: vor 4 Min."; color: "#8ea2b5"; font.pixelSize: 10; font.family: "Segoe UI" }
                Rectangle { x: 405; y: 135; width: 88; height: 38; radius: 9; color: "#081722"; border.width: 1; border.color: "#294b61"; Text { anchors.centerIn: parent; text: "View Bot  ›"; color: "#e3ebf2"; font.pixelSize: 10; font.family: "Segoe UI" } }
            }
        }

        // FOOTER ------------------------------------------------------------------
        Rectangle {
            x: 240; y: 917; width: 1432; height: 24
            color: "#020b14"; border.width: 1; border.color: "#123047"
            Text { x: 17; anchors.verticalCenter: parent.verticalCenter; text: "ⓘ  Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse."; color: "#698095"; font.pixelSize: 9; font.family: "Segoe UI" }
            Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter; text: "UI Prototype 0.5.1 · Runtime Fix"; color: "#536d83"; font.pixelSize: 9; font.family: "Segoe UI" }
        }
    }
}
