import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "./components"

Page {
    id: root
    signal navigateToHistory()
    signal navigateToSettings()

    // 属性定义
    property string inputMode: "text"

    header: ToolBar {
        background: Rectangle { color: "#1976D2" }

        RowLayout {
            anchors.fill: parent
            spacing: 5

            ToolButton {
                icon.source: "qrc:/asset/menu.png"
                onClicked: drawer.open()
            }

            Label {
                text: qsTr("数字人导游")
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
                elide: Label.ElideRight
                color: "white"
            }

            Rectangle {
                width: 32
                height: 32
                radius: width / 2
                clip: true
                antialiasing: true

                Image {
                    anchors.fill: parent
                    source: "qrc:/asset/avatar.jpeg"
                    fillMode: Image.PreserveAspectCrop
                    smooth: true
                }
            }

            Label {
                text: digitalHumanManager ? digitalHumanManager.currentName : ""
                font.pixelSize: 13
                opacity: 0.9
                visible: digitalHumanManager && digitalHumanManager.currentName !== ""
                color: "white"
            }

            ToolButton {
                icon.source: "qrc:/asset/exchange.png"
                onClicked: {
                    if (digitalHumanManager && digitalHumanManager.digitalHumans.length > 0) {
                        digitalHumanManager.switchTo(
                            (digitalHumanManager.currentIndex + 1) % Math.max(digitalHumanManager.digitalHumans.length, 1))
                    }
                }
            }
        }
    }

    Drawer {
        id: drawer
        width: parent.width * 0.7
        height: parent.height

        ListView {
            anchors.fill: parent
            topMargin: 40

            model: ListModel {
                ListElement { iconSource: "qrc:/asset/new.png"; label: "新对话"; action: "newChat" }
                ListElement { iconSource: "qrc:/asset/history.png"; label: "历史记录"; action: "history" }
                ListElement { iconSource: "qrc:/asset/setting.png"; label: "设置"; action: "settings" }
            }

            delegate: ItemDelegate {
                width: parent.width
                height: 56

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    spacing: 16
                    Rectangle {
                        width: 28
                        height: 28
                        color: "transparent"

                        Image {
                            id: menuIcon
                            source: model.iconSource
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            sourceSize.width: width * 2
                            sourceSize.height: height * 2
                            asynchronous: true

                            // 加载失败时显示默认图标
                            onStatusChanged: {
                                if (status === Image.Error) {
                                    source = "qrc:/asset/failure.png"
                                }
                            }
                        }

                        Rectangle {
                            anchors.fill: parent
                            color: "#eee"
                            visible: menuIcon.status === Image.Loading
                            radius: 4
                        }
                    }

                    Label {
                        text: model.label
                        font.pixelSize: 16
                        Layout.fillWidth: true
                        verticalAlignment: Text.AlignVCenter
                    }

                    Text {
                        text: "›"
                        font.pixelSize: 20
                        color: "#ccc"
                    }
                }

                onClicked: {
                    drawer.close()
                    switch (model.action) {
                    case "newChat":
                        if (loginManager && loginManager.currentUser) {
                            conversationManager.startNewConversation(loginManager.currentUser.id, "新对话")
                        }
                        break
                    case "history":
                        root.navigateToHistory()
                        break
                    case "settings":
                        root.navigateToSettings()
                        break
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            visible: true

            Row {
                anchors.centerIn: parent
                spacing: 8

                Button {
                    text: qsTr("文字输入")
                    font.pixelSize: 12
                    flat: true
                    highlighted: root.inputMode === "text"
                    onClicked: root.inputMode = "text"
                }

                Button {
                    text: qsTr("语音输入")
                    font.pixelSize: 12
                    flat: true
                    highlighted: root.inputMode === "voice"
                    onClicked: root.inputMode = "voice"
                }
            }
        }

        ListView {
            id: messageList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            topMargin: 8
            bottomMargin: 8
            spacing: 4

            model: conversationManager ? conversationManager.messages : null
            delegate: MessageBubble {
                width: messageList.width
                isUser: modelData.role === "user"
                messageText: modelData.content
                messageTime: {
                    var d = new Date(modelData.timestamp)
                    return d.getHours().toString().padStart(2,"0") + ":" + d.getMinutes().toString().padStart(2,"0")
                }
            }

            ScrollBar.vertical: ScrollBar {}

            onCountChanged: {
                if (count > 0) {
                    Qt.callLater(() => positionViewAtEnd())
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: inputArea.implicitHeight
            color: "white"

            ColumnLayout {
                id: inputArea
                width: parent.width
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#E0E0E0"
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: 8
                    spacing: 8
                    visible: root.inputMode === "text"

                    TextField {
                        id: inputField
                        Layout.fillWidth: true
                        placeholderText: qsTr("输入消息...")
                        font.pixelSize: 15
                        leftPadding: 12
                        height: 44
                        Material.accent: Material.Blue
                        onAccepted: if (sendBtn.enabled) sendBtn.clicked()
                    }

                    Button {
                        id: sendBtn
                        text: qsTr("发送")
                        font.pixelSize: 15
                        font.bold: true
                        enabled: inputField.text.trim() !== ""
                        Material.background: enabled ? Material.accent : "#ccc"
                        Material.foreground: "white"
                        implicitWidth: 80
                        implicitHeight: 44

                        onClicked: {
                            if (conversationManager) {
                                conversationManager.sendMessage(inputField.text)
                                inputField.text = ""
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 56
                    Layout.margins: 8
                    spacing: 8
                    visible: root.inputMode === "voice"

                    Button {
                        id: recordBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        text: (voiceInterface && voiceInterface.state === voiceInterface.Recording)
                              ? qsTr("■ 停止录音")
                              : qsTr("🎤 按住说话")
                        font.pixelSize: 16
                        Material.background: (voiceInterface && voiceInterface.state === voiceInterface.Recording)
                                             ? Material.Red : Material.accent
                        Material.foreground: "white"

                        onClicked: {
                            if (voiceInterface) {
                                if (voiceInterface.state === voiceInterface.Idle) {
                                    voiceInterface.startRecording()
                                } else if (voiceInterface.state === voiceInterface.Recording) {
                                    voiceInterface.stopRecording()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 安全检查
    Connections {
        target: conversationManager
        enabled: conversationManager !== null
        function onMessageSending() {
            Qt.callLater(() => messageList.positionViewAtEnd())
        }
    }

    Connections {
        target: voiceInterface
        enabled: voiceInterface !== null
        function onVoiceInputReceived(text) {
            if (text && text.trim() !== "" && conversationManager) {
                conversationManager.sendMessage(text)
            }
        }
    }
}
