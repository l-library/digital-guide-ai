#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>

#include "src/apiservice.h"
#include "src/loginmanager.h"
#include "src/conversationmanager.h"
#include "src/historymanager.h"
#include "src/settingsmanager.h"
#include "src/voiceinterface.h"
#include "src/digitalhumanmanager.h"
#include "src/audioplayer.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QQuickStyle::setStyle("Material");

    ApiService::instance();

    LoginManager loginManager;
    ConversationManager conversationManager;
    HistoryManager historyManager;
    SettingsManager settingsManager;
    VoiceInterface voiceInterface;
    DigitalHumanManager digitalHumanManager;
    AudioPlayer audioPlayer;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("loginManager", &loginManager);
    engine.rootContext()->setContextProperty("conversationManager", &conversationManager);
    engine.rootContext()->setContextProperty("historyManager", &historyManager);
    engine.rootContext()->setContextProperty("settingsManager", &settingsManager);
    engine.rootContext()->setContextProperty("voiceInterface", &voiceInterface);
    engine.rootContext()->setContextProperty("digitalHumanManager", &digitalHumanManager);
    engine.rootContext()->setContextProperty("audioPlayer", &audioPlayer);

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);

    engine.loadFromModule("digital_guide_ai", "Main");

    return QCoreApplication::exec();
}
