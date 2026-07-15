import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Page {
    id: root
    signal loginSucceeded()
    signal registerSucceeded(string username, string password)

    property bool isRegisterMode: false

    Rectangle {
        anchors.fill: parent
        color: Material.background

        ScrollView {
            anchors.fill: parent
            contentWidth: parent.width
            contentHeight: card.height + 40

            Pane {
                id: card
                width: Math.min(parent.width - 40, 400)
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: parent.height * 0.15
                padding: 32

                Material.elevation: 4

                ColumnLayout {
                    width: parent.width
                    spacing: 24

                    Text {
                        text: qsTr("数字人导游")
                        font.pixelSize: 28
                        font.bold: true
                        color: Material.accent
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Text {
                        text: isRegisterMode ? qsTr("注册新账号") : qsTr("登录您的账号")
                        font.pixelSize: 14
                        color: "#666"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Item { width: 1; height: 8 }

                    TextField {
                        id: usernameField
                        Layout.fillWidth: true
                        placeholderText: qsTr("用户名")
                        leftPadding: 12
                        font.pixelSize: 16
                        height: 48
                        Material.accent: Material.Blue
                    }

                    TextField {
                        id: passwordField
                        Layout.fillWidth: true
                        placeholderText: qsTr("密码")
                        echoMode: TextInput.Password
                        leftPadding: 12
                        font.pixelSize: 16
                        height: 48
                        Material.accent: Material.Blue
                        onAccepted: loginBtn.clicked()
                    }

                    TextField {
                        id: confirmPasswordField
                        Layout.fillWidth: true
                        visible: isRegisterMode
                        placeholderText: qsTr("确认密码")
                        echoMode: TextInput.Password
                        leftPadding: 12
                        font.pixelSize: 16
                        height: 48
                        Material.accent: Material.Blue
                        onAccepted: loginBtn.clicked()
                    }

                    TextField {
                        id: displayNameField
                        Layout.fillWidth: true
                        visible: isRegisterMode
                        placeholderText: qsTr("昵称")
                        leftPadding: 12
                        font.pixelSize: 16
                        height: 48
                        Material.accent: Material.Blue
                    }

                    CheckBox {
                        id: rememberCb
                        text: qsTr("记住登录状态")
                        checked: true
                        font.pixelSize: 13
                    }

                    Text {
                        id: errorText
                        visible: false
                        color: Material.Red
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        text: isRegisterMode ? qsTr("已有账号？登录") : qsTr("没有账号？注册")
                        color: Material.accent
                        font.pixelSize: 13
                        Layout.alignment: Qt.AlignHCenter

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                isRegisterMode = !isRegisterMode
                                errorText.visible = false
                            }
                        }
                    }

                    Text {
                        text: qsTr("服务器设置")
                        color: "#999"
                        font.pixelSize: 12
                        Layout.alignment: Qt.AlignHCenter

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: serverConfigDialog.open()
                        }
                    }

                    Button {
                        id: loginBtn
                        Layout.fillWidth: true
                        text: isRegisterMode ? qsTr("注 册") : qsTr("登 录")
                        font.pixelSize: 16
                        font.bold: true
                        height: 48
                        enabled: isRegisterMode
                                  ? (usernameField.text.trim() !== "" && passwordField.text !== ""
                                     && confirmPasswordField.text !== "" && displayNameField.text.trim() !== ""
                                     && !loginBtn.loading)
                                  : (usernameField.text.trim() !== "" && passwordField.text !== "" && !loginBtn.loading)

                        property bool loading: false

                        Material.background: enabled ? Material.accent : "#ccc"
                        Material.foreground: "white"

                        onClicked: {
                            if (isRegisterMode) {
                                if (confirmPasswordField.text !== passwordField.text) {
                                    errorText.text = qsTr("两次输入的密码不一致")
                                    errorText.color = Material.Red
                                    errorText.visible = true
                                    return
                                }
                                if (displayNameField.text.trim() === "") {
                                    errorText.text = qsTr("请输入昵称")
                                    errorText.color = Material.Red
                                    errorText.visible = true
                                    return
                                }
                                root.registerSucceeded(usernameField.text.trim(), passwordField.text)
                                return
                            }
                            loading = true
                            errorText.visible = false
                            loginManager.login(usernameField.text.trim(), passwordField.text, rememberCb.checked)
                        }
                    }

                    Connections {
                        target: loginManager
                        function onLoginStateChanged() {
                            if (loginManager.loggedIn) {
                                root.loginSucceeded()
                            }
                            loginBtn.loading = false
                        }
                        function onLoginFailed(error) {
                            errorText.text = error
                            errorText.visible = true
                            loginBtn.loading = false
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: serverConfigDialog
        title: qsTr("服务器地址")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 350)

        ColumnLayout {
            width: parent.width
            spacing: 12

            Label {
                text: qsTr("地址")
                font.pixelSize: 14
            }

            TextField {
                id: configIpField
                Layout.fillWidth: true
                font.pixelSize: 14
                text: settingsManager.backendIp
            }

            Label {
                text: qsTr("端口")
                font.pixelSize: 14
            }

            TextField {
                id: configPortField
                Layout.fillWidth: true
                font.pixelSize: 14
                text: settingsManager.backendPort
                validator: IntValidator { bottom: 1; top: 65535 }
                inputMethodHints: Qt.ImhDigitsOnly
            }
        }

        onAccepted: {
            settingsManager.saveServerConfig(configIpField.text, parseInt(configPortField.text))
        }
    }
}
