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
    initStubData();
}

void ApiService::initStubData()
{
    QVariantMap dh1, dh2, dh3;
    dh1["id"] = 1;
    dh1["name"] = QStringLiteral("小导");
    dh1["description"] = QStringLiteral("标准导游数字人");
    dh1["avatarUrl"] = "";
    dh1["isDefault"] = true;

    dh2["id"] = 2;
    dh2["name"] = QStringLiteral("小薇");
    dh2["description"] = QStringLiteral("温柔风格导游");
    dh2["avatarUrl"] = "";
    dh2["isDefault"] = false;

    dh3["id"] = 3;
    dh3["name"] = QStringLiteral("小智");
    dh3["description"] = QStringLiteral("知识型导游");
    dh3["avatarUrl"] = "";
    dh3["isDefault"] = false;

    m_stubDigitalHumans = {dh1, dh2, dh3};
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

// ==================== Auth (real HTTP) ====================

void ApiService::login(const QString &username, const QString &password)
{
    QUrl url(BASE_URL + "/api/v1/auth/login");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["username"] = username;
    body["password"] = password;

    QNetworkReply *reply = m_networkManager->post(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit loginResult(false, QVariantMap(), QStringLiteral("网络错误：无法连接到服务器"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            m_authToken = data["token"].toString();
            QVariantMap userInfo;
            userInfo["id"] = data["user_id"].toInt();
            userInfo["username"] = data["username"].toString();
            userInfo["displayName"] = data["display_name"].toString();
            userInfo["role"] = data["role"].toString();
            userInfo["avatarUrl"] = data["avatar_url"].toString();
            userInfo["token"] = m_authToken;
            emit loginResult(true, userInfo, "");
        } else {
            emit loginResult(false, QVariantMap(), resp["message"].toString());
        }
    });
}

void ApiService::registerUser(const QString &username, const QString &password,
                               const QString &confirmPassword, const QString &displayName)
{
    QUrl url(BASE_URL + "/api/v1/auth/register");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["username"] = username;
    body["password"] = password;
    body["confirm_password"] = confirmPassword;
    body["display_name"] = displayName;

    QNetworkReply *reply = m_networkManager->post(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit registerResult(false, QVariantMap(), QStringLiteral("网络错误：无法连接到服务器"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            m_authToken = data["token"].toString();
            QVariantMap userInfo;
            userInfo["id"] = data["user_id"].toInt();
            userInfo["username"] = data["username"].toString();
            userInfo["displayName"] = data["display_name"].toString();
            userInfo["role"] = data["role"].toString();
            userInfo["token"] = m_authToken;
            emit registerResult(true, userInfo, "");
        } else {
            emit registerResult(false, QVariantMap(), resp["message"].toString());
        }
    });
}

void ApiService::updateUserProfile(int userId, const QString &displayName, const QString &avatarUrl)
{
    QUrl url(BASE_URL + "/api/v1/auth/profile");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QJsonObject body;
    body["display_name"] = displayName;
    body["avatar_url"] = avatarUrl;

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, userId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit profileUpdateResult(false, QVariantMap(), QStringLiteral("网络错误：无法连接到服务器"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QVariantMap userInfo;
            userInfo["id"] = data["user_id"].toInt();
            userInfo["username"] = data["username"].toString();
            userInfo["displayName"] = data["display_name"].toString();
            userInfo["role"] = data["role"].toString();
            userInfo["avatarUrl"] = data["avatar_url"].toString();
            emit profileUpdateResult(true, userInfo, "");
        } else {
            emit profileUpdateResult(false, QVariantMap(), resp["message"].toString());
        }
    });
}

void ApiService::changeUserPassword(int userId, const QString &oldPassword, const QString &newPassword)
{
    QUrl url(BASE_URL + "/api/v1/auth/password");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QJsonObject body;
    body["old_password"] = oldPassword;
    body["new_password"] = newPassword;

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit passwordChangeResult(false, QStringLiteral("网络错误：无法连接到服务器"));
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            emit passwordChangeResult(true, "");
        } else {
            emit passwordChangeResult(false, resp["message"].toString());
        }
    });
}

