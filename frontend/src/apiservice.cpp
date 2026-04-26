#include "apiservice.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QTimer>
#include <QDebug>

#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>

ApiService &ApiService::instance()
{
    static ApiService inst;
    return inst;
}

ApiService::ApiService(QObject *parent)
    : QObject(parent)
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

// --- Auth ---

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

void ApiService::logout(int /*userId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit logoutResult(true);
    });
}

// --- Conversations ---

void ApiService::createConversation(int userId, const QString &title, int knowledgeDocId)
{
    Q_UNUSED(userId);
    Q_UNUSED(knowledgeDocId);
    static int nextConvId = 100;

    QTimer::singleShot(0, this, [this, title]() {
        int convId = nextConvId++;
        emit conversationCreated(convId);
    });
}

void ApiService::loadConversations(int /*userId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit conversationsLoaded(QVariantList());
    });
}

void ApiService::loadConversationsGroupedByDate(int /*userId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit conversationsGroupedLoaded(QVariantList());
    });
}

void ApiService::deleteConversation(int /*conversationId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit conversationDeleted(true);
    });
}

void ApiService::loadMessages(int /*conversationId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit messagesLoaded(QVariantList(), 0);
    });
}

// --- Messages ---

void ApiService::addMessage(int conversationId, const QString &role, const QString &content)
{
    static int nextMsgId = 1000;

    QTimer::singleShot(0, this, [this, conversationId, role, content]() {
        int msgId = nextMsgId++;
        emit messageAdded(msgId, conversationId);
    });
}

void ApiService::sendAiMessage(int conversationId, const QString &userMessage, int digitalHumanId)
{
    QTimer::singleShot(0, this, [this, conversationId, digitalHumanId, userMessage]() {
        QString dhName = "231";

        QNetworkAccessManager *manager = new QNetworkAccessManager(this);
        QNetworkRequest request;
        request.setUrl(QUrl("http://8.136.128.80:8000/chat"));
        request.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");

        QJsonObject requestData;
        requestData["content"] = userMessage;
        QByteArray data = QJsonDocument(requestData).toJson();

        QNetworkReply *reply = manager->post(request, data);

        // 关键修正：捕获需要的值，而不是引用
        connect(reply, &QNetworkReply::finished, this, [this, conversationId, reply, manager]() {
            if (reply->error() == QNetworkReply::NoError) {
                QByteArray responseData = reply->readAll();
                QJsonDocument jsonResponse = QJsonDocument::fromJson(responseData);
                QString content = jsonResponse.object()["content"].toString();

                // 在这里发送信号
                emit aiResponseReceived(conversationId, content, "ai");
            } else {
                qDebug() << "HTTP error:" << reply->errorString();
                emit aiResponseReceived(conversationId, "抱歉，服务暂时不可用", "ai");
            }
            reply->deleteLater();
            manager->deleteLater(); // 清理manager
        });
        // 不需要立即emit
    });
}

// --- Knowledge docs ---

void ApiService::uploadKnowledgeDoc(int /*userId*/, const QString &title, const QString &filePath, const QString &content)
{
    static int nextDocId = 200;

    QTimer::singleShot(0, this, [this, title]() {
        int docId = nextDocId++;
        emit knowledgeDocUploaded(docId);
    });
}

void ApiService::deleteKnowledgeDoc(int /*docId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit knowledgeDocDeleted(true);
    });
}

void ApiService::loadKnowledgeDocs(int /*userId*/)
{
    QTimer::singleShot(0, this, [this]() {
        emit knowledgeDocsLoaded(QVariantList());
    });
}

// --- Digital humans ---

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

// --- Settings ---

void ApiService::getSetting(const QString &key)
{
    QTimer::singleShot(0, this, [this, key]() {
        emit settingLoaded(key, "");
    });
}

void ApiService::setSetting(const QString &key, const QString &value)
{
    QTimer::singleShot(0, this, [this, key]() {
        emit settingSaved(true);
    });
}

// --- Export ---

void ApiService::exportConversation(int conversationId)
{
    QTimer::singleShot(0, this, [this, conversationId]() {
        emit conversationExported(conversationId, QVariantMap());
    });
}
