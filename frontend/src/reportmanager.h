#ifndef REPORTMANAGER_H
#define REPORTMANAGER_H

#include <QObject>
#include <QVariantMap>
#include <QVariantList>

class ReportManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap visitorInsight READ visitorInsight NOTIFY visitorInsightChanged)
    Q_PROPERTY(QVariantMap emotionTrend READ emotionTrend NOTIFY emotionTrendChanged)
    Q_PROPERTY(QVariantList focusAnalysis READ focusAnalysis NOTIFY focusAnalysisChanged)
    Q_PROPERTY(QVariantList serviceSuggestions READ serviceSuggestions NOTIFY serviceSuggestionsChanged)
    Q_PROPERTY(QString startDate READ startDate NOTIFY dateRangeChanged)
    Q_PROPERTY(QString endDate READ endDate NOTIFY dateRangeChanged)
    Q_PROPERTY(bool isLoading READ isLoading NOTIFY loadingChanged)

public:
    explicit ReportManager(QObject *parent = nullptr);

    QVariantMap visitorInsight() const;
    QVariantMap emotionTrend() const;
    QVariantList focusAnalysis() const;
    QVariantList serviceSuggestions() const;
    QString startDate() const;
    QString endDate() const;
    bool isLoading() const;

    Q_INVOKABLE void setDateRange(const QString &start, const QString &end);
    Q_INVOKABLE void loadAll();

signals:
    void visitorInsightChanged();
    void emotionTrendChanged();
    void focusAnalysisChanged();
    void serviceSuggestionsChanged();
    void dateRangeChanged();
    void loadingChanged();
    void reportError(const QString &error);

private:
    QVariantMap m_visitorInsight;
    QVariantMap m_emotionTrend;
    QVariantList m_focusAnalysis;
    QVariantList m_serviceSuggestions;
    QString m_startDate;
    QString m_endDate;
    bool m_isLoading = false;

    void setLoading(bool loading);
};

#endif // REPORTMANAGER_H
