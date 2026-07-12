#include "livetalkingclient.h"
#include "apiservice.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QDebug>
#include <QLoggingCategory>
#include <QMutexLocker>

Q_LOGGING_CATEGORY(lcLiveTalking, "livetalking.connection")
#include <QRegularExpression>
#include <QDateTime>

LiveTalkingImageProvider::LiveTalkingImageProvider(LiveTalkingClient *client)
    : QQuickImageProvider(QQuickImageProvider::Image)
    , m_client(client)
{
}

QImage LiveTalkingImageProvider::requestImage(const QString &id, QSize *size, const QSize &requestedSize)
{
    QImage frame = m_client->currentFrame();
    if (frame.isNull()) {
        QImage placeholder(2, 2, QImage::Format_RGB32);
        placeholder.fill(Qt::black);
        if (size)
            *size = placeholder.size();
        return placeholder;
    }
    if (size) {
        *size = frame.size();
    }
    if (requestedSize.isValid() && !requestedSize.isEmpty()) {
        return frame.scaled(requestedSize, Qt::KeepAspectRatio, Qt::FastTransformation);
    }
    return frame;
}

LiveTalkingClient::LiveTalkingClient(QObject *parent)
    : QObject(parent)
{
    m_audioFormat.setSampleRate(16000);
    m_audioFormat.setChannelCount(1);
    m_audioFormat.setSampleFormat(QAudioFormat::Int16);

    m_displayTimer = new QTimer(this);
    m_displayTimer->setInterval(10);
    m_lastDisplayTime = 0;
    connect(m_displayTimer, &QTimer::timeout, this, &LiveTalkingClient::onDisplayTimerTick);
}

LiveTalkingClient::~LiveTalkingClient()
{
    disconnectFromServer();
    if (m_audioSink) {
        m_audioSink->stop();
        delete m_audioSink;
    }
}

bool LiveTalkingClient::connected() const
{
    return m_connected;
}

bool LiveTalkingClient::speaking() const
{
    return m_speaking;
}

int LiveTalkingClient::frameCount() const
{
    return m_frameCount;
}

int LiveTalkingClient::frameWidth() const
{
    return m_frameWidth;
}

int LiveTalkingClient::frameHeight() const
{
    return m_frameHeight;
}

QImage LiveTalkingClient::currentFrame() const
{
    QMutexLocker locker(&m_frameMutex);
    return m_currentFrame;
}

QString LiveTalkingClient::sessionId() const
{
    return m_sessionId;
}

int LiveTalkingClient::conversationId() const
{
    return m_conversationId;
}

void LiveTalkingClient::setConversationId(int id)
{
    if (m_conversationId != id) {
        m_conversationId = id;
        emit conversationIdChanged();
        if (id > 0 && !m_sessionId.isEmpty() && m_connected) {
            ApiService::instance().registerLiveTalkingSession(id, m_sessionId);
        }
    }
}

void LiveTalkingClient::connectToServer(const QString &host, int port)
{
    if (m_webSocket && m_webSocket->state() == QAbstractSocket::ConnectedState) {
        return;
    }

    disconnectFromServer();

    m_webSocket = new QWebSocket();
    connect(m_webSocket, &QWebSocket::connected, this, &LiveTalkingClient::onConnected);
    connect(m_webSocket, &QWebSocket::disconnected, this, &LiveTalkingClient::onDisconnected);
    connect(m_webSocket, &QWebSocket::binaryMessageReceived, this, &LiveTalkingClient::onBinaryMessageReceived);
    connect(m_webSocket, &QWebSocket::textMessageReceived, this, &LiveTalkingClient::onTextMessageReceived);
    connect(m_webSocket, &QWebSocket::errorOccurred, this, &LiveTalkingClient::onError);

    QString cleanHost = host;
    cleanHost.remove(QRegularExpression("^https?://"));
    QUrl url(QString("ws://%1:%2/ws_stream").arg(cleanHost).arg(port));
    qCDebug(lcLiveTalking) << "LiveTalking: connecting to" << url.toString();
    m_webSocket->open(url);
}