void ApiService::checkAutoLogin(const QString &token, int userId)
{
    Q_UNUSED(userId)
    if (token.isEmpty()) {
        emit autoLoginResult(false, QVariantMap());
        return;
    }
    // 保存 token 到成员变量，供后续需要认证的请求使用
    m_authToken = token;
    QUrl url(BASE_URL + "/api/v1/auth/verify");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setRawHeader("Authorization", ("Bearer " + token).toUtf8());

    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit autoLoginResult(false, QVariantMap());
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QVariantMap userInfo;
            userInfo["id"] = data["user_id"].toInt();
            userInfo["username"] = data["username"].toString();
            userInfo["displayName"] = data["display_name"].toString();
            userInfo["role"] = data["role"].toString();
            userInfo["avatarUrl"] = data["avatar_url"].toString();
            emit autoLoginResult(true, userInfo);
        } else {
            emit autoLoginResult(false, QVariantMap());
        }
    });
}

void ApiService::validateToken(const QString &token, int userId)
{
    Q_UNUSED(userId)
    if (token.isEmpty()) {
        emit autoLoginResult(false, QVariantMap());
        return;
    }
    // 保存 token 到成员变量，供后续需要认证的请求使用
    m_authToken = token;
    QUrl url(BASE_URL + "/api/v1/auth/verify");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setRawHeader("Authorization", ("Bearer " + token).toUtf8());

    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit autoLoginResult(false, QVariantMap());
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QVariantMap userInfo;
            userInfo["id"] = data["user_id"].toInt();
            userInfo["username"] = data["username"].toString();
            userInfo["displayName"] = data["display_name"].toString();
            userInfo["role"] = data["role"].toString();
            userInfo["avatarUrl"] = data["avatar_url"].toString();
            emit autoLoginResult(true, userInfo);
        } else {
            emit autoLoginResult(false, QVariantMap());
        }
    });
}

void ApiService::logout(int userId)
{
    Q_UNUSED(userId)
    QUrl url(BASE_URL + "/api/v1/auth/logout");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QNetworkReply *reply = m_networkManager->post(req, QByteArray());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        m_authToken.clear();
        emit logoutResult(true);
    });
}

// ==================== Conversations (real HTTP) ====================

void ApiService::createConversation(int userId, const QString &title, int knowledgeDocId)
{
    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/conversations"));
    req.setTransferTimeout(15000);
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
            emit apiError("创建对话失败");
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

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadConversations error:" << reply->errorString();
            emit apiError("加载对话列表失败");
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

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadConversationsGroupedByDate error:" << reply->errorString();
            emit apiError("加载分组对话失败");
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
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    QNetworkReply *reply = m_networkManager->deleteResource(req);
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
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["title"] = newTitle;

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, conversationId, newTitle]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "renameConversation error:" << reply->errorString();
            emit apiError("重命名对话失败");
            return;
        }
        emit conversationRenamed(conversationId, newTitle);
    });
}

