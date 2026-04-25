#ifndef APISERVICE_H
#define APISERVICE_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

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
    void loadMessages(int conversationId);

    // Messages
    void addMessage(int conversationId, const QString &role, const QString &content);
    void sendAiMessage(int conversationId, const QString &userMessage, int digitalHumanId);

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
    void loginResult(bool success, QVariantMap userInfo, const QString &error);
    void autoLoginResult(bool loggedIn, QVariantMap userInfo);
    void logoutResult(bool success);

    void conversationCreated(int conversationId);
    void conversationsLoaded(QVariantList conversations);
    void conversationsGroupedLoaded(QVariantList grouped);
    void conversationDeleted(bool success);
    void messagesLoaded(QVariantList messages, int conversationId);
    void messageAdded(int messageId, int conversationId);
    void aiResponseReceived(int conversationId, const QString &response, const QString &role);

    void knowledgeDocUploaded(int docId);
    void knowledgeDocDeleted(bool success);
    void knowledgeDocsLoaded(QVariantList docs);

    void digitalHumansLoaded(QVariantList digitalHumans);
    void defaultDigitalHumanSet(bool success);

    void settingLoaded(const QString &key, const QString &value);
    void settingSaved(bool success);

    void conversationExported(int conversationId, QVariantMap data);

    void apiError(const QString &error);

private:
    explicit ApiService(QObject *parent = nullptr);
    ~ApiService() = default;
    ApiService(const ApiService &) = delete;
    ApiService &operator=(const ApiService &) = delete;

    QVariantList m_stubDigitalHumans;
    void initStubData();
};

#endif // APISERVICE_H
