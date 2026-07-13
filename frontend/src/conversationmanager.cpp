#include "conversationmanager.h"
#include "apiservice.h"

#include <algorithm>
#include <QDateTime>
#include <QDebug>

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
            ApiService::instance().sendAiMessage(m_currentConversationId, msgText, m_digitalHumanId, m_responseType);
        } else if (!m_pendingVoiceFilePath.isEmpty()) {
            QString filePath = m_pendingVoiceFilePath;
            m_pendingVoiceFilePath.clear();
            ApiService::instance().sendVoiceMessage(m_currentConversationId, filePath, m_digitalHumanId, m_responseType);
        }

        if (m_currentUserId > 0) {
            loadConversationList(m_currentUserId);
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
                int messageCount = first["message_count"].toInt();
                if (messageCount == 0) {
                    // 最新对话为空 → 复用，避免创建重复空对话
                    int convId = first["id"].toInt();
                    loadConversation(convId);
                } else {
                    // 最新对话有消息 → 新建
                    startNewConversation(m_currentUserId, QStringLiteral("新对话"));
                }
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
    connect(&api, &ApiService::conversationDeleted, this, [this](bool success) {
        if (!success) {
            emit errorOccurred(QStringLiteral("删除对话失败"));
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

    // 兜底定时器：若 LiveTalking 未在 duration+5s 内回报本句播完，主动推进
    // 用 5s 而非 3s 余量，避免长句场景下看门狗与 eventpoint==2 竞争
    m_playbackWatchdog.setSingleShot(true);
    connect(&m_playbackWatchdog, &QTimer::timeout,
            this, &ConversationManager::advancePlayback);

    // 预推送定时器：延迟到当前句剩 ~2s 时推送给 LiveTalking
    // 避免立即推送导致的 GPU 争用（口型网络同时推理两句 → 视频卡顿）
    m_prePushTimer.setSingleShot(true);
    connect(&m_prePushTimer, &QTimer::timeout, this, [this]() {
        if (m_currentAudioIndex >= m_audioQueue.size()) return;
        if (m_prePushedIndex == m_currentAudioIndex) return;
        const SentenceAudioItem &nextItem = m_audioQueue.at(m_currentAudioIndex);
        ApiService::instance().playAudioQueued(m_activeConversationId, nextItem.audioFilename);
        m_prePushedIndex = m_currentAudioIndex;
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

    ApiService::instance().sendAiMessage(m_currentConversationId, text.trimmed(), m_digitalHumanId, m_responseType);
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
        return;
    }

    emit messageSending();

    ApiService::instance().sendVoiceMessage(m_currentConversationId, audioFilePath, m_digitalHumanId, m_responseType);
}

void ConversationManager::loadConversation(int conversationId)
{
    m_pendingNewConversation = false;
    if (!ApiService::instance().isWebSocketConnected()) {
        ApiService::instance().connectWebSocket();
    }
    m_pendingMessages.clear();
    clearAudioQueue();
    m_currentConversationId = conversationId;
    // 切换对话时同步更新标题：从已加载的对话列表中查找匹配项的 title，
    // 否则状态栏会停留在上一个对话的标题，直到后端回报 titleAutoUpdated。
    m_currentTitle.clear();
    for (const auto &v : m_conversations) {
        const QVariantMap cm = v.toMap();
        if (cm.value(QStringLiteral("id")).toInt() == conversationId) {
            m_currentTitle = cm.value(QStringLiteral("title")).toString();
            break;
        }
    }
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
    // 如果当前对话为空（无消息），静默复用，避免创建重复空对话
    if (m_currentConversationId > 0 && m_messages.isEmpty()) {
        m_currentUserId = userId;
        m_currentTitle = title;
        m_pendingKnowledgeDocId = knowledgeDocId;
        m_pendingVoiceFilePath.clear();
        clearAudioQueue();
        emit currentConversationChanged();
        return m_currentConversationId;
    }

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
    if (!ApiService::instance().isWebSocketConnected()) {
        ApiService::instance().connectWebSocket();
    }
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

void ConversationManager::deleteConversation(int conversationId)
{
    ApiService::instance().deleteConversation(conversationId);
    for (int i = 0; i < m_conversations.size(); ++i) {
        if (m_conversations[i].toMap()["id"].toInt() == conversationId) {
            m_conversations.removeAt(i);
            emit conversationsChanged();
            break;
        }
    }
    if (conversationId == m_currentConversationId) {
        int savedUserId = m_currentUserId;
        clearCurrentConversation();
        m_currentUserId = savedUserId;
        if (!m_conversations.isEmpty()) {
            int firstId = m_conversations.first().toMap()["id"].toInt();
            loadConversation(firstId);
        } else {
            startNewConversation(m_currentUserId, QStringLiteral("新对话"));
        }
    }
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

    // 有待播放的句子且当前未在播放 → 立即启动
    if (m_currentAudioIndex < m_audioQueue.size() && !m_playbackActive) {
        playNextSentence();
    } else if (m_playbackActive && m_pendingPlaybackConfirm && m_currentSentencePlaying
               && m_currentAudioIndex < m_audioQueue.size()
               && m_prePushedIndex != m_currentAudioIndex) {
        // 当前句已在 LiveTalking 中播放（eventpoint==1 已收到），
        // 下一句刚入队 → 计算剩余时间，决定立即推送还是延迟推送
        const SentenceAudioItem &nextItem = m_audioQueue.at(m_currentAudioIndex);
        const int playingIdx = m_currentAudioIndex - 1;
        if (playingIdx >= 0 && playingIdx < m_audioQueue.size()) {
            const qint64 elapsed = QDateTime::currentMSecsSinceEpoch() - m_currentPlaybackStartMs;
            const qint64 totalMs = static_cast<qint64>(m_audioQueue.at(playingIdx).duration * 1000);
            const qint64 remainingMs = totalMs - elapsed;
            const qint64 prePushDelayMs = remainingMs - 2000;

            if (prePushDelayMs > 300) {
                // 剩余时间充足（>2.3s），延迟预推送
                if (!m_prePushTimer.isActive()) {
                    m_prePushTimer.start(static_cast<int>(prePushDelayMs));
                }
            } else {
                // 剩余时间不多（≤2.3s），立即预推送
                ApiService::instance().playAudioQueued(m_activeConversationId, nextItem.audioFilename);
                m_prePushedIndex = m_currentAudioIndex;
                m_prePushTimer.stop();
            }
        }
    }
}

void ConversationManager::playNextSentence()
{
    if (m_currentAudioIndex >= m_audioQueue.size()) {
        m_playbackActive = false;
        emit playbackActiveChanged();
        emit allSentencesPlayed();
        return;
    }

    if (!m_playbackActive) {
        m_playbackActive = true;
        emit playbackActiveChanged();
    }

    // 用拷贝避免后续队列变动导致引用失效
    const SentenceAudioItem item = m_audioQueue.at(m_currentAudioIndex);
    // 如果本句已被预推送，不重复发送音频文件，改为通知 LiveTalking
    // 将待处理队列中的下一句推入推理管道（flush）
    if (m_prePushedIndex != item.index) {
        ApiService::instance().playAudio(m_activeConversationId, item.audioFilename);
    } else {
        ApiService::instance().flushAudio(m_activeConversationId);
    }

    m_currentAudioIndex++;
    // 标记「等待本句播完」，由 LiveTalking 的 speakingFinished 或 watchdog 推进
    m_pendingPlaybackConfirm = true;

    // 兜底超时：duration + 5s 余量，覆盖 LiveTalking 处理延迟 + 起播抖动
    // 用 5s 而非 3s，避免长句场景下看门狗与 eventpoint==2 同时触发导致跳句
    const int watchdogMs = static_cast<int>((item.duration + 5.0) * 1000);
    m_playbackWatchdog.start(watchdogMs);
}

void ConversationManager::advancePlayback()
{
    if (!m_pendingPlaybackConfirm) {
        // 已被另一路推进过 —— 后到的 watchdog/finished 一律忽略
        return;
    }
    m_pendingPlaybackConfirm = false;
    m_currentSentencePlaying = false;
    m_playbackWatchdog.stop();
    m_prePushTimer.stop();
    playNextSentence();
}

void ConversationManager::onCurrentSentenceStarted()
{
    // eventpoint==1 收到：当前句的音频 chunk 已在 LiveTalking 的 FIFO 队列中
    m_currentSentencePlaying = true;
    m_currentPlaybackStartMs = QDateTime::currentMSecsSinceEpoch();

    // 当前句是 m_currentAudioIndex - 1（playNextSentence 已递增）
    const int playingIdx = m_currentAudioIndex - 1;
    if (playingIdx < 0 || playingIdx >= m_audioQueue.size()) return;

    const SentenceAudioItem &currentItem = m_audioQueue.at(playingIdx);
    const double prePushDelay = currentItem.duration - 2.0;

    if (prePushDelay > 0.3 && m_currentAudioIndex < m_audioQueue.size()
        && m_prePushedIndex != m_currentAudioIndex) {
        // 延迟预推送：当前句够长（>2.3s），等剩 ~2s 时再推送
        // 避免立即推送导致 LiveTalking GPU 同时推理两句口型 → 视频卡顿
        m_prePushTimer.start(static_cast<int>(prePushDelay * 1000));
    } else if (prePushDelay <= 0.3 && m_currentAudioIndex < m_audioQueue.size()
               && m_prePushedIndex != m_currentAudioIndex) {
        // 当前句较短（≤2.3s），立即预推送（无足够延迟窗口）
        const SentenceAudioItem &nextItem = m_audioQueue.at(m_currentAudioIndex);
        ApiService::instance().playAudioQueued(m_activeConversationId, nextItem.audioFilename);
        m_prePushedIndex = m_currentAudioIndex;
    }
}

void ConversationManager::clearAudioQueue()
{
    m_audioQueue.clear();
    m_currentAudioIndex = 0;
    m_activeConversationId = 0;
    m_pendingPlaybackConfirm = false;
    m_prePushedIndex = -1;
    m_currentSentencePlaying = false;
    m_currentPlaybackStartMs = 0;
    m_playbackWatchdog.stop();
    m_prePushTimer.stop();
    if (m_playbackActive) {
        m_playbackActive = false;
        emit playbackActiveChanged();
    }
}
