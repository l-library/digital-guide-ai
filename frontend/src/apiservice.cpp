#include "apiservice.h"

#include <QDateTime>
#include <QFile>
#include <QHttpMultiPart>
#include <QTimer>
#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrlQuery>

static const QString BASE_URL = ConfigManager::getBackendIP() + ":"
                                + QString::number(ConfigManager::getBackendPort());

ApiService &ApiService::instance()
{
    static ApiService inst;
    return inst;
}

ApiService::ApiService(QObject *parent)
    : QObject(parent)
    , m_networkManager(new QNetworkAccessManager(this))
    , m_webSocket(nullptr)
{
}

QVariantList ApiService::mapMessagesToFrontendFormat(const QVariantList &items) const
{
    QVariantList result;
    for (const QVariant &item : items) {
        QVariantMap src = item.toMap();
        QVariantMap dst;
        dst["id"] = src.value("id");
        dst["role"] = src.value("role");
        dst["content"] = src.value("content");
        dst["timestamp"] = src.value("created_at");
        result.append(dst);
    }
    return result;
}

// ==================== Conversations (real HTTP) ====================

void ApiService::createConversation(int userId, const QString &title, int knowledgeDocId)
{
    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/conversations"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["user_id"] = userId;
    body["title"] = title;
    body["knowledge_doc_id"] = knowledgeDocId;

    QNetworkReply *reply = m_networkManager->post(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "createConversation error:" << reply->errorString();
            emit apiError(QStringLiteral("创建对话失败"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int convId = resp["data"].toObject()["conversation_id"].toInt();
        emit conversationCreated(convId);
    });
}

void ApiService::loadConversations(int userId)
{
    QUrl url(BASE_URL + "/api/v1/conversations");
    QUrlQuery query;
    query.addQueryItem("user_id", QString::number(userId));
    url.setQuery(query);

    QNetworkReply *reply = m_networkManager->get(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadConversations error:" << reply->errorString();
            emit apiError(QStringLiteral("加载对话列表失败"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        QJsonArray items = resp["data"].toObject()["items"].toArray();

        QVariantList convs;
        for (const QJsonValue &val : items) {
            QJsonObject obj = val.toObject();
            QVariantMap cm;
            cm["id"] = obj["conversation_id"].toInt();
            cm["title"] = obj["title"].toString();
            cm["message_count"] = obj["message_count"].toInt();
            cm["last_message"] = obj["last_message"].toString();
            cm["updatedAt"] = obj["last_time"].toString();
            cm["created_at"] = obj["created_at"].toString();
            convs.append(cm);
        }
        emit conversationsLoaded(convs);
    });
}

void ApiService::loadConversationsGroupedByDate(int userId)
{
    QUrl url(BASE_URL + "/api/v1/conversations/grouped");
    QUrlQuery query;
    query.addQueryItem("user_id", QString::number(userId));
    url.setQuery(query);

    QNetworkReply *reply = m_networkManager->get(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadConversationsGroupedByDate error:" << reply->errorString();
            emit apiError(QStringLiteral("加载分组对话失败"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        QJsonArray groups = resp["data"].toObject()["groups"].toArray();

        QVariantList grouped;
        for (const QJsonValue &gv : groups) {
            QJsonObject gObj = gv.toObject();
            QVariantMap group;
            group["date"] = gObj["date"].toString();

            QJsonArray convs = gObj["conversations"].toArray();
            QVariantList convList;
            for (const QJsonValue &cv : convs) {
                QJsonObject cObj = cv.toObject();
                QVariantMap cm;
                cm["id"] = cObj["conversation_id"].toInt();
                cm["title"] = cObj["title"].toString();
                cm["message_count"] = cObj["message_count"].toInt();
                cm["updatedAt"] = cObj["updated_at"].toString();
                cm["created_at"] = cObj["created_at"].toString();
                convList.append(cm);
            }
            group["conversations"] = convList;
            grouped.append(group);
        }
        emit conversationsGroupedLoaded(grouped);
    });
}

void ApiService::deleteConversation(int conversationId)
{
    QUrl url(BASE_URL + "/api/v1/conversations/" + QString::number(conversationId));
    QNetworkReply *reply = m_networkManager->deleteResource(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        bool success = (reply->error() == QNetworkReply::NoError);
        if (!success) {
            qDebug() << "deleteConversation error:" << reply->errorString();
        }
        emit conversationDeleted(success);
    });
}

void ApiService::renameConversation(int conversationId, const QString &newTitle)
{
    QUrl url(BASE_URL + "/api/v1/conversations/" + QString::number(conversationId));
    QNetworkRequest req(url);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["title"] = newTitle;

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, conversationId, newTitle]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "renameConversation error:" << reply->errorString();
            emit apiError(QStringLiteral("重命名对话失败"));
            return;
        }
        emit conversationRenamed(conversationId, newTitle);
    });
}

