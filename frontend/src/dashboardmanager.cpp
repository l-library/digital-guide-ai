#include "dashboardmanager.h"
#include "apiservice.h"

/** 构造函数：连接 ApiService 的看板相关信号到本地处理逻辑 */
DashboardManager::DashboardManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();

    // 概览数据加载完成：更新本地概览、取消加载状态、发射信号通知 QML
    connect(&api, &ApiService::dashboardOverviewLoaded, this, [this](QVariantMap data) {
        m_overview = data;
        setLoading(false);
        emit overviewChanged();
    });

    // 服务统计加载完成：更新本地服务统计列表
    connect(&api, &ApiService::serviceStatsLoaded, this, [this](QString period, QVariantList stats) {
        Q_UNUSED(period)
        m_serviceStats = stats;
        emit serviceStatsChanged();
    });

    // 热门问题加载完成：更新本地热门问题列表
    connect(&api, &ApiService::hotQuestionsLoaded, this, [this](QVariantList items) {
        m_hotQuestions = items;
        emit hotQuestionsChanged();
    });

    // 满意度趋势加载完成：更新本地趋势数据列表
    connect(&api, &ApiService::satisfactionTrendLoaded, this, [this](QString period, QVariantList trend) {
        Q_UNUSED(period)
        m_satisfactionTrend = trend;
        emit satisfactionTrendChanged();
    });

    // 完整看板加载完成（全量接口）：解析各字段并更新到对应属性
    connect(&api, &ApiService::dashboardFullLoaded, this, [this](const QVariantMap &data) {
        m_overview = data["overview"].toMap();
        emit overviewChanged();
        if (data.contains("service_stats")) {
            QVariantList stats;
            for (const QVariant &v : data["service_stats"].toList()) {
                stats.append(v.toMap());
            }
            m_serviceStats = stats;
            emit serviceStatsChanged();
        }
        if (data.contains("hot_questions")) {
            QVariantList items;
            for (const QVariant &v : data["hot_questions"].toList()) {
                items.append(v.toMap());
            }
            m_hotQuestions = items;
            emit hotQuestionsChanged();
        }
        if (data.contains("satisfaction_trend")) {
            QVariantList trend;
            for (const QVariant &v : data["satisfaction_trend"].toList()) {
                trend.append(v.toMap());
            }
            m_satisfactionTrend = trend;
            emit satisfactionTrendChanged();
        }
        setLoading(false);
    });

    // API 出错：取消加载状态并转发错误信息到 QML
    connect(&api, &ApiService::apiError, this, [this](const QString &error) {
        setLoading(false);
        emit dashboardError(error);
    });
}

// ── Getter 属性访问器 ──

QVariantMap DashboardManager::overview() const
{
    return m_overview;
}

QVariantList DashboardManager::serviceStats() const
{
    return m_serviceStats;
}

QVariantList DashboardManager::hotQuestions() const
{
    return m_hotQuestions;
}

QVariantList DashboardManager::satisfactionTrend() const
{
    return m_satisfactionTrend;
}

bool DashboardManager::isLoading() const
{
    return m_isLoading;
}

/** 加载看板全部数据：设置加载状态后委托 ApiService 发起 HTTP GET 请求 */
void DashboardManager::loadAll()
{
    setLoading(true);
    ApiService::instance().loadDashboardFull();
}

/** 设置加载状态：仅在状态改变时发射 loadingChanged 信号，避免重复通知 QML */
void DashboardManager::setLoading(bool loading)
{
    if (m_isLoading != loading) {
        m_isLoading = loading;
        emit loadingChanged();
    }
}
