#ifndef LIVETALKINGCLIENT_H
#define LIVETALKINGCLIENT_H

#include <QObject>
#include <QWebSocket>
#include <QImage>
#include <QAudioSink>
#include <QAudioFormat>
#include <QIODevice>
#include <QBuffer>
#include <QQuickImageProvider>
#include <QMutex>
#include <QTimer>
#include <QList>

class LiveTalkingImageProvider : public QQuickImageProvider
{
public:
    explicit LiveTalkingImageProvider(class LiveTalkingClient *client);
    QImage requestImage(const QString &id, QSize *size, const QSize &requestedSize) override;

private:
    LiveTalkingClient *m_client;
};

class LiveTalkingClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool connected READ connected NOTIFY connectedChanged)
    Q_PROPERTY(bool speaking READ speaking NOTIFY speakingChanged)
    Q_PROPERTY(int frameCount READ frameCount NOTIFY frameUpdated)
    Q_PROPERTY(QString sessionId READ sessionId NOTIFY sessionChanged)
    Q_PROPERTY(int frameWidth READ frameWidth NOTIFY frameSizeChanged)
    Q_PROPERTY(int frameHeight READ frameHeight NOTIFY frameSizeChanged)
    Q_PROPERTY(int conversationId READ conversationId WRITE setConversationId NOTIFY conversationIdChanged)

public:
    explicit LiveTalkingClient(QObject *parent = nullptr);
    ~LiveTalkingClient();

    bool connected() const;
    bool speaking() const;
    int frameCount() const;
    int frameWidth() const;
    int frameHeight() const;
    QImage currentFrame() const;
    QString sessionId() const;
    int conversationId() const;
    void setConversationId(int id);

    Q_INVOKABLE void connectToServer(const QString &host, int port = 8010);
    Q_INVOKABLE void disconnectFromServer();
    Q_INVOKABLE void createSession();
    Q_INVOKABLE void sendText(const QString &text);
    Q_INVOKABLE void interrupt();

signals:
    void connectedChanged();
    void speakingChanged();
    void frameUpdated();
    void frameSizeChanged();
    void sessionChanged();
    void sessionCreated(const QString &sessionId);
    void conversationIdChanged();
    void errorOccurred(const QString &error);

private slots:
    void onConnected();
    void onDisconnected();
    void onBinaryMessageReceived(const QByteArray &data);
    void onTextMessageReceived(const QString &message);
    void onError(QAbstractSocket::SocketError error);
    void onDisplayTimerTick();

private:
    void processVideoFrame(const QByteArray &payload);
    void processAudioFrame(const QByteArray &payload);
    void setupAudio();

    QWebSocket *m_webSocket = nullptr;
    QImage m_currentFrame;
    QString m_sessionId;
    bool m_connected = false;
    bool m_speaking = false;
    int m_frameCount = 0;
    int m_frameWidth = 0;
    int m_frameHeight = 0;
    int m_conversationId = -1;

    // Audio playback
    QAudioSink *m_audioSink = nullptr;
    QIODevice *m_audioDevice = nullptr;
    QAudioFormat m_audioFormat;

    // Thread safety for image provider
    mutable QMutex m_frameMutex;

    // Video frame buffering for paced display (25fps = 40ms/frame)
    QList<QByteArray> m_videoFrameBuffer;
    QTimer *m_displayTimer = nullptr;
    qint64 m_lastDisplayTime = 0;

    friend class LiveTalkingImageProvider;
};

#endif // LIVETALKINGCLIENT_H