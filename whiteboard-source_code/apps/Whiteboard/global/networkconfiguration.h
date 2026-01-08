/*
 *  Whiteboard
 *
 *  Copyright © 2024 Ingenuity i/o. All rights reserved.
 *
 *  See license terms for the rights and conditions
 *  defined by copyright holders.
 *
 *  Contributors:
 *    Brandon Gutierrez <gutierrez@ingenuity.io>
 *
 */

#ifndef NETWORKCONFIGURATION_H
#define NETWORKCONFIGURATION_H

#include <QObject>
#include <QQmlEngine>
#include <QJSEngine>

#include "helpers/i2qmlpropertyhelpers.h"


#ifdef INGESCAPE_FROM_PRI
#include "ingescape.h"
#else
#include <ingescape/ingescape.h>
#endif


class Q_DECL_EXPORT NetworkConfiguration : public QObject
{
    Q_OBJECT

    I2_QT5_QML_READONLY_PROPERTY_WITH_CUSTOM_SETTER(QStringList, availableNetworkDevices)
    I2_QT5_QML_READONLY_PROPERTY_WITH_CUSTOM_SETTER(QStringList, availableNetworkDevicesPrettyPrinted)
    I2_QT5_QML_PROPERTY_WITH_CUSTOM_SETTER_AND_SIGNAL_VALUE(QString, currentNetworkDevice)
    I2_QT5_QML_PROPERTY_WITH_CUSTOM_SETTER_AND_SIGNAL_VALUE(QString, currentIpAddress)
    I2_QT5_QML_PROPERTY_WITH_CUSTOM_SETTER_AND_SIGNAL_VALUE(uint, currentPort)

    I2_QT5_QML_READONLY_PROPERTY_WITH_SIGNAL_VALUE(bool, isConnected)

public:
    static constexpr int MONITORING_TIMEOUT_MS = 500;

    NetworkConfiguration(NetworkConfiguration const&) = delete;
    NetworkConfiguration(NetworkConfiguration&&) = delete;
    NetworkConfiguration& operator=(NetworkConfiguration const&) = delete;
    NetworkConfiguration& operator=(NetworkConfiguration&&) = delete;

    static NetworkConfiguration& instance();
    static QObject* qmlSingleton(QQmlEngine* engine, QJSEngine* scriptEngine);

public Q_SLOTS:
    void updateAvailableNetworkDevices();
    bool networkDeviceIsAvailable(const QString& deviceName);
    QString getNetworkDeviceFriendlyName(const QString& deviceName, bool updateCacheIfNeeded = true);
    void updateNetworkDevicesFriendlyNamesCache();
    igs_result_t connectToIngescape();
    void disconnectFromIngescape(bool forceStop = false);
    void disconnectFromIngescapeWithoutStop();

Q_SIGNALS:
    void deviceNoMoreAvailable(const QString& device);
    void igsConnectionFailed();
    void openNetworkConfiguration();

private Q_SLOTS:
    void _startMonitoring(const QString& device, const int port) const;
    void _stopMonitoring() const;
    void _onDeviceNoMoreAvailable(const QString& device);
    void _updatePrettyPrintedList();

private:
    explicit NetworkConfiguration(QObject* parent = nullptr);
    QHash<QString, QString> _networkDevicesSystemNameToFriendlyName;
};

QML_DECLARE_TYPE(NetworkConfiguration)

#endif // NETWORKCONFIGURATION_H
