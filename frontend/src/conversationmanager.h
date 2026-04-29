#ifndef CONVERSATIONMANAGER_H
#define CONVERSATIONMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class ConversationManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(int currentConversationId READ currentConversationId NOTIFY currentConversationChanged)
    Q_PROPERTY(QVariantList messages READ messages NOTIFY messagesChanged)
    Q_PROPERTY(QString currentTitle READ currentTitle NOTIFY currentConversationChanged)
    Q_PROPERTY(bool hasConversation READ hasConversation NOTIFY currentConversationChanged)
public:
    explicit ConversationManager(QObject *parent = nullptr);

    int currentConversationId() const;
    QVariantList messages() const;
    QString currentTitle() const;
    bool hasConversation() const;

    Q_INVOKABLE void sendMessage(const QString &text);
    Q_INVOKABLE void loadConversation(int conversationId);
    Q_INVOKABLE int startNewConversation(int userId, const QString &title, int knowledgeDocId = -1);
    Q_INVOKABLE void clearCurrentConversation();

signals:
    void currentConversationChanged();
    void messagesChanged();
    void messageSending();
    void errorOccurred(const QString &error);

private:
    int m_currentConversationId = -1;
    QVariantList m_messages;
    QString m_currentTitle;
    int m_currentUserId = -1;
    int m_responseType = 1;

    void appendMessage(const QString &role, const QString &content);
};

#endif // CONVERSATIONMANAGER_H
