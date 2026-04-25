import QtQuick
import QtQuick.Controls

Item {
    id: root
    implicitWidth: 120
    implicitHeight: 160

    property string avatarName: "小导"
    property string avatarDescription: "标准导游"
    property string avatarColor: "#2196F3"
    property int avatarSize: 100

    Column {
        anchors.centerIn: parent
        spacing: 8

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: avatarSize
            height: avatarSize
            radius: avatarSize / 2
            color: avatarColor

            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 0.85
                height: parent.height * 0.85
                radius: parent.radius * 0.85
                color: Qt.lighter(avatarColor, 1.3)

                Text {
                    anchors.centerIn: parent
                    text: avatarName.length > 0 ? avatarName.charAt(0) : "?"
                    font.pixelSize: avatarSize * 0.4
                    font.bold: true
                    color: "white"
                }
            }

            Rectangle {
                anchors {
                    right: parent.right
                    bottom: parent.bottom
                }
                width: 28
                height: 28
                radius: 14
                color: "#4CAF50"
                border.color: "white"
                border.width: 2

                Text {
                    anchors.centerIn: parent
                    text: "🎤"
                    font.pixelSize: 14
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: avatarName
            font.pixelSize: 16
            font.bold: true
            color: "#333"
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: avatarDescription
            font.pixelSize: 12
            color: "#999"
        }
    }
}
