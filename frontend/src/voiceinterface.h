#ifndef VOICEINTERFACE_H
#define VOICEINTERFACE_H

#include <QObject>

class VoiceInterface : public QObject
{
    Q_OBJECT
    Q_PROPERTY(VoiceState state READ state NOTIFY stateChanged)
    Q_PROPERTY(QString stateText READ stateText NOTIFY stateChanged)
public:
    enum VoiceState {
        Idle,
        Recording,
        Processing,
        Playing
    };
    Q_ENUM(VoiceState)

    explicit VoiceInterface(QObject *parent = nullptr);

    VoiceState state() const;
    QString stateText() const;

    Q_INVOKABLE void startRecording();
    Q_INVOKABLE void stopRecording();
    Q_INVOKABLE void cancelRecording();

signals:
    void stateChanged();
    void voiceInputReceived(const QString &text);
    void errorOccurred(const QString &error);

private:
    VoiceState m_state = Idle;
    void setState(VoiceState newState);
};

#endif // VOICEINTERFACE_H
