#ifndef SETTINGSMANAGER_H
#define SETTINGSMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class SettingsManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList knowledgeDocs READ knowledgeDocs NOTIFY knowledgeDocsChanged)
    Q_PROPERTY(QVariantMap userInfo READ userInfo NOTIFY userInfoChanged)
    Q_PROPERTY(QString backendIp READ backendIp WRITE setBackendIp NOTIFY backendIpChanged)
    Q_PROPERTY(int backendPort READ backendPort WRITE setBackendPort NOTIFY backendPortChanged)
public:
    explicit SettingsManager(QObject *parent = nullptr);

    QVariantList knowledgeDocs() const;
    QVariantMap userInfo() const;

    // 服务器地址配置（读写 QSettings，跨平台持久化）
    QString backendIp() const;
    void setBackendIp(const QString &ip);
    int backendPort() const;
    void setBackendPort(int port);

    Q_INVOKABLE void loadSettings(int userId);
    Q_INVOKABLE void uploadKnowledgeDoc(int userId, const QString &filePath);
    Q_INVOKABLE void deleteKnowledgeDoc(int docId);
    Q_INVOKABLE void logout();
    Q_INVOKABLE void openDataDashboard();
    Q_INVOKABLE void saveServerConfig(const QString &ip, int port);

signals:
    void knowledgeDocsChanged();
    void userInfoChanged();
    void logoutRequested();
    void openDataDashboardRequested();
    void backendIpChanged();
    void backendPortChanged();
    void serverConfigSaved();

private:
    QVariantList m_knowledgeDocs;
    QVariantMap m_userInfo;
    int m_currentUserId = -1;
};

#endif // SETTINGSMANAGER_H
