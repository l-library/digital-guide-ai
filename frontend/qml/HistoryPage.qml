import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Page {
    id: root
    signal navigateBack()
    signal conversationSelected(int conversationId)

    header: ToolBar {
        background: Rectangle { color: "#1976D2" }

        RowLayout {
            anchors.fill: parent
            spacing: 4

            ToolButton {
                text: qsTr("‹ 返回")
                font.pixelSize: 16
                contentItem: Text { text: qsTr("‹ 返回"); font.pixelSize: 16; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: root.navigateBack()
            }

            Label {
                text: qsTr("历史记录")
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
                elide: Label.ElideRight
                color: "white"
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TextField {
            id: searchField
            Layout.fillWidth: true
            Layout.margins: 12
            placeholderText: qsTr("搜索对话...")
            font.pixelSize: 14
            leftPadding: 36
            height: 44

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                text: "🔍"
                font.pixelSize: 16
            }

            onTextChanged: {
                historyManager.search(loginManager.currentUser.id, text.trim())
            }
        }

        ListView {
            id: historyList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: historyManager.groupedConversations
            delegate: historyGroupDelegate
            ScrollBar.vertical: ScrollBar {}
        }
    }

    Component {
        id: historyGroupDelegate

        Column {
            width: historyList.width
            spacing: 2

            Text {
                x: 16
                topPadding: 16
                bottomPadding: 8
                text: modelData.date
                font.pixelSize: 14
                font.bold: true
                color: Material.accent
            }

            Repeater {
                model: modelData.conversations
                delegate: SwipeDelegate {
                    id: swipeDel
                    width: historyList.width
                    height: 60

                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        spacing: 12

                        Text {
                            text: "💬"
                            font.pixelSize: 22
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Label {
                                text: modelData.title || qsTr("未命名对话")
                                font.pixelSize: 15
                                font.bold: true
                                elide: Label.ElideRight
                                Layout.fillWidth: true
                            }

                            Label {
                                text: {
                                    var d = new Date(modelData.updatedAt)
                                    return d.getFullYear() + "-" +
                                           (d.getMonth()+1).toString().padStart(2,"0") + "-" +
                                           d.getDate().toString().padStart(2,"0") + " " +
                                           d.getHours().toString().padStart(2,"0") + ":" +
                                           d.getMinutes().toString().padStart(2,"0")
                                }
                                font.pixelSize: 12
                                color: "#999"
                            }
                        }

                        Text {
                            text: "›"
                            font.pixelSize: 18
                            color: "#ccc"
                        }
                    }

                    swipe.left: Label {
                        id: deleteLabel
                        text: qsTr("删除")
                        color: "white"
                        verticalAlignment: Label.AlignVCenter
                        horizontalAlignment: Label.AlignHCenter
                        padding: 12
                        width: 72
                        height: parent.height
                        SwipeDelegate.onClicked: {
                            historyManager.deleteConversation(modelData.id)
                        }
                    }

                    swipe.right: Label {
                        text: qsTr("导出")
                        color: "white"
                        verticalAlignment: Label.AlignVCenter
                        horizontalAlignment: Label.AlignHCenter
                        padding: 12
                        width: 72
                        height: parent.height
                        SwipeDelegate.onClicked: {
                            var filePath = "/tmp/conversation_" + modelData.id + ".json"
                            historyManager.exportConversation(modelData.id, filePath)
                        }
                    }

                    onClicked: {
                        root.conversationSelected(modelData.id)
                    }
                }
            }
        }
    }

    Connections {
        target: historyManager
        function onOperationFailed(error) {
            showToast(error)
        }
    }

    function showToast(msg) {
        toastLabel.text = msg
        toastLabel.opacity = 0.9
        toastHideTimer.restart()
    }

    Label {
        id: toastLabel
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 20
        padding: 12
        color: "white"
        font.pixelSize: 14
        background: Rectangle { color: "#424242"; radius: 4 }
        opacity: 0
        z: 100

        Behavior on opacity {
            NumberAnimation { duration: 400 }
        }
    }

    Timer {
        id: toastHideTimer
        interval: 2000
        onTriggered: toastLabel.opacity = 0
    }
}
