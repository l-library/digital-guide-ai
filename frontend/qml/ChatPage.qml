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
    property bool voiceRequestInFlight: false
    property string ttsStatus: ""

    Component.onCompleted: {
        if (digitalHumanManager && digitalHumanManager.currentDigitalHuman && conversationManager) {
            conversationManager.setDigitalHumanId(digitalHumanManager.currentDigitalHuman.id)
        }
        if (conversationManager) {
            conversationManager.setResponseType(root.outputMode === "digitHuman" ? 1 : 0)
        }
        if (liveTalkingClient && conversationManager) {
            liveTalkingClient.conversationId = conversationManager.currentConversationId
        }
    }

    onOutputModeChanged: {
        if (conversationManager) {
            conversationManager.setResponseType(root.outputMode === "digitHuman" ? 1 : 0)
        }
    }

    Timer {
        id: voiceTimeoutTimer
        interval: 30000
        onTriggered: {
            if (voiceRequestInFlight) {
                voiceRequestInFlight = false
                if (voiceInterface) {
                    voiceInterface.finishProcessing()
                }
            }
        }
    }

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
                        var dh = digitalHumanManager.currentDigitalHuman
                        if (dh && conversationManager) {
                            conversationManager.setDigitalHumanId(dh.id)
                        }
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

    Dialog {
        id: errorDialog
        title: qsTr("错误")
        anchors.centerIn: parent
        standardButtons: Dialog.Ok
        modal: true

        property string errorMessage: ""

        onOpened: {
            errorLabel.text = errorMessage
        }

        ColumnLayout {
            spacing: 12
            anchors { left: parent.left; right: parent.right }

            Label {
                id: errorLabel
                text: ""
                font.pixelSize: 14
                wrapMode: Text.Wrap
                Layout.fillWidth: true
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

        Rectangle {
            id: digitHumanDisplay
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: root.outputMode === "digitHuman"
            color: "#1A1A2E"

            // 数字人视频区域 - 占满整个显示区域
            Rectangle {
                anchors.fill: parent
                color: "#1A1A2E"
                clip: true
                visible: liveTalkingClient && liveTalkingClient.connected

                DigitalHumanView {
                    anchors.fill: parent
                }
            }

            // 未连接时的头像占位
            Rectangle {
                anchors.fill: parent
                color: "#F5F5F5"
                visible: !(liveTalkingClient && liveTalkingClient.connected)

                Column {
                    anchors.centerIn: parent
                    spacing: 16

                    Rectangle {
                        width: 120
                        height: 120
                        radius: 60
                        color: audioPlayer && audioPlayer.playing ? "#C8E6C9" : "#E3F2FD"
                        anchors.horizontalCenter: parent.horizontalCenter

                        SequentialAnimation on border.color {
                            running: audioPlayer && audioPlayer.playing
                            loops: Animation.Infinite
                            ColorAnimation { from: "#1976D2"; to: "#4CAF50"; duration: 600 }
                            ColorAnimation { from: "#4CAF50"; to: "#1976D2"; duration: 600 }
                        }

                        border.width: 3
                        border.color: "#1976D2"
                        clip: true

                        Image {
                            anchors.fill: parent
                            anchors.margins: 16
                            source: "qrc:/asset/avatar.jpeg"
                            fillMode: Image.PreserveAspectCrop
                            smooth: true
                        }
                    }

                    Label {
                        text: qsTr("数字人未连接")
                        font.pixelSize: 14
                        color: "#999"
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }

            // 右上角连接状态徽章 - 半透明叠加在视频上
            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                width: connLabel.implicitWidth + 16
                height: connLabel.implicitHeight + 8
                radius: 4
                color: (liveTalkingClient && liveTalkingClient.connected) ? "#4CAF50" : "#F44336"
                opacity: 0.85

                Label {
                    id: connLabel
                    anchors.centerIn: parent
                    text: (liveTalkingClient && liveTalkingClient.connected) ? qsTr("数字人已连接") : qsTr("数字人未连接")
                    font.pixelSize: 11
                    color: "white"
                }
            }

            // 底部状态栏 - 半透明叠加
            Rectangle {
                id: bottomStatusBar
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: statusBarContent.height + 20
                color: "#B3000000"
                visible: true

                ColumnLayout {
                    id: statusBarContent
                    anchors.centerIn: parent
                    width: parent.width - 32
                    spacing: 4

                    Label {
                        id: statusLabel
                        Layout.alignment: Qt.AlignHCenter
                        font.pixelSize: 14
                        color: "#E0E0E0"
                        text: {
                            if (liveTalkingClient && liveTalkingClient.connected && liveTalkingClient.speaking) {
                                return qsTr("数字人说话中...")
                            }
                            if (audioPlayer && audioPlayer.playing) {
                                return audioPlayer.statusText || qsTr("正在播放语音...")
                            }
                            if (root.ttsStatus === "synthesizing") {
                                return qsTr("语音合成中...")
                            }
                            if (conversationManager && conversationManager.streamingAiResponse) {
                                return qsTr("正在思考...")
                            }
                            if (root.ttsStatus === "ready") {
                                return qsTr("语音回复就绪")
                            }
                            return qsTr("等待提问...")
                        }
                    }

                    ProgressBar {
                        id: ttsProgressBar
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 160
                        visible: root.outputMode === "digitHuman" && (root.ttsStatus === "synthesizing" || (audioPlayer && audioPlayer.playing))
                        indeterminate: true
                    }
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
                                conversationManager.setResponseType(root.outputMode === "digitHuman" ? 1 : 0)
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
                        visible: root.inputMode === "voice"
                        onClicked: root.inputMode = "text"
                    }

                    Button {
                        id: recordBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        text: (voiceInterface && voiceInterface.state === 1)
                              ? qsTr("■ 停止录音")
                              : (voiceInterface && voiceInterface.state === 2)
                              ? qsTr("处理中...")
                              : qsTr("🎤 按住说话")
                        font.pixelSize: 16
                        Material.background: (voiceInterface && voiceInterface.state === 1)
                                              ? Material.Red : Material.accent
                        Material.foreground: "white"
                        enabled: voiceInterface && voiceInterface.state !== 2

                        onClicked: {
                            if (voiceInterface) {
                                console.log("Voice button clicked, state:", voiceInterface.state)
                                if (voiceInterface.state === 0) {
                                    voiceInterface.startRecording()
                                } else if (voiceInterface.state === 1) {
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
        function onCurrentConversationChanged() {
            if (liveTalkingClient && conversationManager) {
                liveTalkingClient.conversationId = conversationManager.currentConversationId
            }
        }
        function onMessagesChanged() {
            if (voiceRequestInFlight) {
                voiceRequestInFlight = false
                voiceTimeoutTimer.stop()
                if (voiceInterface) {
                    voiceInterface.finishProcessing()
                }
            }
        }
        function onErrorOccurred(error) {
            if (voiceRequestInFlight) {
                voiceRequestInFlight = false
                voiceTimeoutTimer.stop()
                if (voiceInterface) {
                    voiceInterface.finishProcessing()
                }
            }
            root.ttsStatus = ""
            errorDialog.errorMessage = error
            errorDialog.open()
        }
        function onCurrentAudioUrlChanged() {
            var url = conversationManager.currentAudioUrl
            if (url && audioPlayer) {
                if (root.outputMode === "digitHuman" && liveTalkingClient
                    && liveTalkingClient.connected && liveTalkingClient.sessionId !== "") {
                    return
                }
                audioPlayer.play(url)
            }
        }
        function onTtsPendingChanged() {
            if (conversationManager.ttsPending) {
                if (root.outputMode === "digitHuman" && liveTalkingClient && liveTalkingClient.connected) {
                    root.ttsStatus = "ready"
                } else {
                    root.ttsStatus = "synthesizing"
                }
            }
        }
        function onStreamingAiResponseChanged() {
            if (!conversationManager.streamingAiResponse) {
                if (conversationManager.currentAudioUrl === "" || conversationManager.currentAudioUrl === undefined) {
                    root.ttsStatus = ""
                }
            }
        }
    }

    Connections {
        target: audioPlayer
        enabled: audioPlayer !== null
        function onPlayingChanged() {
            if (audioPlayer && !audioPlayer.playing) {
                root.ttsStatus = "ready"
            }
        }
        function onPlaybackFinished() {
            root.ttsStatus = ""
        }
    }

    Connections {
        target: liveTalkingClient
        enabled: liveTalkingClient !== null && root.outputMode === "digitHuman"
        function onSpeakingChanged() {
            if (liveTalkingClient && liveTalkingClient.speaking) {
                root.ttsStatus = "ready"
            } else {
                root.ttsStatus = ""
            }
        }
    }

    Connections {
        target: voiceInterface
        enabled: voiceInterface !== null
        function onVoiceRecordingReady(filePath) {
            if (!conversationManager) return
            if (!conversationManager.hasConversation) {
                voiceInterface.finishProcessing()
                errorDialog.errorMessage = qsTr("请先创建或选择一个对话，再开始录音")
                errorDialog.open()
                return
            }
            voiceRequestInFlight = true
            voiceTimeoutTimer.start()
            conversationManager.setResponseType(root.outputMode === "digitHuman" ? 1 : 0)
            conversationManager.sendVoiceMessage(filePath)
        }
        function onErrorOccurred(error) {
            voiceRequestInFlight = false
            voiceTimeoutTimer.stop()
            errorDialog.errorMessage = error
            errorDialog.open()
        }
    }
}
