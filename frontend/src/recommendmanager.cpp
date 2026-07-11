#include "recommendmanager.h"
#include "apiservice.h"

/** 构造函数：连接 ApiService 的推荐路线信号到本地处理逻辑 */
RecommendManager::RecommendManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();

    // 推荐路线加载完成：更新本地路线数据、取消加载状态、发射信号通知 QML
    connect(&api, &ApiService::recommendRouteLoaded, this, [this](const QVariantMap &route) {
        m_route = route;
        setLoading(false);
        emit routeChanged();
    });

    // API 出错：取消加载状态并转发错误信息到 QML
    connect(&api, &ApiService::apiError, this, [this](const QString &error) {
        setLoading(false);
        emit recommendError(error);
    });
}

// ── Getter 属性访问器 ──

QVariantMap RecommendManager::route() const
{
    return m_route;
}

bool RecommendManager::isLoading() const
{
    return m_isLoading;
}

/** 加载推荐路线：设置加载状态后委托 ApiService 发起 HTTP GET 请求 */
void RecommendManager::loadRecommend(int userId)
{
    setLoading(true);
    ApiService::instance().loadRecommendRoute(userId);
}

/** 设置加载状态：仅在状态改变时发射 loadingChanged 信号，避免重复通知 QML */
void RecommendManager::setLoading(bool loading)
{
    if (m_isLoading != loading) {
        m_isLoading = loading;
        emit loadingChanged();
    }
}