void ApiService::loadMessages(int conversationId)
{
    QUrl url(BASE_URL + "/api/v1/conversations/" + QString::number(conversationId) + "/messages/all");

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    QNetworkReply *reply = m_networkManager->get(req);
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
                                int digitalHumanId,
                                int response_type)
{
    if (m_webSocket && m_webSocket->state() == QAbstractSocket::ConnectedState) {
        sendChatViaWebSocket(conversationId, userMessage, digitalHumanId, response_type);
        return;
    }

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/chat/stream"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["content"] = userMessage;
    body["response_type"] = response_type;
    body["digital_human_id"] = digitalHumanId;

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

void ApiService::sendChatViaWebSocket(int conversationId, const QString &content, int digitalHumanId, int responseType)
{
    if (!m_webSocket || m_webSocket->state() != QAbstractSocket::ConnectedState) {
        emit wsError(QStringLiteral("WebSocket 未连接"));
        return;
    }
    QJsonObject msg;
    msg["type"] = "chat_message";
    msg["conversation_id"] = conversationId;
    msg["content"] = content;
    msg["digital_human_id"] = digitalHumanId;
    msg["response_type"] = responseType;
    m_webSocket->sendTextMessage(QString(QJsonDocument(msg).toJson(QJsonDocument::Compact)));
}

// ==================== Voice streaming SSE ====================

void ApiService::sendVoiceMessage(int conversationId, const QString &audioFilePath, int digitalHumanId, int responseType)
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

QHttpPart dhIdPart;
    dhIdPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                        QVariant(QStringLiteral("form-data; name=\"digital_human_id\"")));
    dhIdPart.setBody(QString::number(digitalHumanId).toUtf8());

    QHttpPart rtPart;
    rtPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                      QVariant(QStringLiteral("form-data; name=\"response_type\"")));
    rtPart.setBody(QString::number(responseType).toUtf8());

    multiPart->append(audioPart);
    multiPart->append(convIdPart);
    multiPart->append(dhIdPart);
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

// ==================== Knowledge docs (real HTTP) ====================

void ApiService::uploadKnowledgeDoc(int userId, const QString &title, const QString &filePath, const QString &)
{
    QFile *file = new QFile(filePath);
    if (!file->open(QIODevice::ReadOnly)) {
        delete file;
        emit apiError(QStringLiteral("无法打开文件: ") + filePath);
        return;
    }

    QHttpMultiPart *multiPart = new QHttpMultiPart(QHttpMultiPart::FormDataType);

    // file 字段
    QHttpPart filePart;
    filePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                       QVariant(QStringLiteral("form-data; name=\"file\"; filename=\"%1\"").arg(title)));
    filePart.setHeader(QNetworkRequest::ContentTypeHeader, QVariant("application/octet-stream"));
    filePart.setBodyDevice(file);
    file->setParent(multiPart);

    // title 字段
    QHttpPart titlePart;
    titlePart.setHeader(QNetworkRequest::ContentDispositionHeader,
                        QVariant(QStringLiteral("form-data; name=\"title\"")));
    titlePart.setBody(title.toUtf8());

    // user_id 字段
    QHttpPart userIdPart;
    userIdPart.setHeader(QNetworkRequest::ContentDispositionHeader,
                         QVariant(QStringLiteral("form-data; name=\"user_id\"")));
    userIdPart.setBody(QString::number(userId).toUtf8());

    multiPart->append(filePart);
    multiPart->append(titlePart);
    multiPart->append(userIdPart);

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/admin/knowledge-docs"));
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    req.setTransferTimeout(30000);
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

        // 兼容两种响应格式：直接返回数据 或 包在 data 字段中
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
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
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
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
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

        // 兼容两种响应格式
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

// ==================== Digital humans (stubs) ====================

void ApiService::loadDigitalHumans()
{
    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/admin/digital-humans"));
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    req.setTransferTimeout(15000);

    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadDigitalHumans error:" << reply->errorString();
            // Fall back to stub data on network error
            emit digitalHumansLoaded(m_stubDigitalHumans);
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        QJsonArray items;
        if (resp.contains("items")) {
            items = resp["items"].toArray();
        } else if (resp.contains("data") && resp["data"].isObject()) {
            items = resp["data"].toObject()["items"].toArray();
        }

        QVariantList dhs;
        for (const QJsonValue &val : items) {
            QJsonObject obj = val.toObject();
            QVariantMap dh;
            dh["id"] = obj["digital_human_id"].toInt();
            dh["name"] = obj["name"].toString();
            dh["description"] = obj["description"].toString();
            dh["avatarUrl"] = obj["avatar_url"].toString();
            dh["isDefault"] = obj["is_default"].toBool();
            dhs.append(dh);
        }

        if (dhs.isEmpty()) {
            // Fall back to stub data if API returns empty
            emit digitalHumansLoaded(m_stubDigitalHumans);
        } else {
            emit digitalHumansLoaded(dhs);
        }
    });
}

