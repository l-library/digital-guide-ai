cmake_minimum_required(VERSION 3.16)

project(digital_guide_ai VERSION 0.1 LANGUAGES CXX)

set(QT_ANDROID_BUILD_ALL_ABIS TRUE)

set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTORCC ON)

if(WIN32)
    set(APP_ICON_RESOURCE_WINDOWS ${CMAKE_CURRENT_SOURCE_DIR}/app.rc)
endif()

find_package(Qt6 REQUIRED COMPONENTS Quick QuickControls2 Network WebSockets QuickEffects Multimedia)

qt_standard_project_setup(REQUIRES 6.10)

qt_add_executable(appdigital_guide_ai
    main.cpp
    ${APP_ICON_RESOURCE_WINDOWS}
    src/apiservice.cpp
    src/loginmanager.cpp
    src/conversationmanager.cpp
    src/historymanager.cpp
    src/settingsmanager.cpp
    src/voiceinterface.cpp
    src/adminmanager.cpp
    src/audioplayer.cpp
    src/livetalkingclient.cpp
    src/dashboardmanager.cpp
    src/reportmanager.cpp
    src/recommendmanager.cpp
    res.qrc
)

qt_add_qml_module(appdigital_guide_ai
    URI digital_guide_ai
    VERSION 1.0
    QML_FILES
        qml/Main.qml
        qml/AdminPage.qml
        qml/ChatPage.qml
        qml/HistoryPage.qml
        qml/LoginPage.qml
        qml/SettingsPage.qml
        qml/components/MessageBubble.qml
        qml/components/DigitalHumanView.qml
        qml/DashboardTab.qml
        qml/ReportTab.qml
        qml/RecommendTab.qml

        SOURCES src/adminmanager.cpp src/adminmanager.h src/apiservice.cpp src/apiservice.h src/conversationmanager.cpp src/conversationmanager.h src/historymanager.cpp src/historymanager.h src/loginmanager.cpp src/loginmanager.h src/settingsmanager.cpp src/settingsmanager.h src/voiceinterface.cpp src/voiceinterface.h src/audioplayer.cpp src/audioplayer.h src/livetalkingclient.cpp src/livetalkingclient.h src/dashboardmanager.cpp src/dashboardmanager.h src/reportmanager.cpp src/reportmanager.h src/recommendmanager.cpp src/recommendmanager.h
        QML_FILES
)

set_target_properties(appdigital_guide_ai PROPERTIES
    MACOSX_BUNDLE_GUI_IDENTIFIER com.digitalguide.ai
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

target_link_libraries(appdigital_guide_ai
    PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Network Qt6::WebSockets Qt6::QuickEffects Qt6::Multimedia
)

install(TARGETS appdigital_guide_ai
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)