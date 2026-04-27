#ifndef HISTORYMANAGER_H
#define HISTORYMANAGER_H

#include <QObject>
#include <QVariantList>

class HistoryManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList groupedConversations READ groupedConversations NOTIFY historyChanged)
    Q_PROPERTY(bool loading READ loading NOTIFY loadingChanged)
public:
    explicit HistoryManager(QObject *parent = nullptr);

    QVariantList groupedConversations() const;
    bool loading() const;

    Q_INVOKABLE void loadHistory(int userId);
    Q_INVOKABLE void deleteConversation(int conversationId);
    Q_INVOKABLE bool exportConversation(int conversationId, const QString &filePath);
    Q_INVOKABLE void restoreConversation(int conversationId);
    Q_INVOKABLE void search(int userId, const QString &query);

signals:
    void historyChanged();
    void loadingChanged();
    void operationFailed(const QString &error);

public slots:
    void refresh(int userId);

private:
    QVariantList m_groupedConversations;
    bool m_loading = false;
    QVariantList m_allConversations;
    int m_currentUserId = -1;
};

#endif // HISTORYMANAGER_H