void LiveTalkingClient::disconnectFromServer()
{
    if (m_webSocket) {
        m_webSocket->close();
        m_webSocket->deleteLater();
        m_webSocket = nullptr;
    }
    if (m_connected) {
        m_connected = false;
        emit connectedChanged();
    }
    m_sessionId.clear();
    emit sessionChanged();
}

void LiveTalkingClient::createSession()
{
    if (!m_webSocket || m_webSocket->state() != QAbstractSocket::ConnectedState) {
        return;
    }
    QJsonObject msg;
    msg["type"] = "create";
    m_webSocket->sendTextMessage(QJsonDocument(msg).toJson(QJsonDocument::Compact));
}

void LiveTalkingClient::sendText(const QString &text)
{
    if (!m_webSocket || m_webSocket->state() != QAbstractSocket::ConnectedState) {
        return;
    }
    QJsonObject msg;
    msg["type"] = "text";
    msg["text"] = text;
    msg["tts"] = QJsonObject();
    m_webSocket->sendTextMessage(QJsonDocument(msg).toJson(QJsonDocument::Compact));
}

void LiveTalkingClient::interrupt()
{
    if (!m_webSocket || m_webSocket->state() != QAbstractSocket::ConnectedState) {
        return;
    }
    QJsonObject msg;
    msg["type"] = "interrupt";
    m_webSocket->sendTextMessage(QJsonDocument(msg).toJson(QJsonDocument::Compact));
}

void LiveTalkingClient::onConnected()
{
    qCDebug(lcLiveTalking) << "LiveTalking: WebSocket connected, sending create session...";
    m_connected = true;
    emit connectedChanged();
    createSession();
}

void LiveTalkingClient::onDisconnected()
{
    qCDebug(lcLiveTalking) << "LiveTalking: WebSocket disconnected";
    m_connected = false;
    m_speaking = false;
    m_videoFrameBuffer.clear();
    if (m_displayTimer) {
        m_displayTimer->stop();
    }
    {
        QMutexLocker locker(&m_frameMutex);
        m_currentFrame = QImage();
        m_frameCount = 0;
    }
    m_frameWidth = 0;
    m_frameHeight = 0;
    emit connectedChanged();
    emit speakingChanged();
    emit frameUpdated();
    emit frameSizeChanged();
    emit sessionChanged();
}

void LiveTalkingClient::onBinaryMessageReceived(const QByteArray &data)
{
    if (data.size() < 2) {
        return;
    }

    unsigned char frameType = static_cast<unsigned char>(data[0]);
    if (frameType == 0x01) {
        processVideoFrame(data.mid(1));
    } else if (frameType == 0x02) {
        processAudioFrame(data.mid(1));
    }
}

void LiveTalkingClient::onTextMessageReceived(const QString &message)
{
    QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8());
    if (!doc.isObject()) {
        return;
    }
    QJsonObject obj = doc.object();
    QString type = obj["type"].toString();

    if (type == "created") {
        m_sessionId = obj["sessionid"].toString();
        qCDebug(lcLiveTalking) << "LiveTalking: session created:" << m_sessionId;
        emit sessionChanged();
        emit sessionCreated(m_sessionId);
        if (m_conversationId > 0 && !m_sessionId.isEmpty()) {
            ApiService::instance().registerLiveTalkingSession(m_conversationId, m_sessionId);
        }
    } else if (type == "bound") {
        m_sessionId = obj["sessionid"].toString();
        emit sessionChanged();
        emit sessionCreated(m_sessionId);
        if (m_conversationId > 0 && !m_sessionId.isEmpty()) {
            ApiService::instance().registerLiveTalkingSession(m_conversationId, m_sessionId);
        }
    } else if (type == "text_ack") {
    } else if (type == "interrupt_ack") {
    } else if (type == "error") {
        QString errMsg = obj["message"].toString();
        qWarning() << "LiveTalking: error:" << errMsg;
        emit errorOccurred(errMsg);
    }
}

