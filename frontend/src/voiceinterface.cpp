#include "voiceinterface.h"

#include <QTimer>
#include <QDebug>

VoiceInterface::VoiceInterface(QObject *parent)
    : QObject(parent)
{
}

VoiceInterface::VoiceState VoiceInterface::state() const
{
    return m_state;
}

QString VoiceInterface::stateText() const
{
    switch (m_state) {
    case Idle:      return "空闲";
    case Recording: return "录音中...";
    case Processing:return "处理中...";
    case Playing:   return "播放中...";
    }
    return "空闲";
}

void VoiceInterface::startRecording()
{
    if (m_state != Idle)
        return;

    setState(Recording);
    qDebug() << "Voice: Recording started (stub)";
}

void VoiceInterface::stopRecording()
{
    if (m_state != Recording)
        return;

    setState(Processing);

    QTimer::singleShot(500, this, [this]() {
        QString demoText = "这是一段语音识别演示文本";
        setState(Idle);
        emit voiceInputReceived(demoText);
    });
}

void VoiceInterface::cancelRecording()
{
    if (m_state == Recording) {
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
