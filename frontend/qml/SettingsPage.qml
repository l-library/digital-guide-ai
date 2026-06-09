import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs

Page {
    id: root
    signal navigateBack()

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
                title: qsTr("知识库管理")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    Button {
                        text: qsTr("上传文档")
                        icon.source: "qrc:/asset/upload.png"
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
                                text: "\u{1F4C4}"
                                font.pixelSize: 16
                            }

                            Label {
                                text: modelData.title
                                font.pixelSize: 14
                                Layout.fillWidth: true
                                elide: Label.ElideRight
                            }

                            ToolButton {
                                text: qsTr("\u2715")
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
                title: qsTr("关于")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    Label {
                        text: qsTr("数字人导游")
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Label {
                        text: qsTr("基于 AI 数字人技术的智能景区导览系统")
                        font.pixelSize: 13
                        color: "#666"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: qsTr("选择文档")
        fileMode: FileDialog.OpenFile
        nameFilters: ["文档文件 (*.txt *.md *.pdf *.docx)", "所有文件 (*)"]

        onAccepted: {
            settingsManager.uploadKnowledgeDoc(1, selectedFile.toString().replace("file://", ""))
        }
    }
}
