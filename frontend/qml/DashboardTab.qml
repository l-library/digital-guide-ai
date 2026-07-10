import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root
    // Load data when this tab becomes visible
    property bool dataLoaded: false

    onVisibleChanged: {
        if (visible && !dataLoaded) {
            dataLoaded = true
            dashboardManager.loadAll()
            refreshTimer.start()
        }
    }

    // Auto-refresh every 30 seconds
    Timer {
        id: refreshTimer
        interval: 30000
        repeat: true
        onTriggered: {
            if (root.visible && dashboardManager) {
                dashboardManager.loadAll()
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 16
            anchors.margins: 16

            // ── 加载状态 ────────────────────────────────
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: dashboardManager && dashboardManager.isLoading
                visible: dashboardManager && dashboardManager.isLoading && !root.dataLoaded
            }

            // ── Section: Metric Cards ──────────────────
            Label {
                text: qsTr("核心指标")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                // Card 1: Today Services
                DashboardCard {
                    title: qsTr("今日服务人次")
                    value: dashboardManager.overview ? dashboardManager.overview.todayServiceCount || 0 : 0
                    accentColor: "#1976D2"
                }
                // Card 2: Today Visitors
                DashboardCard {
                    title: qsTr("今日访客数")
                    value: dashboardManager.overview ? dashboardManager.overview.todayVisitorCount || 0 : 0
                    accentColor: "#388E3C"
                }
                // Card 3: Week Services
                DashboardCard {
                    title: qsTr("本周服务人次")
                    value: dashboardManager.overview ? dashboardManager.overview.weekServiceCount || 0 : 0
                    accentColor: "#F57C00"
                }
                // Card 4: Avg Satisfaction
                DashboardCard {
                    title: qsTr("平均满意度")
                    value: dashboardManager.overview ? (dashboardManager.overview.avgSatisfaction || 0) : 0
                    accentColor: "#7B1FA2"
                    isFloat: true
                    suffix: "%"
                    floatValue: dashboardManager.overview ? Math.round((dashboardManager.overview.avgSatisfaction || 0) * 100) : 0
                }
            }

            // ── Section: Service Trend Chart ──────────
            Label {
                text: qsTr("服务趋势")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                color: "white"
                radius: 8
                border.width: 1
                border.color: "#E0E0E0"

                Canvas {
                    id: trendCanvas
                    anchors.fill: parent
                    anchors.margins: 16
                    property var stats: dashboardManager.serviceStats || []

                    onStatsChanged: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width, h = height;
                        ctx.clearRect(0, 0, w, h);

                        var stats = trendCanvas.stats;
                        if (!stats || stats.length === 0) {
                            ctx.fillStyle = "#999";
                            ctx.font = "14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("暂无数据"), w/2, h/2);
                            return;
                        }

                        // Find max count for Y scale
                        var maxCount = 1;
                        for (var i = 0; i < stats.length; i++) {
                            maxCount = Math.max(maxCount, stats[i].count || 0);
                        }
                        maxCount = Math.ceil(maxCount * 1.2);

                        var padding = {left: 45, right: 10, top: 10, bottom: 30};
                        var plotW = w - padding.left - padding.right;
                        var plotH = h - padding.top - padding.bottom;

                        // Draw axes
                        ctx.strokeStyle = "#CCC";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(padding.left, padding.top);
                        ctx.lineTo(padding.left, h - padding.bottom);
                        ctx.lineTo(w - padding.right, h - padding.bottom);
                        ctx.stroke();

                        // Draw Y-axis labels
                        ctx.fillStyle = "#666";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "right";
                        for (var yi = 0; yi <= 4; yi++) {
                            var yVal = Math.round(maxCount * yi / 4);
                            var yPos = h - padding.bottom - (yi / 4 * plotH);
                            ctx.fillText(yVal.toString(), padding.left - 5, yPos + 3);
                            // Grid line
                            ctx.strokeStyle = "#F0F0F0";
                            ctx.beginPath();
                            ctx.moveTo(padding.left, yPos);
                            ctx.lineTo(w - padding.right, yPos);
                            ctx.stroke();
                        }

                        // Draw data line
                        var xStep = stats.length > 1 ? plotW / (stats.length - 1) : plotW;
                        ctx.strokeStyle = "#1976D2";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        for (var i = 0; i < stats.length; i++) {
                            var x = padding.left + i * xStep;
                            var y = h - padding.bottom - ((stats[i].count || 0) / maxCount * plotH);
                            if (i === 0) ctx.moveTo(x, y);
                            else ctx.lineTo(x, y);
                        }
                        ctx.stroke();

                        // Draw data points
                        ctx.fillStyle = "#1976D2";
                        for (var i = 0; i < stats.length; i++) {
                            var x = padding.left + i * xStep;
                            var y = h - padding.bottom - ((stats[i].count || 0) / maxCount * plotH);
                            ctx.beginPath();
                            ctx.arc(x, y, 3, 0, Math.PI * 2);
                            ctx.fill();
                        }

                        // X-axis labels (every other one to avoid crowding)
                        ctx.fillStyle = "#666";
                        ctx.textAlign = "center";
                        for (var i = 0; i < stats.length; i += Math.max(1, Math.floor(stats.length / 8))) {
                            var x = padding.left + i * xStep;
                            var label = (stats[i].time || "").substring(5); // show MM-DD
                            ctx.fillText(label, x, h - padding.bottom + 14);
                        }
                    }
                }
            }

            // ── Section: Hot Questions ────────────────
            Label {
                text: qsTr("热门问答排行")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            ListView {
                id: hotQuestionsList
                Layout.fillWidth: true
                Layout.preferredHeight: 280
                clip: true
                model: dashboardManager.hotQuestions || []
                spacing: 8

                delegate: Rectangle {
                    width: hotQuestionsList.width
                    height: 48
                    radius: 6
                    color: "white"
                    border.width: 1
                    border.color: "#E8E8E8"

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 10

                        // Rank number
                        Rectangle {
                            width: 28; height: 28; radius: 14
                            color: index < 3 ? Material.color(Material.Orange, Material.Shade400) : "#BDBDBD"

                            Label {
                                anchors.centerIn: parent
                                text: (index + 1).toString()
                                font.pixelSize: 12
                                font.bold: true
                                color: "white"
                            }
                        }

                        // Question text
                        Label {
                            text: modelData.question || ""
                            font.pixelSize: 13
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        // Count
                        Label {
                            text: modelData.count ? modelData.count + qsTr(" 次") : ""
                            font.pixelSize: 12
                            color: "#666"
                        }

                        // Trend arrow
                        Label {
                            text: modelData.trend === "up" ? "↑" : (modelData.trend === "down" ? "↓" : "→")
                            font.pixelSize: 16
                            color: modelData.trend === "up" ? "#4CAF50" : (modelData.trend === "down" ? "#F44336" : "#999")
                        }
                    }
                }

                // Empty state
                Label {
                    anchors.centerIn: parent
                    text: qsTr("暂无热门问答数据")
                    font.pixelSize: 14
                    color: "#999"
                    visible: hotQuestionsList.count === 0
                }
            }

            // ── Section: Satisfaction Mini Trend ──────
            Label {
                text: qsTr("满意度趋势")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                color: "white"
                radius: 8
                border.width: 1
                border.color: "#E0E0E0"

                Canvas {
                    id: satisfactionCanvas
                    anchors.fill: parent
                    anchors.margins: 16
                    property var trend: dashboardManager.satisfactionTrend || []

                    onTrendChanged: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width, h = height;
                        ctx.clearRect(0, 0, w, h);

                        var trend = satisfactionCanvas.trend;
                        if (!trend || trend.length === 0) {
                            ctx.fillStyle = "#999";
                            ctx.font = "14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("暂无数据"), w/2, h/2);
                            return;
                        }

                        // Satisfaction is 0-1 (or 0-100), scale accordingly
                        var maxScore = 5; // assume 5-point scale
                        var minScore = 0;

                        var padding = {left: 45, right: 10, top: 10, bottom: 30};
                        var plotW = w - padding.left - padding.right;
                        var plotH = h - padding.top - padding.bottom;

                        // Draw axes
                        ctx.strokeStyle = "#CCC";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(padding.left, padding.top);
                        ctx.lineTo(padding.left, h - padding.bottom);
                        ctx.lineTo(w - padding.right, h - padding.bottom);
                        ctx.stroke();

                        // Y-axis labels (1-5 scale)
                        ctx.fillStyle = "#666";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "right";
                        for (var yi = 0; yi <= 4; yi++) {
                            var yVal = Math.round(minScore + (maxScore - minScore) * yi / 4);
                            var yPos = h - padding.bottom - (yi / 4 * plotH);
                            ctx.fillText(yVal.toString(), padding.left - 5, yPos + 3);
                            ctx.strokeStyle = "#F0F0F0";
                            ctx.beginPath();
                            ctx.moveTo(padding.left, yPos);
                            ctx.lineTo(w - padding.right, yPos);
                            ctx.stroke();
                        }

                        // Draw satisfaction line
                        var xStep = trend.length > 1 ? plotW / (trend.length - 1) : plotW;
                        ctx.strokeStyle = "#7B1FA2";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        for (var i = 0; i < trend.length; i++) {
                            var score = trend[i].avgScore || 0;
                            var x = padding.left + i * xStep;
                            var y = h - padding.bottom - ((score - minScore) / (maxScore - minScore) * plotH);
                            if (i === 0) ctx.moveTo(x, y);
                            else ctx.lineTo(x, y);
                        }
                        ctx.stroke();

                        // Draw data points
                        ctx.fillStyle = "#7B1FA2";
                        for (var i2 = 0; i2 < trend.length; i2++) {
                            var x = padding.left + i2 * xStep;
                            var y = h - padding.bottom - ((trend[i2].avgScore || 0) / (maxScore - minScore) * plotH);
                            ctx.beginPath();
                            ctx.arc(x, y, 3, 0, Math.PI * 2);
                            ctx.fill();
                        }

                        // Draw response count bars (thin bars at bottom)
                        var maxResp = 1;
                        for (var j = 0; j < trend.length; j++) {
                            maxResp = Math.max(maxResp, trend[j].responseCount || 0);
                        }
                        var barMaxH = 30;
                        ctx.fillStyle = "rgba(123, 31, 162, 0.15)";
                        for (var k = 0; k < trend.length; k++) {
                            var bx = padding.left + k * xStep - xStep / 4;
                            var bw = Math.max(2, xStep / 2);
                            var bh = ((trend[k].responseCount || 0) / maxResp) * barMaxH;
                            var by = h - padding.bottom - bh;
                            ctx.fillRect(bx, by, bw, bh);
                        }

                        // X-axis labels
                        ctx.fillStyle = "#666";
                        ctx.textAlign = "center";
                        for (var m = 0; m < trend.length; m += Math.max(1, Math.floor(trend.length / 8))) {
                            var lx = padding.left + m * xStep;
                            var label = (trend[m].date || "").substring(5);
                            ctx.fillText(label, lx, h - padding.bottom + 14);
                        }
                    }
                }
            }
        }
    }

    // ── Metric Card Component ──────────────────────
    component DashboardCard: Rectangle {
        property string title: ""
        property int value: 0
        property string accentColor: "#1976D2"
        property bool isFloat: false
        property string suffix: ""
        property int floatValue: 0

        Layout.fillWidth: true
        Layout.preferredHeight: 90
        radius: 8
        color: "white"
        border.width: 1
        border.color: "#E0E0E0"

        Column {
            anchors.centerIn: parent
            spacing: 6

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: title
                font.pixelSize: 12
                color: "#666"
            }

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: isFloat ? floatValue + suffix : value.toString()
                font.pixelSize: 24
                font.bold: true
                color: accentColor
            }
        }
    }
}