void ApiService::loadMessages(int conversationId)
{
    QUrl url(BASE_URL + "/api/v1/conversations/" + QString::number(conversationId) + "/messages/all");

    QNetworkReply *reply = m_networkManager->get(QNetworkRequest(url));
    connect(reply, &QNetworkReply::finished, this, [this, reply, conversationId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadMessages error:" << reply->errorString();
            emit messagesLoaded(QVariantList(), conversationId);
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        QJsonArray items = resp["data"].toObject()["items"].toArray();

        QVariantList messages;
        for (const QJsonValue &val : items) {
            QJsonObject obj = val.toObject();
            QVariantMap mm;
            mm["id"] = obj["id"].toInt();
            mm["role"] = obj["role"].toString();
            mm["content"] = obj["content"].toString();
            mm["timestamp"] = obj["created_at"].toString();
            messages.append(mm);
        }
        emit messagesLoaded(messages, conversationId);
    });
}

// ==================== Messages (real HTTP + WebSocket fallback) ====================

void ApiService::sendAiMessage(int conversationId,
                                const QString &userMessage,
                                int response_type)
{
    if (m_webSocket && m_webSocket->state() == QAbstractSocket::ConnectedState) {
        sendChatViaWebSocket(conversationId, userMessage, response_type);
        return;
    }

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/chat/stream"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["content"] = userMessage;
    body["response_type"] = response_type;
    body["digital_human_id"] = 1;

    m_streamReply = m_networkManager->post(req, QJsonDocument(body).toJson());

    connect(m_streamReply, &QNetworkReply::readyRead, this, [this, conversationId]() {
        m_sseBuffer += m_streamReply->readAll();
        while (true) {
            int idx = m_sseBuffer.indexOf("\n\n");
            if (idx < 0)
                break;
            QByteArray event = m_sseBuffer.left(idx);
            m_sseBuffer = m_sseBuffer.mid(idx + 2);
            for (const QByteArray &line : event.split('\n')) {
                QByteArray trimmed = line.trimmed();
                if (!trimmed.startsWith("data: "))
                    continue;
                QJsonObject obj = QJsonDocument::fromJson(trimmed.mid(6)).object();
                QString type = obj["type"].toString();
                if (type == "token") {
                    emit wsTokenReceived(conversationId, obj["content"].toString());
                } else if (type == "sentence") {
                    emit wsSentenceReceived(conversationId, obj["content"].toString());
                } else if (type == "done") {
                    emit wsDoneReceived(conversationId, obj["message_id"].toInt(), obj["full_content"].toString(), obj["audio_url"].toString());
                } else if (type == "title_updated") {
                    emit titleAutoUpdated(obj["conversation_id"].toInt(), obj["title"].toString());
                } else if (type == "sentence_audio") {
                    int idx = obj["index"].toInt();
                    QString text = obj["text"].toString();
                    QString filename = obj["audio_filename"].toString();
                    double duration = obj["duration"].toDouble();
                    emit sentenceAudioReceived(conversationId, idx, text, filename, duration);
                } else if (type == "error") {
                    emit wsError(obj["message"].toString());
                }
            }
        }
    });

    connect(m_streamReply, &QNetworkReply::finished, this, [this]() {
        m_sseBuffer.clear();
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    });

    connect(m_streamReply, &QNetworkReply::errorOccurred, this, [this, conversationId](QNetworkReply::NetworkError) {
        m_sseBuffer.clear();
        emit wsError(QStringLiteral("网络错误: 服务暂时不可用"));
        m_streamReply->deleteLater();
        m_streamReply = nullptr;
    });
}

