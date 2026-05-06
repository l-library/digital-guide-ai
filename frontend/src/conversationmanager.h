#ifndef CONVERSATIONMANAGER_H
#define CONVERSATIONMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>
#include <QStringList>

class ConversationManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(int currentConversationId READ currentConversationId NOTIFY currentConversationChanged)
    Q_PROPERTY(QVariantList messages READ messages NOTIFY messagesChanged)
    Q_PROPERTY(QVariantList conversations READ conversations NOTIFY conversationsChanged)
    Q_PROPERTY(QString currentTitle READ currentTitle NOTIFY currentConversationChanged)
    Q_PROPERTY(bool hasConversation READ hasConversation NOTIFY currentConversationChanged)
    Q_PROPERTY(bool streamingAiResponse READ streamingAiResponse NOTIFY streamingAiResponseChanged)
public:
    explicit ConversationManager(QObject *parent = nullptr);

    int currentConversationId() const;
    QVariantList messages() const;
    QVariantList conversations() const;
    QString currentTitle() const;
    bool hasConversation() const;
    bool streamingAiResponse() const;

    Q_INVOKABLE void sendMessage(const QString &text);
    Q_INVOKABLE void loadConversation(int conversationId);
    Q_INVOKABLE int startNewConversation(int userId, const QString &title, int knowledgeDocId = -1);
    Q_INVOKABLE void clearCurrentConversation();
    Q_INVOKABLE void loadConversationList(int userId);
    Q_INVOKABLE void renameCurrentConversation(const QString &newTitle);
    Q_INVOKABLE void renameConversationById(int conversationId, const QString &newTitle);
    Q_INVOKABLE void connectWebSocket();
    Q_INVOKABLE void disconnectWebSocket();

signals:
    void currentConversationChanged();
    void messagesChanged();
    void conversationsChanged();
    void streamingAiResponseChanged();
    void messageSending();
    void errorOccurred(const QString &error);

private:
    int m_currentConversationId = -1;
    QVariantList m_messages;
    QVariantList m_conversations;
    QString m_currentTitle;
    int m_currentUserId = -1;
    int m_responseType = 1;
    bool m_streaming = false;
    bool m_pendingNewConversation = false;
    int m_pendingKnowledgeDocId = -1;
    QStringList m_pendingMessages;

    void appendMessage(const QString &role, const QString &content);
    void updateLastAiMessageContent(const QString &token);
};

#endif // CONVERSATIONMANAGER_H
