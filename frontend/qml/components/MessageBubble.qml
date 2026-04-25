import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property bool isUser: false
    property string messageText: ""
    property string messageTime: ""

    implicitHeight: bubble.height + 32
    width: Math.min(parent ? parent.width : 400, 400)

    color: "transparent"

    Row {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            topMargin: 8
        }
        layoutDirection: isUser ? Qt.RightToLeft : Qt.LeftToRight
        spacing: 8

        Item { width: isUser ? 48 : 8; height: 1 }

        Rectangle {
            id: bubble
            width: Math.max(bubbleText.width + 24, 40)
            height: bubbleText.height + 24
            radius: 12
            color: isUser ? "#2196F3" : "#FFFFFF"
            border.width: isUser ? 0 : 1
            border.color: isUser ? "transparent" : "#E0E0E0"

            Text {
                id: bubbleText
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: 12
                }
                text: messageText
                font.pixelSize: 14
                color: isUser ? "white" : "#333"
                wrapMode: Text.WordWrap
                width: Math.min(root.width - 96, 320)
            }

            Text {
                anchors {
                    right: parent.right
                    bottom: parent.bottom
                    margins: 6
                }
                text: messageTime
                font.pixelSize: 10
                color: isUser ? "#CCFFFFFF" : "#999"
                visible: messageTime !== ""
            }
        }

        Item { width: isUser ? 8 : 48; height: 1 }
    }
}
