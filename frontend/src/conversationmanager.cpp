#include "conversationmanager.h"
#include "apiservice.h"

#include <algorithm>
#include <QDateTime>
#include <QDebug>

ConversationManager::ConversationManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
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
            ApiService::instance().sendAiMessage(m_currentConversationId, msgText, m_responseType);
        } else if (!m_pendingVoiceFilePath.isEmpty()) {
            QString filePath = m_pendingVoiceFilePath;
            m_pendingVoiceFilePath.clear();
            qDebug() << "ConversationManager: 对话创建完成，发送暂存语音:" << filePath;
            ApiService::instance().sendVoiceMessage(m_currentConversationId, filePath, m_responseType);
        }

        emit messagesChanged();
    });
    connect(&api, &ApiService::conversationsLoaded, this, [this](QVariantList convs) {
        m_conversations = convs;
        emit conversationsChanged();

        if (m_autoLoadPending) {
            m_autoLoadPending = false;
            if (!convs.isEmpty()) {
                QVariantMap first = convs.first().toMap();
                int convId = first["id"].toInt();
                loadConversation(convId);
            } else {
                startNewConversation(m_currentUserId, QStringLiteral("新对话"));
            }
        }
    });

    connect(&api, &ApiService::wsTokenReceived, this, [this](int conversationId, const QString &token) {
        if (conversationId != m_currentConversationId)
            return;
        updateLastAiMessageContent(token);
    });
    connect(&api, &ApiService::wsSentenceReceived, this, [this](int conversationId, const QString &sentence) {
        if (conversationId != m_currentConversationId)
            return;
        m_currentSentence = sentence;
        emit currentSentenceChanged();
    });
    connect(&api, &ApiService::wsDoneReceived, this, [this](int conversationId, int, const QString &, const QString &audioUrl) {
        if (conversationId != m_currentConversationId)
            return;
        m_streaming = false;
        emit streamingAiResponseChanged();
        if (!audioUrl.isEmpty()) {
            setCurrentAudioUrl(audioUrl);
        }
        setTtsPending(false);
        // 不清除 currentSentence，让字幕在数字人播报期间持续显示
        emit messagesChanged();
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
    });
    connect(&api, &ApiService::wsError, this, [this](const QString &msg) {
        m_streaming = false;
        emit streamingAiResponseChanged();
        emit errorOccurred(msg);
    });
    connect(&api, &ApiService::voiceTranscribedText, this, [this](int conversationId, const QString &text) {
        if (conversationId != m_currentConversationId)
            return;
        appendMessage("user", text);
    });
    connect(&api, &ApiService::voiceTokenReceived, this, [this](int conversationId, const QString &token) {
        if (conversationId != m_currentConversationId)
            return;
        updateLastAiMessageContent(token);
    });
    connect(&api, &ApiService::voiceDoneReceived, this, [this](int conversationId, int, const QString &, const QString &audioUrl) {
        if (conversationId != m_currentConversationId)
            return;
        m_streaming = false;
        emit streamingAiResponseChanged();
        if (!audioUrl.isEmpty()) {
            setCurrentAudioUrl(audioUrl);
        }
        setTtsPending(false);
        // 不清除 currentSentence，让字幕在数字人播报期间持续显示
        emit messagesChanged();
        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
        }
    });
    connect(&api, &ApiService::voiceError, this, [this](const QString &msg) {
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

    connect(&api, &ApiService::sentenceAudioReceived,
            this, &ConversationManager::enqueueSentenceAudio);
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

    clearAudioQueue();

    if (m_pendingNewConversation) {
        m_pendingMessages.append(text.trimmed());
        appendMessage("user", text.trimmed());
        emit messageSending();
        return;
    }

    if (m_currentConversationId <= 0)
        return;

    emit messageSending();

    appendMessage("user", text.trimmed());

    ApiService::instance().sendAiMessage(m_currentConversationId, text.trimmed(), m_responseType);
}

void ConversationManager::sendVoiceMessage(const QString &audioFilePath)
{
    clearAudioQueue();

    if (m_pendingNewConversation) {
        m_pendingVoiceFilePath = audioFilePath;
        emit messageSending();
        return;
    }

    if (m_currentConversationId <= 0) {
        qDebug() << "ConversationManager::sendVoiceMessage: 无有效对话，丢弃语音";
        return;
    }

    emit messageSending();

    qDebug() << "ConversationManager::sendVoiceMessage: 发送语音到对话" << m_currentConversationId;
    ApiService::instance().sendVoiceMessage(m_currentConversationId, audioFilePath, m_responseType);
}

void ConversationManager::loadConversation(int conversationId)
{
    m_pendingNewConversation = false;
    m_pendingMessages.clear();
    clearAudioQueue();
    m_currentConversationId = conversationId;
    m_messages.clear();
    m_currentAudioUrl.clear();
    m_ttsPending = false;
    m_streaming = false;
    m_currentSentence.clear();
    emit messagesChanged();
    emit streamingAiResponseChanged();
    emit currentAudioUrlChanged();
    emit ttsPendingChanged();
    ApiService::instance().loadMessages(conversationId);
    emit currentConversationChanged();
}

int ConversationManager::startNewConversation(int userId, const QString &title, int knowledgeDocId)
{
    m_currentUserId = userId;
    m_currentTitle = title;
    m_currentConversationId = -1;
    m_pendingNewConversation = true;
    m_autoLoadPending = false;
    m_pendingKnowledgeDocId = knowledgeDocId;
    m_pendingVoiceFilePath.clear();
    clearAudioQueue();
    m_messages.clear();
    emit currentConversationChanged();
    emit messagesChanged();

    // 立即在后端创建空对话记录，使其出现在对话列表中
    ApiService::instance().createConversation(userId, title, knowledgeDocId);

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
    m_autoLoadPending = false;
    m_pendingMessages.clear();
    m_pendingVoiceFilePath.clear();
    clearAudioQueue();
    m_currentAudioUrl.clear();
    m_ttsPending = false;
    m_currentSentence.clear();
    emit streamingAiResponseChanged();
    emit currentConversationChanged();
    emit messagesChanged();
    emit currentAudioUrlChanged();
    emit ttsPendingChanged();
    emit currentSentenceChanged();
}

void ConversationManager::loadConversationList(int userId)
{
    ApiService::instance().loadConversations(userId);
}

void ConversationManager::autoLoadOrCreateConversation(int userId)
{
    m_currentUserId = userId;
    m_autoLoadPending = true;
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
    if (role == "user") {
        m_currentAudioUrl.clear();
        m_ttsPending = false;
        m_currentSentence.clear();
        emit currentAudioUrlChanged();
        emit ttsPendingChanged();
        emit currentSentenceChanged();
    }
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
        setTtsPending(true);
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

QString ConversationManager::currentAudioUrl() const
{
    return m_currentAudioUrl;
}

bool ConversationManager::ttsPending() const
{
    return m_ttsPending;
}

QString ConversationManager::currentSentence() const
{
    return m_currentSentence;
}

bool ConversationManager::playbackActive() const
{
    return m_playbackActive;
}

void ConversationManager::setResponseType(int type)
{
    m_responseType = type;
}

void ConversationManager::setCurrentAudioUrl(const QString &url)
{
    if (m_currentAudioUrl != url) {
        m_currentAudioUrl = url;
        emit currentAudioUrlChanged();
    }
}

void ConversationManager::setTtsPending(bool pending)
{
    if (m_ttsPending != pending) {
        m_ttsPending = pending;
        emit ttsPendingChanged();
    }
}

void ConversationManager::enqueueSentenceAudio(int conversationId, int index,
    const QString &text, const QString &audioFilename, double duration)
{
    if (conversationId != m_activeConversationId && m_activeConversationId != 0) {
        clearAudioQueue();
    }
    m_activeConversationId = conversationId;

    SentenceAudioItem item{index, text, audioFilename, duration};
    m_audioQueue.append(item);

    std::sort(m_audioQueue.begin(), m_audioQueue.end(),
              [](const SentenceAudioItem &a, const SentenceAudioItem &b) {
                  return a.index < b.index;
              });

    qDebug() << "SentenceAudioQueue: enqueued index=" << index
             << "audio=" << audioFilename << "duration=" << duration;

    // 有待播放的句子且当前未在播放 → 立即启动
    if (m_currentAudioIndex < m_audioQueue.size() && !m_playbackActive) {
        playNextSentence();
    }
}

void ConversationManager::playNextSentence()
{
    if (m_currentAudioIndex >= m_audioQueue.size()) {
        qDebug() << "SentenceAudioQueue: queue exhausted, waiting for more sentences";
        m_playbackActive = false;
        return;
    }

    if (!m_playbackActive) {
        m_playbackActive = true;
        emit playbackActiveChanged();
    }

    const SentenceAudioItem &item = m_audioQueue.at(m_currentAudioIndex);
    qDebug() << "SentenceAudioQueue: playing index=" << item.index
             << "audio=" << item.audioFilename;

    ApiService::instance().playAudio(m_activeConversationId, item.audioFilename);

    int delayMs = static_cast<int>((item.duration + 0.05) * 1000);
    m_currentAudioIndex++;
    QTimer::singleShot(delayMs, this, &ConversationManager::playNextSentence);
}

void ConversationManager::clearAudioQueue()
{
    m_audioQueue.clear();
    m_currentAudioIndex = 0;
    m_activeConversationId = 0;
    if (m_playbackActive) {
        m_playbackActive = false;
        emit playbackActiveChanged();
    }
    qDebug() << "SentenceAudioQueue: cleared";
}
