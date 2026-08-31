import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window
    width: 1660
    height: 930
    minimumWidth: 1280
    minimumHeight: 760
    visible: true
    color: "#030d16"
    title: "TradePilot · " + backend.version

    property int currentPage: 0
    property var navNames: ["Dashboard", "Bot", "Portfolio", "Markets", "News", "Backtest", "Trades", "Settings"]
    property var navGlyphs: ["▦", "♙", "◔", "◎", "▤", "⌁", "⇄", "⚙"]

    Rectangle {
        anchors.fill: parent
        color: "#030d16"

        // very subtle upper blue ambience
        Rectangle {
            anchors.top: parent.top
            anchors.right: parent.right
            width: parent.width * 0.55
            height: 180
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00000000" }
                GradientStop { position: 1.0; color: "#0b2b64aa" }
            }
            opacity: 0.18
        }

        RowLayout {
            anchors.fill: parent
            spacing: 0

            // SIDEBAR
            Rectangle {
                Layout.preferredWidth: 244
                Layout.fillHeight: true
                color: "#04111c"
                border.width: 1
                border.color: "#123047"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        spacing: 12
                        Text { text: "TP"; font.pixelSize: 30; font.weight: Font.Black; color: "#58a9ff" }
                        Text { text: "TradePilot"; font.pixelSize: 24; font.weight: Font.DemiBold; color: "#f8fbff" }
                    }

                    Repeater {
                        model: 8
                        delegate: NavItem {
                            Layout.fillWidth: true
                            label: window.navNames[index]
                            glyph: window.navGlyphs[index]
                            selected: window.currentPage === index
                            onClicked: {
                                window.currentPage = index
                                backend.navigationClicked(label)
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 112
                        radius: 13
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 16; spacing: 4
                            Text { text: "◉  Market Time (ET)"; color: "#93a8bd"; font.pixelSize: 11 }
                            Text { text: backend.marketTime; color: "#ffffff"; font.pixelSize: 21; font.weight: Font.DemiBold }
                            Text { text: backend.dateText; color: "#74899e"; font.pixelSize: 11 }
                        }
                    }
                }
            }

            // MAIN AREA
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 98
                    color: "#04111b"
                    border.width: 1
                    border.color: "#123047"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 20
                        anchors.rightMargin: 24
                        spacing: 12
                        Item { Layout.fillWidth: true }
                        MarketPill { market: "NYSE"; stateText: "Open"; open: true }
                        MarketPill { market: "NASDAQ"; stateText: "Open"; open: true }
                        MarketPill { market: "XETRA"; stateText: "Closed"; subText: "öffnet später"; open: false; width: 190 }
                        Text { text: "♧"; color: "#e8f0f8"; font.pixelSize: 24; Layout.leftMargin: 8 }
                    }
                }

                // If another nav page is clicked, keep prototype simple and clearly say UI-only.
                Rectangle {
                    visible: window.currentPage !== 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#030d16"
                    Column {
                        anchors.centerIn: parent
                        spacing: 10
                        Text { text: window.navNames[window.currentPage]; color: "#ffffff"; font.pixelSize: 34; font.weight: Font.DemiBold; anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: "Diese Seite wird nach Freigabe des Dashboard-Designs gebaut."; color: "#8095aa"; font.pixelSize: 14; anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }

                // DASHBOARD
                Item {
                    visible: window.currentPage === 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 178
                            spacing: 14
                            MetricCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "Cash Available"; value: "10,000.00 USD"; subtitleLeft: "Buying Power"; subtitleRight: "10,000.00 USD"; iconText: "▣"; accentColor: "#3b9cff" }
                            MetricCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "Invested"; value: "0.00 USD"; subtitleLeft: "In Positions"; subtitleRight: "0.00%"; iconText: "◔"; accentColor: "#32dd89" }
                            MetricCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "Portfolio Value"; value: "10,000.00 USD"; subtitleLeft: "Total Value"; subtitleRight: "10,000.00 USD"; iconText: "⌁"; accentColor: "#8a67ff" }
                            MetricCard { Layout.fillWidth: true; Layout.fillHeight: true; title: "Today"; value: "+0.00 USD"; subtitleLeft: "+0.00%"; subtitleRight: ""; iconText: "↗"; accentColor: "#2d9dff"; valueColor: "#37df8d" }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 14

                            // Recent Trades
                            GlassCard {
                                Layout.preferredWidth: 410
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Recent Trades"; color: "#ffffff"; font.pixelSize: 16; font.weight: Font.DemiBold }
                                        Item { Layout.fillWidth: true }
                                        Text { text: "View All  ›"; color: "#64aefe"; font.pixelSize: 11 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 28
                                        Text { text: "Symbol"; color: "#7f92a7"; font.pixelSize: 10; Layout.preferredWidth: 156 }
                                        Text { text: "Side"; color: "#7f92a7"; font.pixelSize: 10; Layout.preferredWidth: 52 }
                                        Text { text: "Amount"; color: "#7f92a7"; font.pixelSize: 10; Layout.preferredWidth: 92 }
                                        Item { Layout.fillWidth: true }
                                        Text { text: "Time"; color: "#7f92a7"; font.pixelSize: 10 }
                                    }
                                    TradeRow { Layout.fillWidth: true; ticker: "AAPL"; company: "Apple Inc."; side: "BUY"; amount: "$2,250.00"; shares: "10 Shares"; time: "10:31:22 AM"; badgeColor: "#f4f4f4" }
                                    TradeRow { Layout.fillWidth: true; ticker: "NVDA"; company: "NVIDIA Corp."; side: "SELL"; amount: "$1,850.50"; shares: "10 Shares"; time: "10:22:11 AM"; badgeColor: "#76c900" }
                                    TradeRow { Layout.fillWidth: true; ticker: "MSFT"; company: "Microsoft Corp."; side: "BUY"; amount: "$1,875.25"; shares: "15 Shares"; time: "10:15:08 AM"; badgeColor: "#e8edf3" }
                                    TradeRow { Layout.fillWidth: true; ticker: "TSLA"; company: "Tesla, Inc."; side: "SELL"; amount: "$1,950.00"; shares: "12 Shares"; time: "09:58:47 AM"; badgeColor: "#ee2d2d" }
                                    TradeRow { Layout.fillWidth: true; ticker: "SPY"; company: "SPDR S&P 500 ETF"; side: "BUY"; amount: "$1,875.50"; shares: "15 Shares"; time: "09:41:33 AM"; badgeColor: "#3db58c" }
                                    Item { Layout.fillHeight: true }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: "#153049" }
                                    Text { text: "Alle Zeiten lokal"; color: "#74899f"; font.pixelSize: 10 }
                                }
                            }

                            // Portfolio Overview
                            GlassCard {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 6
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Portfolio Overview"; color: "#ffffff"; font.pixelSize: 16; font.weight: Font.DemiBold }
                                        Item { Layout.fillWidth: true }
                                        Rectangle { width: 78; height: 34; radius: 8; color: "#071522"; border.color: "#1e405c"; Text { anchors.centerIn: parent; text: "1D   ⌄"; color: "#e9f1fa"; font.pixelSize: 11 } }
                                    }
                                    Text { text: "10,000.00 USD"; color: "#ffffff"; font.pixelSize: 27; font.weight: Font.DemiBold }
                                    Text { text: "+0.00 USD (+0.00%)"; color: "#31de89"; font.pixelSize: 12 }

                                    Item {
                                        id: chartArea
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 260

                                        Repeater {
                                            model: 4
                                            Rectangle {
                                                x: 8
                                                width: chartArea.width - 16
                                                height: 1
                                                y: 40 + index * ((chartArea.height - 90) / 3)
                                                color: "#153147"
                                            }
                                        }
                                        Canvas {
                                            id: chart
                                            anchors.fill: parent
                                            onPaint: {
                                                var ctx = getContext("2d")
                                                ctx.reset()
                                                var pts = [0.10,0.16,0.08,0.21,0.17,0.29,0.25,0.34,0.31,0.42,0.38,0.49,0.56,0.52,0.63,0.72,0.69,0.80,0.77,0.89,0.84,0.96]
                                                var left = 10; var right = width - 45; var top = 36; var bottom = height - 45
                                                var grad = ctx.createLinearGradient(0, top, 0, bottom)
                                                grad.addColorStop(0, "rgba(55,119,255,0.34)")
                                                grad.addColorStop(1, "rgba(55,119,255,0.00)")
                                                ctx.beginPath()
                                                for (var i=0;i<pts.length;i++) {
                                                    var x = left + (right-left) * i/(pts.length-1)
                                                    var y = bottom - (bottom-top) * pts[i]
                                                    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y)
                                                }
                                                ctx.lineTo(right,bottom); ctx.lineTo(left,bottom); ctx.closePath(); ctx.fillStyle=grad; ctx.fill()
                                                ctx.beginPath()
                                                for (var j=0;j<pts.length;j++) {
                                                    var xx = left + (right-left) * j/(pts.length-1)
                                                    var yy = bottom - (bottom-top) * pts[j]
                                                    if (j===0) ctx.moveTo(xx,yy); else ctx.lineTo(xx,yy)
                                                }
                                                ctx.strokeStyle = "#5a9cff"; ctx.lineWidth = 2.4; ctx.stroke()
                                            }
                                        }
                                        RowLayout {
                                            anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                            anchors.leftMargin: 10; anchors.rightMargin: 45
                                            Text { text: "09:30 AM"; color: "#788ba0"; font.pixelSize: 9 }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "11:00 AM"; color: "#788ba0"; font.pixelSize: 9 }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "12:30 PM"; color: "#788ba0"; font.pixelSize: 9 }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "02:00 PM"; color: "#788ba0"; font.pixelSize: 9 }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "04:00 PM"; color: "#788ba0"; font.pixelSize: 9 }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 34; spacing: 4
                                        Repeater {
                                            model: ["1D","1W","1M","3M","YTD","1Y","All"]
                                            Rectangle {
                                                Layout.fillWidth: true; height: 32; radius: 7
                                                color: index === 0 ? "#0d3967" : "transparent"
                                                border.width: index === 0 ? 1 : 0; border.color: "#235988"
                                                Text { anchors.centerIn: parent; text: modelData; color: index === 0 ? "#8bc5ff" : "#93a4b7"; font.pixelSize: 10 }
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 52
                                        ColumnLayout { Text { text: "●  Stocks"; color: "#519aff"; font.pixelSize: 10 } Text { text: "10,000.00 USD"; color: "#e6edf5"; font.pixelSize: 11 } }
                                        Item { Layout.fillWidth: true }
                                        ColumnLayout { Text { text: "●  ETFs"; color: "#8b62ff"; font.pixelSize: 10 } Text { text: "0.00 USD"; color: "#e6edf5"; font.pixelSize: 11 } }
                                        Item { Layout.fillWidth: true }
                                        ColumnLayout { Text { text: "●  Cash"; color: "#35c6d8"; font.pixelSize: 10 } Text { text: "10,000.00 USD"; color: "#e6edf5"; font.pixelSize: 11 } }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 15; radius: 5; color: "#0a1b29"
                                        RowLayout { anchors.fill: parent; spacing: 0
                                            Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#337dff"; radius: 5 }
                                            Rectangle { Layout.preferredWidth: 0; Layout.fillHeight: true; color: "#8c5cff" }
                                            Rectangle { Layout.preferredWidth: 0; Layout.fillHeight: true; color: "#35cbd4" }
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                Layout.preferredWidth: 480
                                Layout.fillHeight: true
                                spacing: 14

                                GlassCard {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 16; spacing: 8
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "International Market News"; color: "#ffffff"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                            Item { Layout.fillWidth: true }
                                            Text { text: "View All  ›"; color: "#64aefe"; font.pixelSize: 11 }
                                        }
                                        NewsRow { Layout.fillWidth: true; tag: "NEWS"; title: "News-Anbindung vorbereitet"; body: "Marktnachrichten werden später live geladen."; meta: "—" }
                                        NewsRow { Layout.fillWidth: true; tag: "NYSE"; title: "US-Marktstatus aktiv"; body: "NYSE/NASDAQ Handelszeiten werden lokal überwacht."; meta: "live" }
                                        NewsRow { Layout.fillWidth: true; tag: "XETRA"; title: "Europa-Marktstatus aktiv"; body: "XETRA/Wien Status steht im Kopfbereich."; meta: "live" }
                                        NewsRow { Layout.fillWidth: true; tag: "DATA"; title: "Yahoo Finance"; body: "Kursdatenquelle für Analyse und Watchlist."; meta: "local" }
                                        Item { Layout.fillHeight: true }
                                    }
                                }

                                GlassCard {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 220
                                    accent: "#34de86"
                                    Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 2; color: "#32d984"; opacity: 0.8 }
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 18; spacing: 10
                                        Text { text: "Bot Status"; color: "#ffffff"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                        RowLayout {
                                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
                                            Rectangle {
                                                width: 78; height: 78; radius: 39; color: "#092031"; border.width: 2; border.color: "#7d64ff"
                                                Text { anchors.centerIn: parent; text: "🤖"; font.pixelSize: 34 }
                                            }
                                            ColumnLayout {
                                                Layout.fillWidth: true; spacing: 8
                                                Rectangle { Layout.fillWidth: true; height: 34; radius: 8; color: "#0a312d"; border.color: "#1d6d5b"; Text { anchors.centerIn: parent; text: "●  eToro REAL"; color: "#37df8c"; font.pixelSize: 11 } }
                                                Text { text: "manueller Live-Test · max. 10 €"; color: "#8496aa"; font.pixelSize: 10 }
                                                Text { text: "🔒  AutoTrader → REAL gesperrt"; color: "#8496aa"; font.pixelSize: 10 }
                                                Text { text: "Strategie: Research Engine 0.6.1"; color: "#8496aa"; font.pixelSize: 10 }
                                            }
                                            Text { text: "View Bot  ›"; color: "#e8f1fa"; font.pixelSize: 11 }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 34
                    color: "#04111b"
                    border.width: 1
                    border.color: "#123047"
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20
                        Text { text: "ⓘ  Informationen stellen keine Anlageberatung dar. Vergangene Wertentwicklungen sind kein Indikator für zukünftige Ergebnisse."; color: "#71869b"; font.pixelSize: 10 }
                        Item { Layout.fillWidth: true }
                        Text { text: "UI Prototype · keine Broker-Orders"; color: "#71869b"; font.pixelSize: 10 }
                    }
                }
            }
        }
    }
}
