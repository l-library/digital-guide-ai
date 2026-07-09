#include "adminmanager.h"
#include "apiservice.h"

#include <algorithm>

/** 构造函数：连接 ApiService 的管理员相关信号到本地处理逻辑 */
AdminManager::AdminManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();

    // 用户列表加载完成：替换本地列表、更新分页状态、发射信号通知 QML
    connect(&api, &ApiService::usersLoaded, this, [this](QVariantList users, int total, int page, int pageSize) {
        m_users = users;
        updatePagination(total, page, pageSize);
        setLoading(false);
        emit usersChanged();
        emit pageChanged();
        emit usersLoaded();
    });

    // 用户创建成功：重新加载当前页以显示新用户
    connect(&api, &ApiService::userCreated, this, [this](int userId, const QVariantMap &) {
        Q_UNUSED(userId)
        // 创建成功后重新加载当前页
        loadUsers(m_currentPage, m_pageSize, m_searchKeyword);
    });

    // 用户更新成功：就地更新本地列表中对应用户的字段，避免重新请求
    connect(&api, &ApiService::userUpdated, this, [this](int userId, const QVariantMap &userData) {
        // 就地更新本地列表中的对应用户
        for (auto &u : m_users) {
            QVariantMap user = u.toMap();
            if (user["id"].toInt() == userId) {
                if (userData.contains("displayName")) {
                    user["displayName"] = userData["displayName"];
                }
                if (userData.contains("email")) {
                    user["email"] = userData["email"];
                }
                if (userData.contains("phone")) {
                    user["phone"] = userData["phone"];
                }
                if (userData.contains("isActive")) {
                    user["isActive"] = userData["isActive"];
                }
                u = user;
                break;
            }
        }
        emit userUpdated(userId);
        emit usersChanged();
    });

    // 用户删除成功：从本地列表移除已删除用户，更新总数和分页
    connect(&api, &ApiService::userDeleted, this, [this](int userId) {
        // 从本地列表移除已删除用户
        m_users.erase(
            std::remove_if(m_users.begin(), m_users.end(), [userId](const QVariant &v) {
                return v.toMap()["id"].toInt() == userId;
            }),
            m_users.end()
        );
        m_totalUsers = qMax(0, m_totalUsers - 1);
        updatePagination(m_totalUsers, m_currentPage, m_pageSize);
        emit userDeleted(userId);
        emit usersChanged();
        emit pageChanged();
    });

    // 用户状态变更成功：就地更新本地列表中用户的激活状态
    connect(&api, &ApiService::userStatusChanged, this, [this](int userId, bool isActive) {
        // 就地更新本地列表中用户的激活状态
        for (auto &u : m_users) {
            QVariantMap user = u.toMap();
            if (user["id"].toInt() == userId) {
                user["isActive"] = isActive;
                u = user;
                break;
            }
        }
        emit userStatusChanged(userId, isActive);
        emit usersChanged();
    });

    // 管理员操作出错：取消加载状态并转发错误信息到 QML
    connect(&api, &ApiService::adminError, this, [this](const QString &error) {
        setLoading(false);
        emit adminError(error);
    });
}

// ── Getter 属性访问器（实现在头文件中有注释，此处从略） ──

QVariantList AdminManager::users() const
{
    return m_users;
}

int AdminManager::currentPage() const
{
    return m_currentPage;
}

int AdminManager::totalPages() const
{
    return m_totalPages;
}

int AdminManager::totalUsers() const
{
    return m_totalUsers;
}

bool AdminManager::isLoading() const
{
    return m_isLoading;
}

QString AdminManager::searchKeyword() const
{
    return m_searchKeyword;
}

/** 加载用户列表：设置加载状态后委托 ApiService 发起 HTTP GET 请求 */
void AdminManager::loadUsers(int page, int pageSize, const QString &search)
{
    if (m_isLoading) {
        return;
    }
    setLoading(true);
    ApiService::instance().loadUsers(page, pageSize, search);
}

/** 搜索用户：更新搜索关键词后重置到第一页重新加载 */
void AdminManager::searchUsers(const QString &keyword)
{
    m_searchKeyword = keyword;
    emit searchKeywordChanged();
    loadUsers(1, m_pageSize, keyword);
}

/** 翻到下一页：当前页未到最后页时加载下一页 */
void AdminManager::nextPage()
{
    if (m_currentPage < m_totalPages) {
        loadUsers(m_currentPage + 1, m_pageSize, m_searchKeyword);
    }
}

/** 翻到上一页：当前页未到第一页时加载上一页 */
void AdminManager::prevPage()
{
    if (m_currentPage > 1) {
        loadUsers(m_currentPage - 1, m_pageSize, m_searchKeyword);
    }
}

/** 创建新用户：委托 ApiService 发送 HTTP POST 请求 */
void AdminManager::createUser(const QString &username, const QString &password, const QString &displayName)
{
    ApiService::instance().createUser(username, password, displayName);
}

/** 更新用户信息：委托 ApiService 发送 HTTP PUT 请求（部分字段更新） */
void AdminManager::updateUser(int userId, const QVariantMap &fields)
{
    ApiService::instance().updateUser(userId, fields);
}

/** 删除用户：委托 ApiService 发送 HTTP DELETE 请求（级联删除关联数据） */
void AdminManager::deleteUser(int userId)
{
    ApiService::instance().deleteUser(userId);
}

/** 切换用户启用/禁用状态：委托 ApiService 发送 HTTP PUT 请求 */
void AdminManager::toggleUserStatus(int userId, bool isActive)
{
    ApiService::instance().toggleUserStatus(userId, isActive);
}

/** 设置加载状态：仅在状态改变时发射 loadingChanged 信号，避免重复通知 QML */
void AdminManager::setLoading(bool loading)
{
    if (m_isLoading != loading) {
        m_isLoading = loading;
        emit loadingChanged();
    }
}

/** 更新分页信息：根据总条数、当前页码、每页条数重新计算总页数（向上取整，至少 1 页） */
void AdminManager::updatePagination(int total, int page, int pageSize)
{
    m_totalUsers = total;
    m_currentPage = page;
    m_pageSize = pageSize;
    m_totalPages = qMax(1, (total + pageSize - 1) / pageSize);
}
