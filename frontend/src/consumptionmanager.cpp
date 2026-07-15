#include "consumptionmanager.h"
#include "apiservice.h"

/** 构造函数：连接 ApiService 的消费分析相关信号到本地处理逻辑 */
ConsumptionManager::ConsumptionManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();

    // 完整消费分析加载完成（全量接口）：解析各字段并更新到对应属性
    connect(&api, &ApiService::consumptionFullLoaded, this, [this](const QVariantMap &data) {
        m_overview = data["overview"].toMap();
        emit overviewChanged();

        if (data.contains("revenue_trend")) {
            QVariantList trend;
            for (const QVariant &v : data["revenue_trend"].toList()) {
                trend.append(v.toMap());
            }
            m_revenueTrend = trend;
            emit revenueTrendChanged();
        }

        if (data.contains("category_breakdown")) {
            m_categoryBreakdown = data["category_breakdown"].toMap();
            emit categoryBreakdownChanged();
        }

        if (data.contains("demographics")) {
            m_demographics = data["demographics"].toMap();
            emit demographicsChanged();
        }

        setLoading(false);
    });

    // API 出错：取消加载状态并转发错误信息到 QML
    connect(&api, &ApiService::apiError, this, [this](const QString &error) {
        setLoading(false);
        emit consumptionError(error);
    });
}

// ── Getter 属性访问器 ──

QVariantMap ConsumptionManager::overview() const { return m_overview; }
QVariantList ConsumptionManager::revenueTrend() const { return m_revenueTrend; }
QVariantMap ConsumptionManager::categoryBreakdown() const { return m_categoryBreakdown; }
QVariantMap ConsumptionManager::demographics() const { return m_demographics; }
bool ConsumptionManager::isLoading() const { return m_isLoading; }

/** 加载消费分析全部数据：设置加载状态后委托 ApiService 发起 HTTP GET 请求 */
void ConsumptionManager::loadAll()
{
    setLoading(true);
    ApiService::instance().loadConsumptionFull();
}

/** 设置加载状态：仅在状态改变时发射 loadingChanged 信号，避免重复通知 QML */
void ConsumptionManager::setLoading(bool loading)
{
    if (m_isLoading != loading) {
        m_isLoading = loading;
        emit loadingChanged();
    }
}