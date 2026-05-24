#include "livetalkingclient.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QUrl>
#include <QDebug>
#include <QMutexLocker>
#include <QRegularExpression>

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
    static int provCount = 0;
    provCount++;
    if (provCount % 50 == 1) {
        qDebug() << "LiveTalkingImageProvider: serving frame" << m_client->frameCount()
                 << "size:" << frame.width() << "x" << frame.height()
                 << "id:" << id;
    }
    if (size) {
        *size = frame.size();
    }
    if (requestedSize.isValid() && !requestedSize.isEmpty()) {
        return frame.scaled(requestedSize, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    return frame;
}

LiveTalkingClient::LiveTalkingClient(QObject *parent)
    : QObject(parent)
{
    m_audioFormat.setSampleRate(16000);
    m_audioFormat.setChannelCount(1);
    m_audioFormat.setSampleFormat(QAudioFormat::Int16);
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

QImage LiveTalkingClient::currentFrame() const
{
    QMutexLocker locker(&m_frameMutex);
    return m_currentFrame;
}

QString LiveTalkingClient::sessionId() const
{
    return m_sessionId;
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
    qDebug() << "LiveTalking: connecting to" << url.toString();
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
    qDebug() << "LiveTalking: WebSocket connected, sending create session...";
    m_connected = true;
    emit connectedChanged();
    createSession();
}

void LiveTalkingClient::onDisconnected()
{
    qDebug() << "LiveTalking: WebSocket disconnected";
    m_connected = false;
    m_speaking = false;
    {
        QMutexLocker locker(&m_frameMutex);
        m_currentFrame = QImage();
        m_frameCount = 0;
    }
    emit connectedChanged();
    emit speakingChanged();
    emit frameUpdated();
    emit sessionChanged();
}

void LiveTalkingClient::onBinaryMessageReceived(const QByteArray &data)
{
    if (data.size() < 2) {
        return;
    }
    static int binaryCount = 0;
    binaryCount++;
    if (binaryCount <= 5 || binaryCount % 100 == 0) {
        qDebug() << "LiveTalking: binary message received, size:" << data.size()
                 << "type:" << Qt::hex << (unsigned char)data[0]
                 << "count:" << binaryCount;
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
    qDebug() << "LiveTalking: text message received:" << message.left(200);
    QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8());
    if (!doc.isObject()) {
        return;
    }
    QJsonObject obj = doc.object();
    QString type = obj["type"].toString();

    if (type == "created") {
        m_sessionId = obj["sessionid"].toString();
        qDebug() << "LiveTalking: session created:" << m_sessionId;
        emit sessionChanged();
    } else if (type == "bound") {
        m_sessionId = obj["sessionid"].toString();
        qDebug() << "LiveTalking: session bound:" << m_sessionId;
        emit sessionChanged();
    } else if (type == "text_ack") {
        qDebug() << "LiveTalking: text acknowledged";
    } else if (type == "interrupt_ack") {
        qDebug() << "LiveTalking: interrupt acknowledged";
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
    QImage frame;
    if (frame.loadFromData(jpegData, "JPEG")) {
        {
            QMutexLocker locker(&m_frameMutex);
            m_currentFrame = frame;
            m_frameCount++;
        }
        if (m_frameCount % 50 == 1) {
            qDebug() << "LiveTalking: video frame #" << m_frameCount
                     << "size:" << frame.width() << "x" << frame.height();
        }
        emit frameUpdated();
    } else {
        static int failCount = 0;
        failCount++;
        if (failCount <= 3) {
            qWarning() << "LiveTalking: failed to decode JPEG frame, payload size:" << payload.size()
                       << "jpeg size:" << jpegData.size();
        }
    }
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
            emit speakingChanged();
        }
    } else if (eventpointCode == 2) {
        if (m_speaking) {
            m_speaking = false;
            emit speakingChanged();
        }
    }

    if (pcmData.isEmpty()) {
        return;
    }

    if (!m_audioSink) {
        setupAudio();
    }

    if (m_audioDevice) {
        m_audioDevice->write(pcmData);
    }
}

void LiveTalkingClient::setupAudio()
{
    m_audioSink = new QAudioSink(m_audioFormat, this);
    m_audioSink->setVolume(1.0);
    m_audioDevice = m_audioSink->start();
    if (!m_audioDevice) {
        qWarning() << "LiveTalking: failed to start audio sink";
    }
}