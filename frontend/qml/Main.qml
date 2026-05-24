import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: appWindow
    visible: true
    title: qsTr("数字人导游")

    property bool isMobile: Qt.platform.os === "android"
    width: isMobile ? 420 : 480
    height: isMobile ? 760 : 800
    minimumWidth: isMobile ? 360 : 360
    minimumHeight: isMobile ? 600 : 600

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
    }

    function initAfterLogin() {
        digitalHumanManager.loadDigitalHumans()
        var userId = loginManager.currentUser.id
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
