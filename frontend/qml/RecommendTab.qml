import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root

    // 自动加载：首次显示时触发推荐请求
    property bool dataLoaded: false

    onVisibleChanged: {
        if (visible && !dataLoaded) {
            dataLoaded = true
            if (recommendManager && loginManager) {
                recommendManager.loadRecommend(loginManager.currentUser.id)
            }
        }
    }

    Component.onCompleted: {
        if (recommendManager && loginManager && loginManager.currentUser) {
            dataLoaded = true
            recommendManager.loadRecommend(loginManager.currentUser.id)
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

            // ── 标题 ──────────────────────────────
            Label {
                text: qsTr("个性化路线推荐")
                font.pixelSize: 18
                font.bold: true
                Layout.topMargin: 8
            }

            // ── 加载状态 ─────────────────────────
            BusyIndicator {
                Layout.alignment: Qt.AlignHCenter
                running: recommendManager && recommendManager.isLoading
                visible: recommendManager && recommendManager.isLoading
            }

            // ── 刷新按钮 ─────────────────────────
            Button {
                text: qsTr("刷新推荐")
                font.pixelSize: 14
                Material.background: Material.accent
                Material.foreground: "white"
                Layout.alignment: Qt.AlignHCenter
                onClicked: {
                    if (recommendManager && loginManager) {
                        recommendManager.loadRecommend(loginManager.currentUser.id)
                    }
                }
            }

            // ── 错误状态 ─────────────────────────
            Label {
                id: errorLabel
                Layout.fillWidth: true
                text: qsTr("推荐服务暂不可用，请稍后再试")
                font.pixelSize: 14
                color: "#F44336"
                horizontalAlignment: Text.AlignHCenter
                visible: false
            }

            Connections {
                target: recommendManager
                function onRecommendError(error) {
                    errorLabel.text = qsTr("推荐加载失败：") + error
                    errorLabel.visible = true
                }
                function onRouteChanged() {
                    if (recommendManager.route && Object.keys(recommendManager.route).length > 0) {
                        errorLabel.visible = false
                    }
                }
            }

            // ── 空状态 ───────────────────────────
            Label {
                Layout.fillWidth: true
                text: qsTr("暂无推荐路线\n请先进行一些对话，让AI了解您的兴趣")
                font.pixelSize: 14
                color: "#999"
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: recommendManager && !recommendManager.isLoading
                         && (!recommendManager.route || Object.keys(recommendManager.route).length === 0)
            }

            // ── 路线卡片 ─────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: routeCardContent.implicitHeight + 24
                radius: 8
                color: "white"
                border.width: 1
                border.color: "#E0E0E0"
                visible: recommendManager && recommendManager.route
                         && Object.keys(recommendManager.route).length > 0

                ColumnLayout {
                    id: routeCardContent
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    // 路线名称
                    Label {
                        text: recommendManager && recommendManager.route.name
                              ? recommendManager.route.name : ""
                        font.pixelSize: 16
                        font.bold: true
                        color: "#1976D2"
                    }

                    // 预计游览时长
                    Label {
                        text: recommendManager && recommendManager.route.duration_minutes
                              ? qsTr("预计游览时长：%1 分钟").arg(recommendManager.route.duration_minutes)
                              : ""
                        font.pixelSize: 13
                        color: "#666"
                    }

                    // 推荐景点标题
                    Label {
                        text: qsTr("推荐景点：")
                        font.pixelSize: 14
                        font.bold: true
                        visible: spotsRepeater.count > 0
                    }

                    // 景点列表
                    Repeater {
                        id: spotsRepeater
                        model: recommendManager && recommendManager.route.spots
                               ? recommendManager.route.spots : []

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            radius: 4
                            color: "#F5F5F5"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 8

                                Label {
                                    text: modelData.name || ""
                                    font.pixelSize: 13
                                    font.bold: true
                                }

                                Label {
                                    text: modelData.estimated_minutes
                                          ? qsTr("约%1分钟").arg(modelData.estimated_minutes)
                                          : ""
                                    font.pixelSize: 12
                                    color: "#999"
                                }

                                Label {
                                    text: modelData.description || ""
                                    font.pixelSize: 12
                                    color: "#555"
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }

                    // 路线亮点标题
                    Label {
                        text: qsTr("路线亮点：")
                        font.pixelSize: 14
                        font.bold: true
                        visible: highlightsText.text !== ""
                    }

                    // 路线亮点内容
                    Label {
                        id: highlightsText
                        Layout.fillWidth: true
                        text: {
                            if (recommendManager && recommendManager.route.highlights) {
                                var h = recommendManager.route.highlights
                                if (Array.isArray(h)) return h.join("、")
                                return h.toString()
                            }
                            return ""
                        }
                        font.pixelSize: 13
                        color: "#333"
                        wrapMode: Text.WordWrap
                    }

                    // 推荐理由
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(reasonLabel.implicitHeight, reasonLabel.paintedHeight) + 16
                        radius: 6
                        color: "#E3F2FD"

                        Label {
                            id: reasonLabel
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 8
                            text: recommendManager && recommendManager.route.match_reason
                                  ? qsTr("推荐理由：%1").arg(recommendManager.route.match_reason)
                                  : ""
                            font.pixelSize: 12
                            color: "#1565C0"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
