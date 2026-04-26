import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs

Page {
    id: root
    signal navigateBack()
    signal logoutRequested()

    header: ToolBar {
        Material.background: Material.color(Material.Blue, Material.Shade700)
        Material.foreground: "white"

        RowLayout {
            anchors.fill: parent
            spacing: 4

            ToolButton {
                text: qsTr("‹ 返回")
                font.pixelSize: 16
                onClicked: root.navigateBack()
            }

            Item {
                Layout.fillWidth: true
            }

            Label {
                text: qsTr("设置")
                font.pixelSize: 18
                font.bold: true
                elide: Label.ElideRight
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: parent.width
        contentHeight: settingsColumn.height + 32

        ColumnLayout {
            id: settingsColumn
            width: parent.width - 32
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 16

            Item { width: 1; height: 8 }

            GroupBox {
                title: qsTr("个人信息")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        spacing: 12

                        Rectangle {
                            width: 48; height: 48; radius: 24
                            color: Material.color(Material.Blue, Material.Shade200)

                            Text {
                                anchors.centerIn: parent
                                text: settingsManager.userInfo.displayName
                                      ? settingsManager.userInfo.displayName.charAt(0) : "?"
                                font.pixelSize: 22
                                font.bold: true
                                color: "white"
                            }
                        }

                        ColumnLayout {
                            spacing: 2
                            Label {
                                text: settingsManager.userInfo.displayName || qsTr("未知用户")
                                font.pixelSize: 16
                                font.bold: true
                            }
                            Label {
                                text: settingsManager.userInfo.username || ""
                                font.pixelSize: 13
                                color: "#999"
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("数字人选择")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 4

                    Repeater {
                        model: settingsManager.digitalHumans
                        delegate: ItemDelegate {
                            Layout.fillWidth: true
                            height: 48

                            onClicked: {
                                if (modelData.id !== settingsManager.currentDigitalHumanId) {
                                    settingsManager.switchDigitalHuman(modelData.id)
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                spacing: 12

                                Rectangle {
                                    width: 36; height: 36; radius: 18
                                    Layout.alignment: Qt.AlignLeft
                                    color: modelData.id === settingsManager.currentDigitalHumanId
                                           ? Material.accent : Material.color(Material.Grey, Material.Shade300)

                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData.name.charAt(0)
                                        font.pixelSize: 16
                                        font.bold: true
                                        color: "white"
                                    }
                                }

                                ColumnLayout {
                                    spacing: 2
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 100
                                    Label {
                                        text: modelData.name
                                        font.pixelSize: 15
                                        font.bold: true
                                    }
                                    Label {
                                        text: modelData.description || ""
                                        font.pixelSize: 12
                                        color: "#999"
                                    }
                                }

                                // 自定义指示器
                                Rectangle {
                                    width: 20
                                    height: 20
                                    radius: 10
                                    border.width: 1
                                    border.color: modelData.id === settingsManager.currentDigitalHumanId
                                                  ? Material.accent : "#999"
                                    color: "transparent"
                                    Layout.alignment: Qt.AlignRight

                                    Rectangle {
                                        width: 12
                                        height: 12
                                        radius: width/2
                                        anchors.centerIn: parent
                                        visible: modelData.id === settingsManager.currentDigitalHumanId
                                        color: Material.accent
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("知识库管理")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    Button {
                        text: qsTr("📄 上传文档")
                        Layout.fillWidth: true
                        font.pixelSize: 14
                        flat: true
                        onClicked: {
                            fileDialog.open()
                        }
                    }

                    Repeater {
                        model: settingsManager.knowledgeDocs
                        delegate: RowLayout {
                            width: parent.width
                            height: 40
                            spacing: 8

                            Text {
                                text: "📄"
                                font.pixelSize: 16
                            }

                            Label {
                                text: modelData.title
                                font.pixelSize: 14
                                Layout.fillWidth: true
                                elide: Label.ElideRight
                            }

                            ToolButton {
                                text: qsTr("✕")
                                font.pixelSize: 14
                                Material.foreground: Material.Red
                                onClicked: {
                                    settingsManager.deleteKnowledgeDoc(modelData.id)
                                }
                            }
                        }
                    }

                    Label {
                        text: qsTr("暂无文档")
                        font.pixelSize: 13
                        color: "#999"
                        visible: settingsManager.knowledgeDocs.length === 0
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }

            GroupBox {
                title: qsTr("其他")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 0

                    ItemDelegate {
                        Layout.fillWidth: true
                        text: qsTr("📊 数据大屏")
                        font.pixelSize: 14
                        onClicked: settingsManager.openDataDashboard()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#E0E0E0"
                    }

                    ItemDelegate {
                        Layout.fillWidth: true
                        text: qsTr("🚪 退出登录")
                        font.pixelSize: 14
                        Material.foreground: Material.Red
                        onClicked: {
                            logoutConfirmDialog.open()
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: logoutConfirmDialog
        title: qsTr("确认退出")
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        anchors.centerIn: parent

        Label {
            text: qsTr("确定要退出登录吗？")
            font.pixelSize: 14
        }

        onAccepted: {
            root.logoutRequested()
        }
    }

    FileDialog {
        id: fileDialog
        title: qsTr("选择文档")
        fileMode: FileDialog.OpenFile
        nameFilters: ["文档文件 (*.txt *.md *.pdf *.docx)", "所有文件 (*)"]

        onAccepted: {
            var userId = loginManager.currentUser.id
            settingsManager.uploadKnowledgeDoc(userId, selectedFile.toString().replace("file://", ""))
        }
    }
}
