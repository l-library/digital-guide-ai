#include "conversationmanager.h"
#include "apiservice.h"

#include <QDateTime>

ConversationManager::ConversationManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::messageAdded, this, [this](int, int) {
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
        m_pendingNewConversation = false;
        emit currentConversationChanged();

        if (!m_pendingMessages.isEmpty()) {
            QString msgText = m_pendingMessages.takeFirst();
            ApiService::instance().sendAiMessage(m_currentConversationId, msgText, 1, m_responseType);
        }

        emit messagesChanged();
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
    });
    connect(&api, &ApiService::conversationsLoaded, this, [this](QVariantList convs) {
        m_conversations = convs;
        emit conversationsChanged();
    });

    connect(&api, &ApiService::wsTokenReceived, this, [this](int conversationId, const QString &token) {
        if (conversationId != m_currentConversationId)
            return;
        updateLastAiMessageContent(token);
    });
    connect(&api, &ApiService::wsDoneReceived, this, [this](int conversationId, int, const QString &) {
        if (conversationId != m_currentConversationId)
            return;
        m_streaming = false;
        emit streamingAiResponseChanged();
        emit messagesChanged();
        // 刷新对话列表，确保新对话（已有消息）出现在历史列表中
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
    });
    connect(&api, &ApiService::wsError, this, [this](const QString &msg) {
        m_streaming = false;
        emit streamingAiResponseChanged();
        emit errorOccurred(msg);
    });
    connect(&api, &ApiService::conversationRenamed, this, [this](int conversationId, const QString &newTitle) {
        if (conversationId == m_currentConversationId) {
            m_currentTitle = newTitle;
            emit currentConversationChanged();
        }
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
    });
    connect(&api, &ApiService::titleAutoUpdated, this, [this](int conversationId, const QString &newTitle) {
        if (conversationId == m_currentConversationId && !newTitle.isEmpty()) {
            m_currentTitle = newTitle;
            emit currentConversationChanged();
        }
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
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

QVariantList ConversationManager::conversations() const
{
    return m_conversations;
}

QString ConversationManager::currentTitle() const
{
    return m_currentTitle;
}

bool ConversationManager::hasConversation() const
{
    return m_currentConversationId > 0 || m_pendingNewConversation;
}

bool ConversationManager::streamingAiResponse() const
{
    return m_streaming;
}

void ConversationManager::sendMessage(const QString &text)
{
    if (text.trimmed().isEmpty())
        return;

    if (m_pendingNewConversation) {
        m_pendingMessages.append(text.trimmed());
        appendMessage("user", text.trimmed());
        emit messageSending();
        ApiService::instance().createConversation(m_currentUserId, m_currentTitle, m_pendingKnowledgeDocId);
        return;
    }

    if (m_currentConversationId <= 0)
        return;

    emit messageSending();

    appendMessage("user", text.trimmed());

    ApiService::instance().sendAiMessage(m_currentConversationId, text.trimmed(), 1, m_responseType);
}

void ConversationManager::loadConversation(int conversationId)
{
    m_pendingNewConversation = false;
    m_pendingMessages.clear();
    m_currentConversationId = conversationId;
    m_messages.clear();
    emit messagesChanged();
    ApiService::instance().loadMessages(conversationId);
    emit currentConversationChanged();
}

int ConversationManager::startNewConversation(int userId, const QString &title, int knowledgeDocId)
{
    m_currentUserId = userId;
    m_currentTitle = title;
    m_currentConversationId = -1;
    m_pendingNewConversation = true;
    m_pendingKnowledgeDocId = knowledgeDocId;
    m_messages.clear();
    emit currentConversationChanged();
    emit messagesChanged();

    if (!ApiService::instance().isWebSocketConnected()) {
        ApiService::instance().connectWebSocket();
    }

    return 0;
}

void ConversationManager::clearCurrentConversation()
{
    m_currentConversationId = -1;
    m_currentTitle.clear();
    m_messages.clear();
    m_streaming = false;
    m_pendingNewConversation = false;
    m_pendingMessages.clear();
    emit streamingAiResponseChanged();
    emit currentConversationChanged();
    emit messagesChanged();
}

void ConversationManager::loadConversationList(int userId)
{
    ApiService::instance().loadConversations(userId);
}

void ConversationManager::renameCurrentConversation(const QString &newTitle)
{
    if (m_currentConversationId <= 0)
        return;
    ApiService::instance().renameConversation(m_currentConversationId, newTitle);
}

void ConversationManager::renameConversationById(int conversationId, const QString &newTitle)
{
    ApiService::instance().renameConversation(conversationId, newTitle);
}

void ConversationManager::connectWebSocket()
{
    ApiService::instance().connectWebSocket();
}

void ConversationManager::disconnectWebSocket()
{
    ApiService::instance().disconnectWebSocket();
}

void ConversationManager::appendMessage(const QString &role, const QString &content)
{
    QVariantMap msg;
    msg["id"] = 0;
    msg["role"] = role;
    msg["content"] = content;
    msg["timestamp"] = QDateTime::currentDateTime().toString(Qt::ISODate);
    m_messages.append(msg);
    emit messagesChanged();
}

void ConversationManager::updateLastAiMessageContent(const QString &token)
{
    if (!m_streaming) {
        m_streaming = true;
        emit streamingAiResponseChanged();
        QVariantMap placeholder;
        placeholder["id"] = 0;
        placeholder["role"] = "ai";
        placeholder["content"] = token;
        placeholder["timestamp"] = QDateTime::currentDateTime().toString(Qt::ISODate);
        m_messages.append(placeholder);
    } else {
        if (m_messages.isEmpty())
            return;
        QVariantMap last = m_messages.last().toMap();
        last["content"] = last["content"].toString() + token;
        m_messages.last() = last;
    }
    emit messagesChanged();
}
