#ifndef VOICEINTERFACE_H
#define VOICEINTERFACE_H

#include <QObject>
#include <QUrl>

class QMediaCaptureSession;
class QMediaRecorder;
class QAudioInput;

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
    ~VoiceInterface();

    VoiceState state() const;
    QString stateText() const;

    Q_INVOKABLE void startRecording();
    Q_INVOKABLE void stopRecording();
    Q_INVOKABLE void cancelRecording();
    Q_INVOKABLE void finishProcessing();

signals:
    void stateChanged();
    void voiceRecordingReady(const QString &filePath);
    void voiceInputReceived(const QString &text);
    void errorOccurred(const QString &error);

private:
    VoiceState m_state = Idle;
    QMediaCaptureSession *m_captureSession = nullptr;
    QMediaRecorder *m_recorder = nullptr;
    QAudioInput *m_audioInput = nullptr;
    QString m_outputPath;

    void setState(VoiceState newState);
    void setupRecording();
};

#endif // VOICEINTERFACE_H