void ApiService::setDefaultDigitalHuman(int dhId)
{
    QUrl url(BASE_URL + "/api/v1/admin/digital-humans/" + QString::number(dhId) + "/default");
    QNetworkRequest req(url);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    req.setTransferTimeout(15000);

    QNetworkReply *reply = m_networkManager->put(req, QByteArray());
    connect(reply, &QNetworkReply::finished, this, [this, reply, dhId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "setDefaultDigitalHuman error:" << reply->errorString();
            emit defaultDigitalHumanSet(false);
            return;
        }
        // Update local stub data to reflect the change
        for (auto &dh : m_stubDigitalHumans) {
            QVariantMap dhm = dh.toMap();
            dhm["isDefault"] = (dhm["id"].toInt() == dhId);
            dh = dhm;
        }
        emit defaultDigitalHumanSet(true);
    });
}

void ApiService::registerLiveTalkingSession(int conversationId, const QString &sessionId)
{
    QUrl url(BASE_URL + "/api/v1/digital-human/register_session");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["session_id"] = sessionId;

    m_networkManager->post(req, QJsonDocument(body).toJson());
    qDebug() << "ApiService: 注册 LiveTalking session, conversation_id=" << conversationId << "session_id=" << sessionId;
}

// ==================== Settings (stubs) ====================

void ApiService::getSetting(const QString &key)
{
    QTimer::singleShot(0, this, [this, key]() {
        emit settingLoaded(key, "");
    });
}

void ApiService::setSetting(const QString &, const QString &)
{
    QTimer::singleShot(0, this, [this]() {
        emit settingSaved(true);
    });
}

// ==================== Export (stub) ====================

void ApiService::exportConversation(int conversationId)
{
    QTimer::singleShot(0, this, [this, conversationId]() {
        emit conversationExported(conversationId, QVariantMap());
    });
}

// ==================== Admin user management ====================

/** 加载用户列表：GET /api/v1/admin/users?page=&page_size=&search=
 *  解析返回的分页数据，组装成 QVariantMap 列表后发射 usersLoaded 信号 */
void ApiService::loadUsers(int page, int pageSize, const QString &search)
{
    QUrl url(BASE_URL + "/api/v1/admin/users");
    QUrlQuery query;
    query.addQueryItem("page", QString::number(page));
    query.addQueryItem("page_size", QString::number(pageSize));
    if (!search.isEmpty()) {
        query.addQueryItem("search", search);
    }
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, page, pageSize]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "loadUsers error:" << reply->errorString();
            emit adminError("加载用户列表失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QJsonArray items = data["items"].toArray();
            int total = data["total"].toInt();

            QVariantList users;
            for (const QJsonValue &val : items) {
                QJsonObject obj = val.toObject();
                QVariantMap user;
                user["id"] = obj["id"].toInt();
                user["username"] = obj["username"].toString();
                user["displayName"] = obj["display_name"].toString();
                user["role"] = obj["role"].toString();
                user["phone"] = obj["phone"].toString();
                user["email"] = obj["email"].toString();
                user["isActive"] = obj["is_active"].toBool();
                user["avatarUrl"] = obj["avatar_url"].toString();
                user["createdAt"] = obj["created_at"].toString();
                users.append(user);
            }
            emit usersLoaded(users, total, page, pageSize);
        } else {
            emit adminError(resp["message"].toString());
        }
    });
}

/** 创建新用户：POST /api/v1/admin/users
 *  请求体包含 username、password、display_name，成功后发射 userCreated 信号 */
