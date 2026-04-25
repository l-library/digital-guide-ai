import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Page {
    id: root
    signal loginSucceeded()

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
                        text: qsTr("登录您的账号")
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

                    Button {
                        id: loginBtn
                        Layout.fillWidth: true
                        text: qsTr("登 录")
                        font.pixelSize: 16
                        font.bold: true
                        height: 48
                        enabled: usernameField.text.trim() !== "" && passwordField.text !== "" && !loginBtn.loading

                        property bool loading: false

                        Material.background: enabled ? Material.accent : "#ccc"
                        Material.foreground: "white"

                        onClicked: {
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
}
