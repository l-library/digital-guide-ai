#include "voiceinterface.h"

#include <QAudioDevice>
#include <QAudioInput>
#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QMediaCaptureSession>
#include <QMediaDevices>
#include <QMediaFormat>
#include <QMediaRecorder>
#include <QStandardPaths>

VoiceInterface::VoiceInterface(QObject *parent)
    : QObject(parent)
{
    setupRecording();
}

VoiceInterface::~VoiceInterface()
{
    if (m_recorder && m_recorder->recorderState() == QMediaRecorder::RecordingState) {
        m_recorder->stop();
    }
}

void VoiceInterface::setupRecording()
{
    m_audioInput = new QAudioInput(this);
    m_audioInput->setVolume(1.0);

    m_captureSession = new QMediaCaptureSession(this);
    m_captureSession->setAudioInput(m_audioInput);

    m_recorder = new QMediaRecorder(this);
    m_captureSession->setRecorder(m_recorder);

    QMediaFormat wavFormat;
    wavFormat.setFileFormat(QMediaFormat::Wave);
    wavFormat.setAudioCodec(QMediaFormat::AudioCodec::Unspecified);
    m_recorder->setMediaFormat(wavFormat);

    m_recorder->setQuality(QMediaRecorder::HighQuality);
    m_recorder->setAudioChannelCount(1);
    m_recorder->setAudioSampleRate(16000);

    qDebug() << "Voice: Setup complete. Audio input devices:" << QMediaDevices::audioInputs().size();

    QObject::connect(m_recorder, &QMediaRecorder::recorderStateChanged, this, [this](QMediaRecorder::RecorderState state) {
        qDebug() << "Voice: Recorder state changed to:" << state << "(our state:" << m_state << ")";
        if (state == QMediaRecorder::StoppedState && m_state == Processing) {
            if (!m_outputPath.isEmpty()) {
                QUrl url(m_outputPath);
                QString localPath = url.toLocalFile();
                qDebug() << "Voice: Recording saved to" << localPath;
                emit voiceRecordingReady(localPath);
            } else {
                setState(Idle);
            }
        }
    });

    QObject::connect(m_recorder, &QMediaRecorder::errorOccurred, this, [this](QMediaRecorder::Error error, const QString &errorString) {
        Q_UNUSED(error)
        qDebug() << "Voice: Recorder error:" << errorString;
        setState(Idle);
        emit errorOccurred(errorString);
    });
}

VoiceInterface::VoiceState VoiceInterface::state() const
{
    return m_state;
}

QString VoiceInterface::stateText() const
{
    switch (m_state) {
    case Idle:      return QStringLiteral("空闲");
    case Recording: return QStringLiteral("录音中...");
    case Processing:return QStringLiteral("处理中...");
    case Playing:   return QStringLiteral("播放中...");
    }
    return QStringLiteral("空闲");
}

void VoiceInterface::startRecording()
{
    qDebug() << "Voice: startRecording called, current state:" << m_state;

    if (m_state != Idle) {
        qDebug() << "Voice: Not in Idle state, aborting";
        return;
    }

    if (!m_recorder) {
        qDebug() << "Voice: Recorder not initialized";
        emit errorOccurred(QStringLiteral("录音模块未初始化"));
        return;
    }

    QString tempDir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    QDir().mkpath(tempDir);
    QString filePath = tempDir + QString("/voice_rec_%1.wav").arg(QDateTime::currentMSecsSinceEpoch());
    m_outputPath = QUrl::fromLocalFile(filePath).toString();

    m_recorder->setOutputLocation(QUrl(m_outputPath));
    qDebug() << "Voice: Calling record(), output:" << m_outputPath;
    m_recorder->record();

    qDebug() << "Voice: Recorder state after record():" << m_recorder->recorderState();
    setState(Recording);
}

void VoiceInterface::stopRecording()
{
    if (m_state != Recording)
        return;

    setState(Processing);
    m_recorder->stop();
}

void VoiceInterface::cancelRecording()
{
    if (m_state == Recording) {
        m_outputPath.clear();
        m_recorder->stop();
        setState(Idle);
    }
}

void VoiceInterface::finishProcessing()
{
    if (m_state == Processing) {
        setState(Idle);
    }
}

void VoiceInterface::setState(VoiceState newState)
{
    if (m_state != newState) {
        m_state = newState;
        emit stateChanged();
    }
}