void ApiService::createUser(const QString &username, const QString &password, const QString &displayName)
{
    QUrl url(BASE_URL + "/api/v1/admin/users");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QJsonObject body;
    body["username"] = username;
    body["password"] = password;
    body["display_name"] = displayName;

    QNetworkReply *reply = m_networkManager->post(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        // 无论 HTTP 状态码如何，都读取响应体以提取错误详情
        QByteArray responseData = reply->readAll();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "createUser error:" << reply->errorString();
            // 尝试从 422 响应中提取验证错误详情
            QJsonObject resp = QJsonDocument::fromJson(responseData).object();
            if (resp.contains("detail") && resp["detail"].isArray()) {
                QJsonArray details = resp["detail"].toArray();
                if (!details.isEmpty()) {
                    QJsonObject firstError = details[0].toObject();
                    QString msg = firstError["msg"].toString();
                    if (!msg.isEmpty()) {
                        emit adminError("创建用户失败: " + msg);
                        return;
                    }
                }
            }
            emit adminError("创建用户失败: " + reply->errorString());
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(responseData).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QVariantMap userData;
            userData["id"] = data["id"].toInt();
            userData["username"] = data["username"].toString();
            userData["displayName"] = data["display_name"].toString();
            userData["role"] = data["role"].toString();
            userData["isActive"] = data["is_active"].toBool();
            userData["createdAt"] = data["created_at"].toString();
            emit userCreated(data["id"].toInt(), userData);
        } else {
            emit adminError(resp["message"].toString());
        }
    });
}

/** 更新用户信息：PUT /api/v1/admin/users/:id
 *  仅更新 fields 中提供的字段（displayName/email/phone），部分更新 */
void ApiService::updateUser(int userId, const QVariantMap &fields)
{
    QUrl url(BASE_URL + "/api/v1/admin/users/" + QString::number(userId));
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QJsonObject body;
    if (fields.contains("displayName")) {
        body["display_name"] = fields["displayName"].toString();
    }
    if (fields.contains("email")) {
        body["email"] = fields["email"].toString();
    }
    if (fields.contains("phone")) {
        body["phone"] = fields["phone"].toString();
    }

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, userId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "updateUser error:" << reply->errorString();
            emit adminError("更新用户信息失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            QJsonObject data = resp["data"].toObject();
            QVariantMap userData;
            userData["id"] = data["id"].toInt();
            userData["displayName"] = data["display_name"].toString();
            userData["email"] = data["email"].toString();
            userData["phone"] = data["phone"].toString();
            userData["isActive"] = data["is_active"].toBool();
            emit userUpdated(userId, userData);
        } else {
            emit adminError(resp["message"].toString());
        }
    });
}

/** 删除用户：DELETE /api/v1/admin/users/:id
 *  级联删除用户的对话和关联数据，成功后发射 userDeleted 信号 */
void ApiService::deleteUser(int userId)
{
    QUrl url(BASE_URL + "/api/v1/admin/users/" + QString::number(userId));
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QNetworkReply *reply = m_networkManager->deleteResource(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, userId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "deleteUser error:" << reply->errorString();
            emit adminError("删除用户失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            emit userDeleted(userId);
        } else {
            emit adminError(resp["message"].toString());
        }
    });
}

/** 切换用户启用/禁用状态：PUT /api/v1/admin/users/:id/status
 *  请求体包含 is_active，成功后发射 userStatusChanged 信号 */
void ApiService::toggleUserStatus(int userId, bool isActive)
{
    QUrl url(BASE_URL + "/api/v1/admin/users/" + QString::number(userId) + "/status");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }

    QJsonObject body;
    body["is_active"] = isActive;

    QNetworkReply *reply = m_networkManager->put(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, userId, isActive]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "toggleUserStatus error:" << reply->errorString();
            emit adminError("修改用户状态失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        int code = resp["code"].toInt();
        if (code == 200) {
            emit userStatusChanged(userId, isActive);
        } else {
            emit adminError(resp["message"].toString());
        }
    });
}

// ==================== Dashboard & Reports ====================

