/*
 *  Whiteboard
 *
 *  Copyright © 2022 Ingenuity i/o. All rights reserved.
 *
 *  See license terms for the rights and conditions
 *  defined by copyright holders.
 *
 *  Contributors:
 *    Alexandre Lemort <lemort@ingenuity.io>
 *
 */

#include <QtGlobal>
#include <QDebug>
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QSurfaceFormat>
#include <QCommandLineParser>
#include <QQuickWindow>

#ifdef INGESCAPE_FROM_PRI
#include "ingescape.h"
#else
#include <ingescape/ingescape.h>
#endif // INGESCAPE_FROM_PRI

#include "I2Quick.h"

#include "agents/whiteboard.h"
#include "qmlinstrument.h"
#include "global/networkconfiguration.h"


void externalStop_Callback(void* myData)
{
    Q_UNUSED(myData)
    QCoreApplication::quit();
}


static QtMessageHandler previousQtMessageHandler = nullptr;
void igsMessageOutput(QtMsgType type, const QMessageLogContext &context, const QString &msg)
{
    auto localMsg = msg.toLocal8Bit();
    const auto file = context.file ? context.file : "";
    const auto function = context.function ? context.function : "";

    switch (type) {
        case QtDebugMsg:
            igs_debug("%s (%s:%u, %s)", localMsg.constData(), file, context.line, function);
            break;
        case QtInfoMsg:
            igs_info("%s (%s:%u, %s)", localMsg.constData(), file, context.line, function);
            break;
        case QtWarningMsg:
            igs_warn("%s (%s:%u, %s)", localMsg.constData(), file, context.line, function);
            break;
        case QtCriticalMsg:
            igs_error("%s (%s:%u, %s)", localMsg.constData(), file, context.line, function);
            break;
        case QtFatalMsg:
            igs_fatal("%s (%s:%u, %s)", localMsg.constData(), file, context.line, function);
            break;
    }

#ifdef QT_DEBUG
    if (previousQtMessageHandler != nullptr)
        (*previousQtMessageHandler)(type, context, msg);
#endif
}


void registerCustomTypes()
{
    qmlRegisterSingletonType<Whiteboard>("Whiteboard", 1, 0, "Whiteboard", &Whiteboard::qmlSingleton);
    qmlRegisterSingletonType<NetworkConfiguration>("Whiteboard", 1, 0, "NetworkConfiguration", &NetworkConfiguration::qmlSingleton);
    qmlRegisterSingletonType<GraphicElementType>("Whiteboard", 1, 0, "GraphicElementType", &GraphicElementType::qmlSingleton);
    qmlRegisterSingletonType(QUrl("qrc:/qml/Whiteboard/WhiteboardTheme.qml"), "Whiteboard", 1, 0, "WhiteboardTheme");

    qmlRegisterUncreatableType<GraphicElement>("Whiteboard", 1, 0, "GraphicElement", "C++ model");
    qmlRegisterUncreatableType<ImageElement>("Whiteboard", 1, 0, "ImageElement", "C++ model");
    qmlRegisterUncreatableType<TextElement>("Whiteboard", 1, 0, "TextElement", "C++ model");
    qmlRegisterUncreatableType<ShapeElement>("Whiteboard", 1, 0, "ShapeElement", "C++ model");

    qmlRegisterUncreatableType<Message>("Whiteboard", 1, 0, "Message", "C++ model");
}


