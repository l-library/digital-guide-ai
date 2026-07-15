#include "voiceinterface.h"

#include <QDateTime>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QStandardPaths>

VoiceInterface::VoiceInterface(QObject *parent)
    : QObject(parent)
{
    setupRecording();
}

VoiceInterface::~VoiceInterface()
{
    if (m_recordProcess && m_recordProcess->state() != QProcess::NotRunning) {
        m_recordProcess->terminate();
        m_recordProcess->waitForFinished(3000);
    }
}

// Linux 上 QMediaRecorder 通过 FFmpeg/PulseAudio 访问 USB 麦克风时经常录到静音，
// 改用 arecord 直接访问 ALSA 硬件设备，wav 16kHz 单声道
void VoiceInterface::setupRecording()
{
    m_recordProcess = new QProcess(this);

    QObject::connect(m_recordProcess,
        QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
        this, [this](int exitCode, QProcess::ExitStatus exitStatus) {
            Q_UNUSED(exitCode)
            if (m_state == Processing) {
                if (exitStatus == QProcess::NormalExit && !m_outputFilePath.isEmpty()) {
                    // 检查文件大小，排除空文件
                    QFileInfo fi(m_outputFilePath);
                    if (fi.exists() && fi.size() > 1024) {
                        qDebug() << "Voice: 录音完成，文件:" << m_outputFilePath
                                 << "大小:" << fi.size() << "字节";
                        emit voiceRecordingReady(m_outputFilePath);
                    } else {
                        qWarning() << "Voice: 录音文件过小 (" << fi.size()
                                   << "字节)，可能未录到声音";
                        emit errorOccurred(QStringLiteral("录音文件过小，可能未录到声音，请检查麦克风"));
                        setState(Idle);
                    }
                } else {
                    qWarning() << "Voice: arecord 异常退出";
                    emit errorOccurred(QStringLiteral("录音进程异常退出"));
                    setState(Idle);
                }
            }
        });

    QObject::connect(m_recordProcess, &QProcess::errorOccurred,
        this, [this](QProcess::ProcessError error) {
            Q_UNUSED(error)
            qWarning() << "Voice: arecord 错误:" << m_recordProcess->errorString();
            if (m_state == Recording || m_state == Processing) {
                emit errorOccurred(QStringLiteral("录音设备错误: %1").arg(m_recordProcess->errorString()));
                setState(Idle);
            }
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
    if (m_state != Idle) {
        return;
    }

    if (!m_recordProcess) {
        qWarning() << "Voice: 录音进程未初始化";
        emit errorOccurred(QStringLiteral("录音模块未初始化"));
        return;
    }

    QString tempDir = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    QDir().mkpath(tempDir);
    m_outputFilePath = tempDir + QString("/voice_rec_%1.wav")
                           .arg(QDateTime::currentMSecsSinceEpoch());

    // arecord 参数:
    //   -D hw:1,0   → USB 声卡硬件设备 (ALSA 直连, 绕过 PulseAudio)
    //   -r 48000    → 48kHz 采样率 (USB 麦克风普遍只支持 48k)
    //   -f S16_LE   → 16-bit 有符号小端
    //   -c 1        → 单声道
    //   -t wav      → WAV 格式
    QStringList args;
    args << "-D" << "hw:1,0"
         << "-r" << "48000"
         << "-f" << "S16_LE"
         << "-c" << "1"
         << "-t" << "wav"
         << m_outputFilePath;

    qDebug() << "Voice: 启动录音 arecord" << args;
    m_recordProcess->start("arecord", args);

    if (m_recordProcess->waitForStarted(3000)) {
        setState(Recording);
        qDebug() << "Voice: 录音已开始 →" << m_outputFilePath;
    } else {
        qWarning() << "Voice: arecord 启动失败:" << m_recordProcess->errorString();
        emit errorOccurred(QStringLiteral("无法启动录音，请确认麦克风已连接且未被占用"));
    }
}

void VoiceInterface::stopRecording()
{
    if (m_state != Recording)
        return;

    setState(Processing);
    qDebug() << "Voice: 停止录音...";

    // SIGTERM → arecord 正常退出，WAV 头会被正确写入
    m_recordProcess->terminate();
}

void VoiceInterface::cancelRecording()
{
    if (m_state == Recording) {
        m_outputFilePath.clear();
        m_recordProcess->kill();
        m_recordProcess->waitForFinished(3000);
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