// ==================== WebSocket streaming ====================

void ApiService::connectWebSocket()
{
    if (m_webSocket) {
        m_webSocket->deleteLater();
    }
    m_webSocket = new QWebSocket(QString(), QWebSocketProtocol::VersionLatest, this);

    QObject::connect(m_webSocket, &QWebSocket::connected, this, [this]() {
        emit wsConnected();
    });
    QObject::connect(m_webSocket, &QWebSocket::disconnected, this, [this]() {
        emit wsDisconnected();
    });
    QObject::connect(m_webSocket, &QWebSocket::textMessageReceived, this, [this](const QString &message) {
        QJsonObject msg = QJsonDocument::fromJson(message.toUtf8()).object();
        QString type = msg["type"].toString();

        if (type == "token") {
            int convId = msg["conversation_id"].toInt();
            QString token = msg["content"].toString();
            emit wsTokenReceived(convId, token);
        } else if (type == "sentence") {
            int convId = msg["conversation_id"].toInt();
            QString sentence = msg["content"].toString();
            emit wsSentenceReceived(convId, sentence);
        } else if (type == "done") {
            int convId = msg["conversation_id"].toInt();
            int msgId = msg["message_id"].toInt();
            QString fullContent = msg["full_content"].toString();
            QString audioUrl = msg["audio_url"].toString();
            emit wsDoneReceived(convId, msgId, fullContent, audioUrl);
        } else if (type == "error") {
            emit wsError(msg["message"].toString());
        } else if (type == "pong") {
            // 心跳回复，忽略
        } else if (type == "title_updated") {
            int convId = msg["conversation_id"].toInt();
            QString title = msg["title"].toString();
            emit titleAutoUpdated(convId, title);
        } else if (type == "sentence_audio") {
            int convId = msg["conversation_id"].toInt();
            int idx = msg["index"].toInt();
            QString text = msg["text"].toString();
            QString filename = msg["audio_filename"].toString();
            double duration = msg["duration"].toDouble();
            emit sentenceAudioReceived(convId, idx, text, filename, duration);
        }
    });
    QObject::connect(m_webSocket, &QWebSocket::errorOccurred, this, [this](QAbstractSocket::SocketError) {
        emit wsError(m_webSocket->errorString());
    });

    QUrl wsUrl(BASE_URL);
    wsUrl.setScheme("ws");
    wsUrl.setPath("/ws/chat");
    m_webSocket->open(wsUrl);
}

void ApiService::disconnectWebSocket()
{
    if (m_webSocket) {
        m_webSocket->close();
        m_webSocket->deleteLater();
        m_webSocket = nullptr;
    }
}

bool ApiService::isWebSocketConnected() const
{
    return m_webSocket && m_webSocket->state() == QAbstractSocket::ConnectedState;
}

void ApiService::sendChatViaWebSocket(int conversationId, const QString &content, int responseType)
{
    if (!m_webSocket || m_webSocket->state() != QAbstractSocket::ConnectedState) {
        emit wsError(QStringLiteral("WebSocket 未连接"));
        return;
    }
    QJsonObject msg;
    msg["type"] = "chat_message";
    msg["conversation_id"] = conversationId;
    msg["content"] = content;
    msg["digital_human_id"] = 1;
    msg["response_type"] = responseType;
    m_webSocket->sendTextMessage(QString(QJsonDocument(msg).toJson(QJsonDocument::Compact)));
}

// ==================== Voice streaming SSE ====================

