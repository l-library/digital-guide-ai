#ifndef APISERVICE_H
#define APISERVICE_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QWebSocket>

#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSettings>

// 读取配置文件。优先级：QSettings（用户运行时设置）> config.json（打包默认）> 硬编码默认值。
// setter 方法写入 QSettings，跨平台持久化（桌面端写 INI/注册表，Android 写 SharedPreferences）。
class ConfigManager
{
public:
    // ── Backend IP ──
    static QString getBackendIP()
    {
        QSettings settings;
        if (settings.contains("backend/ip"))
            return settings.value("backend/ip").toString();

        QFile file("config.json");
        if (file.open(QIODevice::ReadOnly)) {
            QJsonObject obj = QJsonDocument::fromJson(file.readAll()).object();
            QString ip = obj["backend"].toObject()["ip"].toString();
            if (!ip.isEmpty()) return ip;
        }
        return "http://localhost";
    }
    static void setBackendIP(const QString &ip)
    {
        QSettings settings;
        settings.setValue("backend/ip", ip);
    }

    // ── Backend Port ──
    static int getBackendPort()
    {
        QSettings settings;
        if (settings.contains("backend/port"))
            return settings.value("backend/port").toInt();

        QFile file("config.json");
        if (file.open(QIODevice::ReadOnly)) {
            QJsonObject obj = QJsonDocument::fromJson(file.readAll()).object();
            int port = obj["backend"].toObject()["port"].toInt();
            if (port > 0) return port;
        }
        return 8000;
    }
    static void setBackendPort(int port)
    {
        QSettings settings;
        settings.setValue("backend/port", port);
    }

    // ── LiveTalking Host ──
    static QString getLiveTalkingHost()
    {
        QSettings settings;
        if (settings.contains("livetalking/host"))
            return settings.value("livetalking/host").toString();

        // 无独立配置时，复用后端 IP
        return getBackendIP();
    }
    static void setLiveTalkingHost(const QString &host)
    {
        QSettings settings;
        settings.setValue("livetalking/host", host);
    }

    // ── LiveTalking Port ──
    static int getLiveTalkingPort()
    {
        QSettings settings;
        if (settings.contains("livetalking/port"))
            return settings.value("livetalking/port").toInt();

        return 8010; // 默认端口
    }
    static void setLiveTalkingPort(int port)
    {
        QSettings settings;
        settings.setValue("livetalking/port", port);
    }
};

class ApiService : public QObject
{
    Q_OBJECT
public:
    static ApiService &instance();

    // 刷新服务器配置（QSettings 变更后调用，重建 BASE_URL）
    Q_INVOKABLE void refreshServerUrl();

    // Auth
    void login(const QString &username, const QString &password);
    void checkAutoLogin(const QString &token, int userId);
    void logout(int userId);
    void validateToken(const QString &token, int userId);
    void registerUser(const QString &username, const QString &password,
                      const QString &confirmPassword, const QString &displayName);
    void updateUserProfile(int userId, const QString &displayName, const QString &avatarUrl);
    void changeUserPassword(int userId, const QString &oldPassword, const QString &newPassword);

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
    void sendChatViaWebSocket(int conversationId, const QString &content, int digitalHumanId = 0, int responseType = 0);

    // Voice streaming (upload audio + parse SSE)
    void sendVoiceMessage(int conversationId, const QString &audioFilePath, int digitalHumanId = 0, int responseType = 1);

    // Knowledge docs
    void uploadKnowledgeDoc(int userId, const QString &title, const QString &filePath, const QString &content);
    void deleteKnowledgeDoc(int docId);
    void loadKnowledgeDocs(int userId);

    // Digital humans（数字人选择功能已移除，digital_human_id 硬编码为 1）
    void registerLiveTalkingSession(int conversationId, const QString &sessionId);

    // Settings
    void getSetting(const QString &key);
    void setSetting(const QString &key, const QString &value);

    // Export
    void exportConversation(int conversationId);

    // Admin user management
    /** 加载用户列表（分页+搜索）：GET /api/v1/admin/users */
    void loadUsers(int page, int pageSize, const QString &search);
    /** 创建新用户：POST /api/v1/admin/users */
    void createUser(const QString &username, const QString &password, const QString &displayName);
    /** 更新用户信息（部分更新）：PUT /api/v1/admin/users/:id */
    void updateUser(int userId, const QVariantMap &fields);
    /** 删除用户（级联删除）：DELETE /api/v1/admin/users/:id */
    void deleteUser(int userId);
    /** 切换用户启用/禁用状态：PUT /api/v1/admin/users/:id/status */
    void toggleUserStatus(int userId, bool isActive);

