#ifndef SETTINGSMANAGER_H
#define SETTINGSMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class SettingsManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList knowledgeDocs READ knowledgeDocs NOTIFY knowledgeDocsChanged)
public:
    explicit SettingsManager(QObject *parent = nullptr);

    QVariantList knowledgeDocs() const;

    Q_INVOKABLE void loadSettings(int userId);
    Q_INVOKABLE void uploadKnowledgeDoc(int userId, const QString &filePath);
    Q_INVOKABLE void deleteKnowledgeDoc(int docId);

signals:
    void knowledgeDocsChanged();

private:
    QVariantList m_knowledgeDocs;
    int m_currentUserId = -1;
};

#endif // SETTINGSMANAGER_H
