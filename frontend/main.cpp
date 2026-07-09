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
#include "src/adminmanager.h"
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
    AdminManager adminManager;
    AudioPlayer audioPlayer;
    LiveTalkingClient liveTalkingClient;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("loginManager", &loginManager);
    engine.rootContext()->setContextProperty("conversationManager", &conversationManager);
    engine.rootContext()->setContextProperty("historyManager", &historyManager);
    engine.rootContext()->setContextProperty("settingsManager", &settingsManager);
    engine.rootContext()->setContextProperty("voiceInterface", &voiceInterface);
    engine.rootContext()->setContextProperty("digitalHumanManager", &digitalHumanManager);
    engine.rootContext()->setContextProperty("adminManager", &adminManager);
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

    // 数字人逐句推进：LiveTalking 真正播完一句(eventpoint==2)再发下一句，
    // 取代原先按 wall-clock 估时推进，消除句间不同步导致的视频卡顿。
    QObject::connect(&liveTalkingClient, &LiveTalkingClient::speakingFinished,
                     &conversationManager, &ConversationManager::advancePlayback);

    // eventpoint==1：当前句开始在 LiveTalking 中播放，此时当前句的音频 chunk
    // 已在 FIFO 队列中，可以安全预推送下一句（避免 HTTP 竞态导致乱序）。
    QObject::connect(&liveTalkingClient, &LiveTalkingClient::speakingStarted,
                     &conversationManager, &ConversationManager::onCurrentSentenceStarted);

    return QCoreApplication::exec();
}
