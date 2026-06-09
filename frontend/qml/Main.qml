import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ApplicationWindow {
    id: appWindow
    visible: true
    title: qsTr("数字人导游")

    property bool isMobile: Qt.platform.os === "android"
    property int defaultUserId: 1
    width: isMobile ? 420 : 1024
    height: isMobile ? 760 : 700
    minimumWidth: isMobile ? 360 : 1024
    minimumHeight: isMobile ? 600 : 700

    Material.theme: Material.Light
    Material.accent: Material.Blue
    Material.background: "#F5F5F5"

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
            id: chatPage
            ChatPage {
                onNavigateToHistory: {
                    historyManager.loadHistory(appWindow.defaultUserId)
                    stackView.push(historyPage)
                }
                onNavigateToSettings: {
                    settingsManager.loadSettings(appWindow.defaultUserId)
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
            }
        }
    }

    Component.onCompleted: {
        conversationManager.autoLoadOrCreateConversation(appWindow.defaultUserId)
        stackView.replace(chatPage)
    }
}
