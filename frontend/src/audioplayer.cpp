#include "audioplayer.h"
#include "apiservice.h"

#include <QUrl>
#include <QDebug>

AudioPlayer::AudioPlayer(QObject *parent)
    : QObject(parent)
{
    m_audioOutput = new QAudioOutput(this);
    m_player = new QMediaPlayer(this);
    m_player->setAudioOutput(m_audioOutput);

    QObject::connect(m_player, &QMediaPlayer::playingChanged, this, [this]() {
        setPlaying(m_player->isPlaying());
    });

    QObject::connect(m_player, &QMediaPlayer::mediaStatusChanged, this, [this](QMediaPlayer::MediaStatus status) {
        if (status == QMediaPlayer::EndOfMedia) {
            setPlaying(false);
            setStatusText("");
            emit playbackFinished();
        } else if (status == QMediaPlayer::LoadingMedia) {
            setStatusText(QStringLiteral("语音加载中..."));
        } else if (status == QMediaPlayer::BufferingMedia) {
            setStatusText(QStringLiteral("语音缓冲中..."));
        } else if (status == QMediaPlayer::LoadedMedia) {
            setStatusText(QStringLiteral("正在播放"));
        }
    });

    QObject::connect(m_player, &QMediaPlayer::errorOccurred, this, [this](QMediaPlayer::Error error, const QString &errorString) {
        Q_UNUSED(error)
        qWarning() << "AudioPlayer error:" << errorString;
        setPlaying(false);
        setStatusText(QStringLiteral("播放失败"));
    });
}

bool AudioPlayer::playing() const
{
    return m_playing;
}

QString AudioPlayer::statusText() const
{
    return m_statusText;
}

void AudioPlayer::play(const QString &audioUrl)
{
    if (audioUrl.isEmpty())
        return;

    m_player->stop();

    QString fullUrl = audioUrl;
    if (!audioUrl.startsWith("http")) {
        // 使用与 ApiService 相同的配置读取后端地址
        QString backendBase = ConfigManager::getBackendIP() + ":"
                            + QString::number(ConfigManager::getBackendPort());
        fullUrl = backendBase + audioUrl;
    }

    setStatusText(QStringLiteral("语音加载中..."));
    m_player->setSource(QUrl(fullUrl));
    m_player->play();
}

void AudioPlayer::stop()
{
    m_player->stop();
    setPlaying(false);
    setStatusText("");
}

void AudioPlayer::setPlaying(bool playing)
{
    if (m_playing != playing) {
        m_playing = playing;
        emit playingChanged();
    }
}

void AudioPlayer::setStatusText(const QString &text)
{
    if (m_statusText != text) {
        m_statusText = text;
        emit statusChanged();
    }
}