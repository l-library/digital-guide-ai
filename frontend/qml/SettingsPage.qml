import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs

Page {
    id: root
    signal navigateBack()
    signal logoutRequested()

    property string avatarImagePath: loginManager.currentUser.avatarUrl || ""

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
                    spacing: 12

                    // Avatar + display name row
                    RowLayout {
                        spacing: 12

                        // Avatar circle (first character of displayName)
                        Rectangle {
                            id: userAvatarRect
                            width: 56; height: 56; radius: 28
                            color: Material.color(Material.Blue, Material.Shade300)
                            clip: true

                            Image {
                                anchors.fill: parent
                                source: (loginManager.currentUser.avatarUrl && loginManager.currentUser.avatarUrl !== "") 
                                        ? "file://" + loginManager.currentUser.avatarUrl 
                                        : ""
                                fillMode: Image.PreserveAspectCrop
                                visible: loginManager.currentUser.avatarUrl && loginManager.currentUser.avatarUrl !== ""
                            }

                            Text {
                                anchors.centerIn: parent
                                text: loginManager.currentUser.displayName 
                                      ? loginManager.currentUser.displayName.charAt(0).toUpperCase() 
                                      : (loginManager.currentUser.username 
                                         ? loginManager.currentUser.username.charAt(0).toUpperCase() 
                                         : "?")
                                font.pixelSize: 24
                                font.bold: true
                                color: "white"
                                visible: !(loginManager.currentUser.avatarUrl && loginManager.currentUser.avatarUrl !== "")
                            }
                        }

                        ColumnLayout {
                            spacing: 4

                            // Display name
                            Label {
                                text: loginManager.currentUser.displayName 
                                      || loginManager.currentUser.username 
                                      || qsTr("未知用户")
                                font.pixelSize: 18
                                font.bold: true
                            }

                            // Username
                            Label {
                                text: "@" + (loginManager.currentUser.username || "")
                                font.pixelSize: 13
                                color: "#666"
                            }
                        }
                    }

                    // Role badge
                    Rectangle {
                        Layout.preferredWidth: roleLabel.implicitWidth + 16
                        Layout.preferredHeight: 24
                        radius: 12
                        color: loginManager.currentUser.role === "admin" 
                               ? Material.color(Material.Orange, Material.Shade200)
                               : Material.color(Material.Blue, Material.Shade100)

                        Label {
                            id: roleLabel
                            anchors.centerIn: parent
                            text: loginManager.currentUser.role === "admin" 
                                  ? qsTr("👑 管理员") 
                                  : qsTr("👤 游客")
                            font.pixelSize: 12
                            font.bold: true
                            color: loginManager.currentUser.role === "admin" 
                                   ? Material.color(Material.Orange, Material.Shade900)
                                   : Material.color(Material.Blue, Material.Shade900)
                        }
                    }
                }
            }

            GroupBox {
                title: qsTr("账号设置")
                Layout.fillWidth: true
                Material.elevation: 2

                ColumnLayout {
                    width: parent.width
                    spacing: 16

                    // 修改头像
                    RowLayout {
                        spacing: 12

                        Label {
                            text: qsTr("头像")
                            font.pixelSize: 14
                            Layout.preferredWidth: 60
                        }

                        Rectangle {
                            id: avatarPreview
                            width: 64; height: 64; radius: 32
                            color: Material.color(Material.Grey, Material.Shade200)
                            border.width: 1
                            border.color: Material.color(Material.Grey, Material.Shade400)
                            clip: true

                            Image {
                                anchors.fill: parent
                                source: avatarImagePath !== "" ? "file://" + avatarImagePath : ""
                                fillMode: Image.PreserveAspectCrop
                                visible: avatarImagePath !== ""
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "?"
                                font.pixelSize: 20
                                color: "#999"
                                visible: avatarImagePath === ""
                            }
                        }

                        Button {
                            text: qsTr("选择图片")
                            font.pixelSize: 13
                            flat: true
                            onClicked: avatarFileDialog.open()
                        }

                        Button {
                            text: qsTr("清除")
                            font.pixelSize: 13
                            flat: true
                            visible: avatarImagePath !== ""
                            onClicked: avatarImagePath = ""
                        }
                    }

                    // 修改昵称
                    RowLayout {
                        spacing: 12

                        Label {
                            text: qsTr("昵称")
                            font.pixelSize: 14
                            Layout.preferredWidth: 60
                        }

                        TextField {
                            id: nicknameField
                            Layout.fillWidth: true
                            font.pixelSize: 14
                            placeholderText: qsTr("请输入新昵称")
                            text: loginManager.currentUser.displayName || ""
                            maximumLength: 50
                        }
                    }

                    // 保存个人资料按钮
                    RowLayout {
                        Item { Layout.fillWidth: true }

                        Button {
                            text: qsTr("保存资料")
                            font.pixelSize: 14
                            enabled: nicknameField.text.length > 0
                            onClicked: {
                                loginManager.updateProfile(nicknameField.text, avatarImagePath)
                                profileSavedDialog.open()
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#E0E0E0"
                    }

                    // 修改密码
                    Label {
                        text: qsTr("修改密码")
                        font.pixelSize: 14
                        font.bold: true
                    }

                    RowLayout {
                        spacing: 12

                        Label {
                            text: qsTr("旧密码")
                            font.pixelSize: 14
                            Layout.preferredWidth: 60
                        }

                        TextField {
                            id: oldPasswordField
                            Layout.fillWidth: true
                            font.pixelSize: 14
                            placeholderText: qsTr("请输入旧密码")
                            echoMode: TextInput.Password
                        }
                    }

                    RowLayout {
                        spacing: 12

                        Label {
                            text: qsTr("新密码")
                            font.pixelSize: 14
                            Layout.preferredWidth: 60
                        }

                        TextField {
                            id: newPasswordField
                            Layout.fillWidth: true
                            font.pixelSize: 14
                            placeholderText: qsTr("请输入新密码")
                            echoMode: TextInput.Password
                            maximumLength: 64
                        }
                    }

                    RowLayout {
                        spacing: 12

                        Label {
                            text: qsTr("确认密码")
                            font.pixelSize: 14
                            Layout.preferredWidth: 60
                        }

                        TextField {
                            id: confirmPasswordField
                            Layout.fillWidth: true
                            font.pixelSize: 14
                            placeholderText: qsTr("请再次输入新密码")
                            echoMode: TextInput.Password
                            maximumLength: 64
                        }
                    }

                    RowLayout {
                        Item { Layout.fillWidth: true }

                        Button {
                            text: qsTr("修改密码")
                            font.pixelSize: 14
                            enabled: oldPasswordField.text.length > 0 
                                     && newPasswordField.text.length >= 6 
                                     && newPasswordField.text === confirmPasswordField.text
                            onClicked: {
                                loginManager.changePassword(oldPasswordField.text, newPasswordField.text)
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
                        visible: loginManager.currentUser && loginManager.currentUser.role === "admin"
                        text: qsTr("数据大屏")
                        icon.source: "qrc:/asset/data.png"
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
                        text: qsTr("退出登录")
                        icon.source: "qrc:/asset/exit.png"
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

    FileDialog {
        id: avatarFileDialog
        title: qsTr("选择头像图片")
        fileMode: FileDialog.OpenFile
        nameFilters: ["图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)", "所有文件 (*)"]

        onAccepted: {
            avatarImagePath = selectedFile.toString().replace("file://", "")
        }
    }

    Dialog {
        id: profileSavedDialog
        title: qsTr("提示")
        standardButtons: Dialog.Ok
        modal: true
        anchors.centerIn: parent

        Label {
            text: qsTr("个人资料已保存")
            font.pixelSize: 14
        }
    }

    Dialog {
        id: passwordResultDialog
        title: qsTr("提示")
        standardButtons: Dialog.Ok
        modal: true
        anchors.centerIn: parent

        property string messageText: ""

        Label {
            text: passwordResultDialog.messageText
            font.pixelSize: 14
        }

        onAccepted: {
            if (passwordResultDialog.messageText.indexOf("成功") >= 0) {
                oldPasswordField.text = ""
                newPasswordField.text = ""
                confirmPasswordField.text = ""
            }
        }
    }

    Connections {
        target: loginManager
        function onProfileUpdated(displayName, avatarUrl) {
            avatarImagePath = avatarUrl || ""
        }
        function onPasswordChangeSucceeded() {
            passwordResultDialog.messageText = qsTr("密码修改成功")
            passwordResultDialog.open()
        }
        function onPasswordChangeFailed(error) {
            passwordResultDialog.messageText = error
            passwordResultDialog.open()
        }
    }
}
