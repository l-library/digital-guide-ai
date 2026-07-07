import QtQuick
import QtQuick.Controls

Item {
    id: root

    Image {
        id: videoImage
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        cache: false
        visible: liveTalkingClient && liveTalkingClient.connected
        source: ""

        function refreshSource() {
            if (liveTalkingClient && liveTalkingClient.connected) {
                source = "image://livetalking/video?frame=" + liveTalkingClient.frameCount
            } else {
                source = ""
            }
        }

        Connections {
            target: liveTalkingClient
            enabled: liveTalkingClient !== null
            function onFrameUpdated() {
                videoImage.refreshSource()
            }
            function onConnectedChanged() {
                videoImage.refreshSource()
            }
        }

        Component.onCompleted: {
            refreshSource()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#1A1A2E"
        visible: !videoImage.visible

        Column {
            anchors.centerIn: parent
            spacing: 12

            Label {
                text: qsTr("数字人连接中...")
                font.pixelSize: 16
                color: "#E0E0E0"
                anchors.horizontalCenter: parent.horizontalCenter
            }

            BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: parent.visible
            }
        }
    }

    Rectangle {
        id: statusBadge
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        width: statusText.implicitWidth + 16
        height: statusText.implicitHeight + 8
        color: liveTalkingClient && liveTalkingClient.speaking ? "#4CAF50" : "#80000000"
        radius: 4
        visible: videoImage.visible

        Label {
            id: statusText
            anchors.centerIn: parent
            text: liveTalkingClient && liveTalkingClient.speaking ? qsTr("正在说话...") : qsTr("待机")
            font.pixelSize: 12
            color: "white"
        }
    }
}