#include "reportmanager.h"
#include "apiservice.h"

/** 构造函数：连接 ApiService 的报告相关信号到本地处理逻辑 */
ReportManager::ReportManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();

    // 游客洞察加载完成：存储数据、取消加载状态并发射通知
    connect(&api, &ApiService::visitorInsightLoaded, this, [this](const QVariantMap &data) {
        m_visitorInsight = data;
        setLoading(false);
        emit visitorInsightChanged();
    });

    // 情感趋势加载完成：存储数据、取消加载状态并发射通知
    connect(&api, &ApiService::emotionTrendLoaded, this, [this](const QVariantMap &data) {
        m_emotionTrend = data;
        setLoading(false);
        emit emotionTrendChanged();
    });

    // 关注点分析加载完成：从返回 Map 中提取 categories 列表、取消加载状态并发射通知
    connect(&api, &ApiService::focusAnalysisLoaded, this, [this](const QVariantMap &data) {
        m_focusAnalysis = data["categories"].toList();
        setLoading(false);
        emit focusAnalysisChanged();
    });

    // 服务建议加载完成：从返回 Map 中提取 suggestions 列表、取消加载状态并发射通知
    connect(&api, &ApiService::serviceSuggestionsLoaded, this, [this](const QVariantMap &data) {
        m_serviceSuggestions = data["suggestions"].toList();
        setLoading(false);
        emit serviceSuggestionsChanged();
    });

    // API 出错：取消加载状态并转发错误信息到 QML
    connect(&api, &ApiService::apiError, this, [this](const QString &error) {
        setLoading(false);
        emit reportError(error);
    });
}

// ── Getter 属性访问器 ──

QVariantMap ReportManager::visitorInsight() const
{
    return m_visitorInsight;
}

QVariantMap ReportManager::emotionTrend() const
{
    return m_emotionTrend;
}

QVariantList ReportManager::focusAnalysis() const
{
    return m_focusAnalysis;
}

QVariantList ReportManager::serviceSuggestions() const
{
    return m_serviceSuggestions;
}

QString ReportManager::startDate() const
{
    return m_startDate;
}

QString ReportManager::endDate() const
{
    return m_endDate;
}

bool ReportManager::isLoading() const
{
    return m_isLoading;
}

/** 设置日期范围：更新起止日期并发射 dateRangeChanged 通知 QML */
void ReportManager::setDateRange(const QString &start, const QString &end)
{
    m_startDate = start;
    m_endDate = end;
    emit dateRangeChanged();
}

/** 加载所有报告数据：并行发起四个独立的 API 请求 */
void ReportManager::loadAll()
{
    setLoading(true);
    ApiService::instance().loadVisitorInsight(m_startDate, m_endDate);
    ApiService::instance().loadEmotionTrend(m_startDate, m_endDate);
    ApiService::instance().loadFocusAnalysis(m_startDate, m_endDate);
    ApiService::instance().loadServiceSuggestions(m_startDate, m_endDate);
}

/** 设置加载状态：仅在状态改变时发射 loadingChanged 信号，避免重复通知 QML */
void ReportManager::setLoading(bool loading)
{
    if (m_isLoading != loading) {
        m_isLoading = loading;
        emit loadingChanged();
    }
}
