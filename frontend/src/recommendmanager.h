#ifndef RECOMMENDMANAGER_H
#define RECOMMENDMANAGER_H

#include <QObject>
#include <QVariantMap>

class RecommendManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap route READ route NOTIFY routeChanged)
    Q_PROPERTY(bool isLoading READ isLoading NOTIFY loadingChanged)

public:
    explicit RecommendManager(QObject *parent = nullptr);

    QVariantMap route() const;
    bool isLoading() const;

    Q_INVOKABLE void loadRecommend(int userId);

signals:
    void routeChanged();
    void loadingChanged();
    void recommendError(const QString &error);

private:
    QVariantMap m_route;
    bool m_isLoading = false;

    void setLoading(bool loading);
};

#endif // RECOMMENDMANAGER_H
