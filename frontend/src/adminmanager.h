#ifndef ADMINMANAGER_H
#define ADMINMANAGER_H

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

/** 管理员用户管理器：管理用户列表分页、搜索、CRUD 操作 */
class AdminManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList users READ users NOTIFY usersChanged)         // 当前页用户列表
    Q_PROPERTY(int currentPage READ currentPage NOTIFY pageChanged)       // 当前页码
    Q_PROPERTY(int totalPages READ totalPages NOTIFY pageChanged)         // 总页数
    Q_PROPERTY(int totalUsers READ totalUsers NOTIFY pageChanged)         // 用户总数
    Q_PROPERTY(bool isLoading READ isLoading NOTIFY loadingChanged)       // 是否正在加载
    Q_PROPERTY(QString searchKeyword READ searchKeyword NOTIFY searchKeywordChanged) // 搜索关键词
public:
    explicit AdminManager(QObject *parent = nullptr);

    /** 获取当前用户列表（每个元素为 QVariantMap） */
    QVariantList users() const;
    /** 获取当前页码 */
    int currentPage() const;
    /** 获取总页数 */
    int totalPages() const;
    /** 获取用户总数 */
    int totalUsers() const;
    /** 是否正在加载 */
    bool isLoading() const;
    /** 获取搜索关键词 */
    QString searchKeyword() const;

    /** 加载用户列表（分页+搜索） */
    Q_INVOKABLE void loadUsers(int page = 1, int pageSize = 20, const QString &search = "");
    /** 按关键词搜索用户，重置到第一页 */
    Q_INVOKABLE void searchUsers(const QString &keyword);
    /** 翻到下一页 */
    Q_INVOKABLE void nextPage();
    /** 翻到上一页 */
    Q_INVOKABLE void prevPage();
    /** 创建新用户 */
    Q_INVOKABLE void createUser(const QString &username, const QString &password, const QString &displayName);
    /** 更新用户信息（部分字段更新） */
    Q_INVOKABLE void updateUser(int userId, const QVariantMap &fields);
    /** 删除用户（级联删除关联数据） */
    Q_INVOKABLE void deleteUser(int userId);
    /** 切换用户启用/禁用状态 */
    Q_INVOKABLE void toggleUserStatus(int userId, bool isActive);

signals:
    /** 用户列表数据变化 */
    void usersChanged();
    /** 页面状态（页码/总页数/总用户数）变化 */
    void pageChanged();
    /** 加载状态变化 */
    void loadingChanged();
    /** 搜索关键词变化 */
    void searchKeywordChanged();
    /** 用户列表加载完成 */
    void usersLoaded();
    /** 用户创建成功 */
    void userCreated(int userId);
    /** 用户信息更新成功 */
    void userUpdated(int userId);
    /** 用户删除成功 */
    void userDeleted(int userId);
    /** 用户启用/禁用状态切换成功 */
    void userStatusChanged(int userId, bool isActive);
    /** 管理员操作出错 */
    void adminError(const QString &error);

private:
    QVariantList m_users;         // 当前页用户列表（QVariantMap 列表）
    int m_currentPage = 1;        // 当前页码
    int m_pageSize = 20;          // 每页条数
    int m_totalUsers = 0;         // 用户总数
    int m_totalPages = 1;         // 总页数
    bool m_isLoading = false;     // 是否正在加载
    QString m_searchKeyword;      // 当前搜索关键词

    /** 设置加载状态并发出 loadingChanged 信号 */
    void setLoading(bool loading);
    /** 更新分页信息（总条数、页码、每页条数 → 计算总页数） */
    void updatePagination(int total, int page, int pageSize);
};

#endif // ADMINMANAGER_H