void ApiService::loadDashboardOverview()
{
    QUrl url(BASE_URL + "/api/v1/admin/dashboard/overview");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取概览数据失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit dashboardOverviewLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadServiceStats(const QString &period)
{
    QUrl url(BASE_URL + "/api/v1/admin/dashboard/service-stats");
    QUrlQuery query;
    query.addQueryItem("period", period);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, period]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取服务统计失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            QJsonArray arr = resp["data"].toArray();
            QVariantList stats;
            for (const QJsonValue &val : arr) {
                stats.append(val.toVariant());
            }
            emit serviceStatsLoaded(period, stats);
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadHotQuestions(int top)
{
    QUrl url(BASE_URL + "/api/v1/admin/dashboard/hot-questions");
    QUrlQuery query;
    query.addQueryItem("top", QString::number(top));
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取热门问题失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            QJsonArray arr = resp["data"].toArray();
            QVariantList items;
            for (const QJsonValue &val : arr) {
                items.append(val.toVariant());
            }
            emit hotQuestionsLoaded(items);
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadSatisfactionTrend(const QString &period)
{
    QUrl url(BASE_URL + "/api/v1/admin/dashboard/satisfaction-trend");
    QUrlQuery query;
    query.addQueryItem("period", period);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply, period]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取满意度趋势失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            QJsonArray arr = resp["data"].toArray();
            QVariantList trend;
            for (const QJsonValue &val : arr) {
                trend.append(val.toVariant());
            }
            emit satisfactionTrendLoaded(period, trend);
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadDashboardFull()
{
    QUrl url(BASE_URL + "/api/v1/admin/dashboard/full");
    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取完整面板数据失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit dashboardFullLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadVisitorInsight(const QString &startDate, const QString &endDate)
{
    QUrl url(BASE_URL + "/api/v1/admin/reports/visitor-insight");
    QUrlQuery query;
    query.addQueryItem("start_date", startDate);
    query.addQueryItem("end_date", endDate);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取访客洞察失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit visitorInsightLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadEmotionTrend(const QString &startDate, const QString &endDate)
{
    QUrl url(BASE_URL + "/api/v1/admin/reports/emotion-trend");
    QUrlQuery query;
    query.addQueryItem("start_date", startDate);
    query.addQueryItem("end_date", endDate);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取情绪趋势失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit emotionTrendLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadFocusAnalysis(const QString &startDate, const QString &endDate)
{
    QUrl url(BASE_URL + "/api/v1/admin/reports/focus-analysis");
    QUrlQuery query;
    query.addQueryItem("start_date", startDate);
    query.addQueryItem("end_date", endDate);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取关注分析失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit focusAnalysisLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::loadServiceSuggestions(const QString &startDate, const QString &endDate)
{
    QUrl url(BASE_URL + "/api/v1/admin/reports/service-suggestions");
    QUrlQuery query;
    query.addQueryItem("start_date", startDate);
    query.addQueryItem("end_date", endDate);
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);
    if (!m_authToken.isEmpty()) {
        req.setRawHeader("Authorization", ("Bearer " + m_authToken).toUtf8());
    }
    QNetworkReply *reply = m_networkManager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            emit apiError("获取服务建议失败");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        if (resp["code"].toInt() == 200) {
            emit serviceSuggestionsLoaded(resp["data"].toObject().toVariantMap());
        } else {
            emit apiError(resp["message"].toString());
        }
    });
}

void ApiService::playAudio(int conversationId, const QString &audioFilename)
{
    QNetworkRequest request(QUrl(BASE_URL + "/api/v1/play-audio"));
    request.setTransferTimeout(15000);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["audio_filename"] = audioFilename;

    QNetworkReply *reply = m_networkManager->post(request, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [reply]() {
        reply->deleteLater();
    });
}

void ApiService::playAudioQueued(int conversationId, const QString &audioFilename)
{
    QNetworkRequest request(QUrl(BASE_URL + "/api/v1/play-audio-queue"));
    request.setTransferTimeout(15000);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["audio_filename"] = audioFilename;

    QNetworkReply *reply = m_networkManager->post(request, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [reply]() {
        reply->deleteLater();
    });
}

void ApiService::flushAudio(int conversationId)
{
    QNetworkRequest request(QUrl(BASE_URL + "/api/v1/flush"));
    request.setTransferTimeout(15000);
    request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;

    QNetworkReply *reply = m_networkManager->post(request, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [reply]() {
        reply->deleteLater();
    });
}