void ApiService::sendVoiceMessage(int conversationId, const QString &audioFilePath, int responseType)
{
    QFile *file = new QFile(audioFilePath);
    if (!file->open(QIODevice::ReadOnly)) {
        delete file;
        emit voiceError(QStringLiteral("无法打开录音文件"));
        return;
    }

    QHttpMultiPart *multiPart = new QHttpMultiPart(QHttpMultiPart::FormDataType);

    QHttpPart audioPart;
    audioPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                        QVariant(QStringLiteral("form-data; name=\"audio\"; filename=\"recording.wav\"")));
    audioPart.setHeader(QNetworkRequest::ContentTypeHeader, QVariant(QStringLiteral("audio/wav")));
    audioPart.setBodyDevice(file);
    file->setParent(multiPart);

    QHttpPart convIdPart;
    convIdPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                         QVariant(QStringLiteral("form-data; name=\"conversation_id\"")));
    convIdPart.setBody(QString::number(conversationId).toUtf8());

    QHttpPart rtPart;
    rtPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                      QVariant(QStringLiteral("form-data; name=\"response_type\"")));
    rtPart.setBody(QString::number(responseType).toUtf8());

    multiPart->append(audioPart);
    multiPart->append(convIdPart);
    multiPart->append(rtPart);

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/chat/voice_stream"));
    m_voiceStreamReply = m_networkManager->post(req, multiPart);
    multiPart->setParent(m_voiceStreamReply);

    connect(m_voiceStreamReply, &QNetworkReply::readyRead, this, [this, conversationId]() {
        m_voiceSseBuffer += m_voiceStreamReply->readAll();
        while (true) {
            int idx = m_voiceSseBuffer.indexOf("\n\n");
            if (idx < 0)
                break;
            QByteArray event = m_voiceSseBuffer.left(idx);
            m_voiceSseBuffer = m_voiceSseBuffer.mid(idx + 2);
            for (const QByteArray &line : event.split('\n')) {
                QByteArray trimmed = line.trimmed();
                if (!trimmed.startsWith("data: "))
                    continue;
                QJsonObject obj = QJsonDocument::fromJson(trimmed.mid(6)).object();
                QString type = obj["type"].toString();
                if (type == "transcribed_text") {
                    emit voiceTranscribedText(conversationId, obj["content"].toString());
                } else if (type == "token") {
                    emit voiceTokenReceived(conversationId, obj["content"].toString());
                } else if (type == "sentence") {
                    emit wsSentenceReceived(conversationId, obj["content"].toString());
                } else if (type == "done") {
                    emit voiceDoneReceived(conversationId, obj["message_id"].toInt(), obj["full_content"].toString(), obj["audio_url"].toString());
                } else if (type == "title_updated") {
                    emit titleAutoUpdated(obj["conversation_id"].toInt(), obj["title"].toString());
                } else if (type == "sentence_audio") {
                    int idx = obj["index"].toInt();
                    QString text = obj["text"].toString();
                    QString filename = obj["audio_filename"].toString();
                    double duration = obj["duration"].toDouble();
                    emit sentenceAudioReceived(conversationId, idx, text, filename, duration);
                } else if (type == "error") {
                    emit voiceError(obj["message"].toString());
                }
            }
        }
    });

    connect(m_voiceStreamReply, &QNetworkReply::finished, this, [this]() {
        m_voiceSseBuffer.clear();
        m_voiceStreamReply->deleteLater();
        m_voiceStreamReply = nullptr;
    });

    connect(m_voiceStreamReply, &QNetworkReply::errorOccurred, this, [this, conversationId](QNetworkReply::NetworkError) {
        m_voiceSseBuffer.clear();
        emit voiceError(QStringLiteral("语音上传失败，请检查网络"));
        m_voiceStreamReply->deleteLater();
        m_voiceStreamReply = nullptr;
    });
}

