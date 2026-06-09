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

QVariantList SettingsManager::knowledgeDocs() const
{
    return m_knowledgeDocs;
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
