#include "settingsmanager.h"
#include "apiservice.h"

#include <QFileInfo>
#include <QFile>

SettingsManager::SettingsManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::knowledgeDocsLoaded, this, [this](QVariantList docs) {
        m_knowledgeDocs = docs;
        emit knowledgeDocsChanged();
    });
    connect(&api, &ApiService::knowledgeDocUploaded, this, [this](int) {
        if (m_currentUserId > 0)
            ApiService::instance().loadKnowledgeDocs(m_currentUserId);
    });
    connect(&api, &ApiService::knowledgeDocDeleted, this, [this](bool) {
        if (m_currentUserId > 0)
            ApiService::instance().loadKnowledgeDocs(m_currentUserId);
    });
}

// ── 服务器地址配置（通过 ConfigManager 读写 QSettings）──

QString SettingsManager::backendIp() const
{
    return ConfigManager::getBackendIP();
}

void SettingsManager::setBackendIp(const QString &ip)
{
    ConfigManager::setBackendIP(ip);
    emit backendIpChanged();
}

int SettingsManager::backendPort() const
{
    return ConfigManager::getBackendPort();
}

void SettingsManager::setBackendPort(int port)
{
    ConfigManager::setBackendPort(port);
    emit backendPortChanged();
}

void SettingsManager::saveServerConfig(const QString &ip, int port)
{
    ConfigManager::setBackendIP(ip);
    ConfigManager::setBackendPort(port);
    // LiveTalking 自动跟随：同一 IP，8010 端口
    ConfigManager::setLiveTalkingHost(ip);
    ConfigManager::setLiveTalkingPort(8010);
    ApiService::instance().refreshServerUrl();
    emit serverConfigSaved();
}

QVariantList SettingsManager::knowledgeDocs() const
{
    return m_knowledgeDocs;
}

QVariantMap SettingsManager::userInfo() const
{
    return m_userInfo;
}

void SettingsManager::loadSettings(int userId)
{
    m_currentUserId = userId;
    ApiService::instance().loadKnowledgeDocs(userId);
}

void SettingsManager::uploadKnowledgeDoc(int userId, const QString &filePath)
{
    QFileInfo fi(filePath);
    if (!fi.exists())
        return;

    QFile file(filePath);
    QString content;
    if (file.open(QIODevice::ReadOnly))
        content = QString::fromUtf8(file.readAll());
    file.close();

    ApiService::instance().uploadKnowledgeDoc(userId, fi.fileName(), filePath, content);
}

void SettingsManager::deleteKnowledgeDoc(int docId)
{
    ApiService::instance().deleteKnowledgeDoc(docId);
}

void SettingsManager::logout()
{
    emit logoutRequested();
}

void SettingsManager::openDataDashboard()
{
    emit openDataDashboardRequested();
}
