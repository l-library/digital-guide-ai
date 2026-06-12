#include "loginmanager.h"
#include "apiservice.h"

#include <QSettings>

LoginManager::LoginManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::loginResult, this, [this](bool success, QVariantMap userInfo, const QString &error) {
        if (success) {
            setLoggedInState(true, userInfo);
        } else {
            emit loginFailed(error);
        }
    });
    connect(&api, &ApiService::registerResult, this, [this](bool success, QVariantMap userInfo, const QString &error) {
        if (success) {
            setLoggedInState(true, userInfo);
            emit autoLoginChecked(true);
        } else {
            emit loginFailed(error);
        }
    });
    connect(&api, &ApiService::autoLoginResult, this, [this](bool loggedIn, QVariantMap userInfo) {
        if (loggedIn) {
            setLoggedInState(true, userInfo);
        } else {
            setLoggedInState(false, {});
        }
        emit autoLoginChecked(loggedIn);
    });
    connect(&api, &ApiService::logoutResult, this, [this](bool) {
        setLoggedInState(false, {});
        emit loggedOut();
    });

    // 从持久化存储恢复认证信息
    QSettings settings;
    m_storedToken = settings.value("auth/token").toString();
    m_storedUserId = settings.value("auth/userId", -1).toInt();
}

bool LoginManager::isLoggedIn() const
{
    return m_loggedIn;
}

QVariantMap LoginManager::currentUser() const
{
    return m_currentUser;
}

void LoginManager::checkAutoLogin()
{
    if (m_storedToken.isEmpty()) {
        setLoggedInState(false, {});
        emit autoLoginChecked(false);
        return;
    }
    ApiService::instance().validateToken(m_storedToken, m_storedUserId);
}

void LoginManager::login(const QString &username, const QString &password, bool remember)
{
    m_rememberMe = remember;
    ApiService::instance().login(username, password);
}

void LoginManager::registerUser(const QString &username, const QString &password,
                                 const QString &confirmPassword, const QString &displayName)
{
    m_rememberMe = true;
    ApiService::instance().registerUser(username, password, confirmPassword, displayName);
}

void LoginManager::logout()
{
    clearAuthToken();
    ApiService::instance().logout(m_currentUser["id"].toInt());
}

void LoginManager::setLoggedInState(bool loggedIn, const QVariantMap &user)
{
    if (m_loggedIn != loggedIn) {
        m_loggedIn = loggedIn;
        emit loginStateChanged();
    }
    m_currentUser = user;
    emit currentUserChanged();

    if (loggedIn && m_rememberMe) {
        QSettings settings;
        settings.setValue("auth/token", user["token"].toString());
        settings.setValue("auth/userId", user["id"].toInt());
        settings.setValue("auth/displayName", user["displayName"].toString());
        settings.setValue("auth/role", user["role"].toString());
    }
}

void LoginManager::saveAuthToken(const QString &token, int userId)
{
    m_storedToken = token;
    m_storedUserId = userId;
}

void LoginManager::clearAuthToken()
{
    m_storedToken.clear();
    m_storedUserId = -1;
    QSettings settings;
    settings.remove("auth/token");
    settings.remove("auth/userId");
    settings.remove("auth/displayName");
    settings.remove("auth/role");
}
