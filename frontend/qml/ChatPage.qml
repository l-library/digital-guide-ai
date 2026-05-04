import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "./components"

Page {
    id: root
    signal navigateToHistory()
    signal navigateToSettings()

    property string inputMode: "text"
    property string outputMode: "digitHuman"

    header: ToolBar {
        background: Rectangle { color: "#1976D2" }

        RowLayout {
            anchors.fill: parent
            spacing: 5

            ToolButton {
                icon.source: "qrc:/asset/menu.png"
                onClicked: {
                    conversationManager.loadConversationList(loginManager.currentUser.id)
                    drawer.open()
                }
            }

            Label {
                id: titleLabel
                text: conversationManager && conversationManager.currentTitle
                      ? conversationManager.currentTitle : qsTr("数字人导游")
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
                elide: Label.ElideRight
                color: "white"

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (conversationManager && conversationManager.hasConversation) {
                            renameDialog.open()
                        }
                    }
                }
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

        ColumnLayout {
            anchors.fill: parent
            anchors.topMargin: 20
            spacing: 0

            ItemDelegate {
                Layout.fillWidth: true
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
                            source: "qrc:/asset/new.png"
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                        }
                    }

                    Label {
                        text: qsTr("新对话")
                        font.pixelSize: 16
                        color: "#1976D2"
                        font.bold: true
                        Layout.fillWidth: true
                    }
                }

                onClicked: {
                    drawer.close()
                    if (loginManager && loginManager.currentUser) {
                        conversationManager.startNewConversation(loginManager.currentUser.id, "新对话")
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#E0E0E0"
                Layout.leftMargin: 16
                Layout.rightMargin: 16
            }

            Label {
                text: qsTr("对话列表")
                font.pixelSize: 12
                color: "#999"
                Layout.fillWidth: true
                Layout.leftMargin: 20
                Layout.topMargin: 8
                Layout.bottomMargin: 4
            }

            ListView {
                id: convList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                model: conversationManager ? conversationManager.conversations : null

                delegate: ItemDelegate {
                    width: convList.width
                    height: 64

                    property bool isCurrent: conversationManager
                                             && modelData.id === conversationManager.currentConversationId

                    Rectangle {
                        anchors.fill: parent
                        color: isCurrent ? "#E3F2FD" : "transparent"
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 24
                        anchors.rightMargin: 12
                        spacing: 12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Label {
                                    text: modelData.title || qsTr("未命名对话")
                                    font.pixelSize: 15
                                    font.bold: isCurrent
                                    elide: Label.ElideRight
                                    Layout.fillWidth: true
                                }
                            }

                            Label {
                                text: {
                                    if (modelData.updatedAt) {
                                        var d = new Date(modelData.updatedAt)
                                        return Qt.formatDateTime(d, "MM-dd hh:mm")
                                    }
                                    return ""
                                }
                                font.pixelSize: 11
                                color: "#999"
                            }
                        }

                        ItemDelegate {
                            implicitWidth: 36
                            implicitHeight: 36

                            Image {
                                anchors.centerIn: parent
                                source: "qrc:/asset/setting.png"
                                width: 18
                                height: 18
                                smooth: true
                            }

                            onClicked: {
                                renameDialog.conversationId = modelData.id
                                renameDialog.conversationTitle = modelData.title || ""
                                renameDialog.open()
                            }
                        }
                    }

                    onClicked: {
                        if (!isCurrent) {
                            conversationManager.loadConversation(modelData.id)
                        }
                        drawer.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#E0E0E0"
                Layout.leftMargin: 16
                Layout.rightMargin: 16
            }

            ItemDelegate {
                Layout.fillWidth: true
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
                            source: "qrc:/asset/history.png"
                            width: 28; height: 28
                            smooth: true
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Label {
                        text: qsTr("历史记录")
                        font.pixelSize: 16
                        Layout.fillWidth: true
                    }
                }

                onClicked: {
                    drawer.close()
                    root.navigateToHistory()
                }
            }

            ItemDelegate {
                Layout.fillWidth: true
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
                            source: "qrc:/asset/setting.png"
                            width: 28; height: 28
                            smooth: true
                            fillMode: Image.PreserveAspectFit
                        }
                    }
                    Label {
                        text: qsTr("设置")
                        font.pixelSize: 16
                        Layout.fillWidth: true
                    }
                }
                onClicked: {
                    drawer.close()
                    root.navigateToSettings()
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    Dialog {
        id: renameDialog
        title: qsTr("重命名对话")
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel

        property int conversationId: -1
        property string conversationTitle: ""

        onOpened: {
            nameField.text = conversationTitle
            nameField.selectAll()
            nameField.forceActiveFocus()
        }

        onAccepted: {
            var newTitle = nameField.text.trim()
            if (newTitle !== "" && conversationId > 0) {
                if (conversationId === conversationManager.currentConversationId) {
                    conversationManager.renameCurrentConversation(newTitle)
                } else {
                    conversationManager.renameConversationById(conversationId, newTitle)
                }
            }
        }

        ColumnLayout {
            spacing: 12
            anchors { left: parent.left; right: parent.right }

            Label {
                text: qsTr("请输入新的对话名称：")
                font.pixelSize: 14
            }

            TextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: qsTr("对话名称")
                font.pixelSize: 15
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
                    text: qsTr("数字人")
                    font.pixelSize: 12
                    flat: true
                    highlighted: root.outputMode === "digitHuman"
                    onClicked: root.outputMode = "digitHuman"
                }

                Button {
                    text: qsTr("文字输出")
                    font.pixelSize: 12
                    flat: true
                    highlighted: root.outputMode === "text"
                    onClicked: root.outputMode = "text"
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
            visible: root.outputMode === "text"

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

        Rectangle{
            id: digitHumanDisplay
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: root.outputMode === "digitHuman"
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

                    Button {
                        icon.source: "qrc:/asset/voice.png"
                        font.pixelSize: 12
                        flat: true
                        onClicked: root.inputMode = "voice"
                    }

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
                        icon.source: "qrc:/asset/text.png"
                        font.pixelSize: 12
                        flat: true
                        visible: root.inputMode = "voice"
                        onClicked: root.inputMode = "text"
                    }

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
