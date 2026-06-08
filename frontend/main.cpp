#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QQuickImageProvider>

#include "src/apiservice.h"
#include "src/loginmanager.h"
#include "src/conversationmanager.h"
#include "src/historymanager.h"
#include "src/settingsmanager.h"
#include "src/voiceinterface.h"
#include "src/digitalhumanmanager.h"
#include "src/audioplayer.h"
#include "src/livetalkingclient.h"

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
    LiveTalkingClient liveTalkingClient;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("loginManager", &loginManager);
    engine.rootContext()->setContextProperty("conversationManager", &conversationManager);
    engine.rootContext()->setContextProperty("historyManager", &historyManager);
    engine.rootContext()->setContextProperty("settingsManager", &settingsManager);
    engine.rootContext()->setContextProperty("voiceInterface", &voiceInterface);
    engine.rootContext()->setContextProperty("digitalHumanManager", &digitalHumanManager);
    engine.rootContext()->setContextProperty("audioPlayer", &audioPlayer);
    engine.rootContext()->setContextProperty("liveTalkingClient", &liveTalkingClient);
    engine.rootContext()->setContextProperty("apiService", &ApiService::instance());

    engine.addImageProvider("livetalking", new LiveTalkingImageProvider(&liveTalkingClient));

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);

    engine.loadFromModule("digital_guide_ai", "Main");

    QString ltHost = ConfigManager::getLiveTalkingHost();
    int ltPort = ConfigManager::getLiveTalkingPort();
    liveTalkingClient.connectToServer(ltHost, ltPort);

    return QCoreApplication::exec();
}