    // Dashboard
    void loadDashboardOverview();
    void loadServiceStats(const QString &period);
    void loadHotQuestions(int top = 10);
    void loadSatisfactionTrend(const QString &period);
    void loadDashboardFull();

    // Consumption analytics
    void loadConsumptionFull();

    // Reports
    void loadVisitorInsight(const QString &startDate, const QString &endDate);
    void loadEmotionTrend(const QString &startDate, const QString &endDate);
    void loadFocusAnalysis(const QString &startDate, const QString &endDate);
    void loadServiceSuggestions(const QString &startDate, const QString &endDate);

    // Recommend
    void loadRecommendRoute(int userId);

    // Audio playback
public slots:
    void playAudio(int conversationId, const QString &audioFilename);
    void playAudioQueued(int conversationId, const QString &audioFilename);
    void flushAudio(int conversationId);

signals:
    // Auth
    void loginResult(bool success, QVariantMap userInfo, const QString &error);
    void autoLoginResult(bool loggedIn, QVariantMap userInfo);
    void logoutResult(bool success);
    void registerResult(bool success, QVariantMap userInfo, const QString &error);
    void profileUpdateResult(bool success, QVariantMap updatedUser, const QString &error);
    void passwordChangeResult(bool success, const QString &error);

    // Conversations
    void conversationCreated(int conversationId);
    void conversationsLoaded(QVariantList conversations);
    void conversationsGroupedLoaded(QVariantList grouped);
    void conversationDeleted(bool success);
    void conversationRenamed(int conversationId, const QString &newTitle);
    void titleAutoUpdated(int conversationId, const QString &newTitle);
    void messagesLoaded(QVariantList messages, int conversationId);
    void messageAdded(int messageId, int conversationId);
    void aiResponseReceived(int conversationId, const QString &response, const QString &role);

    // WebSocket streaming
    void wsConnected();
    void wsDisconnected();
    void wsTokenReceived(int conversationId, const QString &token);
    void wsSentenceReceived(int conversationId, const QString &sentence);
    void wsDoneReceived(int conversationId, int messageId, const QString &fullContent, const QString &audioUrl);
    void wsError(const QString &message);

    // Voice streaming SSE
    void voiceTranscribedText(int conversationId, const QString &text);
    void voiceTokenReceived(int conversationId, const QString &token);
    void voiceDoneReceived(int conversationId, int messageId, const QString &fullContent, const QString &audioUrl);
    void voiceError(const QString &message);

    // Knowledge docs
    void knowledgeDocUploaded(int docId);
    void knowledgeDocDeleted(bool success);
    void knowledgeDocsLoaded(QVariantList docs);

    // Digital humans（选择功能已移除）

    // Settings
    void settingLoaded(const QString &key, const QString &value);
    void settingSaved(bool success);

    // Export
    void conversationExported(int conversationId, QVariantMap data);

    // Sentence audio
    void sentenceAudioReceived(int conversationId, int index, const QString &text,
                                const QString &audioFilename, double duration);

    // Admin user management
    void usersLoaded(QVariantList users, int total, int page, int pageSize);
    void userCreated(int userId, const QVariantMap &userData);
    void userUpdated(int userId, const QVariantMap &userData);
    void userDeleted(int userId);
    void userStatusChanged(int userId, bool isActive);
    void adminError(const QString &error);

    // Dashboard
    void dashboardOverviewLoaded(const QVariantMap &data);
    void serviceStatsLoaded(const QString &period, const QVariantList &stats);
    void hotQuestionsLoaded(const QVariantList &items);
    void satisfactionTrendLoaded(const QString &period, const QVariantList &trend);
    void dashboardFullLoaded(const QVariantMap &data);

    // Consumption analytics
    void consumptionFullLoaded(const QVariantMap &data);

    // Reports
    void visitorInsightLoaded(const QVariantMap &data);
    void emotionTrendLoaded(const QVariantMap &data);
    void focusAnalysisLoaded(const QVariantMap &data);
    void serviceSuggestionsLoaded(const QVariantMap &data);

    // Recommend
    void recommendRouteLoaded(const QVariantMap &route);

    // Error
    void apiError(const QString &error);

private:
    explicit ApiService(QObject *parent = nullptr);
    ~ApiService() = default;
    ApiService(const ApiService &) = delete;
    ApiService &operator=(const ApiService &) = delete;

    QNetworkAccessManager *m_networkManager;
    QString m_authToken;
    QWebSocket *m_webSocket;
    QNetworkReply *m_streamReply = nullptr;
    QNetworkReply *m_voiceStreamReply = nullptr;
    QByteArray m_sseBuffer;
    QByteArray m_voiceSseBuffer;

    // 数字人选择功能已移除
    void initStubData();
    QVariantList mapMessagesToFrontendFormat(const QVariantList &items) const;
};

#endif // APISERVICE_H