void ApiService::uploadKnowledgeDoc(int userId, const QString &title, const QString &filePath, const QString &)
{
    QFile *file = new QFile(filePath);
    if (!file->open(QIODevice::ReadOnly)) {
        delete file;
        emit apiError(QStringLiteral("无法打开文件: ") + filePath);
        return;
    }

    QHttpMultiPart *multiPart = new QHttpMultiPart(QHttpMultiPart::FormDataType);

    QHttpPart filePart;
    filePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                       QVariant(QStringLiteral("form-data; name=\"file\"; filename=\"%1\"").arg(title)));
    filePart.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/octet-stream"));
    filePart.setBodyDevice(file);
    file->setParent(multiPart);

    QHttpPart titlePart;
    titlePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                        QVariant(QStringLiteral("form-data; name=\"title\"")));
    titlePart.setBody(title.toUtf8());

    QHttpPart userIdPart;
    userIdPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                         QVariant(QStringLiteral("form-data; name=\"user_id\"")));
    userIdPart.setBody(QString::number(userId).toUtf8());

    multiPart->append(filePart);
    multiPart->append(titlePart);
    multiPart->append(userIdPart);

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/admin/knowledge-docs"));
    QNetworkReply *reply = m_networkManager->post(req, multiPart);
    multiPart->setParent(reply);

    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "uploadKnowledgeDoc error:" << reply->errorString();
            emit apiError(QStringLiteral("文档上传失败: ") + reply->errorString());
            return;
        }
        QByteArray responseData = reply->readAll();
        QJsonObject resp = QJsonDocument::fromJson(responseData).object();
        qDebug() << "uploadKnowledgeDoc response:" << responseData;

        int docId = 0;
        if (resp.contains("doc_id")) {
            docId = resp["doc_id"].toInt();
        } else if (resp.contains("data") && resp["data"].isObject()) {
            docId = resp["data"].toObject()["doc_id"].toInt();
        }

        if (docId > 0) {
            emit knowledgeDocUploaded(docId);
        } else {
            emit apiError(QStringLiteral("文档上传成功但返回数据异常"));
        }
    });
}

void ApiService::deleteKnowledgeDoc(int docId)
{
    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/admin/knowledge-docs/" + QString::number(docId)));
    QNetworkReply *reply = m_networkManager->deleteResource(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        bool success = (reply->error() == QNetworkReply::NoError);
        if (!success) {
            qDebug() << "deleteKnowledgeDoc error:" << reply->errorString();
        }
        emit knowledgeDocDeleted(success);
    });
}

void ApiService::loadKnowledgeDocs(int)
{
    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/admin/knowledge-docs"));
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadKnowledgeDocs error:" << reply->errorString();
            emit knowledgeDocsLoaded(QVariantList());
            return;
        }
        QByteArray responseData = reply->readAll();
        QJsonObject resp = QJsonDocument::fromJson(responseData).object();
        qDebug() << "loadKnowledgeDocs response:" << responseData;

        QJsonArray items;
        if (resp.contains("items")) {
            items = resp["items"].toArray();
        } else if (resp.contains("data") && resp["data"].isObject()) {
            items = resp["data"].toObject()["items"].toArray();
        }

        QVariantList docs;
        for (const QJsonValue &val : items) {
            QJsonObject obj = val.toObject();
            QVariantMap doc;
            doc["id"] = obj["doc_id"].toInt();
            doc["title"] = obj["title"].toString();
            doc["fileType"] = obj["file_type"].toString();
            doc["fileSize"] = obj["file_size"].toInt();
            doc["status"] = obj["status"].toString();
            doc["chunkCount"] = obj["chunk_count"].toInt();
            doc["createdAt"] = obj["created_at"].toString();
            docs.append(doc);
        }
        emit knowledgeDocsLoaded(docs);
    });
}

void ApiService::registerLiveTalkingSession(int conversationId, const QString &sessionId)
{
    QUrl url(BASE_URL + "/api/v1/digital-human/register_session");
    QNetworkRequest req(url);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["session_id"] = sessionId;

    m_networkManager->post(req, QJsonDocument(body).toJson());
    qDebug() << "ApiService: 注册 LiveTalking session, conversation_id=" << conversationId << "session_id=" << sessionId;
}

void ApiService::playAudio(int conversationId, const QString &audioFilename)
{
    QNetworkRequest request(QUrl(BASE_URL + "/api/v1/play-audio"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["audio_filename"] = audioFilename;

    QNetworkReply *reply = m_networkManager->post(request, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [reply]() {
        reply->deleteLater();
    });
}
