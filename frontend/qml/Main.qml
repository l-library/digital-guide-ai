import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: appWindow
    visible: true
    title: qsTr("数字人导游")

    property bool isMobile: Qt.platform.os === "android"
    width: isMobile ? 420 : 1024
    height: isMobile ? 760 : 700
    minimumWidth: isMobile ? 360 : 1024
    minimumHeight: isMobile ? 600 : 700

    Material.theme: Material.Light
    Material.accent: Material.Blue
    Material.background: "#F5F5F5"

    property bool initialCheckDone: false

    StackView {
        id: stackView
        anchors.fill: parent
        initialItem: busyPage

        Component {
            id: busyPage
            Item {
                BusyIndicator {
                    anchors.centerIn: parent
                    running: true
                }
            }
        }

        Component {
            id: loginPage
            LoginPage {
                onLoginSucceeded: {
                    initAfterLogin()
                    stackView.replace(chatPage)
                }
                onRegisterSucceeded: function(username, password) {
                    initialCheckDone = false
                    loginManager.registerUser(username, password, password, username)
                }
            }
        }

        Component {
            id: chatPage
            ChatPage {
                onNavigateToHistory: {
                    historyManager.loadHistory(loginManager.currentUser.id)
                    stackView.push(historyPage)
                }
                onNavigateToSettings: {
                    settingsManager.loadSettings(loginManager.currentUser.id)
                    stackView.push(settingsPage)
                }
                onNavigateToAdmin: {
                    adminManager.loadUsers(1, 20, "")
                    stackView.push(adminPage)
                }
            }
        }

        Component {
            id: historyPage
            HistoryPage {
                onNavigateBack: stackView.pop()
                onConversationSelected: function(convId) {
                    conversationManager.loadConversation(convId)
                    stackView.pop()
                }
            }
        }

        Component {
            id: settingsPage
            SettingsPage {
                onNavigateBack: stackView.pop()
                onLogoutRequested: {
                    loginManager.logout()
                    stackView.replace(loginPage)
                }
            }
        }

        Component {
            id: adminPage
            AdminPage {
                onNavigateBack: stackView.pop()
            }
        }
    }

    function initAfterLogin() {
        var userId = loginManager.currentUser.id
        // 先加载已有对话列表，仅当列表为空时才创建新对话，避免重复创建空对话
        conversationManager.autoLoadOrCreateConversation(userId)
    }

    Connections {
        target: loginManager
        function onAutoLoginChecked(loggedIn) {
            if (!initialCheckDone) {
                initialCheckDone = true
                if (loggedIn) {
                    initAfterLogin()
                    stackView.replace(chatPage)
                } else {
                    stackView.replace(loginPage)
                }
            }
        }
    }

    Component.onCompleted: {
        loginManager.checkAutoLogin()
    }
}
