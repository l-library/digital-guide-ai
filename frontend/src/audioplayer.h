#ifndef AUDIOPLAYER_H
#define AUDIOPLAYER_H

#include <QObject>
#include <QMediaPlayer>
#include <QAudioOutput>
#include <QUrl>

class AudioPlayer : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool playing READ playing NOTIFY playingChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusChanged)
public:
    explicit AudioPlayer(QObject *parent = nullptr);

    bool playing() const;
    QString statusText() const;

    Q_INVOKABLE void play(const QString &audioUrl);
    Q_INVOKABLE void stop();

signals:
    void playingChanged();
    void statusChanged();
    void playbackFinished();

private:
    QMediaPlayer *m_player = nullptr;
    QAudioOutput *m_audioOutput = nullptr;
    bool m_playing = false;
    QString m_statusText;

    void setPlaying(bool playing);
    void setStatusText(const QString &text);
};

#endif // AUDIOPLAYER_H