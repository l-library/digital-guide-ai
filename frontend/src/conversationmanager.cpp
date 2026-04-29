#include "conversationmanager.h"
#include "apiservice.h"

#include <QDateTime>

ConversationManager::ConversationManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::messageAdded, this, [this](int msgId, int conversationId) {
        Q_UNUSED(conversationId);
        Q_UNUSED(msgId);
        emit messagesChanged();
    });
    connect(&api, &ApiService::aiResponseReceived, this, [this](int conversationId, const QString &response, const QString &role) {
        if (conversationId != m_currentConversationId)
            return;
        appendMessage(role, response);
    });
    connect(&api, &ApiService::messagesLoaded, this, [this](QVariantList messages, int conversationId) {
        if (conversationId != m_currentConversationId && conversationId != 0)
            return;
        m_messages = messages;
        emit messagesChanged();
    });
    connect(&api, &ApiService::conversationCreated, this, [this](int convId) {
        m_currentConversationId = convId;
        m_messages.clear();
        emit currentConversationChanged();
        emit messagesChanged();
    });
}

int ConversationManager::currentConversationId() const
{
    return m_currentConversationId;
}

QVariantList ConversationManager::messages() const
{
    return m_messages;
}

QString ConversationManager::currentTitle() const
{
    return m_currentTitle;
}

bool ConversationManager::hasConversation() const
{
    return m_currentConversationId > 0;
}

void ConversationManager::sendMessage(const QString &text)
{
    if (m_currentConversationId <= 0 || text.trimmed().isEmpty())
        return;

    emit messageSending();

    appendMessage("user", text.trimmed());

    ApiService::instance().sendAiMessage(m_currentConversationId, text.trimmed(), 1, m_responseType);
}

void ConversationManager::loadConversation(int conversationId)
{
    m_currentConversationId = conversationId;
    ApiService::instance().loadMessages(conversationId);
    emit currentConversationChanged();
}

int ConversationManager::startNewConversation(int userId, const QString &title, int knowledgeDocId)
{
    m_currentUserId = userId;
    m_currentTitle = title;
    m_messages.clear();
    emit messagesChanged();
    ApiService::instance().createConversation(userId, title, knowledgeDocId);
    return 0;
}

void ConversationManager::clearCurrentConversation()
{
    m_currentConversationId = -1;
    m_currentTitle.clear();
    m_messages.clear();
    emit currentConversationChanged();
    emit messagesChanged();
}

void ConversationManager::appendMessage(const QString &role, const QString &content)
{
    QVariantMap msg;
    msg["id"] = 0;
    msg["role"] = role;
    msg["content"] = content;
    msg["timestamp"] = QDateTime::currentDateTime().toString(Qt::ISODate);
    m_messages.append(msg);
    ApiService::instance().addMessage(m_currentConversationId, role, content);
    emit messagesChanged();
}
