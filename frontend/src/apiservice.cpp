#include "apiservice.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QTimer>
#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrlQuery>

static const QString BASE_URL = QStringLiteral("http://0.0.0.0:8000");

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

// ==================== Auth (stubs kept for now) ====================

void ApiService::login(const QString &username, const QString &password)
{
    QString hash = QString(QCryptographicHash::hash(password.toUtf8(), QCryptographicHash::Sha256).toHex());

    QTimer::singleShot(0, this, [this, username, hash]() {
        if (username == "admin" && hash == QString(QCryptographicHash::hash(QString("admin123").toUtf8(), QCryptographicHash::Sha256).toHex())) {
            QVariantMap userInfo;
            userInfo["id"] = 1;
            userInfo["username"] = "admin";
            userInfo["displayName"] = QStringLiteral("管理员");
            userInfo["avatarUrl"] = "";
            emit loginResult(true, userInfo, "");
        } else {
            emit loginResult(false, QVariantMap(), QStringLiteral("用户名或密码错误"));
        }
    });
}

void ApiService::checkAutoLogin(const QString &token, int userId)
{
    QTimer::singleShot(0, this, [this, token, userId]() {
        if (!token.isEmpty() && userId > 0) {
            QVariantMap userInfo;
            userInfo["id"] = userId;
            userInfo["username"] = "admin";
            userInfo["displayName"] = QStringLiteral("管理员");
            userInfo["avatarUrl"] = "";
            emit autoLoginResult(true, userInfo);
        } else {
            emit autoLoginResult(false, QVariantMap());
        }
    });
}

void ApiService::validateToken(const QString &token, int userId)
{
    QTimer::singleShot(0, this, [this, token, userId]() {
        if (!token.isEmpty() && userId > 0) {
            QVariantMap userInfo;
            userInfo["id"] = userId;
            userInfo["username"] = "admin";
            userInfo["displayName"] = QStringLiteral("管理员");
            userInfo["avatarUrl"] = "";
            emit autoLoginResult(true, userInfo);
        } else {
            emit autoLoginResult(false, QVariantMap());
        }
    });
}

void ApiService::logout(int)
{
    QTimer::singleShot(0, this, [this]() {
        emit logoutResult(true);
    });
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

    QNetworkReply *reply = m_networkManager->get(QNetworkRequest(url));
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

    QNetworkReply *reply = m_networkManager->get(QNetworkRequest(url));
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
            emit apiError("重命名对话失败");
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
                               int digitalHumanId,
                               int response_type)
{
    if (m_webSocket && m_webSocket->state() == QAbstractSocket::ConnectedState) {
        sendChatViaWebSocket(conversationId, userMessage, digitalHumanId);
        return;
    }

    QNetworkRequest req(QUrl(BASE_URL + "/api/v1/chat/text"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

    QJsonObject body;
    body["conversation_id"] = conversationId;
    body["content"] = userMessage;
    body["response_type"] = response_type;
    body["digital_human_id"] = digitalHumanId;

    QNetworkReply *reply = m_networkManager->post(req, QJsonDocument(body).toJson());
    connect(reply, &QNetworkReply::finished, this, [this, reply, conversationId]() {
        reply->deleteLater();
        if (reply->error() != QNetworkReply::NoError) {
            qDebug() << "sendAiMessage error:" << reply->errorString();
            emit aiResponseReceived(conversationId, QStringLiteral("抱歉，服务暂时不可用"), "ai");
            return;
        }
        QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
        QJsonObject data = resp["data"].toObject();
        QString content = data["content"].toString();
        emit aiResponseReceived(conversationId, content, "ai");
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
        } else if (type == "done") {
            int convId = msg["conversation_id"].toInt();
            int msgId = msg["message_id"].toInt();
            QString fullContent = msg["full_content"].toString();
            emit wsDoneReceived(convId, msgId, fullContent);
        } else if (type == "error") {
            emit wsError(msg["message"].toString());
        } else if (type == "pong") {
            // 心跳回复，忽略
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

void ApiService::sendChatViaWebSocket(int conversationId, const QString &content, int digitalHumanId)
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
    m_webSocket->sendTextMessage(QString(QJsonDocument(msg).toJson(QJsonDocument::Compact)));
}

// ==================== Knowledge docs (stubs) ====================

void ApiService::uploadKnowledgeDoc(int, const QString &title, const QString &, const QString &)
{
    static int nextDocId = 200;
    QTimer::singleShot(0, this, [this, nextDocId]() {
        emit knowledgeDocUploaded(nextDocId);
    });
}

void ApiService::deleteKnowledgeDoc(int)
{
    QTimer::singleShot(0, this, [this]() {
        emit knowledgeDocDeleted(true);
    });
}

void ApiService::loadKnowledgeDocs(int)
{
    QTimer::singleShot(0, this, [this]() {
        emit knowledgeDocsLoaded(QVariantList());
    });
}

// ==================== Digital humans (stubs) ====================

void ApiService::loadDigitalHumans()
{
    QTimer::singleShot(0, this, [this]() {
        emit digitalHumansLoaded(m_stubDigitalHumans);
    });
}

void ApiService::setDefaultDigitalHuman(int dhId)
{
    for (auto &dh : m_stubDigitalHumans) {
        QVariantMap dhm = dh.toMap();
        dhm["isDefault"] = (dhm["id"].toInt() == dhId);
        dh = dhm;
    }
    QTimer::singleShot(0, this, [this]() {
        emit defaultDigitalHumanSet(true);
    });
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
