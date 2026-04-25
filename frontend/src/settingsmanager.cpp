#include "settingsmanager.h"
#include "apiservice.h"

#include <QFileInfo>
#include <QFile>

SettingsManager::SettingsManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::digitalHumansLoaded, this, [this](QVariantList digitalHumans) {
        m_digitalHumans = digitalHumans;
        for (const auto &dh : m_digitalHumans) {
            QVariantMap dhm = dh.toMap();
            if (dhm["isDefault"].toBool()) {
                m_currentDigitalHumanId = dhm["id"].toInt();
                break;
            }
        }
        emit digitalHumansChanged();
        emit currentDigitalHumanChanged();
    });
    connect(&api, &ApiService::defaultDigitalHumanSet, this, [this](bool) {
        ApiService::instance().loadDigitalHumans();
    });
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

QVariantList SettingsManager::digitalHumans() const
{
    return m_digitalHumans;
}

int SettingsManager::currentDigitalHumanId() const
{
    return m_currentDigitalHumanId;
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
    ApiService::instance().loadDigitalHumans();
    ApiService::instance().loadKnowledgeDocs(userId);
}

void SettingsManager::switchDigitalHuman(int dhId)
{
    m_currentDigitalHumanId = dhId;
    emit currentDigitalHumanChanged();
    ApiService::instance().setDefaultDigitalHuman(dhId);
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
