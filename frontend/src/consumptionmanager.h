#ifndef CONSUMPTIONMANAGER_H
#define CONSUMPTIONMANAGER_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

/**
 * 消费分析数据管理器
 *
 * 与 DashboardManager 同构：监听 ApiService 的消费分析相关信号，
 * 通过 Q_PROPERTY 把数据暴露给 QML，加载入口是 loadAll()（调用 ApiService::loadConsumptionFull）。
 */
class ConsumptionManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap overview READ overview NOTIFY overviewChanged)
    Q_PROPERTY(QVariantList revenueTrend READ revenueTrend NOTIFY revenueTrendChanged)
    Q_PROPERTY(QVariantMap categoryBreakdown READ categoryBreakdown NOTIFY categoryBreakdownChanged)
    Q_PROPERTY(QVariantMap demographics READ demographics NOTIFY demographicsChanged)
    Q_PROPERTY(bool isLoading READ isLoading NOTIFY loadingChanged)

public:
    explicit ConsumptionManager(QObject *parent = nullptr);

    QVariantMap overview() const;
    QVariantList revenueTrend() const;
    QVariantMap categoryBreakdown() const;
    QVariantMap demographics() const;
    bool isLoading() const;

    Q_INVOKABLE void loadAll();

signals:
    void overviewChanged();
    void revenueTrendChanged();
    void categoryBreakdownChanged();
    void demographicsChanged();
    void loadingChanged();
    void consumptionError(const QString &error);

private:
    QVariantMap m_overview;
    QVariantList m_revenueTrend;
    QVariantMap m_categoryBreakdown;
    QVariantMap m_demographics;
    bool m_isLoading = false;

    void setLoading(bool loading);
};

#endif // CONSUMPTIONMANAGER_H