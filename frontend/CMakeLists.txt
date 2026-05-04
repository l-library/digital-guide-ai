cmake_minimum_required(VERSION 3.16)

project(digital_guide_ai VERSION 0.1 LANGUAGES CXX)

set(QT_ANDROID_BUILD_ALL_ABIS TRUE)

set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTORCC ON)

find_package(Qt6 REQUIRED COMPONENTS Quick QuickControls2 Network WebSockets QuickEffects)

qt_standard_project_setup(REQUIRES 6.10)

qt_add_executable(appdigital_guide_ai
    main.cpp
    src/apiservice.cpp
    src/loginmanager.cpp
    src/conversationmanager.cpp
    src/historymanager.cpp
    src/settingsmanager.cpp
    src/voiceinterface.cpp
    src/digitalhumanmanager.cpp
    res.qrc
)

qt_add_qml_module(appdigital_guide_ai
    URI digital_guide_ai
    VERSION 1.0
    QML_FILES
        qml/Main.qml
        qml/LoginPage.qml
        qml/ChatPage.qml
        qml/HistoryPage.qml
        qml/SettingsPage.qml
        qml/components/MessageBubble.qml

        SOURCES src/apiservice.cpp src/apiservice.h src/conversationmanager.cpp src/conversationmanager.h src/digitalhumanmanager.cpp src/digitalhumanmanager.h src/historymanager.cpp src/historymanager.h src/loginmanager.cpp src/loginmanager.h src/settingsmanager.cpp src/settingsmanager.h src/voiceinterface.cpp src/voiceinterface.h
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
    PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Network Qt6::WebSockets Qt6::QuickEffects
)

install(TARGETS appdigital_guide_ai
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)