void LiveTalkingClient::onError(QAbstractSocket::SocketError error)
{
    Q_UNUSED(error)
    if (m_webSocket) {
        qWarning() << "LiveTalking: socket error:" << m_webSocket->errorString();
        emit errorOccurred(m_webSocket->errorString());
    }
}

void LiveTalkingClient::processVideoFrame(const QByteArray &payload)
{
    if (payload.size() < 4) {
        return;
    }

    QByteArray jpegData = payload.mid(4);

    m_videoFrameBuffer.append(jpegData);
    // 缓冲上限约 1 秒（30 帧）。逐帧丢弃最旧帧，避免一次性批量 erase
    // 导致的"快进跳帧"——视频动画看起来卡住的常见原因。
    if (m_videoFrameBuffer.size() > 30) {
        m_videoFrameBuffer.removeFirst();
    }
    if (!m_displayTimer->isActive()) {
        m_displayTimer->start();
    }
}

void LiveTalkingClient::onDisplayTimerTick()
{
    if (m_videoFrameBuffer.isEmpty()) {
        return;
    }

    qint64 now = QDateTime::currentMSecsSinceEpoch();
    qint64 elapsed = m_lastDisplayTime > 0 ? now - m_lastDisplayTime : 33;

    // 30fps 节流（33ms/帧）。tick 间隔（10ms）小于此阈值，
    // 早期返回由 elapsed 过滤，保证不漏 tick 且不超采。
    if (elapsed < 33) {
        return;
    }

    // 每次 tick 最多显示 1 帧。即使缓冲积压也只取 1 帧，
    // 让积压在后续 tick 平滑消化，避免一次性"快进"跳帧。
    QByteArray jpegData = m_videoFrameBuffer.takeFirst();
    m_lastDisplayTime = now;

    QImage frame;
    if (frame.loadFromData(jpegData, "JPEG")) {
        QMutexLocker locker(&m_frameMutex);
        m_frameCount++;
        bool sizeChanged = (m_frameWidth != frame.width() || m_frameHeight != frame.height());
        m_frameWidth = frame.width();
        m_frameHeight = frame.height();
        m_currentFrame = frame;
        if (sizeChanged) {
            emit frameSizeChanged();
        }
    }
    emit frameUpdated();
}

void LiveTalkingClient::processAudioFrame(const QByteArray &payload)
{
    if (payload.size() < 1) {
        return;
    }

    unsigned char eventpointCode = static_cast<unsigned char>(payload[0]);
    QByteArray pcmData = payload.mid(1);

    if (eventpointCode == 1) {
        if (!m_speaking) {
            m_speaking = true;
            // 清空旧句的视频缓冲，但保留 m_currentFrame 不动——
            // 过渡期间 QML 继续显示上一句最后一帧，新句视频帧到达后
            // 在下一个显示周期（≤40ms）内接上，音画不同步极小。
            m_videoFrameBuffer.clear();
            emit speakingChanged();
            emit speakingStarted();
        }
    } else if (eventpointCode == 2) {
        if (m_speaking) {
            m_speaking = false;
            emit speakingChanged();
            // 当前句播完，通知 ConversationManager 推进下一句
            emit speakingFinished();
        }
    }

    if (pcmData.isEmpty()) {
        return;
    }

    if (!m_audioSink) {
        setupAudio();
    }

    if (m_audioDevice) {
        qint64 written = m_audioDevice->write(pcmData);
        if (written != pcmData.size()) {
            static int partialCount = 0;
            partialCount++;
            if (partialCount <= 5 || partialCount % 50 == 0) {
                qWarning() << "[音频] 部分写入! 期望:" << pcmData.size()
                           << "实际:" << written << "累计:" << partialCount;
            }
        }
    }
}

void LiveTalkingClient::setupAudio()
{
    m_audioSink = new QAudioSink(m_audioFormat, this);
    m_audioSink->setVolume(1.0);
    m_audioSink->setBufferSize(16000 * 2 * 1);  // 500ms buffer @ 16kHz int16 mono = 16000 samples
    m_audioDevice = m_audioSink->start();
    if (!m_audioDevice) {
        qWarning() << "LiveTalking: failed to start audio sink";
    }
}