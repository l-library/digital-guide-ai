import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Page {
    id: root
    signal navigateBack()

    Component.onCompleted: {
        adminManager.loadUsers(1, 20, "")
    }

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

            Item { Layout.fillWidth: true }

            Label {
                text: qsTr("后台管理")
                font.pixelSize: 18
                font.bold: true
                elide: Label.ElideRight
            }

            Item { Layout.fillWidth: true }
        }
    }

    // ════════════════════════════════════════════════════
    // 标签栏
    // ════════════════════════════════════════════════════
    TabBar {
        id: tabBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        TabButton {
            text: qsTr("用户管理")
        }
        TabButton {
            text: qsTr("数据大屏")
        }
        TabButton {
            text: qsTr("游客报告")
        }
    }

    // ════════════════════════════════════════════════════
    // 标签页内容
    // ════════════════════════════════════════════════════
    SwipeView {
        id: tabView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: tabBar.bottom
        anchors.bottom: parent.bottom
        currentIndex: tabBar.currentIndex
        interactive: false

        // ── 标签页 0：用户管理 ───────────────────────────
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                // ── 搜索栏 ──────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    TextField {
                        id: searchField
                        Layout.fillWidth: true
                        font.pixelSize: 14
                        placeholderText: qsTr("搜索用户名或昵称")
                        Material.accent: Material.Blue
                        onAccepted: searchBtn.clicked()
                    }

                    Button {
                        id: searchBtn
                        text: qsTr("搜索")
                        font.pixelSize: 14
                        Material.background: Material.accent
                        Material.foreground: "white"
                        onClicked: adminManager.searchUsers(searchField.text.trim())
                    }

                    Button {
                        id: clearBtn
                        text: qsTr("清除")
                        font.pixelSize: 14
                        flat: true
                        visible: searchField.text.length > 0
                        onClicked: {
                            searchField.text = ""
                            adminManager.loadUsers(1, 20, "")
                        }
                    }
                }

                // ── 加载状态 ────────────────────────────────────
                BusyIndicator {
                    Layout.alignment: Qt.AlignHCenter
                    running: adminManager.isLoading
                    visible: adminManager.isLoading
                }

                // ── 用户列表 ────────────────────────────────────
                ListView {
                    id: userList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    visible: !adminManager.isLoading

                    model: adminManager.users

                    // 空列表占位
                    Label {
                        anchors.centerIn: parent
                        text: qsTr("暂无用户")
                        font.pixelSize: 14
                        color: "#999"
                        visible: userList.count === 0 && !adminManager.isLoading
                    }

                    delegate: Rectangle {
                        width: userList.width
                        height: 72
                        radius: 8
                        color: "white"
                        border.width: 1
                        border.color: "#E0E0E0"

                        // 头像（固定在左侧）
                        Rectangle {
                            id: delegateAvatar
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            width: 44; height: 44; radius: 22
                            color: (modelData.role === "admin")
                                   ? Material.color(Material.Orange, Material.Shade300)
                                   : Material.color(Material.Blue, Material.Shade300)
                            clip: true

                            Image {
                                id: avatarImage
                                anchors.fill: parent
                                source: {
                                    var url = modelData.avatarUrl || ""
                                    if (url !== "" && url.indexOf("/") === 0) {
                                        return "file://" + url
                                    }
                                    return url
                                }
                                fillMode: Image.PreserveAspectCrop
                                visible: {
                                    var url = modelData.avatarUrl || ""
                                    return url !== "" && status === Image.Ready
                                }
                                onStatusChanged: {
                                    if (status === Image.Error) {
                                        visible = false
                                    }
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                text: modelData.displayName
                                      ? modelData.displayName.charAt(0).toUpperCase()
                                      : (modelData.username
                                         ? modelData.username.charAt(0).toUpperCase()
                                         : "?")
                                font.pixelSize: 18
                                font.bold: true
                                color: "white"
                                visible: !avatarImage.visible
                            }
                        }

                        // 删除按钮（固定在右侧）
                        ToolButton {
                            id: deleteBtn
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            text: qsTr("删除")
                            font.pixelSize: 13
                            Material.foreground: Material.Red
                            enabled: modelData.role !== "admin"
                            onClicked: {
                                deleteDialog.userId = modelData.id
                                deleteDialog.username = modelData.username || ""
                                deleteDialog.open()
                            }
                        }

                        // 编辑按钮（紧贴删除按钮左侧）
                        ToolButton {
                            id: editBtn
                            anchors.right: deleteBtn.left
                            anchors.verticalCenter: parent.verticalCenter
                            text: qsTr("编辑")
                            font.pixelSize: 13
                            onClicked: {
                                editDialog.userId = modelData.id
                                editDialog.originalNickname = modelData.displayName || ""
                                editDialog.originalPhone = modelData.phone || ""
                                editDialog.originalEmail = modelData.email || ""
                                editNicknameField.text = modelData.displayName || ""
                                editPhoneField.text = modelData.phone || ""
                                editEmailField.text = modelData.email || ""
                                editDialog.open()
                            }
                        }

                        // 启用/禁用开关（紧贴编辑按钮左侧）
                        Switch {
                            id: activeSwitch
                            anchors.right: editBtn.left
                            anchors.verticalCenter: parent.verticalCenter
                            enabled: modelData.role !== "admin"
                            checked: modelData.isActive !== undefined ? modelData.isActive : true
                            // 使用 onClicked 而非 onCheckedChanged，避免列表重载时 checked 重新绑定触发循环
                            onClicked: {
                                adminManager.toggleUserStatus(modelData.id, checked)
                            }
                        }

                        // 用户信息（填充头像和开关之间的空间）
                        Column {
                            anchors.left: delegateAvatar.right
                            anchors.leftMargin: 12
                            anchors.right: activeSwitch.left
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            Row {
                                spacing: 6

                                Label {
                                    text: modelData.displayName || modelData.username || ""
                                    font.pixelSize: 15
                                    font.bold: true
                                    elide: Label.ElideRight
                                    width: Math.min(implicitWidth, 120)
                                }

                                Label {
                                    text: "@" + (modelData.username || "")
                                    font.pixelSize: 12
                                    color: "#999"
                                }
                            }

                            // 角色标签
                            Rectangle {
                                width: roleBadgeText.implicitWidth + 12
                                height: 20
                                radius: 10
                                color: modelData.role === "admin"
                                       ? Material.color(Material.Orange, Material.Shade200)
                                       : Material.color(Material.Blue, Material.Shade100)

                                Label {
                                    id: roleBadgeText
                                    anchors.centerIn: parent
                                    text: modelData.role === "admin"
                                          ? qsTr("管理员")
                                          : qsTr("游客")
                                    font.pixelSize: 11
                                    font.bold: true
                                    color: modelData.role === "admin"
                                           ? Material.color(Material.Orange, Material.Shade900)
                                           : Material.color(Material.Blue, Material.Shade900)
                                }
                            }
                        }
                    }
                }

                // ── 分页导航 ────────────────────────────────────
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Button {
                        text: qsTr("‹ 上一页")
                        font.pixelSize: 13
                        flat: true
                        enabled: adminManager.currentPage > 1
                        onClicked: adminManager.prevPage()
                    }

                    Label {
                        text: qsTr("第 %1 页 / 共 %2 页 (共 %3 用户)")
                              .arg(adminManager.currentPage)
                              .arg(adminManager.totalPages)
                              .arg(adminManager.totalUsers)
                        font.pixelSize: 13
                        color: "#666"
                        Layout.alignment: Qt.AlignHCenter
                    }

                    Button {
                        text: qsTr("下一页 ›")
                        font.pixelSize: 13
                        flat: true
                        enabled: adminManager.currentPage < adminManager.totalPages
                        onClicked: adminManager.nextPage()
                    }

                    Item { Layout.fillWidth: true }

                    Button {
                        id: createBtn
                        text: qsTr("+ 新建用户")
                        font.pixelSize: 14
                        font.bold: true
                        Material.background: Material.accent
                        Material.foreground: "white"
                        onClicked: {
                            createUsernameField.text = ""
                            createPasswordField.text = ""
                            createConfirmPasswordField.text = ""
                            createDisplayNameField.text = ""
                            createErrorText.visible = false
                            createDialog.open()
                        }
                    }
                }
            }
        }

        // ── 标签页 1：数据大屏（懒加载）────────────────────
        Loader {
            id: dashboardLoader
            active: tabView.currentIndex === 1
            source: "DashboardTab.qml"
        }

        // ── 标签页 2：游客报告（懒加载）────────────────────
        Loader {
            id: reportLoader
            active: tabView.currentIndex === 2
            source: "ReportTab.qml"
        }
    }

    // ════════════════════════════════════════════════════
    // 编辑用户弹窗
    // ════════════════════════════════════════════════════
    Dialog {
        id: editDialog
        title: qsTr("编辑用户")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        anchors.centerIn: parent
        width: 360

        property int userId: -1
        property string originalNickname: ""
        property string originalPhone: ""
        property string originalEmail: ""

        onAccepted: {
            var fields = {}
            var nickname = editNicknameField.text.trim()
            var phone = editPhoneField.text.trim()
            var email = editEmailField.text.trim()

            if (nickname !== originalNickname) fields.displayName = nickname
            if (phone !== originalPhone) fields.phone = phone
            if (email !== originalEmail) fields.email = email

            if (Object.keys(fields).length > 0 && userId > 0) {
                adminManager.updateUser(userId, fields)
            }
        }

        ColumnLayout {
            anchors { left: parent.left; right: parent.right }
            spacing: 12

            Label {
                text: qsTr("昵称")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: editNicknameField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入昵称")
                maximumLength: 50
            }

            Label {
                text: qsTr("手机")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: editPhoneField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入手机号")
                maximumLength: 20
            }

            Label {
                text: qsTr("邮箱")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: editEmailField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入邮箱")
                maximumLength: 100
            }
        }
    }

    // ════════════════════════════════════════════════════
    // 新建用户弹窗
    // ════════════════════════════════════════════════════
    Dialog {
        id: createDialog
        title: qsTr("新建用户")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        anchors.centerIn: parent
        width: 360

        onAccepted: {
            var username = createUsernameField.text.trim()
            var password = createPasswordField.text
            var confirm = createConfirmPasswordField.text
            var displayName = createDisplayNameField.text.trim()

            if (!username || !password || !confirm || !displayName) {
                createErrorText.text = qsTr("所有字段均为必填")
                createErrorText.visible = true
                Qt.callLater(function() { createDialog.open() })
                return
            }
            if (username.length < 3) {
                createErrorText.text = qsTr("用户名至少 3 个字符")
                createErrorText.visible = true
                Qt.callLater(function() { createDialog.open() })
                return
            }
            if (password.length < 6) {
                createErrorText.text = qsTr("密码至少 6 个字符")
                createErrorText.visible = true
                Qt.callLater(function() { createDialog.open() })
                return
            }
            if (password !== confirm) {
                createErrorText.text = qsTr("两次输入的密码不一致")
                createErrorText.visible = true
                Qt.callLater(function() { createDialog.open() })
                return
            }

            createErrorText.visible = false
            adminManager.createUser(username, password, displayName)
        }

        ColumnLayout {
            anchors { left: parent.left; right: parent.right }
            spacing: 12

            Label {
                text: qsTr("用户名")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: createUsernameField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入用户名")
                maximumLength: 50
            }

            Label {
                text: qsTr("密码")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: createPasswordField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入密码")
                echoMode: TextInput.Password
                maximumLength: 64
            }

            Label {
                text: qsTr("确认密码")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: createConfirmPasswordField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请再次输入密码")
                echoMode: TextInput.Password
                maximumLength: 64
            }

            Label {
                text: qsTr("昵称")
                font.pixelSize: 13
                color: "#666"
            }

            TextField {
                id: createDisplayNameField
                Layout.fillWidth: true
                font.pixelSize: 14
                placeholderText: qsTr("请输入昵称")
                maximumLength: 50
            }

            Label {
                id: createErrorText
                visible: false
                color: Material.Red
                font.pixelSize: 12
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }
    }

    // ════════════════════════════════════════════════════
    // 删除确认弹窗
    // ════════════════════════════════════════════════════
    Dialog {
        id: deleteDialog
        title: qsTr("确认删除")
        standardButtons: Dialog.Ok | Dialog.Cancel
        modal: true
        anchors.centerIn: parent
        width: 360

        property int userId: -1
        property string username: ""

        onAccepted: {
            adminManager.deleteUser(userId)
        }

        Label {
            text: qsTr("确定要删除用户 @%1 吗？此操作将删除其所有对话和数据，且不可恢复。")
                  .arg(deleteDialog.username)
            font.pixelSize: 14
            wrapMode: Text.Wrap
            width: parent.width
        }
    }

    // ════════════════════════════════════════════════════
    // 错误提示弹窗
    // ════════════════════════════════════════════════════
    Dialog {
        id: errorDialog
        title: qsTr("错误")
        standardButtons: Dialog.Ok
        modal: true
        anchors.centerIn: parent
        width: 360

        property string messageText: ""

        Label {
            text: errorDialog.messageText
            font.pixelSize: 14
            wrapMode: Text.Wrap
            width: parent.width
        }
    }

    // ════════════════════════════════════════════════════
    // 信号连接：监听 AdminManager 的信号并响应
    // 注意：AdminManager.cpp 内部已在 ApiService 信号回调中做了就地更新或重载，
    // 此处只需处理错误提示，不再重复调用 loadUsers
    // ════════════════════════════════════════════════════
    Connections {
        target: adminManager
        enabled: adminManager !== null

        // 管理员操作出错：弹出错误提示弹窗
        function onAdminError(error) {
            errorDialog.messageText = error
            errorDialog.open()
        }
    }
}
