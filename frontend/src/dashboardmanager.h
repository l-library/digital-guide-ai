#ifndef DASHBOARDMANAGER_H
#define DASHBOARDMANAGER_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

class DashboardManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap overview READ overview NOTIFY overviewChanged)
    Q_PROPERTY(QVariantList serviceStats READ serviceStats NOTIFY serviceStatsChanged)
    Q_PROPERTY(QVariantList hotQuestions READ hotQuestions NOTIFY hotQuestionsChanged)
    Q_PROPERTY(QVariantList satisfactionTrend READ satisfactionTrend NOTIFY satisfactionTrendChanged)
    Q_PROPERTY(bool isLoading READ isLoading NOTIFY loadingChanged)

public:
    explicit DashboardManager(QObject *parent = nullptr);

    QVariantMap overview() const;
    QVariantList serviceStats() const;
    QVariantList hotQuestions() const;
    QVariantList satisfactionTrend() const;
    bool isLoading() const;

    Q_INVOKABLE void loadAll();

signals:
    void overviewChanged();
    void serviceStatsChanged();
    void hotQuestionsChanged();
    void satisfactionTrendChanged();
    void loadingChanged();
    void dashboardError(const QString &error);

private:
    QVariantMap m_overview;
    QVariantList m_serviceStats;
    QVariantList m_hotQuestions;
    QVariantList m_satisfactionTrend;
    bool m_isLoading = false;

    void setLoading(bool loading);
};

#endif // DASHBOARDMANAGER_H
