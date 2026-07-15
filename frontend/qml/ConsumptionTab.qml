import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

/**
 * 消费分析标签页
 *
 * 数据来源：GET /api/v1/admin/consumption/full
 * 依赖 context property: consumptionManager（在 main.cpp 中注册）
 * 展示内容：核心指标卡 → 营收月度趋势折线图 → 消费类别分布 → 客群画像（年龄+性别）
 */
Item {
    id: root
    property bool dataLoaded: false

    onVisibleChanged: {
        if (visible && !dataLoaded) {
            dataLoaded = true
            consumptionManager.loadAll()
        }
    }

    Component.onCompleted: {
        if (consumptionManager) {
            dataLoaded = true
            consumptionManager.loadAll()
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
                running: consumptionManager && consumptionManager.isLoading
                visible: consumptionManager && consumptionManager.isLoading
            }

            // ── Section: 核心指标 ─────────────────────
            Label {
                text: qsTr("核心指标")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                // Card 1: 总营收
                ConsumptionCard {
                    title: qsTr("总营收 (元)")
                    valueText: {
                        if (!consumptionManager.overview) return "0"
                        return formatMoney(consumptionManager.overview.total_revenue || 0)
                    }
                    accentColor: "#1976D2"
                }
                // Card 2: 人均消费
                ConsumptionCard {
                    title: qsTr("人均消费 (元)")
                    valueText: {
                        if (!consumptionManager.overview) return "0"
                        return formatMoney(consumptionManager.overview.avg_spending || 0)
                    }
                    accentColor: "#388E3C"
                }
                // Card 3: 消费人次
                ConsumptionCard {
                    title: qsTr("消费人次")
                    valueText: {
                        if (!consumptionManager.overview) return "0"
                        return (consumptionManager.overview.total_visitors || 0).toString()
                    }
                    accentColor: "#F57C00"
                }
                // Card 4: 平均满意度
                ConsumptionCard {
                    title: qsTr("平均满意度")
                    valueText: {
                        if (!consumptionManager.overview) return "0.0"
                        return (consumptionManager.overview.avg_satisfaction || 0).toFixed(2) + " / 5"
                    }
                    accentColor: "#7B1FA2"
                }
                // Card 5: 平均停留时长
                ConsumptionCard {
                    title: qsTr("平均停留 (小时)")
                    valueText: {
                        if (!consumptionManager.overview) return "0.0"
                        return (consumptionManager.overview.avg_stay_duration || 0).toFixed(2)
                    }
                    accentColor: "#E91E63"
                }
            }

            // ── Section: 营收月度趋势 ───────────────
            Label {
                text: qsTr("营收月度趋势")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 240
                color: "white"
                radius: 8
                border.width: 1
                border.color: "#E0E0E0"

                Canvas {
                    id: revenueCanvas
                    anchors.fill: parent
                    anchors.margins: 16
                    property var stats: consumptionManager.revenueTrend || []

                    onStatsChanged: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width, h = height;
                        ctx.clearRect(0, 0, w, h);

                        var stats = revenueCanvas.stats;
                        if (!stats || stats.length === 0) {
                            ctx.fillStyle = "#999";
                            ctx.font = "14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("暂无数据"), w/2, h/2);
                            return;
                        }

                        var maxRevenue = 1;
                        for (var i = 0; i < stats.length; i++) {
                            maxRevenue = Math.max(maxRevenue, stats[i].revenue || 0);
                        }
                        maxRevenue = Math.ceil(maxRevenue * 1.15);

                        var padding = {left: 60, right: 10, top: 10, bottom: 30};
                        var plotW = w - padding.left - padding.right;
                        var plotH = h - padding.top - padding.bottom;

                        // 坐标轴
                        ctx.strokeStyle = "#CCC";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(padding.left, padding.top);
                        ctx.lineTo(padding.left, h - padding.bottom);
                        ctx.lineTo(w - padding.right, h - padding.bottom);
                        ctx.stroke();

                        // Y 轴刻度
                        ctx.fillStyle = "#666";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "right";
                        for (var yi = 0; yi <= 4; yi++) {
                            var yVal = Math.round(maxRevenue * yi / 4);
                            var yPos = h - padding.bottom - (yi / 4 * plotH);
                            ctx.fillText("¥" + yVal, padding.left - 5, yPos + 3);
                            ctx.strokeStyle = "#F0F0F0";
                            ctx.beginPath();
                            ctx.moveTo(padding.left, yPos);
                            ctx.lineTo(w - padding.right, yPos);
                            ctx.stroke();
                        }

                        // 折线
                        var xStep = stats.length > 1 ? plotW / (stats.length - 1) : plotW;
                        ctx.strokeStyle = "#1976D2";
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        for (var i = 0; i < stats.length; i++) {
                            var x = padding.left + i * xStep;
                            var y = h - padding.bottom - ((stats[i].revenue || 0) / maxRevenue * plotH);
                            if (i === 0) ctx.moveTo(x, y);
                            else ctx.lineTo(x, y);
                        }
                        ctx.stroke();

                        // 数据点 + 数值标注
                        ctx.fillStyle = "#1976D2";
                        for (var i = 0; i < stats.length; i++) {
                            var x = padding.left + i * xStep;
                            var y = h - padding.bottom - ((stats[i].revenue || 0) / maxRevenue * plotH);
                            ctx.beginPath();
                            ctx.arc(x, y, 3, 0, Math.PI * 2);
                            ctx.fill();
                        }

                        // X 轴标签（YYYY-MM）
                        ctx.fillStyle = "#666";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "center";
                        for (var i = 0; i < stats.length; i++) {
                            var lx = padding.left + i * xStep;
                            ctx.fillText(stats[i].time || "", lx, h - padding.bottom + 14);
                        }
                    }
                }
            }

            // ── Section: 消费类别分布 ─────────────
            Label {
                text: qsTr("消费类别分布")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                spacing: 16

                // 左侧：饼图
                Rectangle {
                    Layout.preferredWidth: 220
                    Layout.fillHeight: true
                    color: "white"
                    radius: 8
                    border.width: 1
                    border.color: "#E0E0E0"

                    Canvas {
                        id: pieCanvas
                        anchors.fill: parent
                        anchors.margins: 16
                        property var categories: consumptionManager.categoryBreakdown ? consumptionManager.categoryBreakdown.categories || [] : []
                        // 类别配色，按顺序：门票/餐饮/购物/交通/娱乐
                        property var palette: ["#1976D2", "#388E3C", "#F57C00", "#7B1FA2", "#E91E63"]

                        onCategoriesChanged: requestPaint()

                        onPaint: {
                            var ctx = getContext("2d");
                            var w = width, h = height;
                            ctx.clearRect(0, 0, w, h);

                            var cats = pieCanvas.categories;
                            if (!cats || cats.length === 0) {
                                ctx.fillStyle = "#999";
                                ctx.font = "14px sans-serif";
                                ctx.textAlign = "center";
                                ctx.fillText(qsTr("暂无数据"), w/2, h/2);
                                return;
                            }

                            var cx = w / 2, cy = h / 2;
                            var radius = Math.min(w, h) / 2 - 8;
                            var startAngle = -Math.PI / 2;

                            for (var i = 0; i < cats.length; i++) {
                                var pct = (cats[i].percentage || 0) / 100.0;
                                if (pct <= 0) continue;
                                var endAngle = startAngle + pct * Math.PI * 2;
                                ctx.beginPath();
                                ctx.moveTo(cx, cy);
                                ctx.arc(cx, cy, radius, startAngle, endAngle);
                                ctx.closePath();
                                ctx.fillStyle = pieCanvas.palette[i % pieCanvas.palette.length];
                                ctx.fill();
                                startAngle = endAngle;
                            }
                            // 中央圆洞做环状图
                            ctx.beginPath();
                            ctx.arc(cx, cy, radius * 0.55, 0, Math.PI * 2);
                            ctx.fillStyle = "white";
                            ctx.fill();

                            // 中央标注总金额
                            ctx.fillStyle = "#333";
                            ctx.font = "bold 11px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("类别总额"), cx, cy - 6);
                            ctx.font = "bold 14px sans-serif";
                            var total = consumptionManager.categoryBreakdown ? consumptionManager.categoryBreakdown.total || 0 : 0;
                            ctx.fillText("¥" + total.toFixed(0), cx, cy + 12);
                        }
                    }
                }

                // 右侧：图例 + 金额列表
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "white"
                    radius: 8
                    border.width: 1
                    border.color: "#E0E0E0"

                    ListView {
                        id: categoryLegend
                        anchors.fill: parent
                        anchors.margins: 12
                        clip: true
                        spacing: 8
                        model: consumptionManager.categoryBreakdown ? consumptionManager.categoryBreakdown.categories || [] : []

                        Label {
                            anchors.centerIn: parent
                            text: qsTr("暂无分类数据")
                            font.pixelSize: 13
                            color: "#999"
                            visible: categoryLegend.count === 0
                        }

                        delegate: RowLayout {
                            width: categoryLegend.width
                            spacing: 8

                            Rectangle {
                                width: 12; height: 12; radius: 2
                                color: ["#1976D2", "#388E3C", "#F57C00", "#7B1FA2", "#E91E63"][index % 5]
                            }
                            Label {
                                text: modelData.name || ""
                                font.pixelSize: 13
                                font.bold: true
                                Layout.preferredWidth: 50
                            }
                            Label {
                                text: "¥" + (modelData.amount || 0).toFixed(2)
                                font.pixelSize: 13
                                color: "#333"
                                Layout.fillWidth: true
                            }
                            Label {
                                text: (modelData.percentage || 0).toFixed(1) + "%"
                                font.pixelSize: 13
                                color: "#666"
                                Layout.preferredWidth: 60
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }
                }
            }

            // ── Section: 客群画像 - 年龄段 ─────
            Label {
                text: qsTr("客群画像 - 年龄段")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 200
                color: "white"
                radius: 8
                border.width: 1
                border.color: "#E0E0E0"

                Canvas {
                    id: ageBarCanvas
                    anchors.fill: parent
                    anchors.margins: 16
                    property var groups: consumptionManager.demographics ? consumptionManager.demographics.age_groups || [] : []

                    onGroupsChanged: requestPaint()

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width, h = height;
                        ctx.clearRect(0, 0, w, h);
                        var groups = ageBarCanvas.groups;
                        if (!groups || groups.length === 0) {
                            ctx.fillStyle = "#999";
                            ctx.font = "14px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText(qsTr("暂无数据"), w/2, h/2);
                            return;
                        }

                        // 最大人均消费用于 Y 缩放（柱状图）
                        var maxAvg = 1;
                        for (var i = 0; i < groups.length; i++) {
                            maxAvg = Math.max(maxAvg, groups[i].avg_spending || 0);
                        }
                        maxAvg = Math.ceil(maxAvg * 1.15 / 100) * 100;

                        var padding = {left: 60, right: 10, top: 10, bottom: 30};
                        var plotW = w - padding.left - padding.right;
                        var plotH = h - padding.top - padding.bottom;
                        var barW = plotW / groups.length * 0.55;

                        // Y 轴
                        ctx.strokeStyle = "#CCC";
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(padding.left, padding.top);
                        ctx.lineTo(padding.left, h - padding.bottom);
                        ctx.lineTo(w - padding.right, h - padding.bottom);
                        ctx.stroke();

                        ctx.fillStyle = "#666";
                        ctx.font = "10px sans-serif";
                        ctx.textAlign = "right";
                        for (var yi = 0; yi <= 4; yi++) {
                            var yVal = Math.round(maxAvg * yi / 4);
                            var yPos = h - padding.bottom - (yi / 4 * plotH);
                            ctx.fillText("¥" + yVal, padding.left - 5, yPos + 3);
                            ctx.strokeStyle = "#F0F0F0";
                            ctx.beginPath();
                            ctx.moveTo(padding.left, yPos);
                            ctx.lineTo(w - padding.right, yPos);
                            ctx.stroke();
                        }

                        // 柱子
                        var colors = ["#90CAF9", "#1976D2", "#388E3C", "#F57C00", "#7B1FA2", "#E91E63"];
                        for (var i = 0; i < groups.length; i++) {
                            var groupX = padding.left + (i + 0.5) * (plotW / groups.length);
                            var barHeight = (groups[i].avg_spending || 0) / maxAvg * plotH;
                            var barX = groupX - barW / 2;
                            var barY = h - padding.bottom - barHeight;

                            ctx.fillStyle = colors[i % colors.length];
                            ctx.fillRect(barX, barY, barW, barHeight);

                            // 顶部金额标注
                            ctx.fillStyle = "#333";
                            ctx.font = "10px sans-serif";
                            ctx.textAlign = "center";
                            ctx.fillText("¥" + (groups[i].avg_spending || 0).toFixed(0), groupX, barY - 5);

                            // X 轴年龄段标签
                            ctx.fillStyle = "#666";
                            ctx.font = "11px sans-serif";
                            ctx.fillText(groups[i].group || "", groupX, h - padding.bottom + 14);

                            // 人次标签
                            ctx.fillStyle = "#999";
                            ctx.font = "9px sans-serif";
                            ctx.fillText((groups[i].visitors || 0) + " 人次", groupX, h - padding.bottom + 26);
                        }
                    }
                }
            }

            // ── Section: 客群画像 - 性别 ───────
            Label {
                text: qsTr("客群画像 - 性别")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                color: "white"
                radius: 8
                border.width: 1
                border.color: "#E0E0E0"

                ListView {
                    id: genderList
                    anchors.fill: parent
                    anchors.margins: 16
                    orientation: ListView.Horizontal
                    spacing: 16
                    clip: true
                    model: consumptionManager.demographics ? consumptionManager.demographics.gender || [] : []

                    Label {
                        anchors.centerIn: parent
                        text: qsTr("暂无数据")
                        font.pixelSize: 13
                        color: "#999"
                        visible: genderList.count === 0
                    }

                    delegate: Rectangle {
                        width: genderList.width / Math.max(1, genderList.count) - 16
                        height: genderList.height
                        color: "#FAFAFA"
                        radius: 8
                        border.width: 1
                        border.color: "#E0E0E0"

                        Column {
                            anchors.centerIn: parent
                            spacing: 6

                            // 性别图标
                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (modelData.gender === "男") ? "♂" : "♀"
                                font.pixelSize: 28
                                color: modelData.gender === "男" ? "#1976D2" : "#E91E63"
                            }

                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.gender || "未知"
                                font.pixelSize: 13
                                color: "#666"
                            }

                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: (modelData.visitors || 0) + " 人次"
                                font.pixelSize: 12
                                color: "#999"
                            }

                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "总营收: ¥" + (modelData.revenue || 0).toFixed(0)
                                font.pixelSize: 13
                                font.bold: true
                                color: "#333"
                            }

                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "人均: ¥" + (modelData.avg_spending || 0).toFixed(2)
                                font.pixelSize: 12
                                color: "#666"
                            }
                        }
                    }
                }
            }
        }
    }

    // ── 工具函数：金额格式化（千分位）─────────
    function formatMoney(v) {
        if (v === undefined || v === null) v = 0;
        var n = Math.round(v);
        // 千分位分隔符
        return n.toLocaleString(Qt.locale("zh_CN"), 'f', 0);
    }

    // ── 度量卡组件 ──────────────────────
    component ConsumptionCard: Rectangle {
        property string title: ""
        property string valueText: ""
        property string accentColor: "#1976D2"

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
                text: valueText
                font.pixelSize: 20
                font.bold: true
                color: accentColor
                elide: Label.ElideRight
            }
        }
    }
}