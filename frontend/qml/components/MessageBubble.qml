import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property bool isUser: false
    property string messageText: ""
    property string messageTime: ""

    // 气泡最大宽度为窗口宽度的70%
    property real maxBubbleWidth: (parent ? parent.width : 400) * 0.7

    implicitHeight: column.height + 16
    width: parent ? parent.width : 400

    color: "transparent"

    Column {
        id: column
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            topMargin: 8
        }
        spacing: 2

        Row {
            id: bubbleRow
            width: parent.width
            layoutDirection: isUser ? Qt.RightToLeft : Qt.LeftToRight
            spacing: 8

            Item { width: isUser ? 48 : 8; height: 1 }

            Rectangle {
                id: bubble
                width: Math.min(bubbleText.implicitWidth + 24, root.maxBubbleWidth)
                height: bubbleText.height + 24
                radius: 12
                color: isUser ? "#2196F3" : "#FFFFFF"
                border.width: isUser ? 0 : 1
                border.color: isUser ? "transparent" : "#E0E0E0"

                Text {
                    id: bubbleText
                    anchors {
                        left: parent.left
                        top: parent.top
                        right: parent.right
                        margins: 12
                    }
                    text: messageText
                    font.pixelSize: 14
                    color: isUser ? "white" : "#333"
                    wrapMode: Text.WordWrap
                }
            }

            Item { width: isUser ? 8 : 48; height: 1 }
        }

        Text {
            text: messageTime
            font.pixelSize: 10
            color: "black"
            visible: messageTime !== ""
            anchors.left: parent.left
            anchors.right: parent.right
            horizontalAlignment: isUser ? Text.AlignRight : Text.AlignLeft
            leftPadding: isUser ? 0 : 16
            rightPadding: isUser ? 56 : 0
        }
    }
}
