import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root
    property bool dataLoaded: false

    Component.onCompleted: {
        // 默认日期范围：最近 30 天
        var end = new Date()
        var start = new Date()
        start.setDate(start.getDate() - 30)
        reportManager.setDateRange(
            start.toISOString().slice(0, 10),
            end.toISOString().slice(0, 10)
        )
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 16
            anchors.margins: 16

            // ── 日期选择区 ─────────────────────────
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Label { text: qsTr("起始日期:"); font.pixelSize: 13 }
                TextField {
                    id: startDateField
                    font.pixelSize: 13
                    Layout.preferredWidth: 130
                    placeholderText: "YYYY-MM-DD"
                    text: reportManager.startDate || ""
                }

                Label { text: qsTr("结束日期:"); font.pixelSize: 13 }
                TextField {
                    id: endDateField
                    font.pixelSize: 13
                    Layout.preferredWidth: 130
                    placeholderText: "YYYY-MM-DD"
                    text: reportManager.endDate || ""
                }

                Button {
                    text: qsTr("查询")
                    font.pixelSize: 13
                    Material.background: Material.accent
                    Material.foreground: "white"
                    onClicked: {
                        var s = startDateField.text.trim()
                        var e = endDateField.text.trim()
                        if (s.length > 0 && e.length > 0) {
                            dataLoaded = true
                            reportManager.setDateRange(s, e)
                            reportManager.loadAll()
                        }
                    }
                }
            }

            // ── 加载指示器 ─────────────────────────
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: reportManager.isLoading
                visible: reportManager.isLoading
            }

            // ── 情感趋势 ───────────────────────────
            Label {
                text: qsTr("情感趋势")
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
                    id: emotionCanvas
                    anchors.fill: parent
                    anchors.margins: 16
                    property var trendData: reportManager.emotionTrend ? (reportManager.emotionTrend.trend || []) : []

                    onTrendDataChanged: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width, h = height;
                        ctx.clearRect(0, 0, w, h);

                        var trend = emotionCanvas.trendData;
                        if (!trend || trend.length === 0) {
                            ctx.fillStyle = "#999";
                            ctx.font = "14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("暂无情感数据"), w/2, h/2);
                            return;
                        }

                        var padding = {left: 40, right: 10, top: 10, bottom: 30};
                        var plotW = w - padding.left - padding.right;
                        var plotH = h - padding.top - padding.bottom;
                        var xStep = trend.length > 1 ? plotW / (trend.length - 1) : plotW;

                        // 坐标轴
                        ctx.strokeStyle = "#CCC";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(padding.left, padding.top);
                        ctx.lineTo(padding.left, h - padding.bottom);
                        ctx.lineTo(w - padding.right, h - padding.bottom);
                        ctx.stroke();

                        // Y 轴刻度 0-100%
                        ctx.fillStyle = "#666";
                        ctx.font = "9px sans-serif";
                        ctx.textAlign = "right";
                        for (var yi = 0; yi <= 4; yi++) {
                            var pct = 100 - yi * 25;
                            var yPos = padding.top + yi * plotH / 4;
                            ctx.fillText(pct + "%", padding.left - 5, yPos + 3);
                        }

                        // 三条折线：积极(绿)、中性(灰)、消极(红)
                        var colors = ["#4CAF50", "#9E9E9E", "#F44336"];
                        var keys = ["positive", "neutral", "negative"];

                        for (var k = 0; k < 3; k++) {
                            ctx.strokeStyle = colors[k];
                            ctx.lineWidth = 1.5;
                            ctx.beginPath();
                            for (var i = 0; i < trend.length; i++) {
                                var val = (trend[i][keys[k]] || 0) * 100;
                                var x = padding.left + i * xStep;
                                var y = h - padding.bottom - (val / 100 * plotH);
                                if (i === 0) ctx.moveTo(x, y);
                                else ctx.lineTo(x, y);
                            }
                            ctx.stroke();
                        }

                        // X 轴标签（显示月-日）
                        ctx.fillStyle = "#666";
                        ctx.textAlign = "center";
                        for (var i = 0; i < trend.length; i += Math.max(1, Math.floor(trend.length / 8))) {
                            var x = padding.left + i * xStep;
                            ctx.fillText((trend[i].date || "").substring(5), x, h - padding.bottom + 14);
                        }

                        // 图例
                        var legendY = padding.top + 5;
                        var labels = [qsTr("积极"), qsTr("中性"), qsTr("消极")];
                        for (var k = 0; k < 3; k++) {
                            ctx.fillStyle = colors[k];
                            var lx = w - 120 + k * 45;
                            ctx.fillRect(lx, legendY, 10, 10);
                            ctx.fillStyle = "#666";
                            ctx.font = "10px sans-serif";
                            ctx.textAlign = "left";
                            ctx.fillText(labels[k], lx + 14, legendY + 9);
                        }
                    }
                }
            }

            // 情感总结文本
            Label {
                Layout.fillWidth: true
                text: reportManager.emotionTrend ? (reportManager.emotionTrend.summary || qsTr("点击查询按钮加载数据")) : qsTr("点击查询按钮加载数据")
                font.pixelSize: 13
                color: "#555"
                wrapMode: Text.WordWrap
                visible: reportManager.emotionTrend !== undefined
            }

            // ── 关注点分布 ─────────────────────────
            Label {
                text: qsTr("关注点分布")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    model: reportManager.focusAnalysis || []

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: modelData.category || ""
                            font.pixelSize: 13
                            Layout.preferredWidth: 120
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 20
                            radius: 10
                            color: "#E3F2FD"

                            Rectangle {
                                height: parent.height
                                width: Math.max(4, parent.width * (modelData.percentage || 0) / 100)
                                radius: 10
                                color: "#1976D2"
                            }
                        }

                        Label {
                            text: (modelData.percentage || 0) + "%"
                            font.pixelSize: 12
                            color: "#666"
                            Layout.preferredWidth: 40
                        }

                        Label {
                            text: modelData.trend === "up" ? "↑" : (modelData.trend === "down" ? "↓" : "→")
                            font.pixelSize: 14
                            color: modelData.trend === "up" ? "#4CAF50" : (modelData.trend === "down" ? "#F44336" : "#999")
                        }
                    }
                }

                Label {
                    text: qsTr("暂无关注点数据")
                    font.pixelSize: 14
                    color: "#999"
                    visible: (!reportManager.focusAnalysis || reportManager.focusAnalysis.length === 0) && !reportManager.isLoading
                }
            }

            // ── 服务改进建议 ───────────────────────
            Label {
                text: qsTr("服务改进建议")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Repeater {
                    model: reportManager.serviceSuggestions || []
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 80
                        radius: 8
                        color: "white"
                        border.width: 1
                        border.color: "#E0E0E0"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 12

                            // 优先级徽章
                            Rectangle {
                                width: 70; height: 26; radius: 13
                                color: modelData.priority === "high" ? "#F44336"
                                     : modelData.priority === "medium" ? "#FF9800"
                                     : "#4CAF50"

                                Label {
                                    anchors.centerIn: parent
                                    text: modelData.priority === "high" ? qsTr("高优")
                                        : modelData.priority === "medium" ? qsTr("中优")
                                        : qsTr("低优")
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: "white"
                                }
                            }

                            Column {
                                Layout.fillWidth: true
                                spacing: 4

                                Label {
                                    text: qsTr("问题：") + (modelData.issue || "")
                                    font.pixelSize: 13
                                    font.bold: true
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                                Label {
                                    text: qsTr("建议：") + (modelData.suggestion || "")
                                    font.pixelSize: 12
                                    color: "#555"
                                    elide: Text.ElideRight
                                    width: parent.width
                                    maximumLineCount: 2
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }

                Label {
                    text: qsTr("暂无服务建议")
                    font.pixelSize: 14
                    color: "#999"
                    visible: (!reportManager.serviceSuggestions || reportManager.serviceSuggestions.length === 0) && !reportManager.isLoading
                }
            }
        }
    }
}
