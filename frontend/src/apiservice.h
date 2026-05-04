#ifndef APISERVICE_H
#define APISERVICE_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

#include <QNetworkAccessManager>
#include <QWebSocket>

class ApiService : public QObject
{
    Q_OBJECT
public:
    static ApiService &instance();

    // Auth
    void login(const QString &username, const QString &password);
    void checkAutoLogin(const QString &token, int userId);
    void logout(int userId);
    void validateToken(const QString &token, int userId);

    // Conversations
    void createConversation(int userId, const QString &title, int knowledgeDocId = -1);
    void loadConversations(int userId);
    void loadConversationsGroupedByDate(int userId);
    void deleteConversation(int conversationId);
    void renameConversation(int conversationId, const QString &newTitle);
    void loadMessages(int conversationId);

    // Messages
    void sendAiMessage(int conversationId,
                       const QString &userMessage,
                       int digitalHumanId,
                       int response_type);

    // WebSocket streaming chat
    void connectWebSocket();
    void disconnectWebSocket();
    bool isWebSocketConnected() const;
    void sendChatViaWebSocket(int conversationId, const QString &content, int digitalHumanId = 0);

    // Knowledge docs
    void uploadKnowledgeDoc(int userId, const QString &title, const QString &filePath, const QString &content);
    void deleteKnowledgeDoc(int docId);
    void loadKnowledgeDocs(int userId);

    // Digital humans
    void loadDigitalHumans();
    void setDefaultDigitalHuman(int dhId);

    // Settings
    void getSetting(const QString &key);
    void setSetting(const QString &key, const QString &value);

    // Export
    void exportConversation(int conversationId);

signals:
    // Auth
    void loginResult(bool success, QVariantMap userInfo, const QString &error);
    void autoLoginResult(bool loggedIn, QVariantMap userInfo);
    void logoutResult(bool success);

    // Conversations
    void conversationCreated(int conversationId);
    void conversationsLoaded(QVariantList conversations);
    void conversationsGroupedLoaded(QVariantList grouped);
    void conversationDeleted(bool success);
    void conversationRenamed(int conversationId, const QString &newTitle);
    void messagesLoaded(QVariantList messages, int conversationId);
    void messageAdded(int messageId, int conversationId);
    void aiResponseReceived(int conversationId, const QString &response, const QString &role);

    // WebSocket streaming
    void wsConnected();
    void wsDisconnected();
    void wsTokenReceived(int conversationId, const QString &token);
    void wsDoneReceived(int conversationId, int messageId, const QString &fullContent);
    void wsError(const QString &message);

    // Knowledge docs
    void knowledgeDocUploaded(int docId);
    void knowledgeDocDeleted(bool success);
    void knowledgeDocsLoaded(QVariantList docs);

    // Digital humans
    void digitalHumansLoaded(QVariantList digitalHumans);
    void defaultDigitalHumanSet(bool success);

    // Settings
    void settingLoaded(const QString &key, const QString &value);
    void settingSaved(bool success);

    // Export
    void conversationExported(int conversationId, QVariantMap data);

    // Error
    void apiError(const QString &error);

private:
    explicit ApiService(QObject *parent = nullptr);
    ~ApiService() = default;
    ApiService(const ApiService &) = delete;
    ApiService &operator=(const ApiService &) = delete;

    QNetworkAccessManager *m_networkManager;
    QWebSocket *m_webSocket;
    QVariantList m_stubDigitalHumans;

    void initStubData();
    QVariantList mapMessagesToFrontendFormat(const QVariantList &items) const;
};

#endif // APISERVICE_H
