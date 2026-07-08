#ifndef CONVERSATIONMANAGER_H
#define CONVERSATIONMANAGER_H

#include <QObject>
#include <QList>
#include <QTimer>
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
    Q_PROPERTY(QString currentAudioUrl READ currentAudioUrl NOTIFY currentAudioUrlChanged)
    Q_PROPERTY(bool ttsPending READ ttsPending NOTIFY ttsPendingChanged)
    Q_PROPERTY(QString currentSentence READ currentSentence NOTIFY currentSentenceChanged)
    Q_PROPERTY(bool playbackActive READ playbackActive NOTIFY playbackActiveChanged)
public:
    explicit ConversationManager(QObject *parent = nullptr);

    int currentConversationId() const;
    QVariantList messages() const;
    QVariantList conversations() const;
    QString currentTitle() const;
    bool hasConversation() const;
    bool streamingAiResponse() const;
    QString currentAudioUrl() const;
    bool ttsPending() const;
    QString currentSentence() const;
    bool playbackActive() const;

    Q_INVOKABLE void sendMessage(const QString &text);
    Q_INVOKABLE void sendVoiceMessage(const QString &audioFilePath);
    Q_INVOKABLE void loadConversation(int conversationId);
    Q_INVOKABLE int startNewConversation(int userId, const QString &title, int knowledgeDocId = -1);
    Q_INVOKABLE void clearCurrentConversation();
    Q_INVOKABLE void loadConversationList(int userId);
    Q_INVOKABLE void autoLoadOrCreateConversation(int userId);
    Q_INVOKABLE void renameCurrentConversation(const QString &newTitle);
    Q_INVOKABLE void renameConversationById(int conversationId, const QString &newTitle);
    Q_INVOKABLE void deleteConversation(int conversationId);
    Q_INVOKABLE void connectWebSocket();
    Q_INVOKABLE void disconnectWebSocket();

    Q_INVOKABLE void setResponseType(int type);
    Q_INVOKABLE void setDigitalHumanId(int id);

    Q_INVOKABLE void playNextSentence();
    Q_INVOKABLE void clearAudioQueue();

public slots:
    void enqueueSentenceAudio(int conversationId, int index, const QString &text,
                               const QString &audioFilename, double duration);
    // 由 LiveTalking 的 speakingFinished 信号触发，或由 watchdog 兜底推进。
    // 内部用 m_pendingPlaybackConfirm 做去重，避免双推进跳句。
    void advancePlayback();
    // 由 LiveTalking 的 speakingStarted 信号触发（eventpoint==1）。
    // 此时当前句的音频 chunk 已在 LiveTalking 的 FIFO 队列中，
    // 可以安全预推送下一句（不会乱序）。
    void onCurrentSentenceStarted();

signals:
    void currentConversationChanged();
    void messagesChanged();
    void conversationsChanged();
    void streamingAiResponseChanged();
    void messageSending();
    void errorOccurred(const QString &error);
    void currentAudioUrlChanged();
    void ttsPendingChanged();
    void currentSentenceChanged();
    void allSentencesPlayed();
    void playbackActiveChanged();
    void playbackSentenceReady(const QString &sentence);

private:
    struct SentenceAudioItem {
        int index;
        QString text;
        QString audioFilename;
        double duration;
    };

    int m_currentConversationId = -1;
    QVariantList m_messages;
    QVariantList m_conversations;
    QString m_currentTitle;
    int m_currentUserId = -1;
    int m_responseType = 1;
    int m_digitalHumanId = 1;
    bool m_streaming = false;
    bool m_pendingNewConversation = false;
    bool m_autoLoadPending = false;
    int m_pendingKnowledgeDocId = -1;
    QStringList m_pendingMessages;
    QString m_pendingVoiceFilePath;
    QString m_currentAudioUrl;
    bool m_ttsPending = false;
    QString m_currentSentence;

    QList<SentenceAudioItem> m_audioQueue;
    int m_currentAudioIndex = 0;
    int m_activeConversationId = 0;
    bool m_playbackActive = false;

    // 逐句播放的兜底定时器：在 LiveTalking 未回报 speakingFinished 时
    // 按 duration+5s 主动推进，避免永远卡死。
    QTimer m_playbackWatchdog;
    // 当前是否在等待 LiveTalking 回报本句播完；
    // 任何一路（finished / watchdog）先到即推进，后到者被忽略。
    bool m_pendingPlaybackConfirm = false;

    // 预推送：当下一句音频入队时，如果当前句已在 LiveTalking 中播放（eventpoint==1 已收到），
    // 立即推送给 LiveTalking。LiveTalking 的 FIFO 队列保证预推送的音频排在当前句后。
    // 必须等 eventpoint==1 后才预推送，否则当前句的 HTTP 请求可能还没到达 LiveTalking，
    // 导致预推送的音频排到当前句前面（HTTP 竞态乱序）。
    int m_prePushedIndex = -1;  // 已预推送的句子 index，-1 表示无
    bool m_currentSentencePlaying = false;  // eventpoint==1 已收到，当前句在 LiveTalking 中播放

    void appendMessage(const QString &role, const QString &content);
    void updateLastAiMessageContent(const QString &token);
    void setCurrentAudioUrl(const QString &url);
    void setTtsPending(bool pending);
};

#endif // CONVERSATIONMANAGER_H