int main(int argc, char *argv[])
{
#ifdef Q_OS_WIN
    // NB: this line is mandatory and without it, Ingescape will not be able to use
    //     network devices which name contains diacritics when Windows uses UTF-8 as
    //     system locale (i.e. Windows is configured for worldwide language support)
    setlocale(LC_ALL, "");
#endif

    //------------------------------
    // Configure Qt
    //------------------------------
#ifdef QT_DEBUG
    // Print out general information about various parts of the scene graph and the graphics stack
    QStringList filtersRules {"qt.scenegraph.general = true", "qt.rhi.general = true"};
    QLoggingCategory::setFilterRules(filtersRules.join("\n"));

    qSetMessagePattern("[%{time hh:mm:ss.zzz}][%{type}] %{if-category}%{category}: %{endif}file://%{file}:%{line} - %{message}");
#endif

    // Redirect Qt logs to Ingescape logs
    previousQtMessageHandler = qInstallMessageHandler(igsMessageOutput);


    //------------------------------
    // Configure our application
    //------------------------------
    igs_net_raise_sockets_limit();

    QGuiApplication app(argc, argv);
    QGuiApplication::setOrganizationName("Ingenuity io");
    QGuiApplication::setOrganizationDomain("ingenuity.io");
    QGuiApplication::setApplicationName(APP_NAME);
    QGuiApplication::setApplicationVersion(VERSION);


    //------------------------------
    // Command line arguments
    //------------------------------

    QCommandLineParser commandLineParser;
    commandLineParser.setApplicationDescription(APP_NAME);
    commandLineParser.addHelpOption();
    commandLineParser.addVersionOption();
    QCommandLineOption deviceOption("device", "Newtwork device", "device");
    commandLineParser.addOption(deviceOption);
    QCommandLineOption portOption("port", "Newtwork port", "5670");
    commandLineParser.addOption(portOption);

    commandLineParser.process(app);

#ifdef Q_OS_MAC
    QString networkDevice {"en0"};
#else
    QString networkDevice {};
#endif
    if (auto networkDeviceValue = commandLineParser.value(deviceOption); !networkDeviceValue.isEmpty())
        networkDevice = networkDeviceValue;

    uint networkPort {5670};
    if (auto networkPortValue = commandLineParser.value(portOption); !networkPortValue.isEmpty())
        networkPort = networkPortValue.toUInt();


    //------------------------------
    // Configure QML
    //------------------------------

    // MSAA
    const auto graphicsAPi = QQuickWindow::graphicsApi();

    int numSamples {2};
    if ((graphicsAPi == QSGRendererInterface::Vulkan) || (graphicsAPi == QSGRendererInterface::Metal))
        numSamples = 4;

    if (numSamples > 0)
    {
        QSurfaceFormat surfaceFormat;
        surfaceFormat.setSamples(numSamples);
        QSurfaceFormat::setDefaultFormat(surfaceFormat);
        qInfo() << "Using MSAA" << QString("%1x").arg(QSurfaceFormat::defaultFormat().samples()) << "(required value is" << numSamples << ")";
    }


    // QML engine and custom types
    QQmlApplicationEngine engine;
    I2Quick::init(&engine);
    registerCustomTypes();


#if (defined Q_OS_MACOS || defined Q_OS_ANDROID)
    QQmlFileSelector fileSelector(&engine);
    fileSelector.setExtraSelectors({QLatin1String("nativemenubar")});
#endif

    I2QmlHotReloader::instance().setengine(&engine);
    I2QmlHotReloader::instance().seturl(QUrl("qrc:/qml/Whiteboard/Content.qml"));

#ifdef QT_DEBUG
    auto sourceDirPath = QFileInfo(QFINDTESTDATA(__FILE__)).absolutePath();
    I2QmlHotReloader::instance().addRootDirPath(sourceDirPath);
    I2QmlHotReloader::instance().watchDirPath(QString("%1%2qml").arg(sourceDirPath).arg(QDir::separator()));
    I2QmlHotReloader::instance().watchDirPath(QString("%1%2resources").arg(sourceDirPath).arg(QDir::separator()));
    I2QmlHotReloader::instance().start();
#endif


    //------------------------------
    // Ingescape agent configuration
    //------------------------------

    if (NetworkConfiguration::instance().networkDeviceIsAvailable(networkDevice))
        NetworkConfiguration::instance().setcurrentNetworkDevice(networkDevice);

    if ((0 < networkPort) && (networkPort < 65535))
        NetworkConfiguration::instance().setcurrentPort(networkPort);

    // Agents initialisation
    Whiteboard::instance();
    QmlInstrument qmlInstrument;

    igs_set_command_line_from_args(argc, const_cast<const char**>(argv));
    igs_log_set_console(true);
    igs_log_set_stream(true);
    igs_log_set_file(true, nullptr);

#ifdef QT_DEBUG
    igs_log_set_console_level(IGS_LOG_DEBUG);
#else
    igs_log_set_console_level(IGS_LOG_INFO);
#endif

    //------------------------------
    // Start application
    //------------------------------

    igs_observe_forced_stop(externalStop_Callback, nullptr);

    if (NetworkConfiguration::instance().networkDeviceIsAvailable(networkDevice)
        && 0 < networkPort && networkPort < 65535)
        NetworkConfiguration::instance().connectToIngescape();

    QObject::connect(qGuiApp, &QGuiApplication::aboutToQuit, []() {
        qInfo() << "Application about to quit";
        NetworkConfiguration::instance().disconnectFromIngescape();
    });

    const QUrl url(QStringLiteral("qrc:/qml/main.qml"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
        &app, [url, &qmlInstrument](QObject *obj, const QUrl &objUrl) {
            if (url == objUrl)
            {
                if (!obj)
                    QCoreApplication::exit(-1);

                qmlInstrument.setRootObject(obj);
            }
        },
        Qt::QueuedConnection);
    engine.load(url);

    qInfo() << "Starting" << QGuiApplication::applicationName() << QGuiApplication::applicationVersion() << "with processID" << QGuiApplication::applicationPid();
    int exitCode = QGuiApplication::exec();
    qInfo() << "Quitting application with exit code" << exitCode;

    return exitCode;
}

