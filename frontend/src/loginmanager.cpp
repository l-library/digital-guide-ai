#include "loginmanager.h"
#include "apiservice.h"

#include <QCryptographicHash>
#include <QRandomGenerator>

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
    if (m_storedToken.isEmpty() || m_storedUserId <= 0) {
        setLoggedInState(false, {});
        emit autoLoginChecked(false);
        return;
    }
    ApiService::instance().validateToken(m_storedToken, m_storedUserId);
}

void LoginManager::login(const QString &username, const QString &password, bool remember)
{
    ApiService::instance().login(username, password);

    if (remember) {
        m_storedToken = generateToken();
        m_storedUserId = 1;
    }
}

void LoginManager::logout()
{
    clearAuthToken();
    ApiService::instance().logout(m_currentUser["id"].toInt());
}

QString LoginManager::generateToken() const
{
    const QString chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    QString token;
    token.reserve(64);
    for (int i = 0; i < 64; ++i) {
        int index = QRandomGenerator::global()->bounded(chars.size());
        token.append(chars.at(index));
    }
    return token;
}

void LoginManager::setLoggedInState(bool loggedIn, const QVariantMap &user)
{
    if (m_loggedIn != loggedIn) {
        m_loggedIn = loggedIn;
        emit loginStateChanged();
    }
    m_currentUser = user;
    emit currentUserChanged();
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
}
