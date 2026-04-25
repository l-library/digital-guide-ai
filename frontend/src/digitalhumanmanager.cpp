#include "digitalhumanmanager.h"
#include "apiservice.h"

DigitalHumanManager::DigitalHumanManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::digitalHumansLoaded, this, [this](QVariantList digitalHumans) {
        m_digitalHumans = digitalHumans;
        for (int i = 0; i < m_digitalHumans.size(); ++i) {
            QVariantMap dh = m_digitalHumans[i].toMap();
            if (dh["isDefault"].toBool()) {
                m_currentIndex = i;
                break;
            }
        }
        emit digitalHumansChanged();
        emit currentIndexChanged();
    });
}

QVariantList DigitalHumanManager::digitalHumans() const
{
    return m_digitalHumans;
}

int DigitalHumanManager::currentIndex() const
{
    return m_currentIndex;
}

QString DigitalHumanManager::currentName() const
{
    if (m_currentIndex >= 0 && m_currentIndex < m_digitalHumans.size()) {
        QVariantMap dh = m_digitalHumans[m_currentIndex].toMap();
        return dh["name"].toString();
    }
    return {};
}

QVariantMap DigitalHumanManager::currentDigitalHuman() const
{
    if (m_currentIndex >= 0 && m_currentIndex < m_digitalHumans.size()) {
        return m_digitalHumans[m_currentIndex].toMap();
    }
    return {};
}

void DigitalHumanManager::loadDigitalHumans()
{
    ApiService::instance().loadDigitalHumans();
}

void DigitalHumanManager::switchTo(int index)
{
    if (index >= 0 && index < m_digitalHumans.size() && index != m_currentIndex) {
        m_currentIndex = index;
        int dhId = m_digitalHumans[index].toMap()["id"].toInt();
        ApiService::instance().setDefaultDigitalHuman(dhId);
        emit currentIndexChanged();
    }
}

void DigitalHumanManager::switchToId(int dhId)
{
    for (int i = 0; i < m_digitalHumans.size(); ++i) {
        if (m_digitalHumans[i].toMap()["id"].toInt() == dhId) {
            switchTo(i);
            return;
        }
    }
}
