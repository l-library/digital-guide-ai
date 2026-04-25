import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "./components"

Page {
    id: root
    signal navigateToHistory()
    signal navigateToSettings()

    header: ToolBar {
        background: Rectangle { color: "#1976D2" }

        RowLayout {
            anchors.fill: parent
            spacing: 4

            ToolButton {
                text: qsTr("☰")
                font.pixelSize: 20
                contentItem: Text { text: qsTr("☰"); font.pixelSize: 20; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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

            Label {
                text: digitalHumanManager.currentName
                font.pixelSize: 13
                opacity: 0.9
                visible: digitalHumanManager.currentName !== ""
                color: "white"
            }

            ToolButton {
                text: qsTr("🔄")
                font.pixelSize: 18
                contentItem: Text { text: qsTr("🔄"); font.pixelSize: 18; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: {
                    digitalHumanManager.switchTo(
                        (digitalHumanManager.currentIndex + 1) % Math.max(digitalHumanManager.digitalHumans.length, 1))
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
                ListElement { icon: "💬"; label: "新对话"; action: "newChat" }
                ListElement { icon: "📋"; label: "历史记录"; action: "history" }
                ListElement { icon: "⚙️"; label: "设置"; action: "settings" }
            }

            delegate: ItemDelegate {
                width: parent.width
                height: 56

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 24
                    spacing: 16

                    Text {
                        text: model.icon
                        font.pixelSize: 22
                    }

                    Label {
                        text: model.label
                        font.pixelSize: 16
                        Layout.fillWidth: true
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
                        var userId = loginManager.currentUser.id
                        conversationManager.startNewConversation(userId, "新对话")
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

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 200
            color: "#E3F2FD"

            DigitalHumanAvatar {
                anchors.centerIn: parent
                avatarSize: 90
                avatarName: digitalHumanManager.currentName
            }

            Column {
                anchors {
                    bottom: parent.bottom
                    horizontalCenter: parent.horizontalCenter
                    bottomMargin: 8
                }
                spacing: 4

                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 8

                    Button {
                        text: qsTr("文字输入")
                        font.pixelSize: 12
                        flat: true
                        highlighted: inputModeGroup.current === "text"
                        onClicked: inputModeGroup.current = "text"
                    }

                    Button {
                        text: qsTr("语音输入")
                        font.pixelSize: 12
                        flat: true
                        highlighted: inputModeGroup.current === "voice"
                        onClicked: inputModeGroup.current = "voice"
                    }
                }
            }
        }

        QtObject { id: inputModeGroup; property string current: "text" }

        ListView {
            id: messageList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            topMargin: 8
            bottomMargin: 8
            spacing: 4

            model: conversationManager.messages
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
                    positionViewAtEnd()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: inputArea.height
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
                    visible: inputModeGroup.current === "text"

                    TextField {
                        id: inputField
                        Layout.fillWidth: true
                        placeholderText: qsTr("输入消息...")
                        font.pixelSize: 15
                        leftPadding: 12
                        height: 44
                        Material.accent: Material.Blue
                        onAccepted: sendBtn.clicked()
                    }

                    Button {
                        id: sendBtn
                        text: qsTr("发送")
                        font.pixelSize: 14
                        font.bold: true
                        enabled: inputField.text.trim() !== ""
                        Material.background: enabled ? Material.accent : "#ccc"
                        Material.foreground: "white"
                        implicitWidth: 64
                        implicitHeight: 44

                        onClicked: {
                            conversationManager.sendMessage(inputField.text)
                            inputField.text = ""
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 56
                    Layout.margins: 8
                    spacing: 8
                    visible: inputModeGroup.current === "voice"

                    Button {
                        id: recordBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        text: voiceInterface.state === voiceInterface.Recording
                              ? qsTr("■ 停止录音")
                              : qsTr("🎤 按住说话")
                        font.pixelSize: 16
                        Material.background: voiceInterface.state === voiceInterface.Recording
                                             ? Material.Red : Material.accent
                        Material.foreground: "white"

                        onClicked: {
                            if (voiceInterface.state === voiceInterface.Idle) {
                                voiceInterface.startRecording()
                            } else if (voiceInterface.state === voiceInterface.Recording) {
                                voiceInterface.stopRecording()
                            }
                        }
                    }
                }

                Connections {
                    target: voiceInterface
                    function onVoiceInputReceived(text) {
                        if (text.trim() !== "") {
                            conversationManager.sendMessage(text)
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: conversationManager
        function onMessageSending() {
            messageList.positionViewAtEnd()
        }
    }
}
