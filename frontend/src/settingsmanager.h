#ifndef SETTINGSMANAGER_H
#define SETTINGSMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class SettingsManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList digitalHumans READ digitalHumans NOTIFY digitalHumansChanged)
    Q_PROPERTY(int currentDigitalHumanId READ currentDigitalHumanId NOTIFY currentDigitalHumanChanged)
    Q_PROPERTY(QVariantList knowledgeDocs READ knowledgeDocs NOTIFY knowledgeDocsChanged)
    Q_PROPERTY(QVariantMap userInfo READ userInfo NOTIFY userInfoChanged)
public:
    explicit SettingsManager(QObject *parent = nullptr);

    QVariantList digitalHumans() const;
    int currentDigitalHumanId() const;
    QVariantList knowledgeDocs() const;
    QVariantMap userInfo() const;

    Q_INVOKABLE void loadSettings(int userId);
    Q_INVOKABLE void switchDigitalHuman(int dhId);
    Q_INVOKABLE void uploadKnowledgeDoc(int userId, const QString &filePath);
    Q_INVOKABLE void deleteKnowledgeDoc(int docId);
    Q_INVOKABLE void logout();
    Q_INVOKABLE void openDataDashboard();

signals:
    void digitalHumansChanged();
    void currentDigitalHumanChanged();
    void knowledgeDocsChanged();
    void userInfoChanged();
    void logoutRequested();
    void openDataDashboardRequested();

private:
    QVariantList m_digitalHumans;
    int m_currentDigitalHumanId = -1;
    QVariantList m_knowledgeDocs;
    QVariantMap m_userInfo;
    int m_currentUserId = -1;
};

#endif // SETTINGSMANAGER_H
