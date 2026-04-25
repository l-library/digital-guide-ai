#include "historymanager.h"
#include "apiservice.h"

#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDateTime>

HistoryManager::HistoryManager(QObject *parent)
    : QObject(parent)
{
    auto &api = ApiService::instance();
    connect(&api, &ApiService::conversationsGroupedLoaded, this, [this](QVariantList grouped) {
        m_groupedConversations = grouped;
        m_loading = false;
        emit loadingChanged();
        emit historyChanged();
    });
    connect(&api, &ApiService::conversationsLoaded, this, [this](QVariantList conversations) {
        m_allConversations = conversations;
    });
    connect(&api, &ApiService::conversationDeleted, this, [this](bool success) {
        if (!success) {
            emit operationFailed(QStringLiteral("删除对话失败"));
        }
    });
}

QVariantList HistoryManager::groupedConversations() const
{
    return m_groupedConversations;
}

bool HistoryManager::loading() const
{
    return m_loading;
}

void HistoryManager::loadHistory(int userId)
{
    m_loading = true;
    m_currentUserId = userId;
    emit loadingChanged();
    ApiService::instance().loadConversationsGroupedByDate(userId);
}

void HistoryManager::deleteConversation(int conversationId)
{
    ApiService::instance().deleteConversation(conversationId);
    for (int i = 0; i < m_groupedConversations.size(); ++i) {
        QVariantMap group = m_groupedConversations[i].toMap();
        QVariantList convs = group["conversations"].toList();
        bool changed = false;
        for (int j = 0; j < convs.size(); ++j) {
            if (convs[j].toMap()["id"].toInt() == conversationId) {
                convs.removeAt(j);
                changed = true;
                break;
            }
        }
        if (changed) {
            if (convs.isEmpty()) {
                m_groupedConversations.removeAt(i);
            } else {
                group["conversations"] = convs;
                m_groupedConversations[i] = group;
            }
            break;
        }
    }
    emit historyChanged();
}

bool HistoryManager::exportConversation(int conversationId, const QString &filePath)
{
    QJsonObject root;
    root["id"] = conversationId;
    root["exportedAt"] = QDateTime::currentDateTime().toString(Qt::ISODate);
    root["title"] = QStringLiteral("对话");
    root["messages"] = QJsonArray();

    QJsonDocument doc(root);

    QString outPath = filePath;
    if (!outPath.endsWith(".json"))
        outPath += ".json";

    QFile file(outPath);
    if (!file.open(QIODevice::WriteOnly)) {
        emit operationFailed(QStringLiteral("无法写入文件：%1").arg(file.errorString()));
        return false;
    }
    file.write(doc.toJson(QJsonDocument::Indented));
    file.close();
    return true;
}

void HistoryManager::restoreConversation(int conversationId)
{
    QVariantMap conv;
    for (const auto &g : m_groupedConversations) {
        QVariantList cl = g.toMap()["conversations"].toList();
        for (const auto &c : cl) {
            if (c.toMap()["id"].toInt() == conversationId) {
                conv = c.toMap();
                break;
            }
        }
        if (!conv.isEmpty())
            break;
    }
    if (!conv.isEmpty()) {
        emit historyChanged();
    } else {
        emit operationFailed(QStringLiteral("恢复对话失败"));
    }
}

void HistoryManager::search(int userId, const QString &query)
{
    if (query.isEmpty()) {
        ApiService::instance().loadConversationsGroupedByDate(userId);
        return;
    }

    ApiService::instance().loadConversations(userId);
    QVariantList filtered;
    for (const auto &c : m_allConversations) {
        QVariantMap cm = c.toMap();
        if (cm["title"].toString().contains(query, Qt::CaseInsensitive)) {
            filtered.append(c);
        }
    }

    QVariantList grouped;
    QVariantMap group;
    group["date"] = QStringLiteral("搜索结果");
    group["conversations"] = filtered;
    grouped.append(group);

    m_groupedConversations = grouped;
    m_loading = false;
    emit loadingChanged();
    emit historyChanged();
}

void HistoryManager::refresh(int userId)
{
    loadHistory(userId);
}
