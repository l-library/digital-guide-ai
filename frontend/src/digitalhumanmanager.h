#ifndef DIGITALHUMANMANAGER_H
#define DIGITALHUMANMANAGER_H

#include <QObject>
#include <QVariantList>

class DigitalHumanManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList digitalHumans READ digitalHumans NOTIFY digitalHumansChanged)
    Q_PROPERTY(int currentIndex READ currentIndex NOTIFY currentIndexChanged)
    Q_PROPERTY(QString currentName READ currentName NOTIFY currentIndexChanged)
    Q_PROPERTY(QVariantMap currentDigitalHuman READ currentDigitalHuman NOTIFY currentIndexChanged)
public:
    explicit DigitalHumanManager(QObject *parent = nullptr);

    QVariantList digitalHumans() const;
    int currentIndex() const;
    QString currentName() const;
    QVariantMap currentDigitalHuman() const;

    Q_INVOKABLE void loadDigitalHumans();
    Q_INVOKABLE void switchTo(int index);
    Q_INVOKABLE void switchToId(int dhId);

signals:
    void digitalHumansChanged();
    void currentIndexChanged();

private:
    QVariantList m_digitalHumans;
    int m_currentIndex = 0;
};

#endif // DIGITALHUMANMANAGER_H
