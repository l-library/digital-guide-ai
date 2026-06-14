#ifndef LOGINMANAGER_H
#define LOGINMANAGER_H

#include <QObject>
#include <QVariantMap>

class LoginManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool loggedIn READ isLoggedIn NOTIFY loginStateChanged)
    Q_PROPERTY(QVariantMap currentUser READ currentUser NOTIFY currentUserChanged)
public:
    explicit LoginManager(QObject *parent = nullptr);

    bool isLoggedIn() const;
    QVariantMap currentUser() const;

    Q_INVOKABLE void checkAutoLogin();
    Q_INVOKABLE void login(const QString &username, const QString &password, bool remember);
    Q_INVOKABLE void registerUser(const QString &username, const QString &password,
                                   const QString &confirmPassword, const QString &displayName);
    Q_INVOKABLE void logout();
    Q_INVOKABLE void updateProfile(const QString &displayName, const QString &avatarUrl);
    Q_INVOKABLE void changePassword(const QString &oldPassword, const QString &newPassword);

signals:
    void loginStateChanged();
    void currentUserChanged();
    void autoLoginChecked(bool loggedIn);
    void loginFailed(const QString &error);
    void loggedOut();
    void profileUpdated(const QString &displayName, const QString &avatarUrl);
    void passwordChangeFailed(const QString &error);
    void passwordChangeSucceeded();

private:
    bool m_loggedIn = false;
    QVariantMap m_currentUser;
    QString m_storedToken;
    int m_storedUserId = -1;
    bool m_rememberMe = false;
    void setLoggedInState(bool loggedIn, const QVariantMap &user);
    void saveAuthToken(const QString &token, int userId);
    void clearAuthToken();
};

#endif // LOGINMANAGER_H
